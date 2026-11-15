# Kết quả U-Boot USB rollback — 05/11/2026

Đã build và kiểm tra tĩnh FIP mới cho **VNPT iGate XSW250-NS**, U-Boot 2026.07. **Chưa boot candidate, nhận USB hoặc ghi NAND trên phần cứng thật.** Đây là candidate để thử UART/RAM và `xswstock check` trước.

- Nguồn biên dịch: `145ba7cdac5902c89ac1abb8c3a9ad19bc2dc6e8`.
- [CI 41980418648](https://github.com/tuanviet200777-lab/iGate-XSW250-NS-mod-and-openwrt/actions/runs/41980418648): host tests, source verification, cross-compile, FIP packing và artifact checks đều thành công.
- FIP: `openwrt-airoha-an7581-vnpt_xsw250ns-ubi-usb-stock-bl31-uboot.fip`, **342.420 byte**.
- SHA256: `14596df91783e5298adc38db75d80e730f31b863b0665c070926de1a5bb973cd`.

## Kiểm tra ảnh thực

Binary ARM64 có entry `0x81e00000`, chứa đúng DTB, driver xHCI/USB2 và lệnh rollback. Có đủ 12 bộ kích thước/offset/SHA256 cùng hash calibration trong binary. FIP chứa đúng BL33 vừa build; payload BL31 nén giữ nguyên byte từ FIP XSW250NS đầu vào, SHA256 `9c16b893ec8a904ce0c1f287180267b0892933416d8f35040607ce56c0423a05`. Không tạo hoặc đổi BL2/preloader.

Đối chiếu độc lập cho thấy **65 node cũ cùng toàn bộ property giữ nguyên** so với DTB trong FIP đã cung cấp; chỉ thêm bốn node USB/PHY. Hai root USB `0x1fab0000`/`0x1fad0000` chỉ tham chiếu PHY USB2, high-speed và tắt cổng USB3. Bộ PHY chỉ truy cập thanh ghi USB2; không đổi SerDes PCIe.

DTC cảnh báo vì source decompile dùng số phandle thay cho tham chiếu `&label`. Đã xác minh trực tiếp **33 tham chiếu clock/PHY/reset/GPIO** đều trỏ đến provider thật và có đúng số cell; đồng thời so khớp toàn bộ node cũ. Không dùng suppress-warning để bỏ qua liên kết hỏng.

Nguồn U-Boot, 41 patch nền, PHY Linux tham khảo và FIP đầu vào được ghim trong `sources.json`. Ba ZIP artifact tải về đã khớp digest GitHub trước khi giải nén. Có kiểm tra lại FIP/ELF/DTB và cấu hình resolved ở máy cục bộ.

## Kiểm thử lệnh ghi với NAND giả lập

**19/19 đạt** khi biên dịch chính `xswstock.c` bằng GCC và chạy với bản backup thật trong RAM trên máy cục bộ; **19/19 đạt** trên Ubuntu CI dùng dữ liệu tổng hợp, không upload backup riêng. Các API filesystem/MTD/console được thay bằng shim để chèn lỗi; đây không phải mô phỏng controller USB/NAND vật lý.

Các tình huống gồm menu environment cũ/mới, check không ghi, USB lỗi, thiếu/truncated/hỏng file, sai board/geometry/calibration, bad block, hủy xác nhận, không detach được UBI, xóa/ghi lỗi, đọc lại sai byte, retry không cần USB khi backup còn trong RAM và retry sau khi vùng calibration bị xóa dở. Ca thành công so byte đủ tám vùng cuối cùng, giữ nguyên các khoảng không có backup/BMT, kiểm tra bootloader được ghi cuối và block số 0 là lần ghi cuối trước reset.

Bộ `nandback2.zip` đã qua CRC; đủ 12 SHA256 và bốn phép so vùng chồng nhau. Mtd2/3 là tập con của mtd4, mtd5/6 là tập con của mtd7. Lệnh không nối 12 file thành một ảnh raw toàn chip và không ghi chồng các vùng này.

## Giới hạn cần giữ rõ

Driver PHY mới được port và biên dịch, chưa có UART chứng minh nó nhận giắc USB đã mod. Chưa thử đường hàn/nguồn 5 V, reset nóng/lạnh, NAND ECC thực, BMT/bad block của thiết bị hoặc boot lại firmware hãng. Mọi lỗi preflight đều dừng trước xóa; kiểm tra này không làm thao tác ghi bootloader trở nên nguyên tử khi mất nguồn.

Các JSON ở [evidence](evidence/) tách kiểm tra ảnh, host test thật/synthetic và kiểm tra backup. Không có raw MTD hoặc khóa/calibration trong artifact công khai. Đọc [hướng dẫn thao tác](README.vi.md) và thử `xswstock check` trong candidate nạp RAM trước; chưa coi candidate là bootloader đã kiểm chứng trên máy thật.
