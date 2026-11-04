#!/usr/bin/env python3
"""Verify FIT, lower-root NAND fix, and the files actually shipped by native build."""
import hashlib,importlib.util,json,pathlib,subprocess,sys
folder=pathlib.Path(sys.argv[1]);out=pathlib.Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
spec=importlib.util.spec_from_file_location('fit',pathlib.Path(__file__).with_name('verify-fit.py'))
fit=importlib.util.module_from_spec(spec);spec.loader.exec_module(fit)
images=list(folder.glob('*xsw250ns*sysupgrade.itb'))
recoveries=list(folder.glob('*xsw250ns*recovery.itb'))
assert len(images)==1,images
assert len(recoveries)==1,('expected one recovery image',recoveries)
for image in images+recoveries:fit.verify(image)
data=images[0].read_bytes();nodes,_=fit.parse(data);node=nodes['/images/rootfs-1']
offset=int.from_bytes(node['data-position'],'big');size=int.from_bytes(node['data-size'],'big')
squash=out/'rootfs.squashfs';squash.write_bytes(data[offset:offset+size])
root=out/'rootfs';subprocess.run(['unsquashfs','-d',str(root),str(squash)],check=True,stdout=subprocess.DEVNULL)
assert (root/'etc/xsw250ns-build-id').read_text().strip()=='xsw250ns-20261104-r5-usb-nas'
assert (root/'etc/fw_env.config').is_symlink()
assert str((root/'etc/fw_env.config').readlink())=='/tmp/xsw250ns-fw_env.config'
assert hashlib.sha256((root/'etc/board.d/04_xsw250ns_ubootenv').read_bytes()).hexdigest()=='d5f7da4aa0809654cb491e04a1064ef181dde1dec54865008050fe2f380ef9c2'
for path in ['sbin/block','usr/bin/lsusb','usr/sbin/smbd','usr/bin/testparm','usr/sbin/openvpn','usr/share/rpcd/ucode/luci.xsw250ns-port','usr/share/rpcd/ucode/luci.xsw250ns-status','usr/share/ucode/xsw250ns/state.uc','www/luci-static/resources/view/system/startup-xsw250ns-v2.js']:
    assert (root/path).is_file(),path
for module in ['usb-storage.ko','uas.ko','xhci-hcd.ko','xhci-mtk-hcd.ko','exfat.ko','ntfs3.ko','vfat.ko']:
    assert list((root/'lib/modules').rglob(module)),module
acl=json.loads((root/'usr/share/rpcd/acl.d/luci-xsw250ns-port.json').read_text())
assert 'uci' not in acl['luci-xsw250ns-port']['read']
template=(root/'etc/samba/smb.conf.template').read_text()
for setting in ['server min protocol = SMB2_10','map to guest = Never','null passwords = no','bind interfaces only = yes']:
    assert setting in template,setting
for path in ['usr/libexec/xsw250ns-hotfix','www/luci-static/resources/view/system/xsw250ns-hotfix.js','www/luci-static/resources/view/status/include/99_xsw250ns_port.js']:
    assert not (root/path).exists(),path
result={'build':'xsw250ns-20261104-r5-usb-nas','image':images[0].name,'sha256':hashlib.sha256(data).hexdigest(),'native_build':True,'fit_verified':True,'lower_nand_hook_verified':True,'usb_nas_contents_verified':True,'physical_boot_or_usb_tested':False}
(out/'image-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
