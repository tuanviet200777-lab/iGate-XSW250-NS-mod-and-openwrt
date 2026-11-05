#!/usr/bin/env python3
"""Validate the device-bound backup before creating its USB directory."""
from pathlib import Path
import argparse,hashlib,json,zipfile

parser=argparse.ArgumentParser()
parser.add_argument('backup',type=Path,help='Original nandback2.zip or directory of extracted MTD files')
parser.add_argument('destination',type=Path,help='USB root or a staging directory; never formats a drive')
args=parser.parse_args()
layout=json.loads((Path(__file__).resolve().parents[1]/'backup-layout.json').read_text())
rows=layout['files'];expected={r['file']:r for r in rows}
if args.backup.is_dir():
    data={name:(args.backup/name).read_bytes() for name in expected}
else:
    assert hashlib.sha256(args.backup.read_bytes()).hexdigest()==layout['backup_archive_sha256'],'Wrong backup archive'
    with zipfile.ZipFile(args.backup) as z:
        assert z.testzip() is None,'ZIP CRC failure'
        members={}
        for entry in z.infolist():
            if entry.is_dir():continue
            name=Path(entry.filename).name
            assert name in expected and name not in members,'Unexpected/duplicate file'
            assert entry.file_size==expected[name]['bytes'],'Wrong file size'
            members[name]=z.read(entry)
        data=members
assert set(data)==set(expected),'Missing backup file'
for name,row in expected.items():
    assert len(data[name])==row['bytes'] and hashlib.sha256(data[name]).hexdigest()==row['sha256'],name+' mismatch'
for sub,whole in [(2,4),(3,4),(5,7),(6,7)]:
    start=rows[sub]['offset']-rows[whole]['offset']
    assert data[rows[sub]['file']]==data[rows[whole]['file']][start:start+rows[sub]['bytes']]
dest=args.destination/'XSW250NS-STOCK'
dest.mkdir(parents=True,exist_ok=True)
for name,content in data.items():
    output=dest/name
    if output.exists():assert output.read_bytes()==content,'Refuse to replace different file: '+str(output)
    else:output.write_bytes(content)
(dest/'SHA256SUMS').write_text(''.join(r['sha256']+'  '+r['file']+'\n' for r in rows))
print(f'Verified and prepared all 12 original MTD files at {dest}. No formatting or flash writes.')
