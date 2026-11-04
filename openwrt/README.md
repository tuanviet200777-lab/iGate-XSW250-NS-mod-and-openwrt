# XSW250-NS r4: diagnostics-only LuCI and NAND preinit fix

Current build ID: `xsw250ns-20261104-r4-diag-nand1`. The old AI/API-key/chat and JSON hotfix feature has been removed, including its worker, policy module, write ACL, RPC endpoints and S18 recovery service. LuCI **System → Chẩn đoán hệ thống** now collects six detailed read-only groups on demand, with findings and JSON export. See [Vietnamese guide](docs/DIAGNOSTICS.vi.md). MAC/IP remain in the report; review it before sharing.

This directory supplies the source changes for `vnpt,xsw250ns-ubi`. It is a board port on ImmortalWrt, not an upstream-supported OpenWrt device profile.

- Base: `tuanviet200777-lab/immortalwrt` at `e695009c15c623f4f6a83376b505faaf7a4ae5b5`.
- Target: `airoha/an7581`, kernel 6.18.55, MT7916, EN8811H, four LAN ports plus a 2.5G port.
- Full board patch: `patches/xsw250ns-support-r4-diag.patch` (apply once to the pinned base).
- Build config and all five feed revisions: `config/`.
- Prior results: `evidence/`; these distinguish static/MSYS checks from hardware observations.

## Confirmed bug and correction

The old r3 board hook calls `touch /etc/config/ubootenv` and UCI while the initial root is read-only SquashFS. `preinit_ip` invokes `board_detect` before `80_mount_root`, causing the observed EROFS/UCI/fw_env/NVMEM messages.

The corrected hook writes a runtime reader to tmpfs, discovers both UBI environment volumes by name and validates their geometry. The reader symlink and corrected hook must be present in the lower SquashFS. Installing them only into overlay does not fix preinit; that earlier add-on recommendation has been withdrawn.

The original r3 has booted from NAND with U-Boot 2026.07 and mounted UBIFS according to the supplied UART log. The corrected image has **not** been boot-tested on the physical board. PON/TEL remain unsupported; MAC identity and link stability still need investigation. Raw UART, calibration, subscriber configuration, keys and NAND dumps are not part of this source handoff.

## Prepare a native Linux build

Use an unprivileged account and a case-sensitive Linux filesystem. Install the OpenWrt build prerequisites for the host distribution first. Do not use the Windows/MSYS repacking pipeline to claim a native build.

From this project repository:

```bash
bash openwrt/scripts/prepare-build.sh /workspace/xsw250ns-native-build
```

The destination must be a new directory. This clones the pinned source, applies the full patch, pins feeds, loads the saved full config and runs `make defconfig`. It does not modify another checkout or start a long build automatically.

Then, in the prepared build directory:

```bash
make -j4 download
make -j4 tools/install
make -j4 toolchain/install
set -o pipefail
make -j4 V=s 2>&1 | tee ../xsw250ns-native-build.log
```

Choose concurrency for available RAM. Stop on a failed step; use `make -j1 V=s` to diagnose. Output images are under `bin/targets/airoha/an7581/`. Names may start with `immortalwrt-`; verify FIT metadata, not only filenames. A fresh build has new signing keys unless existing keys are supplied through a proper private secret store; never commit private keys.

## Component tests and image checks

```bash
python3 openwrt/tests/test_reader.py
python3 openwrt/tests/test_rom_checker.py
python3 openwrt/scripts/verify-fit.py /path/to/recovery.itb /path/to/sysupgrade.itb
```

The component tests mock UBI character nodes and `fw_printenv`. They are not a NAND, kernel, reboot or real read-only mount test. The cloud task must add native layered-root integration and inspect the files extracted from the actual built SquashFS. See `CLOUD-TASK.md` for the required work.

After a real device boots the corrected sysupgrade, `scripts/check-nand-fix.sh` verifies both `/rom` and runtime state. A build ID in `/etc` alone is insufficient because overlay can replace it.

The source commit records the fix and prior evidence. Firmware release artifacts should be produced by the native cloud build and accompanied by checksums, build logs and an honest hardware-test status.
