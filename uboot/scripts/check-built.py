#!/usr/bin/env python3
"""Inspect the actual ARM64 U-Boot, DTB and FIP; no device access."""
from pathlib import Path
import hashlib,json,lzma,struct,sys

def parse_fdt(blob):
    magic,total,os,ot,om,ver,last,cpu,ss,st=struct.unpack_from('>10I',blob)
    assert magic==0xd00dfeed and total<=len(blob) and os+st<=total and ot+ss<=total
    nodes={};stack=[];p=os
    while p<os+st:
        token=struct.unpack_from('>I',blob,p)[0];p+=4
        if token==1:
            end=blob.index(0,p,os+st);stack.append(blob[p:end].decode());p=(end+4)&~3
            name='/'+'/'.join(stack[1:]);assert name not in nodes;nodes[name]={}
        elif token==2:
            assert stack;stack.pop()
        elif token==3:
            length,noff=struct.unpack_from('>II',blob,p);p+=8
            assert stack and noff<ss and p+length<=os+st
            end=blob.index(0,ot+noff,ot+ss);name=blob[ot+noff:end].decode()
            nodes['/'+'/'.join(stack[1:])][name]=blob[p:p+length];p=(p+length+3)&~3
        elif token==4:pass
        elif token==9:
            assert not stack;return nodes
        else:raise AssertionError(f'Unknown FDT token {token}')
    raise AssertionError('FDT end missing')

def fip_entries(blob):
    assert struct.unpack_from('<I',blob)[0]==0xaa640001
    rows={}
    for p in range(16,len(blob),40):
        key,off,size,flags=struct.unpack_from('<16sQQQ',blob,p)
        if key==bytes(16):break
        assert key not in rows and off>=136 and off+size<=len(blob)
        rows[key.hex()]=(blob[off:off+size],off,flags)
    assert len(rows)==2
    return rows

def main(folder,original,out):
    files={}
    for name in ['u-boot.bin','u-boot.dtb','u-boot','resolved.config']:
        matches=[p for p in folder.rglob(name) if p.is_file()]
        assert len(matches)==1,(name,matches)
        files[name]=matches[0]
    binary=files['u-boot.bin'].read_bytes();dtb=files['u-boot.dtb'].read_bytes();elf=files['u-boot'].read_bytes()
    assert elf[:4]==b'\x7fELF' and elf[4:6]==b'\x02\x01'
    assert struct.unpack_from('<H',elf,18)[0]==183 and struct.unpack_from('<Q',elf,24)[0]==0x81e00000
    assert binary.find(dtb)>=0,'DTB not embedded in produced U-Boot binary'
    assert b'airoha-usb2-phy\0' in binary and b'xhci-mtk\0' in binary,'USB driver registrations missing'
    assert b'xswstock' in binary and b'RESTORE-STOCK' in binary and b'Restore original firmware from USB' in binary
    tree=parse_fdt(dtb)
    assert b'vnpt,xsw250ns-ubi' in tree['/']['compatible'].split(b'\0')
    memory=tree['/memory@80000000']['reg'];assert struct.unpack('>QQ',memory)==(0x80000000,0x20000000)
    roots=[]
    for i in range(2):
        address=0x1fab0000+0x20000*i;phy=address+0x10000
        usb=tree[f'/usb@{address:x}'];provider=tree[f'/phy@{phy:x}']
        assert usb['status']==b'okay\0' and usb['maximum-speed']==b'high-speed\0'
        assert usb['compatible'].startswith(b'airoha,an7581-xhci\0')
        assert struct.unpack('>IIII',usb['reg'][:16])==(0,address,0,0x3e00)
        handle,typ=struct.unpack('>II',usb['phys']);assert typ==3
        assert handle==int.from_bytes(provider['phandle'],'big')
        assert provider['compatible']==b'airoha,an7581-usb2-phy\0'
        assert int.from_bytes(provider['airoha,usb2-monitor-clk-sel'],'big')==i+1
        assert int.from_bytes(usb['mediatek,u3p-dis-msk'],'big')==1
        roots.append({'mac':hex(address),'phy':hex(phy),'usb2_only':True})
    partitions={props['label'].rstrip(b'\0').decode():props for path,props in tree.items() if '/partitions/' in path and 'label' in props}
    assert struct.unpack('>II',partitions['bl2']['reg'])==(0,0x20000)
    assert struct.unpack('>II',partitions['ubi']['reg'])==(0x20000,0xdda0000)
    assert struct.unpack('>II',partitions['reservearea']['reg'])==(0xddc0000,0x240000)
    layout=json.loads((Path(__file__).resolve().parents[1]/'backup-layout.json').read_text())
    for row in layout['files']:
        pattern=struct.pack('<QI',row['bytes'],row['offset'])+bytes.fromhex(row['sha256'])
        assert pattern in binary,row['file']+' exact size/offset/SHA table missing from production binary'
    assert bytes.fromhex(layout['live_eeprom_sha256']) in binary
    fips=list(folder.rglob('*usb-stock-bl31-uboot.fip'));assert len(fips)==1
    fip=fips[0].read_bytes();old=original.read_bytes()
    assert hashlib.sha256(old).hexdigest()=='44d225b61b940e34a9a8490063688071e01f699af13cded8cc76fa19ed738779'
    a=fip_entries(fip);b=fip_entries(old)
    bl31='47d4086d4cfe98469b952950cbbd5a00';bl33='d6d0eea7fcead54b97829934f234b6e4'
    assert fip[:16]==old[:16] and a[bl31][0]==b[bl31][0] and a[bl31][2]==b[bl31][2]
    assert lzma.decompress(a[bl33][0])==binary and a[bl33][2]==b[bl33][2]
    old_binary=lzma.decompress(b[bl33][0])
    dtpos=old_binary.rfind(b'\xd0\x0d\xfe\xed');assert dtpos>=0
    original_tree=parse_fdt(old_binary[dtpos:])
    for path,props in original_tree.items():
        assert path in tree and tree[path]==props,('Original board DT changed',path)
    assert set(tree)-set(original_tree)=={'/usb@1fab0000','/usb@1fad0000','/phy@1fac0000','/phy@1fae0000'}
    handles={int.from_bytes(v['phandle'],'big'):v for v in tree.values() if 'phandle' in v}
    references=0
    for props in tree.values():
        for prop,cells in [('clocks','#clock-cells'),('phys','#phy-cells'),('resets','#reset-cells'),('gpios','#gpio-cells')]:
            if prop not in props:continue
            raw=props[prop];assert len(raw)%4==0
            values=struct.unpack('>'+str(len(raw)//4)+'I',raw);pos=0
            while pos<len(values):
                handle=values[pos];assert handle in handles,(prop,handle)
                provider=handles[handle];assert cells in provider,(prop,cells)
                count=int.from_bytes(provider[cells],'big');pos+=1+count
                assert pos<=len(values);references+=1
    assert a[bl31][1]+len(a[bl31][0])<=a[bl33][1]
    report={'fip':fips[0].name,'sha256':hashlib.sha256(fip).hexdigest(),'bytes':len(fip),
            'arm64_elf_entry':'0x81e00000','board':'vnpt,xsw250ns-ubi','ram_bytes':0x20000000,
            'usb_dtb':roots,'stock_file_metadata_verified_in_binary':12,
            'original_board_dt_nodes_preserved_exactly':len(original_tree),
            'only_four_usb_nodes_added':True,'numeric_clock_phy_reset_gpio_references_verified':references,
            'live_eeprom_hash_gate_present':True,'retained_bl31_compressed_sha256':hashlib.sha256(a[bl31][0]).hexdigest(),
            'new_bl33_matches_compiled_uboot_bin':True,
            'compiled_files':[{'name':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files.values()],
            'physical_usb_boot_or_flash_tested':False,'scope':'static artifact checks only; host command tests are separate'}
    out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]))
