#!/usr/bin/env python3
"""Prepare the checksum-pinned U-Boot source and apply the board overlay."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,tarfile,urllib.request

SOURCE=Path(__file__).resolve().parents[1]
spec=json.loads((SOURCE/'sources.json').read_text())
root=Path(sys.argv[1]).resolve()
assert not root.exists(),f'Refuse to replace existing build directory: {root}'
root.parent.mkdir(parents=True,exist_ok=True)
archive=root.parent/'u-boot-2026.07.tar.bz2'
if not archive.exists():urllib.request.urlretrieve(spec['archive_url'],archive)
assert hashlib.sha256(archive.read_bytes()).hexdigest()==spec['archive_sha256'],'U-Boot source checksum mismatch'
with tarfile.open(archive) as tar:
    tar.extractall(root.parent,filter='data')
unpacked=root.parent/'u-boot-2026.07'
assert unpacked.exists()
unpacked.rename(root)
cache=root.parent/'xsw250ns-uboot-patches'
cache.mkdir(exist_ok=True)
for entry in spec['patches']:
    file=cache/entry['path']
    if not file.exists():
        url=f"https://raw.githubusercontent.com/tuanviet200777-lab/immortalwrt/{spec['openwrt_commit']}/package/boot/uboot-airoha/patches/{entry['path']}"
        urllib.request.urlretrieve(url,file)
    data=file.read_bytes()
    blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
    assert blob==entry['git_blob'],entry['path']
    subprocess.run(['patch','-p1','--batch','--forward','-i',str(file)],cwd=root,check=True)
for file in (SOURCE/'overlay').rglob('*'):
    if file.is_file():
        destination=root/file.relative_to(SOURCE/'overlay')
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(file,destination)
def append(relative,content):
    with (root/relative).open('a') as f:f.write('\n'+content+'\n')
append('cmd/Makefile','obj-$(CONFIG_CMD_XSWSTOCK) += xswstock.o')
append('cmd/Kconfig','''config CMD_XSWSTOCK
    bool "XSW250NS device-bound USB stock rollback"
    depends on TARGET_AN7581
    depends on USB_STORAGE && FS_FAT && CMD_USB && CMD_MTD && CMD_UBI
    depends on SHA256 && LMB && EVENT
''')
append('drivers/phy/Makefile','obj-$(CONFIG_PHY_AIROHA_USB2) += phy-airoha-usb2.o')
append('drivers/phy/Kconfig','''config PHY_AIROHA_USB2
    bool "Airoha AN7581 USB2 PHY"
    depends on TARGET_AN7581
    select GENERIC_PHY
''')
file=root/'drivers/usb/host/xhci-mtk.c'
content=file.read_text()
old='ret = clk_get_bulk(dev, &mtk->clks);\n\tif (ret) {'
assert old in content
content=content.replace(old,'''ret = clk_get_bulk(dev, &mtk->clks);
	/* AN7581 has no gated USB clock property in its Linux binding. */
	if (ret == -ENOENT && ofnode_device_is_compatible(dev_ofnode(dev),
						 "airoha,an7581-xhci"))
		ret = 0;
	if (ret) {''')
for member in ['vusb33_supply','vbus_supply']:
    old=f'ret = regulator_set_enable(mtk->{member}, true);'
    assert old in content
    content=content.replace(old,f'ret = mtk->{member} ? regulator_set_enable(mtk->{member}, true) : 0;')
    old=f'regulator_set_enable(mtk->{member}, false);'
    assert old in content
    content=content.replace(old,f'if (mtk->{member})\n\t\tregulator_set_enable(mtk->{member}, false);')
file.write_text(content)
(root/'xsw250ns-source-provenance.json').write_text(json.dumps(spec,indent=2)+'\n')
print(f'Prepared {root}; source and all {len(spec["patches"])} base patches verified')
