#!/usr/bin/env python3
"""Check FIT payload hashes and board identity without running target code."""
import gzip, hashlib, lzma, struct, sys, zlib
from pathlib import Path

def parse(blob):
    magic,total,off_struct,off_strings,_,_,_,_,size_strings,size_struct=struct.unpack_from('>10I',blob)
    assert magic==0xd00dfeed and total<=len(blob), 'invalid FDT header'
    strings=blob[off_strings:off_strings+size_strings]
    pos=off_struct; stack=[]; nodes={}
    while pos<off_struct+size_struct:
        token=struct.unpack_from('>I',blob,pos)[0];pos+=4
        if token==1:
            end=blob.index(0,pos);name=blob[pos:end].decode();pos=(end+4)&~3
            stack.append(name);nodes['/'+ '/'.join(stack[1:])]={}
        elif token==2:stack.pop()
        elif token==3:
            length,nameoff=struct.unpack_from('>II',blob,pos);pos+=8
            end=strings.index(0,nameoff);name=strings[nameoff:end].decode()
            nodes['/'+'/'.join(stack[1:])][name]=blob[pos:pos+length];pos=(pos+length+3)&~3
        elif token==4:pass
        elif token==9:break
        else:raise AssertionError(('unknown FDT token',token,pos))
    return nodes,total

def text(value):return value.rstrip(b'\0').decode()
def number(value):return int.from_bytes(value,'big')
def has_recovery_cpio(raw):
    # This build explicitly selects uncompressed embedded initramfs.
    candidate=raw.find(b'070701')
    while candidate>=0:
        pos=candidate;names=set();owners={}
        try:
            while raw[pos:pos+6] in (b'070701',b'070702'):
                fields=[int(raw[pos+6+i*8:pos+14+i*8],16) for i in range(13)]
                filesize,namesize=fields[6],fields[11]
                assert 0<namesize<=4096 and filesize<=len(raw)
                start=pos+110;end=start+namesize
                assert raw[end-1]==0
                name=raw[start:end-1].decode().lstrip('./')
                if name=='TRAILER!!!':break
                names.add(name);owners[name]=(fields[2],fields[3],fields[1])
                data=candidate+((end-candidate+3)&~3)
                assert data+filesize<=len(raw)
                pos=candidate+((data+filesize-candidate+3)&~3)
            if {'init','bin/busybox'}<=names:
                assert owners['init'][:2]==(0,0) and owners['bin/busybox'][:2]==(0,0),'initramfs ownership is not root'
                assert owners['bin/busybox'][2]&0o111,'busybox is not executable'
                return len(names)
        except (AssertionError,ValueError,UnicodeDecodeError,IndexError):pass
        candidate=raw.find(b'070701',candidate+1)
    return 0

def verify(path):
    blob=path.read_bytes();nodes,total=parse(blob)
    assert text(nodes['/configurations']['default'])=='config-1'
    config=nodes['/configurations/config-1'];checked=0;types={};payloads={}
    for node,props in nodes.items():
        if not node.startswith('/images/') or node.count('/')!=2:continue
        if 'data' in props:data=props['data']
        else:
            pos=number(props['data-position']) if 'data-position' in props else ((total+3)&~3)+number(props['data-offset'])
            size=number(props['data-size']);assert pos+size<=len(blob)
            data=blob[pos:pos+size]
        count=0
        for hashnode,hashprops in nodes.items():
            if hashnode.rsplit('/',1)[0]!=node or 'algo' not in hashprops:continue
            algo=text(hashprops['algo'])
            actual=struct.pack('>I',zlib.crc32(data)&0xffffffff) if algo=='crc32' else hashlib.new(algo,data).digest()
            assert actual==hashprops['value'],(path.name,node,algo,'hash mismatch')
            count+=1;checked+=1
        assert count>=1,(node,'no hashes checked')
        kind=text(props['type']);types[kind]=types.get(kind,0)+1;payloads[kind]=(props,data)
        print(path.name,node,len(data),'bytes:',count,'hashes verified')
    kernel,raw=payloads['kernel']
    assert text(kernel['arch'])=='arm64'
    assert number(kernel['load'])==0x80200000 and number(kernel['entry'])==0x80200000
    compression=text(kernel['compression'])
    if compression=='gzip':raw=gzip.decompress(raw)
    elif compression=='lzma':raw=lzma.decompress(raw)
    else:assert compression=='none',compression
    assert raw[0x38:0x3c]==b'ARMd','not an ARM64 Linux Image'
    dtb=parse(payloads['flat_dt'][1])[0]
    assert dtb['/']['compatible'].split(b'\0')[0]==b'vnpt,xsw250ns-ubi'
    if 'sysupgrade' in path.name:
        assert payloads['filesystem'][1][:4]==b'hsqs','missing SquashFS payload'
        assert len(blob)<0xdda0000
    elif 'recovery' in path.name:
        assert len(blob)%(128*1024)==0,'recovery must be erase-block padded'
        count=has_recovery_cpio(raw)
        assert count>0,'recovery is missing embedded init/busybox CPIO'
        print(path.name+': embedded recovery CPIO verified, '+str(count)+' entries')
    print(path.name+': FIT config, board DTB, ARM64 kernel and payload integrity verified; SHA256 '+hashlib.sha256(blob).hexdigest())
if __name__ == '__main__':
    for arg in sys.argv[1:]:
        verify(Path(arg))
