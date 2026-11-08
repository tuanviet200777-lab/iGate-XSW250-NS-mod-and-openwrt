#!/usr/bin/env python3
"""Prepare the checksum-pinned U-Boot source and apply the board overlay."""

if not __debug__:
    raise RuntimeError("Refusing optimized Python: integrity checks required")
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,tarfile,urllib.request

SOURCE=Path(__file__).resolve().parents[1]
spec=json.loads((SOURCE/'sources.json').read_text())
root=Path(sys.argv[1]).resolve()
assert not root.exists(),f'Refuse to replace existing build directory: {root}'
root.parent.mkdir(parents=True,exist_ok=True)
archive=root.parent/'u-boot-2026.07.tar.bz2'
# Prefer the byte-pinned release tarball; never reuse a partial download.
if archive.exists() and hashlib.sha256(archive.read_bytes()).hexdigest()!=spec['archive_sha256']:
    archive.unlink()
if not archive.exists():
    mirrors=['https://sources.cdn.openwrt.org/u-boot-2026.07.tar.bz2',spec['archive_url']]
    for url in mirrors:
        result=subprocess.run(['curl','-4','--fail','--location','--connect-timeout','10',
                               '--max-time','75','--retry','1','-o',str(archive),url])
        if result.returncode==0 and archive.exists() and (
                hashlib.sha256(archive.read_bytes()).hexdigest()==spec['archive_sha256']):
            break
        archive.unlink(missing_ok=True)
unpacked=root.parent/'u-boot-2026.07'
if archive.exists():
    if unpacked.exists():
        raise RuntimeError('Refuse to overwrite extracted source')
    with tarfile.open(archive) as tar:
        tar.extractall(root.parent,filter='data')
    if not unpacked.exists():
        raise RuntimeError('Expected source directory missing')
    unpacked.rename(root)
else:
    # Network fallback: exact upstream Git commit, not a moving branch/tag.
    subprocess.run(['git','init',str(root)],check=True,stdout=subprocess.DEVNULL)
    subprocess.run(['git','-C',str(root),'remote','add','origin',
                    'https://github.com/u-boot/u-boot.git'],check=True)
    subprocess.run(['git','-C',str(root),'fetch','--depth=1','--no-tags','origin',
                    spec['upstream_commit']],check=True)
    subprocess.run(['git','-C',str(root),'checkout','--detach','FETCH_HEAD'],check=True)
    head=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
    if head!=spec['upstream_commit']:
        raise RuntimeError('Git source revision mismatch')
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
    select PHY
''')
kconfig=root/'drivers/usb/host/Kconfig'
text=kconfig.read_text()
old='config USB_XHCI_MTK\n\tbool \"Support for MediaTek on-chip xHCI USB controller\"\n\tdepends on ARCH_MEDIATEK || SOC_MT7621'
assert old in text
kconfig.write_text(text.replace(old,old+' || TARGET_AN7581'))
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
