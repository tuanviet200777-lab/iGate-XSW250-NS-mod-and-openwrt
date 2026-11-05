# U-Boot XSW250-NS: khôi phục firmware gốc từ USB

Đã có FIP candidate build thành công, xem [kết quả và checksum](VALIDATION.vi.md).

Mục menu mới: **Restore original firmware from USB (erases OpenWrt)**. Nhận USB bằng xHCI/PHY USB2 riêng cho AN7581; không bật SerDes USB3 hoặc đoán GPIO nguồn. Bản này cần thử RAM/UART trên máy thật trước khi dùng để ghi flash. Việc build và kiểm thử giả lập không xác nhận PHY USB hoặc boot NAND vật lý.

## Chuẩn bị USB

Dùng đúng bộ `nandback2.zip` đã xác nhận: **12 file mtd0 đến mtd11**. Không dùng file của máy khác. Các SHA256 và kích thước được cố định trong lệnh U-Boot; đây không phải trình nạp script tùy ý từ USB.

USB dùng FAT32, nên dùng một partition đầu tiên. Giải nén và đặt thư mục như sau, không để nguyên file ZIP trên USB:

```text
USB:/XSW250NS-STOCK/
  mtd0-bootloader.bin
  mtd1-romfile.bin
  mtd2-kernel.bin
  mtd3-rootfs.bin
  mtd4-tclinux.bin
  mtd5-kernel_slave.bin
  mtd6-rootfs_slave.bin
  mtd7-tclinux_slave.bin
  mtd8-config.bin
  mtd9-userdata.bin
  mtd10-safedata.bin
  mtd11-reservearea.bin
  SHA256SUMS
```

Có thể tạo thư mục staging bằng `python3 uboot/scripts/prepare-usb.py /path/nandback2.zip /path/staging`, rồi chép `XSW250NS-STOCK` ra gốc USB. Script kiểm tra đủ SHA256 và các vùng chồng nhau trước khi chép; không format ổ. Backup chứa cấu hình, khóa/dữ liệu riêng và calibration: giữ bộ USB riêng, không đăng công khai.

## Thử trước bằng UART/RAM

FIP mới giữ nguyên BL31 nén của FIP XSW250NS đã cung cấp và thay BL33 bằng U-Boot vừa build. Không có thay đổi BL2/preloader. Ưu tiên dùng chế độ nạp FIP qua UART/XMODEM vào RAM của BL2 hiện tại để thử; chưa ghi FIP mới hoặc preloader chỉ vì đã build thành công. Đây là bước đưa candidate vào RAM, khác với mục ghi FIP vào NAND trong menu.

Sau khi vào candidate, kiểm tra log USB và chạy:

```text
usb tree
usb storage
xswstock check
```

`xswstock check` kiểm tra toàn bộ file, SHA256, quan hệ kernel/rootfs với hai slot, board, hình học NAND, bad block và dấu vân tay calibration hiện tại. Lệnh này không xóa/ghi NAND. Nếu USB không nhận hoặc check thất bại, dừng ở đây và giữ UART log để chẩn đoán; không đổi offset hoặc bỏ kiểm tra.

## Khôi phục gốc

Chỉ thực hiện khi chấp nhận xóa OpenWrt/cấu hình hiện tại và có nguồn ổn định cùng đường phục hồi UART. Cắm USB và chọn mục **Restore original firmware from USB (erases OpenWrt)**. Vị trí số thứ tự có thể khác khi environment cũ giữ menu riêng.

U-Boot đọc đủ 12 file vào RAM và xác minh trước. Sau khi báo PASS, nhập đúng `RESTORE-STOCK` để bắt đầu; ENTER để hủy. Sau xác nhận, thao tác xóa/ghi/đọc lại và reboot được thực hiện tự động. USB không còn được đọc trong giai đoạn ghi NAND.

Chỉ tám vùng độc lập được ghi: mtd4, mtd7, mtd8, mtd9, mtd10, mtd11, mtd1 và **mtd0 cuối cùng**. Mtd2/3/5/6 được kiểm tra đối chiếu, không ghi chồng lên slot. Trong mtd0, block đầu tiên được ghi sau cùng. Mỗi eraseblock đều đọc lại so byte. Không dịch offset khi có bad block, không ghi OOB hoặc vùng trống/BMT không có backup.

**Đây là về firmware và bootloader hãng**, không giữ U-Boot OpenWrt sau khi hoàn tất. Bộ này khôi phục các vùng MTD đã backup; không được gọi là ảnh raw toàn chip kèm OOB/BMT.

Nếu lỗi sau khi bắt đầu ghi: **giữ nguồn**, không reset. Lệnh giữ backup đã kiểm tra trong RAM; có thể chạy `xswstock retry` để thử lại và xác nhận lần nữa. Lỗi bad block không được tự bỏ qua. Nếu mất nguồn giữa chừng, RAM mất và có thể cần phục hồi qua UART/programmer; thao tác này không có tính nguyên tử.

## Build lại

Trên Linux, cài GCC AArch64, make, bison, flex, libssl-dev, libgnutls28-dev, Python development/setuptools, swig và dtc. Sau đó:

```bash
python3 uboot/scripts/prepare-build.py "$HOME/xsw250ns-uboot"
cd "$HOME/xsw250ns-uboot"
make ARCH=arm CROSS_COMPILE=aarch64-linux-gnu- an7581_xsw250ns_usb_stock_defconfig
python3 /path/source/uboot/scripts/check-config.py .config
make -j4 ARCH=arm CROSS_COMPILE=aarch64-linux-gnu-
```

Nguồn U-Boot 2026.07 và toàn bộ patch nền được ghim trong `sources.json`; chuẩn bị nguồn kiểm tra SHA256/Git blob. Packer `scripts/pack-fip.py` bắt buộc FIP gốc có đúng SHA256 đã biết và giữ nguyên payload BL31. Workflow riêng chỉ build U-Boot, không thay firmware r5 trước đó. Không công bố các MTD backup trong artifact CI.
