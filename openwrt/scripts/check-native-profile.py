#!/usr/bin/env python3
"""Fail if Kconfig silently dropped a required USB/NAS feature."""

if not __debug__:
    raise RuntimeError("Refusing optimized Python: integrity checks required")
import json,pathlib,re,subprocess,sys
root=pathlib.Path(sys.argv[1]);config=(root/'.config').read_text()
required=['TARGET_airoha_an7581_DEVICE_vnpt_xsw250ns-ubi','PACKAGE_block-mount','PACKAGE_blockd','PACKAGE_kmod-usb3','PACKAGE_kmod-usb-xhci-mtk','PACKAGE_kmod-usb-storage','PACKAGE_kmod-usb-storage-uas','PACKAGE_kmod-fs-ext4','PACKAGE_kmod-fs-exfat','PACKAGE_kmod-fs-ntfs3','PACKAGE_kmod-fs-vfat','PACKAGE_usbutils','PACKAGE_samba4-server','PACKAGE_luci-app-samba4','PACKAGE_openvpn-openssl']
for key in required:
    assert 'CONFIG_'+key+'=y' in config,key+' was dropped by defconfig'
assert 'CONFIG_TARGET_INITRAMFS_COMPRESSION_GZIP=y' in config,'recovery must compress its embedded initramfs'
makefile=(root/'feeds/packages/net/openvpn/Makefile').read_text()
assert 'PKG_VERSION:=2.7.8' in makefile
assert 'c070d1d2440b5a6fca6c2c68645c98cd492116ac36ef4f0946177115532c8e36' in makefile
base=root/'target/linux/airoha/an7581/base-files'
for path in ['usr/share/luci/menu.d/luci-mod-system.json','etc/config/samba4','etc/samba/smb.conf.template']:
    assert not (base/path).exists(),path+' must be owned by its LuCI/Samba package, not base-files'
menu=json.loads((root/'feeds/luci/modules/luci-mod-system/root/usr/share/luci/menu.d/luci-mod-system.json').read_text())
assert menu['admin/system/startup']['action']['path']=='system/startup-xsw250ns-v2'
template=(root/'feeds/packages/net/samba4/files/smb.conf.template').read_text()
for setting in ['server min protocol = SMB2_10','map to guest = Never','null passwords = no']:
    assert setting in template,setting
print('PASS: required board, kernel driver, filesystem, LuCI, NAS and patched VPN selections resolved.')
