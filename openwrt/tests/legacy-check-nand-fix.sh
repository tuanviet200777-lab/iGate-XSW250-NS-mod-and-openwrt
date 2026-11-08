#!/bin/sh
# Historical runtime-only checker, for regression testing only.
set -eu
[ "$(cat /tmp/sysinfo/board_name)" = 'vnpt,xsw250ns-ubi' ]
[ "$(cat /etc/xsw250ns-build-id)" = 'xsw250ns-hotfix-20261029-r3-nand1' ]
[ "$(readlink /etc/fw_env.config)" = '/tmp/xsw250ns-fw_env.config' ]
[ -s /tmp/xsw250ns-fw_env.config ]
[ "$(wc -l < /tmp/xsw250ns-fw_env.config)" -eq 2 ]
fw_printenv > /dev/null
awk '$2 == "/overlay" && $3 == "ubifs" && $4 ~ /(^|,)rw(,|$)/ { ok=1 } END { exit !ok }' /proc/mounts
echo 'PASS legacy runtime-only checker'
