"""Recovery regression tests: embedded gzip CPIO and reserved-memory boundaries."""
from pathlib import Path
import gzip
import importlib.util
import stat
import struct

script=Path(__file__).resolve().parents[1]/'scripts/verify-fit.py'
spec=importlib.util.spec_from_file_location('fit',script)
fit=importlib.util.module_from_spec(spec)
spec.loader.exec_module(fit)

def entry(name,data=b'',uid=0):
    name=name.encode()+b'\0'
    values=[1,stat.S_IFREG|0o755,uid,0,1,0,len(data),0,0,0,0,len(name),0]
    header=b'070701'+b''.join(('%08x'%value).encode() for value in values)+name
    return header+b'\0'*((-len(header))%4)+data+b'\0'*((-len(data))%4)

archive=entry('init',b'init')+entry('bin/busybox',b'busybox')+entry('TRAILER!!!')
assert fit.has_recovery_cpio(b'kernel padding'+archive+b'trailing kernel data')==2
packed=gzip.compress(archive,mtime=0)
wrapped=b'ARM64 kernel data'+packed+b'following section'
assert fit.has_recovery_cpio(wrapped)==2
assert fit.recovery_entries(wrapped)['bin/busybox']['data']==b'busybox'
assert fit.has_recovery_cpio(b'prefix'+packed[:-8])==0,'truncated gzip was accepted'
bad=entry('init',b'init',uid=1001)+entry('bin/busybox',b'busybox')+entry('TRAILER!!!')
try:
    fit.has_recovery_cpio(gzip.compress(bad,mtime=0))
except AssertionError:
    pass
else:
    raise AssertionError('non-root initramfs was accepted')

dtb={'/memory@80000000':{'device_type':b'memory\0','reg':struct.pack('>QQ',0x80000000,0x20000000)},
     '/reserved-memory/npu@84000000':{'reg':struct.pack('>QQ',0x84000000,0xa00000)}}
assert fit.verify_kernel_memory(0x80200000,0x3e00000,dtb)['end']=='0x84000000'
for load,size in [(0x80200000,0x3e00001),(0xa0000000,1)]:
    try:
        fit.verify_kernel_memory(load,size,dtb)
    except AssertionError:
        pass
    else:
        raise AssertionError('unsafe kernel placement was accepted')
print('PASS: raw/gzip CPIO, gzip integrity, root ownership and reserved-memory boundaries')
