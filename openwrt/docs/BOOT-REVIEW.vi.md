# Rà soát firmware r3 và r3-nand1 theo thứ tự thực thi

Ngày: 04/11/2026. Đọc trực tiếp rootfs trong ITB, đối chiếu log UART mới và mã đóng gói/kiểm thử. Không ghi flash hoặc kết nối router.

## Phát hiện 1 — firmware r3 ghi /etc quá sớm

**Mức ảnh hưởng: lỗi chức năng preinit.** Hook r3 `04_xsw250ns_ubootenv`, dòng 19–24, tạo file và chạy các hàm ghi UCI trước khi overlay mount. Trong RAM recovery, `/etc` ghi được nên lỗi có thể không lộ; trên SquashFS/NAND thì báo Read-only, UCI và thiếu reader environment.

| Bước | Mã thực tế | Kết quả rà soát |
|---|---|---|
| 1 | Kernel mount SquashFS readonly | Bình thường; log xác nhận ở dòng 1128/1876 |
| 2 | `/etc/preinit` nạp `/lib/preinit/*` theo thứ tự và chạy `preinit_main` | Hook file 10 đứng trước file 80 |
| 3 | `10_indicate_preinit`: `preinit_config_board`, dòng 96, gọi `/bin/board_detect /tmp/board.json` | Đã chạy board scripts khi overlay chưa có |
| 4 | `bin/board_detect`, dòng 25, duyệt `/etc/board.d/*` | Chạy 04 trước 05, từ SquashFS đang làm root |
| 5 | `04_xsw250ns_ubootenv`, dòng 19, `touch /etc/config/ubootenv` | Sai giai đoạn; log dòng 1140/1888 báo EROFS |
| 6 | Dòng 20, `ubootenv_add_ubi_default`; dòng 23–24, load và xuất config | Hàm thư viện dùng `uci batch/commit`, ghi `/etc/fw_env.config`; cùng bị ảnh hưởng bởi root readonly |
| 7 | `05_fw_defaults`: `fw_loadenv` gọi `fw_printenv` | Reader chưa có, nên log thiếu fw_env.config và fallback NVMEM; không chứng minh EEPROM radio hỏng |
| 8 | `80_mount_root`, dòng 37, mới gọi `mount_root start` | Log dòng 1202/1950 mới chuyển sang UBIFS overlay |
| 9 | `82_config_generate`, dòng 7, chạy defaults environment sau mount | Đúng thời điểm ghi UCI, nhưng không xóa được lỗi đã phát sinh ở bước 5–7 |

Image r3-nand1 thay hook và thêm reader symlink vào chính SquashFS, nên sửa được nguyên nhân ở bước 5. Đây là kết luận theo mã và cấu trúc image, còn cần UART sau boot r3-nand1 để xác nhận thực tế.

## Phát hiện 2 — khuyến nghị add-on trước đây không sửa được lỗi này

**Mức ảnh hưởng: cách triển khai sai, có thể báo đã sửa nhưng lỗi vẫn còn.** Installer cũ chép hook và symlink vào overlay UBIFS của r3. Ở bước 3–7, overlay chưa mount nên máy vẫn chạy hook cũ từ SquashFS. Hook mới chỉ xuất hiện sau bước 8.

Nếu `/etc/board-base.json` đã có trong overlay thì `board_detect` sau mount có thể không chạy lại hook. Khi đó symlink mới trong overlay còn có thể trỏ tới `/tmp/xsw250ns-fw_env.config` chưa được tạo ở lần boot mới, làm reader runtime không hoạt động cho tới khi chạy lại hook bằng tay. Không dùng tình trạng đó làm một bản sửa bền vững.

Đã thu hồi cách cài add-on. Installer ở workspace được chặn ngay đầu; gói đã rà soát không phân phối installer này. Image sysupgrade r3-nand1 giữ nguyên byte vì đã chứa sửa trong lower SquashFS.

## Phát hiện 3 — ca test “reboot” cũ không mô hình đúng boot

**Mức ảnh hưởng: kiểm thử đưa ra kết luận quá rộng.** `legacy-test-installer.py.txt`, dòng 63–64, xóa file `/tmp` rồi gọi thẳng hook mới trong cây đã cài overlay. Đây là kiểm tra hook tự tạo lại config, không phải boot từ SquashFS cũ rồi mount overlay. Vì vậy năm ca installer cũ không chứng minh add-on sửa được lỗi đầu boot.

Checker cũ chỉ đọc `/etc`, reader hiện tại và mount UBIFS. Đã tái hiện nó trả PASS khi runtime có file mới nhưng `/rom` vẫn là r3. Checker mới xác minh cả build ID, hash hook và symlink trong `/rom`, đồng thời chấp nhận conffile thường được sysupgrade giữ lại chỉ khi nội dung khớp reader runtime mới.

## Những phần khác đã đối chiếu

- FIT rootfs position/size, CRC32/SHA1 payload và CRC metadata trailer hợp lệ; kernel/DTB không đổi byte.
- Root UID/GID/mode/mtime, các tệp giữ lại, hardlink và số thiết bị `dev/console` đã được đối chiếu với r3. Không có bằng chứng hiện tại về lỗi đóng gói ở các mục đó.
- Các điều kiện board, tên volume, node character và LEB trong hook mới dùng đúng profile UBI được log xác nhận; không hardcode số volume. Chưa xác minh trên NAND thật bằng hook mới.
- Hook mới chỉ ghi cấu hình reader vào `/tmp`, không gọi `fw_setenv` hoặc công cụ ghi/xóa flash.
- Đồng hồ, LED, đổi vai trò cổng, Hotfix AI/VPN được giữ nguyên từ r3; không suy diễn rằng chúng đã qua kiểm thử phần cứng trong lần rà soát này.
- Log có MAC U-Boot toàn ff và Linux sinh random MAC ở nhiều lần boot. Đây là lỗi danh tính mạng còn tồn tại, tách khỏi lỗi trình tự đọc environment; không gán MAC mặc định của máy khác để che cảnh báo.
- Không thấy bad/corrupted PEB trong phần log đã đọc. `available PEBs: 0`, mount SquashFS readonly, initramfs fallback, PCI reconfiguration và lần khởi tạo UBIFS đầu không tự chứng minh NAND hỏng.

## Bằng chứng đi kèm

- `boot-order-results.json`: thứ tự hook được trích từ ITB và ba trường hợp r3 / r3+addon / image nand1.
- `rom-checker-results.json`: kiểm thử checker cũ báo PASS sai, checker mới nhận đúng lower image và từ chối trạng thái không đủ điều kiện.
- `base-r3/`: bản trích chọn script gốc, có thể mở để xem đúng số dòng được dẫn ở trên.
- `legacy-install-nand-fix.sh.txt`, `legacy-test-installer.py.txt`: mã cũ được giữ làm bằng chứng, không phải hướng dẫn cài.

Không có phép thử reboot router mới trong lần rà soát này. Hash/FIT hợp lệ không thay thế kiểm thử boot và lưu cấu hình trên phần cứng.
