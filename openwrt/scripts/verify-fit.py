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
def _scan_newc(raw):
    start = raw.find(b'070701')
    while start >= 0:
        pos = start; entries = {}; complete = False
        try:
            while raw[pos:pos+6] in (b'070701', b'070702'):
                fields = [int(raw[pos+6+i*8:pos+14+i*8], 16) for i in range(13)]
                length, namesize = fields[6], fields[11]
                assert 0 < namesize <= 4096
                end = pos + 110 + namesize
                assert raw[end-1] == 0
                name = raw[pos+110:end-1].decode().removeprefix('./').lstrip('/')
                if name == 'TRAILER!!!':
                    complete = True
                    break
                data = start + ((end-start+3) & ~3)
                assert data+length <= len(raw)
                entries[name] = {'data': raw[data:data+length], 'mode': fields[1],
                                 'uid': fields[2], 'gid': fields[3]}
                pos = start + ((data+length-start+3) & ~3)
        except (AssertionError, ValueError, UnicodeDecodeError, IndexError):
            complete = False
        if complete and {'init', 'bin/busybox'} <= entries.keys():
            for name in ['init', 'bin/busybox']:
                assert (entries[name]['uid'], entries[name]['gid']) == (0, 0), 'initramfs ownership is not root'
            assert entries['bin/busybox']['mode'] & 0o111, 'busybox is not executable'
            return entries
        start = raw.find(b'070701', start+1)
    return {}

def recovery_entries(raw):
    entries = _scan_newc(raw)
    if entries:
        return entries
    # Gzip-compress the embedded initramfs to keep the ARM64 Image below the
    # board's NPU reservation. Ignore unrelated gzip-looking bytes in code.
    start = raw.find(b'\x1f\x8b\x08')
    while start >= 0:
        try:
            decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
            archive = decoder.decompress(raw[start:], 256 * 1024 * 1024)
            if decoder.eof:
                entries = _scan_newc(archive)
                if entries:
                    return entries
        except zlib.error:
            pass
        start = raw.find(b'\x1f\x8b\x08', start+1)
    return {}

def has_recovery_cpio(raw):
    return len(recovery_entries(raw))

def verify_kernel_memory(load, size, dtb):
    assert size > 0, 'ARM64 image_size is missing'
    end = load + size
    ram = [struct.unpack('>QQ', props['reg']) for name, props in dtb.items()
           if props.get('device_type') == b'memory\0' and len(props.get('reg', b'')) == 16]
    assert any(base <= load and end <= base+length for base, length in ram), 'kernel does not fit usable RAM'
    for name, props in dtb.items():
        if not name.startswith('/reserved-memory/') or 'reg' not in props or props.get('status') == b'disabled\0':
            continue
        assert len(props['reg']) % 16 == 0
        for offset in range(0, len(props['reg']), 16):
            base, length = struct.unpack_from('>QQ', props['reg'], offset)
            assert not (load < base+length and base < end), (
                'kernel overlaps reserved RAM', name, hex(load), hex(end))
    return {'load': hex(load), 'end': hex(end), 'image_size': size}

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
    memory = verify_kernel_memory(number(kernel['load']), struct.unpack_from('<Q', raw, 16)[0], dtb)
    print(path.name+': kernel RAM placement verified '+str(memory))
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
