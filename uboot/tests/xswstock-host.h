/* Host fault-injection API boundary for the actual production command. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <openssl/sha.h>
typedef uint8_t u8;
typedef uint32_t u32;
typedef uintptr_t phys_addr_t;
typedef size_t phys_size_t;
typedef int64_t loff_t;
#define SZ_2K 0x800u
#define SZ_128K 0x20000u
#define SZ_256M 0x10000000u
#define ARCH_DMA_MINALIGN 64
#define ALIGN(v,a) (((v)+(a)-1)&~((a)-1))
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define LMB_NONE 0
#define LMB_MEM_ALLOC_MAX 2
#define FS_TYPE_FAT 1
#define CMD_RET_SUCCESS 0
#define CMD_RET_FAILURE 1
#define CMD_RET_USAGE 2
#define EVENT_SPY_SIMPLE(...)
#define U_BOOT_CMD(...)
#define IS_ERR_OR_NULL(v) (!(v))
#define mtd_type_is_nand(m) ((m)->nand)
#define mtd_is_bitflip(e) ((e)==-117)
struct cmd_tbl {int unused;};
struct mtd_info {struct mtd_info *parent; uint64_t size; u32 erasesize,writesize;bool nand;};
struct erase_info {uint64_t addr,len;};
static void *ubi_devices[1];
static char console_buffer[64];
static int hash_block(const char *,const void *,size_t,u8 *,int *);
static long lmb_free(phys_addr_t,phys_size_t,u32);
static int lmb_alloc_mem(int,uint64_t,phys_addr_t *,phys_size_t,u32);
static void *map_sysmem(phys_addr_t,size_t);
static int run_command(const char *,int);
static int fs_set_blk_dev(const char *,const char *,int);
static int fs_size(const char *,loff_t *);
static int fs_read(const char *,phys_addr_t,loff_t,loff_t,loff_t *);
static int mtd_probe_devices(void);
static struct mtd_info *get_mtd_device_nm(const char *);
static void put_mtd_device(struct mtd_info *);
static int mtd_block_isbad(struct mtd_info *,uint64_t);
static int mtd_read(struct mtd_info *,uint64_t,size_t,size_t *,u8 *);
static int mtd_write(struct mtd_info *,uint64_t,size_t,size_t *,const u8 *);
static int mtd_erase(struct mtd_info *,struct erase_info *);
static int ctrlc(void);
static int cli_readline(const char *);
static int env_set(const char *,const char *);
static const char *env_get(const char *);
static int ofnode_root(void);
static int ofnode_device_is_compatible(int,const char *);
