#!/usr/bin/env python3
"""Replace BL33 while retaining the exact supplied compressed BL31 payload."""
from pathlib import Path
import hashlib,json,lzma,struct,sys

original=Path(sys.argv[1]).read_bytes()
assert hashlib.sha256(original).hexdigest()=='44d225b61b940e34a9a8490063688071e01f699af13cded8cc76fa19ed738779'
assert struct.unpack_from('<I',original)[0]==0xaa640001
entries=[]
for pos in range(16,len(original),40):
    uuid,off,size,flags=struct.unpack_from('<16sQQQ',original,pos)
    if uuid==bytes(16):break
    assert off+size<=len(original)
    entries.append((uuid,original[off:off+size],flags))
assert [e[0].hex() for e in entries]==['47d4086d4cfe98469b952950cbbd5a00','d6d0eea7fcead54b97829934f234b6e4']
uboot=Path(sys.argv[2]).read_bytes()
old=entries[1][1]
prop=old[0];lc=prop%9;prop//=9;lp=prop%5;pb=prop//5
filters=[{'id':lzma.FILTER_LZMA1,'dict_size':int.from_bytes(old[1:5],'little'),'lc':lc,'lp':lp,'pb':pb}]
compressed=lzma.compress(uboot,format=lzma.FORMAT_ALONE,filters=filters)
assert lzma.decompress(compressed)==uboot
entries[1]=(entries[1][0],compressed,entries[1][2])
offset=16+(len(entries)+1)*40
table=b'';payload=b''
for uuid,data,flags in entries:
    table+=struct.pack('<16sQQQ',uuid,offset,len(data),flags)
    payload+=data;offset+=len(data)
table+=struct.pack('<16sQQQ',bytes(16),offset,0,0)
result=original[:16]+table+payload
assert len(result)==offset and len(result)<0x100000
out=Path(sys.argv[3]);out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(result)
manifest={'artifact':out.name,'bytes':len(result),'sha256':hashlib.sha256(result).hexdigest(),
          'original_fip_sha256':hashlib.sha256(original).hexdigest(),
          'retained_compressed_bl31_sha256':hashlib.sha256(entries[0][1]).hexdigest(),
          'new_uboot_bin_sha256':hashlib.sha256(uboot).hexdigest(),
          'new_bl33_compression':'LZMA_ALONE, original dictionary/lc/lp/pb',
          'preloader_changed':False,'physical_boot_usb_or_flash_tested':False}
out.with_suffix('.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
