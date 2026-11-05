// SPDX-License-Identifier: GPL-2.0
/* AN7581 USB2-only PHY. Register sequence adapted from Christian Marangi's
 * Linux phy-airoha-usb.c, pinned in the accompanying source manifest.
 * No USB3/PCIe SerDes registers are accessed. VBUS is supplied by the board mod.
 */
#include <dm.h>
#include <dm/device_compat.h>
#include <generic-phy.h>
#include <asm/io.h>
#include <dt-bindings/phy/phy.h>
#include <linux/bitfield.h>
#include <linux/delay.h>
#include <linux/kernel.h>

struct airoha_u2 {
	void __iomem *base;
	u32 monclk;
};

static void update(struct airoha_u2 *p, u32 reg, u32 mask, u32 value)
{
	clrsetbits_le32(p->base + reg, mask, value & mask);
}

static int airoha_u2_xlate(struct phy *phy, struct ofnode_phandle_args *args)
{
	if (args->args_count != 1 || args->args[0] != PHY_TYPE_USB2)
		return -EINVAL;
	phy->id = PHY_TYPE_USB2;
	return 0;
}

static int airoha_u2_init(struct phy *phy)
{
	struct airoha_u2 *p = dev_get_priv(phy->dev);
	u32 count = 0, sr = 5;
	int i;

	update(p, 0x310, GENMASK(10, 8), 6 << 8);
	update(p, 0x310, GENMASK(2, 0), 2);
	update(p, 0x318, GENMASK(3, 0), 9);
	update(p, 0x318, GENMASK(7, 4), 10 << 4);
	clrbits_le32(p->base + 0x318, BIT(23));
	setbits_le32(p->base + 0x314, BIT(15));
	udelay(1000);
	setbits_le32(p->base + 0x110, BIT(8));
	update(p, 0x100, GENMASK(27, 26), p->monclk << 26);
	update(p, 0x100, GENMASK(23, 0), 1024);
	setbits_le32(p->base + 0x100, BIT(24));
	for (i = 0; i < 10; i++) {
		count = readl(p->base + 0x10c);
		if (count)
			break;
		udelay(1000);
	}
	clrbits_le32(p->base + 0x100, BIT(24));
	clrbits_le32(p->base + 0x110, BIT(8));
	clrbits_le32(p->base + 0x314, BIT(15));
	udelay(1000);
	if (count) {
		sr = (20 * 28 * 1024) / count;
		sr = DIV_ROUND_CLOSEST(sr, 1000);
	} else {
		dev_warn(phy->dev, "USB2 frequency unavailable, default SR=5\n");
	}
	/* Preserve the original field width when calibration rounds high. */
	update(p, 0x314, GENMASK(14, 12), sr << 12);
	setbits_le32(p->base + 0x318, BIT(23));
	udelay(1000);
	return 0;
}

static int airoha_u2_on(struct phy *phy)
{
	struct airoha_u2 *p = dev_get_priv(phy->dev);

	/* Fixed host connector: force IDDIG low, as in the Linux host mode. */
	update(p, 0x36c, BIT(9) | BIT(1), BIT(9));
	clrbits_le32(p->base + 0x318, BIT(23));
	udelay(1000);
	return 0;
}

static int airoha_u2_off(struct phy *phy)
{
	struct airoha_u2 *p = dev_get_priv(phy->dev);

	setbits_le32(p->base + 0x318, BIT(23));
	udelay(1000);
	return 0;
}

static int airoha_u2_probe(struct udevice *dev)
{
	struct airoha_u2 *p = dev_get_priv(dev);
	int ret;

	p->base = dev_read_addr_ptr(dev);
	if (!p->base)
		return -EINVAL;
	ret = dev_read_u32(dev, "airoha,usb2-monitor-clk-sel", &p->monclk);
	if (ret || p->monclk > 3)
		return -EINVAL;
	return 0;
}

static const struct phy_ops airoha_u2_ops = {
	.of_xlate = airoha_u2_xlate,
	.init = airoha_u2_init,
	.power_on = airoha_u2_on,
	.power_off = airoha_u2_off,
};

static const struct udevice_id airoha_u2_ids[] = {
	{ .compatible = "airoha,an7581-usb2-phy" },
	{ }
};

U_BOOT_DRIVER(airoha_usb2_phy) = {
	.name = "airoha-usb2-phy",
	.id = UCLASS_PHY,
	.of_match = airoha_u2_ids,
	.probe = airoha_u2_probe,
	.ops = &airoha_u2_ops,
	.priv_auto = sizeof(struct airoha_u2),
};
