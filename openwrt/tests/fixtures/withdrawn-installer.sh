#!/bin/sh
# Withdrawn: overlay changes cannot replace a pre-overlay SquashFS hook.
echo 'DUNG: add-on cu khong sua duoc loi preinit trong SquashFS.' >&2
echo 'Can dung image sysupgrade da sua; doc HUONG-DAN.md da ra soat.' >&2
echo 'Chua thay doi tep hay cau hinh nao.' >&2
exit 1
