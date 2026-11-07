#!/usr/bin/env python3
"""Create public, non-device fixture bytes for host API fault injection."""
from pathlib import Path
import hashlib,json,sys
source=Path(__file__).resolve().parents[1]
layout=json.loads((source/'backup-layout.json').read_text())
dest=Path(sys.argv[1]);dest.mkdir(parents=True,exist_ok=True)
rows=layout['files'];data={}
for i in layout['write_order']:
    data[i]=hashlib.shake_256(f'SYNTHETIC-TEST-ONLY-{i}'.encode()).digest(rows[i]['bytes'])
for sub,whole in [(2,4),(3,4),(5,7),(6,7)]:
    start=rows[sub]['offset']-rows[whole]['offset']
    data[sub]=data[whole][start:start+rows[sub]['bytes']]
header='/* Synthetic test fingerprints, never used in a production U-Boot. */\n'
header+='static const struct stock_file stock_files[] = {\n'
for i,row in enumerate(rows):
    (dest/row['file']).write_bytes(data[i])
    digest=hashlib.sha256(data[i]).digest()
    header+=' {"%s",0x%x,0x%x,{%s}},\n'%(row['file'],len(data[i]),row['offset'],','.join('0x%02x'%v for v in digest))
header+='};\nstatic const u8 stock_eeprom_sha[32] = {'+','.join('0x%02x'%v for v in hashlib.sha256(data[11][0x4c000:0x4d000]).digest())+'};\n'
Path(sys.argv[2]).write_text(header)
print('Generated synthetic backup fixture; no actual router data used')
