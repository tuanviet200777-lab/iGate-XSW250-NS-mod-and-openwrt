#!/usr/bin/env python3
from pathlib import Path
import sys
config=Path(sys.argv[1]).read_text()
keys=['ARM64','TARGET_AN7581','USB','DM_USB','USB_STORAGE','USB_XHCI_HCD','USB_XHCI_MTK',
      'CMD_USB','FS_FAT','CMD_FAT','GENERIC_PHY','PHY_AIROHA_USB2','CMD_XSWSTOCK',
      'CMD_HASH','SHA256','LMB','EVENT','ENV_IS_IN_UBI']
for key in keys:assert f'CONFIG_{key}=y\n' in config,key+' missing from resolved configuration'
assert 'CONFIG_TEXT_BASE=0x81e00000\n' in config
assert 'CONFIG_DEFAULT_DEVICE_TREE="airoha/an7581-xsw250ns-usb-stock"\n' in config
print('PASS: USB2, restore command, memory, hash and board selections resolved')
