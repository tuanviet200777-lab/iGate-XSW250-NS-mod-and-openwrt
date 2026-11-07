// SPDX-License-Identifier: GPL-2.0+
/* Device-bound USB rollback. Never execute scripts or offsets from USB. */
#ifdef XSWSTOCK_HOST_TEST
#include "xswstock-host.h"
#else
#include <command.h>
#include <cli.h>
#include <console.h>
#include <dm/ofnode.h>
#include <env.h>
#include <event.h>
#include <fs.h>
#include <hash.h>
#include <lmb.h>
#include <mapmem.h>
#include <memalign.h>
#include <mtd.h>
#include <ubi_uboot.h>
#include <linux/err.h>
#include <linux/sizes.h>
#endif

struct stock_file {
	const char *name;
	size_t size;
	u32 offset;
	u8 digest[32];
};
#ifndef XSWSTOCK_LAYOUT_HEADER
#define XSWSTOCK_LAYOUT_HEADER "xswstock-layout.h"
#endif
#include XSWSTOCK_LAYOUT_HEADER

static const u8 write_order[] = {4, 7, 8, 9, 10, 11, 1, 0};
static phys_addr_t stage_base;
static phys_size_t stage_size;
static void *file_data[12];
static u8 *scratch;
static bool staged, flash_changed, identity_verified;

static int digest_matches(const void *data, size_t size, const u8 *expected)
{
	u8 digest[32];
	int length = sizeof(digest);

	if (hash_block("sha256", data, size, digest, &length))
		return -1;
	return length == 32 && !memcmp(digest, expected, 32) ? 0 : -1;
}

static void release_stage(void)
{
	if (stage_size)
		lmb_free(stage_base, stage_size, LMB_NONE);
	stage_base = 0;
	stage_size = 0;
	staged = false;
}

static int validate_staged(void)
{
	static const u8 subfiles[] = {2, 3, 5, 6};
	unsigned int i;

	for (i = 0; i < ARRAY_SIZE(stock_files); i++)
		if (digest_matches(file_data[i], stock_files[i].size,
				   stock_files[i].digest)) {
			printf("STOP: SHA256 mismatch: %s\n", stock_files[i].name);
			return -1;
		}
	for (i = 0; i < ARRAY_SIZE(subfiles); i++) {
		int sub = subfiles[i], whole = sub < 5 ? 4 : 7;
		size_t off = stock_files[sub].offset - stock_files[whole].offset;

		if (off > stock_files[whole].size ||
		    stock_files[sub].size > stock_files[whole].size - off ||
		    memcmp(file_data[sub], (u8 *)file_data[whole] + off,
			   stock_files[sub].size)) {
			puts("STOP: overlapping backup files disagree\n");
			return -1;
		}
	}
	return 0;
}

static int stage_usb(void)
{
	char device[32] = "", path[96], candidate[32];
	loff_t size, actual;
	phys_size_t total = SZ_128K, cursor = 0;
	int dev, part;
	unsigned int i;

	if (staged)
		return validate_staged();
	if (run_command("usb start", 0)) {
		puts("STOP: USB host start failed\n");
		return -1;
	}
	for (dev = 0; dev < 8 && !device[0]; dev++) {
		for (part = 0; part <= 4; part++) {
			snprintf(candidate, sizeof(candidate), "%d:%d", dev, part);
			if (!fs_set_blk_dev("usb", candidate, FS_TYPE_FAT) &&
			    !fs_size("/XSW250NS-STOCK/mtd0-bootloader.bin", &size) &&
			    size == (loff_t)stock_files[0].size) {
				strcpy(device, candidate);
				break;
			}
		}
	}
	if (!device[0]) {
		puts("STOP: FAT USB /XSW250NS-STOCK not found\n");
		return -1;
	}
	for (i = 0; i < ARRAY_SIZE(stock_files); i++)
		total += ALIGN(stock_files[i].size, ARCH_DMA_MINALIGN);
	stage_base = 0x9c000000;
	if (lmb_alloc_mem(LMB_MEM_ALLOC_MAX, ARCH_DMA_MINALIGN,
			  &stage_base, total, LMB_NONE)) {
		puts("STOP: insufficient unreserved RAM for all backup files\n");
		stage_base = 0;
		return -1;
	}
	stage_size = total;
	for (i = 0; i < ARRAY_SIZE(stock_files); i++) {
		const struct stock_file *f = &stock_files[i];

		file_data[i] = map_sysmem(stage_base + cursor, f->size);
		snprintf(path, sizeof(path), "/XSW250NS-STOCK/%s", f->name);
		if (fs_set_blk_dev("usb", device, FS_TYPE_FAT) ||
		    fs_size(path, &size) || size != (loff_t)f->size ||
		    fs_set_blk_dev("usb", device, FS_TYPE_FAT) ||
		    fs_read(path, stage_base + cursor, 0, f->size, &actual) ||
		    actual != (loff_t)f->size) {
			printf("STOP: missing, wrong-size or unreadable %s\n", f->name);
			release_stage();
			return -1;
		}
		printf("Loaded %s (%zu bytes)\n", f->name, f->size);
		cursor += ALIGN(f->size, ARCH_DMA_MINALIGN);
	}
	scratch = map_sysmem(stage_base + cursor, SZ_128K);
	if (validate_staged()) {
		release_stage();
		return -1;
	}
	staged = true;
	return 0;
}

static int check_flash(struct mtd_info *mtd)
{
	size_t actual;
	int ret;
	unsigned int i;

	if (mtd->parent || mtd->size != SZ_256M ||
	    mtd->erasesize != SZ_128K || mtd->writesize != SZ_2K ||
	    !mtd_type_is_nand(mtd)) {
		puts("STOP: unexpected SPI NAND geometry\n");
		return -1;
	}
	for (i = 0; i < ARRAY_SIZE(write_order); i++) {
		const struct stock_file *f = &stock_files[write_order[i]];
		u32 off;

		if ((f->offset | f->size) & (SZ_128K - 1) ||
		    f->offset > mtd->size || f->size > mtd->size - f->offset)
			return -1;
		for (off = f->offset; off < f->offset + f->size; off += SZ_128K) {
			ret = mtd_block_isbad(mtd, off);
			if (ret) {
				printf("STOP: bad/unreadable block at 0x%x; no shifting allowed\n", off);
				return -1;
			}
		}
	}
	if (flash_changed && identity_verified)
		return 0; /* A prior failed write may have touched reservearea. */
	ret = mtd_read(mtd, 0xddc0000 + 0x4c000, 0x1000, &actual, scratch);
	if ((ret && !mtd_is_bitflip(ret)) || actual != 0x1000 ||
	    digest_matches(scratch, 0x1000, stock_eeprom_sha)) {
		puts("STOP: live calibration identity does not match this backup\n");
		return -1;
	}
	identity_verified = true;
	return 0;
}

static int write_verified(struct mtd_info *mtd, unsigned int index)
{
	const struct stock_file *f = &stock_files[index];
	u8 *data = file_data[index];
	u32 pos, step;
	size_t actual;
	int ret;

	printf("Restoring %s at 0x%x...\n", f->name, f->offset);
	for (step = 0; step < f->size; step += SZ_128K) {
		struct erase_info erase = { .mtd = mtd, .len = SZ_128K };

		/* Retain the current primary BL2 block until the final operation. */
		pos = index == 0 ? f->size - SZ_128K - step : step;
		erase.addr = f->offset + pos;

		if (mtd_block_isbad(mtd, erase.addr))
			return -1;
		flash_changed = true;
		if (mtd_erase(mtd, &erase))
			return -1;
		ret = mtd_write(mtd, f->offset + pos, SZ_128K, &actual, data + pos);
		if (ret || actual != SZ_128K)
			return -1;
		ret = mtd_read(mtd, f->offset + pos, SZ_128K, &actual, scratch);
		if ((ret && !mtd_is_bitflip(ret)) || actual != SZ_128K ||
		    memcmp(data + pos, scratch, SZ_128K))
			return -1;
		if (ctrlc())
			return -1;
	}
	printf("Verified %s\n", f->name);
	return 0;
}

static int do_xswstock(struct cmd_tbl *cmdtp, int flag, int argc, char *const argv[])
{
	struct mtd_info *mtd;
	bool restore;
	unsigned int i;
	int ret = CMD_RET_FAILURE;

	if (argc != 2 || (strcmp(argv[1], "check") && strcmp(argv[1], "restore") &&
			  strcmp(argv[1], "retry")))
		return CMD_RET_USAGE;
	if (!ofnode_device_is_compatible(ofnode_root(), "vnpt,xsw250ns-ubi")) {
		puts("STOP: incompatible board\n");
		return CMD_RET_FAILURE;
	}
	restore = strcmp(argv[1], "check") != 0;
	if (!strcmp(argv[1], "retry") && !staged) {
		puts("STOP: no retained verified backup in RAM\n");
		return CMD_RET_FAILURE;
	}
	if (stage_usb())
		return CMD_RET_FAILURE;
	mtd_probe_devices();
	mtd = get_mtd_device_nm("spi-nand0");
	if (IS_ERR_OR_NULL(mtd)) {
		puts("STOP: SPI NAND master not found\n");
		goto out_stage;
	}
	if (check_flash(mtd))
		goto out_mtd;
	puts("PASS: all 12 files, overlaps, geometry, blocks and device identity\n");
	if (!restore) {
		ret = CMD_RET_SUCCESS;
		goto out_mtd;
	}
	puts("This erases OpenWrt and restores the ORIGINAL BOOTLOADER too.\n");
	if (cli_readline("Type RESTORE-STOCK to start, or ENTER to cancel: ") < 0 ||
	    strcmp(console_buffer, "RESTORE-STOCK")) {
		puts("Cancelled. No new flash writes.\n");
		goto out_mtd;
	}
	/* No external USB DMA or UBI access is allowed during direct NAND writes. */
	if (run_command("usb stop", 0))
		goto out_mtd;
	if (ubi_devices[0] && (run_command("ubi detach", 0) || ubi_devices[0])) {
		puts("STOP: cannot detach UBI\n");
		goto out_mtd;
	}
	if (env_set("bootcmd", "false") || env_set("bootmenu_delay", "-1") ||
	    env_set("bootdelay", "-1")) {
		puts("STOP: cannot disable autoboot; no new flash writes.\n");
		goto out_mtd;
	}
	for (i = 0; i < ARRAY_SIZE(write_order); i++)
		if (write_verified(mtd, write_order[i])) {
			puts("RESTORE INCOMPLETE. KEEP POWER ON. Use xswstock retry.\n");
			goto out_mtd;
		}
	puts("All restored regions read back correctly. Rebooting to stock.\n");
	ret = CMD_RET_SUCCESS;
	put_mtd_device(mtd);
	run_command("reset", 0);
	return ret;
out_mtd:
	put_mtd_device(mtd);
out_stage:
	if (!flash_changed)
		release_stage();
	return ret;
}

static int xswstock_menu_init(void)
{
	char variable[24];
	unsigned int i;

	if (!ofnode_device_is_compatible(ofnode_root(), "vnpt,xsw250ns-ubi"))
		return 0;

	/* Append to old saved menus too: bootmenu stops at its first missing key. */
	for (i = 0; i < 100; i++) {
		const char *value;

		snprintf(variable, sizeof(variable), "bootmenu_%u", i);
		value = env_get(variable);
		if (!value || strstr(value, "xswstock restore")) {
			env_set(variable, "Restore original firmware from USB (erases OpenWrt)=xswstock restore");
			break;
		}
	}
	/* Runtime-only menu update, never saveenv. */
	run_command("usb start", 0);
	return 0;
}
EVENT_SPY_SIMPLE(EVT_LAST_STAGE_INIT, xswstock_menu_init);

U_BOOT_CMD(xswstock, 2, 0, do_xswstock,
	"check or restore this XSW250NS original backup from FAT USB",
	"check - verify all files and device without writing NAND\n"
	"xswstock restore - verify, confirm, restore and reboot\n"
	"xswstock retry - retry a failed write using retained verified RAM data");
