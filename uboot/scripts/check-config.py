#!/usr/bin/env python3

if not __debug__:
    raise RuntimeError("Refusing optimized Python: integrity checks required")
from pathlib import Path
import sys
config=Path(sys.argv[1]).read_text()
keys=['ARM64','TARGET_AN7581','USB','DM_USB','USB_STORAGE','USB_XHCI_HCD','USB_XHCI_MTK',
      'CMD_USB','FS_FAT','CMD_FAT','PHY','PHY_AIROHA_USB2','CMD_XSWSTOCK',
      'CMD_HASH','SHA256','LMB','EVENT','ENV_IS_IN_UBI']
missing=[key for key in keys if f'CONFIG_{key}=y\n' not in config]
assert not missing,'Missing from resolved configuration: '+', '.join(missing)
assert 'CONFIG_TEXT_BASE=0x81e00000\n' in config
assert 'CONFIG_DEFAULT_DEVICE_TREE="airoha/an7581-xsw250ns-usb-stock"\n' in config
print('PASS: USB2, restore command, memory, hash and board selections resolved')
