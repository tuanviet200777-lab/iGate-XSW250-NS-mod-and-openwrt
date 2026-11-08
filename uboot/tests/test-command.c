// SPDX-License-Identifier: GPL-2.0+
#define XSWSTOCK_HOST_TEST
#include "../overlay/cmd/xswstock.c"

static struct mtd_info chip;
static u8 *nand_data;
static char fixture[1024];
static int missing=-1,short_file=-1,corrupt=-1,bad_block=-1;
static int fail_erase,fail_write,fail_readback,fail_identity,wrong_board,wrong_geometry;
static int cancel,usb_unavailable,detach_failure,erase_count,write_count,reset_count,usb_starts;
static int bootloader_seen,write_region_count,previous_region=-1;
static unsigned int observed_regions[8];
static uint64_t last_write_offset;
static int existing_menu_count;
static const char *fail_env;
static char added_menu_key[32];
static int total_tests;
static u8 *backup_data[12];
static size_t backup_len[12];
static int backup_writes,backup_read_corrupt;
static const char *current_name;

static int file_index(const char *path)
{
	const char *name=strrchr(path,'/');
	int i;
	name=name ? name+1 : path;
	for(i=0;i<12;i++)if(!strcmp(name,stock_files[i].name))return i;
	return -1;
}
static FILE *open_input(int index)
{
	char name[1200];
	snprintf(name,sizeof(name),"%s/%s",fixture,stock_files[index].name);
	return fopen(name,"rb");
}
static int hash_block(const char *alg,const void *data,size_t len,u8 *out,int *size)
{
	assert(!strcmp(alg,"sha256") && *size>=32);
	SHA256(data,len,out);*size=32;return 0;
}
static int lmb_alloc_mem(int type,uint64_t align,phys_addr_t *addr,phys_size_t len,u32 flags)
{
	void *p=malloc(len);(void)type;(void)align;(void)flags;
	if(!p)return -1;
	*addr=(uintptr_t)p;return 0;
}
static long lmb_free(phys_addr_t addr,phys_size_t len,u32 flags)
{(void)len;(void)flags;free((void *)addr);return 0;}
static void *map_sysmem(phys_addr_t addr,size_t len){(void)len;return(void *)addr;}
static int run_command(const char *cmd,int flags)
{
	(void)flags;
	if(!strcmp(cmd,"usb start")){usb_starts++;return usb_unavailable;}
	if(!strcmp(cmd,"usb stop"))return 0;
	if(!strcmp(cmd,"ubi detach")){if(!detach_failure)ubi_devices[0]=NULL;return detach_failure;}
	if(!strcmp(cmd,"reset")){reset_count++;return 0;}
	assert(!"unexpected command");return -1;
}
static int fs_set_blk_dev(const char *type,const char *device,int fs)
{assert(!strcmp(type,"usb") && fs==FS_TYPE_FAT);return strcmp(device,"0:1") ? -1 : 0;}
static int fs_size(const char *path,loff_t *size)
{
	int i=file_index(path);FILE *f;
	if(strstr(path,"XSW250NS-DUMP/READY.TXT")){*size=(loff_t)strlen("XSW250NS-RAW-BACKUP-V1\n");return 0;}
	if(i<0||i==missing)return -1;
	f=open_input(i);if(!f)return -1;
	fseek(f,0,SEEK_END);*size=ftell(f);fclose(f);
	if(i==short_file)(*size)--;
	return 0;
}
static int fs_read(const char *path,phys_addr_t addr,loff_t offset,loff_t len,loff_t *actual)
{
	int i=file_index(path);FILE *f;
	if(strstr(path,"XSW250NS-DUMP/READY.TXT")){
		const char *marker="XSW250NS-RAW-BACKUP-V1\\n";
		assert(offset==0 && len==(loff_t)strlen(marker));
		memcpy((void *)addr,marker,len);*actual=len;return 0;
	}
	if(strstr(path,"XSW250NS-DUMP/")){
		assert(i>=0 && backup_data[i] && offset+len<=(loff_t)backup_len[i]);
		memcpy((void *)addr,backup_data[i]+offset,len);*actual=len;
		if(backup_read_corrupt && backup_writes)((u8 *)addr)[0]^=1;
		return 0;
	}
	f=open_input(i);
	assert(f && offset==0);
	*actual=fread((void *)addr,1,len,f);fclose(f);
	if(i==corrupt)((u8 *)addr)[len/2]^=1;
	return 0;
}
static int fs_exists(const char *path)
{
	int i=file_index(path);
	assert(strstr(path,"XSW250NS-DUMP/") && i>=0);
	return backup_data[i]!=NULL;
}
static int fs_write(const char *path,phys_addr_t addr,loff_t offset,loff_t len,loff_t *actual)
{
	int i=file_index(path);
	assert(strstr(path,"XSW250NS-DUMP/") && i>=0 && offset>=0 && len>0);
	assert(offset+len<=(loff_t)stock_files[i].size);
	if(!backup_data[i]){backup_data[i]=malloc(stock_files[i].size);assert(backup_data[i]);}
	assert((size_t)offset==backup_len[i]);
	memcpy(backup_data[i]+offset,(void *)addr,len);
	backup_len[i]=offset+len;backup_writes++;*actual=len;return 0;
}
static int mtd_probe_devices(void){return 0;}
static struct mtd_info *get_mtd_device_nm(const char *name)
{assert(!strcmp(name,"spi-nand0"));return &chip;}
static void put_mtd_device(struct mtd_info *mtd){assert(mtd==&chip);}
static int mtd_block_isbad(struct mtd_info *mtd,uint64_t off)
{assert(mtd==&chip);return bad_block>=0 && off==(unsigned)bad_block;}
static int mtd_read(struct mtd_info *mtd,uint64_t off,size_t len,size_t *actual,u8 *data)
{
	assert(mtd==&chip && off+len<=SZ_256M);
	memcpy(data,nand_data+off,len);*actual=len;
	if(!write_count && fail_identity && off==0xde0c000)data[0]^=1;
	if(write_count && fail_readback){data[0]^=1;fail_readback=0;}
	return 0;
}
static int mtd_write(struct mtd_info *mtd,uint64_t off,size_t len,size_t *actual,const u8 *data)
{
	int i,region=-1;
	assert(mtd==&chip && len==SZ_128K && off+len<=SZ_256M);
	write_count++;last_write_offset=off;
	if(fail_write && write_count==fail_write){*actual=0;return -1;}
	for(i=0;i<8;i++){
		int idx=write_order[i];
		if(off>=stock_files[idx].offset && off<stock_files[idx].offset+stock_files[idx].size)region=idx;
	}
	assert(region>=0);
	if(region!=previous_region){
		assert(write_region_count<8);observed_regions[write_region_count++]=region;previous_region=region;
	}
	if(region==0)bootloader_seen=1;
	else assert(!bootloader_seen);
	memcpy(nand_data+off,data,len);*actual=len;return 0;
}
static int mtd_erase(struct mtd_info *mtd,struct erase_info *e)
{
	assert(mtd==&chip && e->mtd==mtd && e->len==SZ_128K && e->addr+e->len<=SZ_256M);
	erase_count++;
	if(fail_erase && erase_count==fail_erase)return -1;
	memset(nand_data+e->addr,0xff,e->len);return 0;
}
static int ctrlc(void){return 0;}
static int cli_readline(const char *prompt)
{(void)prompt;strcpy(console_buffer,cancel?"cancel":"RESTORE-STOCK");return strlen(console_buffer);}
static int env_set(const char *name,const char *value)
{
    if(fail_env && !strcmp(name,fail_env))return -1;
    if(strstr(value,"xswstock restore"))snprintf(added_menu_key,sizeof(added_menu_key),"%s",name);
    return 0;
}
static const char *env_get(const char *name)
{
    unsigned int i;
    if(sscanf(name,"bootmenu_%u",&i)==1 && i<(unsigned)existing_menu_count)return "existing menu";
    return NULL;
}
static int ofnode_root(void){return 0;}
static int ofnode_device_is_compatible(int node,const char *compat)
{(void)node;assert(!strcmp(compat,"vnpt,xsw250ns-ubi"));return !wrong_board;}

static void setup(const char *name)
{
	FILE *f;
	for(int i=0;i<12;i++){free(backup_data[i]);backup_data[i]=NULL;backup_len[i]=0;}
	backup_writes=backup_read_corrupt=0;
	if(stage_size)release_stage();
	flash_changed=identity_verified=false;
	fail_env=NULL;
	missing=short_file=corrupt=bad_block=-1;
	fail_erase=fail_write=fail_readback=fail_identity=wrong_board=wrong_geometry=0;
	cancel=usb_unavailable=detach_failure=erase_count=write_count=reset_count=usb_starts=0;
	bootloader_seen=write_region_count=0;previous_region=-1;ubi_devices[0]=NULL;
	chip=(struct mtd_info){.size=SZ_256M,.erasesize=SZ_128K,.writesize=SZ_2K,.nand=true};
	memset(nand_data,0xa5,SZ_256M);
	f=open_input(11);assert(f);
	assert(fread(nand_data+stock_files[11].offset,1,stock_files[11].size,f)==stock_files[11].size);fclose(f);
	current_name=name;
}
static int call(const char *operation)
{char *args[]={"xswstock",(char *)operation};return do_xswstock(NULL,0,2,args);}
static void pass(void){printf("TEST PASS: %s\n",current_name);total_tests++;}
static void no_write(void)
{assert(call("restore")==CMD_RET_FAILURE);assert(!erase_count&&!write_count&&!reset_count);pass();}
static void complete(void)
{
	int i;u8 *expected;
	assert(reset_count==1 && write_region_count==8 && bootloader_seen && last_write_offset==0);
	for(i=0;i<8;i++){
		int idx=write_order[i];FILE *f=open_input(idx);assert(f);
		assert(observed_regions[i]==write_order[i]);
		expected=malloc(stock_files[idx].size);assert(expected);
		assert(fread(expected,1,stock_files[idx].size,f)==stock_files[idx].size);fclose(f);
		assert(!memcmp(expected,nand_data+stock_files[idx].offset,stock_files[idx].size));free(expected);
	}
	/* Gaps outside the backed-up regions and the BMT tail stay untouched. */
	assert(nand_data[0x5bc0000]==0xa5 && nand_data[0xddbffff]==0xa5 && nand_data[0xe000000]==0xa5 && nand_data[SZ_256M-1]==0xa5);
}
int main(int argc,char **argv)
{
	FILE *report;
	assert(argc==3);snprintf(fixture,sizeof(fixture),"%s",argv[1]);
	nand_data=malloc(SZ_256M);assert(nand_data);
	setup("menu appears after older persisted eight-entry menu without writes");existing_menu_count=8;added_menu_key[0]=0;assert(xswstock_menu_init()==0);assert(!strcmp(added_menu_key,"bootmenu_8")&&usb_starts==1&&!erase_count&&!write_count);pass();
	setup("menu appears after current nine-entry menu without writes");existing_menu_count=9;added_menu_key[0]=0;assert(xswstock_menu_init()==0);assert(!strcmp(added_menu_key,"bootmenu_9")&&usb_starts==1&&!erase_count&&!write_count);pass();
	setup("check validates actual files without NAND writes");assert(call("check")==0);assert(!erase_count&&!write_count&&!reset_count&&!stage_size);pass();
	setup("USB start failure performs no writes");usb_unavailable=1;no_write();
	setup("wrong board rejected");wrong_board=1;no_write();
	setup("missing file rejected");missing=3;no_write();
	setup("truncated file rejected");short_file=7;no_write();
	setup("same-size corrupted file rejected");corrupt=10;no_write();
	setup("bad block rejected before any erase");bad_block=0x100000;no_write();
	setup("wrong flash geometry rejected");chip.writesize=0x1000;no_write();
	setup("different calibration identity rejected");fail_identity=1;no_write();
	setup("cancel confirmation performs no writes");cancel=1;no_write();
	setup("UBI detach failure prevents erase");ubi_devices[0]=(void *)1;detach_failure=1;no_write();
	setup("bootcmd failure prevents writes");fail_env="bootcmd";no_write();
	setup("bootmenu_delay failure prevents writes");fail_env="bootmenu_delay";no_write();
	setup("bootdelay failure prevents writes");fail_env="bootdelay";no_write();
	setup("complete restore writes correct extents, bootloader last, resets once");assert(call("restore")==0);complete();pass();
	setup("erase failure preserves staged RAM and does not reboot");fail_erase=2;assert(call("restore")==1);assert(staged&&flash_changed&&!reset_count);pass();
	setup("write failure does not reboot; retry succeeds without USB");fail_write=3;assert(call("restore")==1);assert(staged&&flash_changed&&!reset_count);fail_write=0;usb_unavailable=1;erase_count=write_count=write_region_count=0;previous_region=-1;assert(call("retry")==0);complete();pass();
	setup("retry survives a partially erased reservearea identity block");fail_write=731;assert(call("restore")==1);assert(staged&&flash_changed&&!reset_count);assert(digest_matches(nand_data+0xde0c000,0x1000,stock_eeprom_sha)!=0);fail_write=0;usb_unavailable=1;erase_count=write_count=write_region_count=0;previous_region=-1;assert(call("retry")==0);complete();pass();
	setup("readback mismatch stops restore without reboot");fail_readback=1;assert(call("restore")==1);assert(staged&&flash_changed&&!reset_count);pass();
	setup("retry without retained stage rejected");assert(call("retry")==1);assert(!erase_count&&!write_count&&!reset_count);pass();
	setup("layout checks NAND without USB or flash writes");assert(call("layout")==0);assert(!erase_count&&!write_count&&!usb_starts);pass();
	setup("raw backup refuses missing USB");usb_unavailable=1;assert(call("backup")==1);assert(!erase_count&&!write_count&&!backup_writes);pass();
	setup("raw backup refuses bad NAND block before USB writes");bad_block=0x100000;assert(call("backup")==1);assert(!erase_count&&!write_count&&!backup_writes);pass();
	setup("raw backup copies all 12 ranges with per-chunk USB readback");assert(call("backup")==0);assert(backup_writes>12);
	for(int i=0;i<12;i++){assert(backup_len[i]==stock_files[i].size);assert(!memcmp(backup_data[i],nand_data+stock_files[i].offset,backup_len[i]));}
	assert(!erase_count&&!write_count&&!reset_count);pass();
	setup("raw backup refuses a corrupted USB readback");backup_read_corrupt=1;assert(call("backup")==1);assert(backup_writes>0&&!erase_count&&!write_count);pass();
	report=fopen(argv[2],"wb");assert(report);
	fprintf(report,"{\"tests\":%d,\"passed\":%d,\"actual_production_command_compiled\":true,\"physical_flash_performed\":false,\"scope\":\"host API fault injection, in-memory NAND; USB/PHY not emulated\"}\n",total_tests,total_tests);fclose(report);
	if(stage_size)release_stage();
	free(nand_data);
	printf("ALL %d HOST TESTS PASSED\n",total_tests);return 0;
}
