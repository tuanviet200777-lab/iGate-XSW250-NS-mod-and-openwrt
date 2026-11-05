# Cloud continuation: XSW250-NS r5 USB2/NAS native build

Current source is r5: use `scripts/prepare-build.sh`, which applies `patches/xsw250ns-support-r5-usb-nas.patch`, pins feeds and applies the OpenVPN, Samba defaults and LuCI Startup feed patches. Read `docs/BUILD-R5.vi.md` and `docs/R5-USB-NAS.vi.md`. Keep LuCI/Samba-owned files out of board base-files to avoid APK ownership conflicts. Recovery uses a gzip-compressed embedded initramfs; verify the ARM64 Image range against DTB reserved memory. Keep candidate image artifacts and verification logs even if the checker fails. The r4 description and evidence below are historical context; do not apply the old full patch on top of r5.

## Objective

Continue the user's XSW250-NS firmware work on Linux. The current source is r5 USB2/NAS: apply `patches/xsw250ns-support-r5-usb-nas.patch` with its feed patches and pinned profile. Preserve the diagnostics-only UI and NAND fixes inherited from r4. Validate USB2-only DTBs, matching storage modules, Samba defaults and authenticated file transfers; distinguish native compilation, QEMU userland tests and physical USB tests. The user explicitly removed the AI/API/chat and JSON hotfix feature; do not restore them. Check all six diagnostic groups, missing-data behavior, read-only ACL, secret filtering, removal of retained-overlay files/credentials, startup ordering of S00 retirement before old S18, and stale overlay build IDs. Preserve the existing NAND reader fix. Native builds must produce both updated recovery and sysupgrade, with no retired files in either image. Validate the reviewed NAND preinit correction, fix any actual defects found, build recovery and sysupgrade natively, and leave source changes and reproducible evidence for review. Do not claim a physical-device test without one.

## Repositories and starting point

This is the public project repository `tuanviet200777-lab/iGate-XSW250-NS-mod-and-openwrt`. The historical private backup is `tuanviet200777-lab/xsw250ns-backup`; its `reference-fix` predates r3. Its legacy `immortalwrt-custom-backup/modified_files.patch` is empty and is not a source of the latest changes.

The saved cloud environment is associated with `tuanviet200777-lab/immortalwrt`. Inspect the environment first, following its cloud-environment runtime skill if available. Use a separate clean checkout/build directory when its existing checkout contains unrelated changes. Do not reset, force-push or overwrite other work.

The full board patch and configs in this handoff restore the current source on commit `e695009c15c623f4f6a83376b505faaf7a4ae5b5`; all five feeds are pinned. Do not silently switch to the latest main/master or mix module ABIs. Preserve signing and checksum verification. Never use a pasted PAT or store credentials in repository content, git remotes, task prompts, shell commands or logs.

## Evidence that matters

The user supplied a newer UART log: U-Boot 2026.07 reads a FIT from NAND, sysupgrade succeeds, SquashFS mounts and UBIFS overlay mounts. UBI reports zero bad/corrupted PEBs in those boots. The repeated EROFS/UCI/fw_env/NVMEM messages arise before overlay mount. The public summary records the log hash; the raw log and device-specific backups stay private.

The r3 hook creates `/etc/config/ubootenv` and calls UCI in `board_detect` during `preinit_ip`. The corrected hook writes a reader into `/tmp`; the lower image supplies `/etc/fw_env.config` as a symlink. The old overlay-only installer cannot fix this phase and has been withdrawn. Its earlier mock "reboot" test called the new overlay hook directly, which did not model the real initial SquashFS root. The new checker verifies the hook/build ID/symlink in `/rom`.

The earlier Windows-repacked sysupgrade hash is `5c0a9cc947a4cbbb176e74d0f1694b6718662ebe3e87a7dbe1ddf2b0ca830b77`. It is prior evidence, not the expected hash of a fresh native build. Native outputs may differ because of build context/signing keys/timestamps. Do not copy its test status onto new outputs.

## Required work

1. Read the board source patch, boot fixtures and review before changing code. Confirm order: `preinit_ip` → early `board_detect`/04/05 → `80_mount_root` → `82_config_generate`. Check both fresh install and retained conffile/overlay scenarios.
2. Run the portable component fixtures. Strengthen them using BusyBox ash/real shell behavior. Add a native Linux layered-root integration reproducer if mounts/namespaces are available: read-only lower root with the old hook plus later overlay, then the fixed lower image. Include the negative case where only overlay is patched. If the sandbox cannot mount or emulate this, record that limitation and use the strongest honest alternative; never relabel a path-mapped fixture as an actual reboot test.
3. Check reader discovery and geometry, missing volumes, character-device checks, atomic tmpfs write and cleanup. Inspect whether sysupgrade preserves a regular fw_env.config or older UCI config; ensure the current checker handles valid retained configuration without falsely certifying the old lower image.
4. Build in a native Linux environment as an unprivileged user from the pinned source/config/feeds. Prepare tools/dependencies according to the actual host. Reuse a verified download cache when helpful. Build both recovery and sysupgrade, diagnose failures rather than forcing past checks.
5. Extract the actual DTB/rootfs/initramfs from the built images. Check FIT hashes, compatible/board/config, partition boundaries, reservearea/BMT protections, EEPROM endpoint, reader files and symlink in the immutable lower image, init/console, ownership/modes and required modules/firmware. Validate source-to-image correspondence and full build/feeds provenance.
6. Export the two images, SHA256SUMS, native build logs/status, manifest/config/source patch and test results to the task artifacts or a draft release only if publishing is available and authorized. Do not upload raw NAND, calibration/romfile/userdata/safedata, unfiltered UART, VPN/API keys or private signing keys to this public repo. If artifact publication is unavailable, provide the artifact path/download route actually available; do not invent a release URL.
7. Commit source/test/documentation improvements to the dedicated handoff branch and update its existing PR without changing its draft state. Do not merge or force-push main. Keep the final report clear about native build tests, emulation and physical-router tests.

## Limits and scope

No flash or remote router connection is part of this cloud task. Keep PON/TEL unsupported and do not infer USB wiring, factory MAC or PHY reset behavior from another model without evidence. MAC ff/random fallback and idle 2.5G link flap are known issues; diagnose source evidence if useful, but do not assign shared/default MACs, change bootloader/environment or force link settings to hide them.

The repository's older stock reconstruction script produces only the stated 0x51c0000-byte subset and excludes safedata/reservearea; do not describe it as a full raw 256 MiB NAND+OOB backup. Initial bootloader-conversion instructions are separate from the NAND preinit fix; no BL2/FIP replacement is needed to fix this script ordering bug.
