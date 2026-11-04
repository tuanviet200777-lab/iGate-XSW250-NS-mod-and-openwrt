# XSW250-NS r3-nand1 — hướng dẫn đã rà soát lại

Ngày rà soát: 04/11/2026. **Khuyến nghị dùng add-on trong câu trả lời trước đã được thu hồi.** Add-on chỉ sửa overlay, còn lỗi xảy ra trước khi overlay được mount. Gói phát hành đã rà soát chỉ cung cấp image sysupgrade và script kiểm tra; không cung cấp cách cài add-on để sửa lỗi này.

## Đã xác định sai ở đâu?

Firmware r3 gọi `04_xsw250ns_ubootenv` từ `board_detect` trong preinit. Tại thời điểm đó root là SquashFS chỉ đọc. Các lệnh tạo `/etc/config/ubootenv`, gọi UCI và tạo `/etc/fw_env.config` không thể hoàn tất, gây nhóm lỗi Read-only/UCI/fw_env/NVMEM trong log.

Image r3-nand1 sửa ngay bản script trong **SquashFS gốc**, tạo reader config trong `/tmp` và có sẵn symlink `/etc/fw_env.config`. Chỉ chép các file đó vào overlay của r3 cũ không thay được script đang chạy ở giai đoạn preinit. Bộ kiểm tra cũ cũng chưa kiểm tra `/rom`, nên có thể PASS khi hệ thống vẫn boot từ image r3 cũ.

**Image ITB r3-nand1 không thay byte trong lần rà soát này**; phần phải sửa là khuyến nghị add-on, bộ kiểm tra và phạm vi kết luận từ các test. SHA-256 của image vẫn là:

`5c0a9cc947a4cbbb176e74d0f1694b6718662ebe3e87a7dbe1ddf2b0ca830b77`

## Nội dung gói đã rà soát

- `firmware/openwrt-airoha-an7581-vnpt_xsw250ns-ubi-squashfs-sysupgrade.itb`: image đã có sửa trong SquashFS.
- `kiem-tra/check-nand-fix.sh`: kiểm tra bản script trong `/rom` và trạng thái reader/UBIFS hiện tại.
- `ky-thuat/`: patch nguồn, config, manifest, kết quả phân tích thứ tự boot và kiểm thử checker.
- `RA-SOAT-TUNG-BUOC.md`: bằng chứng và giới hạn của lần rà soát.
- `SHA256SUMS`: checksum các tệp trong gói.

## Cài image

Log mới đã xác nhận máy dùng U-Boot 2026.07, đọc FIT từ volume NAND và mount overlay UBIFS thành công. Trước khi cài, sao lưu cấu hình cần giữ; kiểm tra thiết bị hiện tại vẫn đúng board/layout đó.

Qua LuCI: System → Backup / Flash Firmware, chọn image trong thư mục `firmware`, đọc kết quả kiểm tra tương thích rồi mới thực hiện nâng cấp. Không ép qua lỗi kiểm tra image. Giữ UART để ghi lại lần boot đầu của image mới. Không cần ghi BL2/FIP cho lỗi preinit này.

Nếu muốn kiểm tra image qua SSH trước khi ghi, chép image vào `/tmp` rồi chạy:

```sh
sysupgrade -T /tmp/openwrt-airoha-an7581-vnpt_xsw250ns-ubi-squashfs-sysupgrade.itb
```

`-T` là kiểm tra image, không phải lệnh cài và cũng không chứng minh boot thật thành công. Có thể tiếp tục cài qua LuCI sau bước kiểm tra.

Menu U-Boot "Load production system via TFTP then write to NAND" trong log xóa/tạo lại `fit` và `rootfs_data`. Thao tác đó có thể xóa cấu hình, nên không dùng việc flash lại bằng menu này làm phép thử giữ cấu hình qua reboot. Giữ Recovery ITB r3 gốc để cứu hộ RAM nếu cần.

## Kiểm tra sau khi boot

Chép file `kiem-tra/check-nand-fix.sh` vào router, ví dụ `/root/check-nand-fix.sh`, rồi chạy:

```sh
sh /root/check-nand-fix.sh
```

Checker mới phải xác nhận:

1. `/rom/etc/xsw250ns-build-id` là `xsw250ns-hotfix-20261029-r3-nand1`.
2. Hook `04_xsw250ns_ubootenv` trong `/rom` đúng hash đã kiểm tra và symlink reader có trong lower image.
3. Reader runtime có hai dòng đúng với cấu hình UBI vừa phát hiện; nếu sysupgrade giữ một `fw_env.config` dạng file thường cũ thì chỉ chấp nhận khi nội dung khớp.
4. `fw_printenv` đọc được environment và `/overlay` là UBIFS đang mount ghi được. Không in các giá trị environment ra màn hình.

Ngoài kết quả checker, phải đối chiếu UART từ đầu boot để xác nhận hết lỗi `touch ... Read-only file system`, `uci: Entry not found`, thiếu `fw_env.config` và NVMEM do reader. Thử đổi một cấu hình vô hại, reboot bình thường không flash lại, rồi kiểm tra cấu hình còn được giữ.

Nếu trước đó đã cài add-on cũ: runtime có thể báo build ID mới dù `/rom` vẫn là r3. Checker mới sẽ từ chối trạng thái này. Đừng coi build ID ở `/etc` hoặc kết quả checker cũ là bằng chứng preinit đã sửa. Trường hợp đó cần image có sửa trong SquashFS; không tiếp tục dùng lại installer add-on cũ.

## Phạm vi đã kiểm chứng

Đã đọc các script boot trực tiếp từ hai ITB, xác định thứ tự hook, xác minh khác biệt lower/overlay; tái hiện checker cũ PASS sai và checker mới từ chối, kiểm tra trường hợp `/rom` đúng/sai cùng conffile được giữ lại. Các ca shell dùng fixture MSYS và `fw_printenv` giả lập; chưa chạy kernel/UBIFS/NAND thật trong lần rà soát này.

FIT/payload và metadata của image đã qua kiểm tra; kernel/DTB giữ nguyên byte, root filesystem giữ metadata và hardlink như báo cáo. **Chưa boot r3-nand1 trên router thật.** Lỗi MAC `ff:ff:ff:ff:ff:ff`/random fallback, PON/TEL và các giới hạn phần cứng đã ghi trước vẫn cần xử lý/kiểm chứng riêng.
