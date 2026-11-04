# Build firmware r5 USB 2.0/NAS cho XSW250-NS

Nguồn r5: nhánh `codex/xsw250ns-native-build` của repo `tuanviet200777-lab/iGate-XSW250-NS-mod-and-openwrt`. Nhánh `main` hiện chủ yếu chứa ghi chú phần cứng và bootloader. `build_stock_all_flash.py` ghép backup hãng; nó không biên dịch firmware OpenWrt.

## Nguồn và cấu hình cần giữ đúng

- Nền ImmortalWrt: `e695009c15c623f4f6a83376b505faaf7a4ae5b5`.
- Target `airoha/an7581`, profile `vnpt_xsw250ns-ubi`.
- Áp đúng một patch đầy đủ `patches/xsw250ns-support-r5-usb-nas.patch`; không áp chồng patch r4.
- Ghim đủ năm feeds bằng `config/feeds.pinned.conf`, rồi áp `patches/openvpn-2.7.8.patch` vào feed packages.
- Script prepare cũng áp patch Samba vào feed packages và patch menu Startup vào feed LuCI. Ba tệp này thuộc gói Samba/LuCI; đưa chúng vào board `base-files` gây lỗi APK `trying to overwrite` ở bước ghép rootfs.
- Dùng `config/xsw250ns.full.config`, chạy `make defconfig` và kiểm tra cấu hình đã resolve.

## Vì sao cần build cả kernel

R4 chưa bật node USB trong Device Tree và chưa chứa bộ module lưu trữ USB tương ứng. Chỉ thêm giao diện Samba hoặc chép module từ snapshot khác không đủ. R5 cần build Device Tree, kernel, module và rootfs cùng bộ nguồn/cấu hình.

AN7581 dùng xHCI MediaTek. Trong Makefile của đúng commit nền, `kmod-usb3` phụ thuộc `kmod-usb-xhci-mtk` khi target là AN7581. PHY Airoha USB đã được bật trong cấu hình kernel nền. Tên gói này không biến đường D+/D− thành USB SuperSpeed.

Patch PHY của nền nêu USB2 hoạt động độc lập với cấu hình SerDes USB3; nếu không dùng USB3 phải tắt cổng USB3 trong xHCI. Vì vậy r5 chỉ tham chiếu `PHY_TYPE_USB2` và đặt `mediatek,u3p-dis-msk = <1>`. Hai root USB2 được bật do ảnh mod chưa xác định root nối ra giắc; cần UART máy thật xác nhận. Nguồn VBUS 5 V lấy từ phần cứng mod, không gán GPIO chưa biết.

## Các bước trên Linux

Dùng Linux/WSL2 với cây build trong filesystem Linux phân biệt hoa/thường, tài khoản thường và dependency theo tài liệu OpenWrt. Không build trực tiếp trong Desktop NTFS.

```bash
git clone --branch codex/xsw250ns-native-build --single-branch \
  https://github.com/tuanviet200777-lab/iGate-XSW250-NS-mod-and-openwrt.git xsw250ns-source
cd xsw250ns-source
git rev-parse HEAD  # lưu commit của bộ handoff vào hồ sơ build
bash openwrt/scripts/prepare-build.sh "$HOME/xsw250ns-r5-build"
python3 openwrt/tests/test_fit_import.py
python3 openwrt/scripts/check-native-profile.py "$HOME/xsw250ns-r5-build"
cd "$HOME/xsw250ns-r5-build"
make -j4 download
set -o pipefail
make -j2 V=s 2>&1 | tee ../xsw250ns-r5-build.log
```

Chỉ chạy bước sau nếu bước trước thành công. Dừng khi có lỗi, giữ log và dùng `make -j1 V=s` để chẩn đoán. Chọn số job theo RAM của máy build. Script prepare yêu cầu thư mục đích mới để giữ nguyên các cây nguồn đã có.

## Kiểm tra trước khi gọi là gói firmware hoàn tất

Trong thư mục `xsw250ns-source`, chạy:

```bash
python3 openwrt/scripts/check-built-images.py \
  "$HOME/xsw250ns-r5-build/bin/targets/airoha/an7581" \
  "$HOME/xsw250ns-r5-verification"
```

Cần có đủ một recovery ITB và một sysupgrade ITB, hash FIT đúng, đúng board, bản sửa NAND ở lower SquashFS và các module/tiện ích USB/NAS trong image thực. Lưu `.config` đã resolve, `config.buildinfo`, `feeds.buildinfo`, `version.buildinfo`, checksum, log và JSON kiểm tra cùng image. Kết quả kiểm thử r4 là lịch sử, không tự chứng nhận r5.

Sau boot recovery trên máy thật, kiểm tra `dmesg`, `lsusb -t`, `block info`, nhận ổ, mount/unmount và hai radio PCIe còn hoạt động. Thử tệp trên ổ thử nghiệm rồi so checksum, thử Samba bằng tài khoản riêng trong LAN, và kiểm tra lưu cấu hình qua reboot. VM QEMU virt không mô phỏng USB PHY, NAND hay radio AN7581 nên chưa xác nhận các bước này. Chưa coi 480 Mb/s là thông lượng NAS thực tế.

## Nguồn đối chiếu

- [OpenWrt: chuẩn bị môi trường build](https://openwrt.org/docs/guide-developer/toolchain/install-buildsystem).
- [OpenWrt: sử dụng Build System](https://openwrt.org/docs/guide-developer/toolchain/use-buildsystem).
- [OpenWrt: thêm thiết bị](https://openwrt.org/docs/guide-developer/adding_new_device).
- [OpenWrt: lưu trữ USB](https://openwrt.org/docs/guide-user/storage/usb-drives-quickstart).
- [Ghi chú mod USB của thiết bị](https://github.com/tuanviet200777-lab/iGate-XSW250-NS-mod-and-openwrt/tree/main/mod/usb).
- [Makefile USB của đúng nền](https://github.com/tuanviet200777-lab/immortalwrt/blob/e695009c15c623f4f6a83376b505faaf7a4ae5b5/package/kernel/linux/modules/usb.mk).
- [Patch PHY AN7581 của đúng nền](https://github.com/tuanviet200777-lab/immortalwrt/blob/e695009c15c623f4f6a83376b505faaf7a4ae5b5/target/linux/airoha/patches-6.18/220-07-phy-airoha-Add-support-for-Airoha-AN7581-USB-PHY.patch).
- [Binding xHCI MediaTek trong Linux](https://github.com/torvalds/linux/blob/master/Documentation/devicetree/bindings/usb/mediatek%2Cmtk-xhci.yaml).

Các trang wiki bị Anubis chặn truy cập trực tiếp trong phiên 04/11/2026; nội dung hướng dẫn được đối chiếu qua bản lập chỉ mục trên openwrt.org. Makefile và patch của nền đã đọc trực tiếp qua GitHub.
