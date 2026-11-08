"""Execute the production shell hook with filesystem/device discovery fixtures.
Device-node checks are mapped to fixture regular files; no NAND is emulated.
"""
from pathlib import Path
import json, os, subprocess, uuid, shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SHELL = os.environ.get("XSW_TEST_SHELL") or shutil.which("ash") or shutil.which("sh") or "C:/msys64/usr/bin/bash.exe"

def shell_path(path):
    text = str(path.resolve()).replace('\\', '/')
    return '/' + text[0].lower() + text[2:] if os.name == "nt" else text

def mapped(source):
    source = source.replace('. /lib/functions.sh', '. "$FIXTURE/functions.sh"')
    source = source.replace('. /lib/upgrade/nand.sh', '. "$FIXTURE/nand.sh"')
    source = source.replace('. /lib/uboot-envtools.sh', '. "$FIXTURE/envtools.sh"')
    source = source.replace('"/dev/', '"$FIXTURE/dev/')
    source = source.replace('"/sys/', '"$FIXTURE/sys/')
    source = source.replace('/tmp/xsw250ns', '$FIXTURE/tmp/xsw250ns')
    source = source.replace('/etc/fw_env.config', '$FIXTURE/etc/fw_env.config')
    source = source.replace('/etc/config/ubootenv', '$FIXTURE/etc/config/ubootenv')
    # Windows cannot create Linux UBI character devices; discovery is mocked.
    source = source.replace('[ -c ', '[ -f ').replace('&& [ -c ', '&& [ -f ')
    return source

def run():
    new = (ROOT/'files/etc/board.d/04_xsw250ns_ubootenv').read_text()
    old = (HERE/'fixtures/r3/04_xsw250ns_ubootenv').read_text()
    rows = []
    run_root = ROOT/'test-results/reader-fixtures'/uuid.uuid4().hex[:12]
    cases = [
        ('old-readonly-regression', old, 'vnpt,xsw250ns-ubi', 'ubi0', 'ubi0_0', 'ubi0_1', '126976', False),
        ('pre-overlay-readonly', new, 'vnpt,xsw250ns-ubi', 'ubi0', 'ubi0_0', 'ubi0_1', '126976', True),
        ('discovered-not-hardcoded-ids', new, 'vnpt,xsw250ns-ubi', 'ubi2', 'ubi2_9', 'ubi2_4', '126976', True),
        ('missing-second-volume', new, 'vnpt,xsw250ns-ubi', 'ubi0', 'ubi0_0', '', '126976', False),
        ('same-volume-rejected', new, 'vnpt,xsw250ns-ubi', 'ubi0', 'ubi0_0', 'ubi0_0', '126976', False),
        ('wrong-leb-size-rejected', new, 'vnpt,xsw250ns-ubi', 'ubi0', 'ubi0_0', 'ubi0_1', '129024', False),
        ('malformed-id-rejected', new, 'vnpt,xsw250ns-ubi', 'ubi0x', 'ubi0x_0', 'ubi0x_1', '126976', False),
        ('different-board-untouched', new, 'other,board', 'ubi0', 'ubi0_0', 'ubi0_1', '126976', False),
    ]
    for name, source, board, ubi, first, second, size, want_reader in cases:
        root = run_root/name
        for directory in ['dev', 'tmp', 'etc/config']:
            (root/directory).mkdir(parents=True, exist_ok=True)
        for volume in set([first,second]) - {''}:
            (root/'dev'/volume).touch()
            node = root/'sys/class/ubi'/volume
            node.mkdir(parents=True,exist_ok=True)
            (node/'usable_eb_size').write_text(size+'\n',newline='\n')
        (root/'functions.sh').write_text('board_name() { printf "%s\\n" "$TEST_BOARD"; }\n',newline='\n')
        (root/'nand.sh').write_text('nand_find_ubi() { [ -n "$TEST_UBI" ] && printf "%s\\n" "$TEST_UBI"; }\nnand_find_volume() { case "$2" in ubootenv) v="$TEST_ENV1";; ubootenv2) v="$TEST_ENV2";; *) return 1;; esac; [ -n "$v" ] && printf "%s\\n" "$v"; }\n',newline='\n')
        (root/'envtools.sh').write_text('ubootenv_add_ubi_default() { uci; }\nconfig_load() { uci; }\nconfig_foreach() { uci; }\n',newline='\n')
        prelude = 'touch() { echo "touch: /etc/config/ubootenv: Read-only file system" >&2; return 1; }\nuci() { echo "uci: Entry not found" >&2; return 1; }\n'
        script = root/'hook.sh'
        script.write_text(prelude+mapped(source),encoding='utf-8',newline='\n')
        env = os.environ.copy()
        env.update({'PATH':('C:/msys64/usr/bin;' if os.name == 'nt' else '')+env.get('PATH',''), 'FIXTURE':shell_path(root), 'TEST_BOARD':board, 'TEST_UBI':ubi, 'TEST_ENV1':first, 'TEST_ENV2':second})
        proc = subprocess.run([SHELL, shell_path(script)],env=env,text=True,capture_output=True)
        reader = root/'tmp/xsw250ns-fw_env.config'
        actual = reader.read_text() if reader.is_file() else None
        expected = f'/dev/{first} 0x0 0x1f000 0x1f000 1\n/dev/{second} 0x0 0x1f000 0x1f000 1\n'
        if name.startswith('old-'):
            passed = actual is None and 'Read-only file system' in proc.stderr and 'uci: Entry not found' in proc.stderr
        elif want_reader:
            passed = proc.returncode == 0 and actual == expected and not proc.stderr
            again = subprocess.run([SHELL,shell_path(script)],env=env,text=True,capture_output=True)
            passed = passed and again.returncode == 0 and reader.read_text() == expected and not again.stderr
            passed = passed and not any(p.is_file() or p.is_symlink() for p in (root/'etc').rglob('*'))
        else:
            passed = actual is None and (proc.returncode == 0 if board != 'vnpt,xsw250ns-ubi' else proc.returncode != 0)
        rows.append({'case':name,'passed':passed,'exit_code':proc.returncode,'stderr':proc.stderr})
    (ROOT/'test-results/reader-tests.json').write_text(json.dumps(rows,indent=2)+'\n')
    assert all(x['passed'] for x in rows), rows
    return rows

if __name__ == '__main__':
    print(json.dumps(run(),indent=2))
