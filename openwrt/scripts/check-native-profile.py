#!/usr/bin/env python3
"""Fail if Kconfig silently dropped a required USB/NAS feature."""
import pathlib,re,subprocess,sys
root=pathlib.Path(sys.argv[1]);config=(root/'.config').read_text()
required=['TARGET_airoha_an7581_DEVICE_vnpt_xsw250ns-ubi','PACKAGE_block-mount','PACKAGE_blockd','PACKAGE_kmod-usb3','PACKAGE_kmod-usb-xhci-mtk','PACKAGE_kmod-usb-storage','PACKAGE_kmod-usb-storage-uas','PACKAGE_kmod-fs-ext4','PACKAGE_kmod-fs-exfat','PACKAGE_kmod-fs-ntfs3','PACKAGE_kmod-fs-vfat','PACKAGE_usbutils','PACKAGE_samba4-server','PACKAGE_luci-app-samba4','PACKAGE_openvpn-openssl']
for key in required:
    assert 'CONFIG_'+key+'=y' in config,key+' was dropped by defconfig'
makefile=(root/'feeds/packages/net/openvpn/Makefile').read_text()
assert 'PKG_VERSION:=2.7.8' in makefile
assert 'c070d1d2440b5a6fca6c2c68645c98cd492116ac36ef4f0946177115532c8e36' in makefile
print('PASS: required board, kernel driver, filesystem, LuCI, NAS and patched VPN selections resolved.')
