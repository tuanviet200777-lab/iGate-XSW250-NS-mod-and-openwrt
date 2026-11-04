#!/bin/sh
# Check lower SquashFS and runtime; overlay files alone do not prove preinit.
# No environment values or credentials are printed.
set -eu
fail() { echo "FAIL: $*" >&2; exit 1; }
[ "$(cat /tmp/sysinfo/board_name)" = 'vnpt,xsw250ns-ubi' ]
[ "$(cat /rom/etc/xsw250ns-build-id 2>/dev/null)" = 'xsw250ns-20261104-r4-diag-nand1' ] ||
	fail 'SquashFS /rom chua co NAND fix. Add-on trong overlay khong sua duoc preinit; can dung image da sua.'
expected=d5f7da4aa0809654cb491e04a1064ef181dde1dec54865008050fe2f380ef9c2
actual="$(sha256sum /rom/etc/board.d/04_xsw250ns_ubootenv)"
actual=${actual%% *}
[ "$actual" = "$expected" ] || fail 'Script preinit trong /rom khong dung ban da doi chieu.'
[ "$(readlink /rom/etc/fw_env.config)" = '/tmp/xsw250ns-fw_env.config' ] || fail 'Thieu symlink reader trong /rom.'
[ "$(cat /etc/xsw250ns-build-id)" = 'xsw250ns-20261104-r4-diag-nand1' ] || fail 'Build ID runtime bi overlay thay doi.'
[ -s /tmp/xsw250ns-fw_env.config ] || fail 'Chua tao duoc reader runtime.'
[ "$(wc -l < /tmp/xsw250ns-fw_env.config)" -eq 2 ] || fail 'Reader runtime khong du hai dong.'
# sysupgrade may preserve an older regular conffile over the image symlink.
# Accept it only if it matches the freshly discovered geometry exactly.
cmp -s /etc/fw_env.config /tmp/xsw250ns-fw_env.config || fail 'Reader trong /etc khac cau hinh UBI vua phat hien.'
fw_printenv > /dev/null || fail 'Khong doc duoc environment.'
awk '$2 == "/overlay" && $3 == "ubifs" && $4 ~ /(^|,)rw(,|$)/ { ok=1 } END { exit !ok }' /proc/mounts || fail 'Overlay UBIFS chua ghi duoc.'
echo 'PASS: /rom co NAND fix, reader environment doc duoc va overlay UBIFS ghi duoc.'
echo 'Can doi chieu log UART sau reboot de xac nhan het loi preinit tren may.'
