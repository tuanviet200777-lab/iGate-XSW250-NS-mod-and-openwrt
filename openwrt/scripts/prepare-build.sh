#!/usr/bin/env bash
set -euo pipefail
umask 022

kit_dir="$(cd -- "$(dirname -- "$0")/.." && pwd)"
build_dir="${1:?Usage: prepare-build.sh NEW_BUILD_DIRECTORY}"
base_commit=e695009c15c623f4f6a83376b505faaf7a4ae5b5
source_url=https://github.com/tuanviet200777-lab/immortalwrt.git

if [ "$(id -u)" = 0 ]; then
    echo 'Run the OpenWrt build as an unprivileged user.' >&2
    exit 2
fi
case "$build_dir" in *' '*) echo 'Build path must not contain spaces.' >&2; exit 2 ;; esac
if [ -e "$build_dir" ]; then
    echo 'Destination already exists; choose a new build directory. Existing work is preserved.' >&2
    exit 2
fi

git -c core.autocrlf=false clone --filter=blob:none --no-checkout "$source_url" "$build_dir"
git -C "$build_dir" config core.autocrlf false
git -C "$build_dir" checkout --detach "$base_commit"
git -C "$build_dir" apply --check "$kit_dir/patches/xsw250ns-support-r5-usb-nas.patch"
git -C "$build_dir" apply "$kit_dir/patches/xsw250ns-support-r5-usb-nas.patch"
cp "$kit_dir/config/feeds.pinned.conf" "$build_dir/feeds.conf"
cp "$kit_dir/config/xsw250ns.full.config" "$build_dir/.config"
cd "$build_dir"
./scripts/feeds update -a
./scripts/feeds install -a
git -C feeds/packages apply --check "$kit_dir/patches/openvpn-2.7.8.patch"
git -C feeds/packages apply "$kit_dir/patches/openvpn-2.7.8.patch"
make defconfig

python3 - "$kit_dir/evidence/base-r3-build-manifest.json" <<'PY'
import json, pathlib, subprocess, sys
manifest=json.loads(pathlib.Path(sys.argv[1]).read_text())
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==manifest['base_commit']
for name,expected in manifest['feed_commits'].items():
    assert subprocess.check_output(['git','-C','feeds/'+name,'rev-parse','HEAD'],text=True).strip()==expected,name
config=pathlib.Path('.config').read_text()
for required in ['CONFIG_TARGET_airoha_an7581_DEVICE_vnpt_xsw250ns-ubi=y','CONFIG_TARGET_ROOTFS_INITRAMFS=y','CONFIG_TARGET_ROOTFS_SQUASHFS=y']:
    assert required in config,required
link=pathlib.Path('target/linux/airoha/an7581/base-files/etc/fw_env.config')
assert link.is_symlink() and str(link.readlink())=='/tmp/xsw250ns-fw_env.config'
print('PASS: source, feeds, board, image formats and lower-image symlink are pinned.')
PY

echo "Prepared $build_dir. Build and validate using openwrt/README.md."
