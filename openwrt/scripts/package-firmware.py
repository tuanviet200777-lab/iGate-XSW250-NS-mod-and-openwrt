#!/usr/bin/env python3
"""Verify native images, then package exactly sysupgrade and recovery."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile

p=argparse.ArgumentParser()
p.add_argument('images',type=Path)
p.add_argument('output',type=Path)
a=p.parse_args()
images=[]
for kind in ['sysupgrade','recovery']:
    found=list(a.images.glob('*xsw250ns*'+kind+'.itb'))
    if len(found)!=1:
        raise SystemExit('Expected exactly one '+kind+' image')
    if not found[0].is_file() or found[0].is_symlink():
        raise SystemExit('Image must be a regular file')
    images.append(found[0])
if a.output.exists():
    raise SystemExit('Refuse to overwrite existing archive')
a.output.parent.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(prefix='xsw-image-verify-') as tmp:
    subprocess.run([sys.executable,str(Path(__file__).with_name('check-built-images.py')),
                    str(a.images),tmp],check=True)
    manifest=json.loads((Path(tmp)/'image-verification.json').read_text())
    manifest['files']=[{'name':f.name,'bytes':f.stat().st_size,
                        'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in images]
    # Create only after verification. Never label an unverified binary release-ready.
    with zipfile.ZipFile(a.output,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for f in images:z.write(f,arcname=f.name)
    with zipfile.ZipFile(a.output) as z:
        if z.testzip() is not None or len(z.namelist())!=2:
            raise RuntimeError('Archive validation failed')
        for row in manifest['files']:
            if hashlib.sha256(z.read(row['name'])).hexdigest()!=row['sha256']:
                raise RuntimeError('Packaged image checksum mismatch')
    manifest['zip_sha256']=hashlib.sha256(a.output.read_bytes()).hexdigest()
    a.output.with_suffix('.verification.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(a.output)
