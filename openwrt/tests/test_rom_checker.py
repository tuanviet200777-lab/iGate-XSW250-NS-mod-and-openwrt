"""Regression: a successful overlay install must not certify the lower image.
Path-mapped MSYS shell fixtures only; fw_printenv and mount data are mocked.
"""
from pathlib import Path
import json, os, re, subprocess, uuid, shutil
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(ROOT))
from test_reader import shell_path

def run():
    shell=os.environ.get('XSW_TEST_SHELL') or shutil.which('ash') or shutil.which('sh') or 'C:/msys64/usr/bin/bash.exe'
    cases=[('legacy-false-positive','legacy',False,False,False,0),
           ('reject-overlay-only','new',False,False,False,1),
           ('accept-correct-rom','new',True,False,False,0),
           ('reject-wrong-rom-hook','new',True,True,False,1),
           ('accept-preserved-regular-conffile','new',True,False,False,0),
           ('reject-missing-runtime-reader','new',True,False,True,1)]
    results=[]
    old_hook=(HERE/'fixtures/r3/04_xsw250ns_ubootenv').read_bytes()
    new_hook=(ROOT/'files/etc/board.d/04_xsw250ns_ubootenv').read_bytes()
    for name,kind,fixed_rom,wrong_hook,missing_reader,wanted in cases:
        root=ROOT/'test-results/checker-fixtures'/uuid.uuid4().hex[:12]
        assert root.resolve().is_relative_to(ROOT.resolve())
        for d in ['rom/etc/board.d','etc','tmp/sysinfo','proc','bin']:(root/d).mkdir(parents=True,exist_ok=True)
        rp=shell_path(root)
        (root/'tmp/sysinfo/board_name').write_bytes(b'vnpt,xsw250ns-ubi\n')
        (root/'etc/xsw250ns-build-id').write_bytes(b'xsw250ns-hotfix-20261029-r3-nand1\n' if kind == 'legacy' else b'xsw250ns-20261104-r4-diag-nand1\n')
        (root/'rom/etc/xsw250ns-build-id').write_bytes(b'xsw250ns-20261104-r4-diag-nand1\n' if fixed_rom else b'xsw250ns-hotfix-20261029-r3\n')
        (root/'rom/etc/board.d/04_xsw250ns_ubootenv').write_bytes(new_hook if fixed_rom and not wrong_hook else old_hook)
        (root/'tmp/xsw250ns-fw_env.config').write_bytes(b'/dev/ubi0_0 0x0 0x1f000 0x1f000 1\n/dev/ubi0_1 0x0 0x1f000 0x1f000 1\n')
        (root/'proc/mounts').write_bytes(b'ubi0:rootfs_data /overlay ubifs rw,noatime 0 0\n/dev/fit0 /rom squashfs ro 0 0\n')
        mock=root/'bin/fw_printenv';mock.write_bytes(b'#!/bin/sh\nexit 0\n')
        env=os.environ.copy();env['PATH']=str(root/'bin')+os.pathsep+('C:/msys64/usr/bin;' if os.name == 'nt' else '')+env.get('PATH','');env['MSYS']='winsymlinks:sys'
        setup=['chmod 755 "$1"','ln -s "$2" "$3"','ln -s "$2" "$4"']
        subprocess.run([shell,'-c','; '.join(setup),'fixture',shell_path(mock),rp+'/tmp/xsw250ns-fw_env.config',rp+'/etc/fw_env.config',rp+'/rom/etc/fw_env.config'],env=env,check=True,capture_output=True)
        if name=='accept-preserved-regular-conffile':
            subprocess.run([shell,'-c','rm "$1" && cp "$2" "$1"','fixture',rp+'/etc/fw_env.config',rp+'/tmp/xsw250ns-fw_env.config'],env=env,check=True,capture_output=True)
        if missing_reader:(root/'tmp/xsw250ns-fw_env.config').unlink()
        source=(HERE/'legacy-check-nand-fix.sh' if kind=='legacy' else ROOT/'scripts/check-nand-fix.sh').read_text()
        source=re.sub(r'(?<![A-Za-z0-9_$}])/(rom|etc|tmp|proc|var)/',lambda m:rp+m.group(),source)
        target=root/'check.sh';target.write_text(source,newline='\n')
        p=subprocess.run([shell,shell_path(target)],env=env,text=True,capture_output=True)
        results.append({'case':name,'expected_exit':wanted,'actual_exit':p.returncode,'passed':p.returncode==wanted,'stdout':p.stdout,'stderr':p.stderr})
    env=os.environ.copy();env['PATH']=('C:/msys64/usr/bin;' if os.name == 'nt' else '')+env.get('PATH','')
    for path in [HERE/'fixtures/withdrawn-installer.sh',ROOT/'scripts/check-nand-fix.sh',ROOT/'files/etc/board.d/04_xsw250ns_ubootenv']:
        subprocess.run([shell,'-n',shell_path(path)],env=env,check=True,capture_output=True)
    disabled=subprocess.run([shell,shell_path(HERE/'fixtures/withdrawn-installer.sh')],env=env,text=True,capture_output=True)
    results.append({'case':'withdrawn-installer-stops-before-writing','passed':disabled.returncode==1 and 'DUNG:' in disabled.stderr,'actual_exit':disabled.returncode})
    (ROOT/'test-results/rom-checker-results.json').write_text(json.dumps(results,indent=2)+'\n',newline='\n')
    assert all(row['passed'] for row in results),results
    return results

if __name__=='__main__':print(json.dumps(run(),indent=2))
