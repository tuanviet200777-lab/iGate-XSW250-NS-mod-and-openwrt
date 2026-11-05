# Kết quả native r5 USB 2.0/NAS — 05/11/2026

Đã build cả recovery và sysupgrade từ commit `b2cb17d69347e95c57b28da71bda498b2cd9fef0`, nền ImmortalWrt `e695009c15c623f4f6a83376b505faaf7a4ae5b5`, kernel 6.18.55. Không flash hoặc kết nối router vật lý trong lần kiểm tra này.

| Ảnh | Dung lượng | SHA256 |
|---|---:|---|
| `immortalwrt-airoha-an7581-vnpt_xsw250ns-ubi-squashfs-sysupgrade.itb` | 24.613.142 byte | `0342ae8dee7114de5683ae7e2237b7c0cc85133e23ea531fc8c3cb16dad31283` |
| `immortalwrt-airoha-an7581-vnpt_xsw250ns-ubi-initramfs-recovery.itb` | 28.573.696 byte | `f79c1068096358572818e653ba7b9e2b6532a2332dc22c248612ff19930819a1` |

[Lượt build 41963638759](https://github.com/tuanviet200777-lab/iGate-XSW250-NS-mod-and-openwrt/actions/runs/41963638759) biên dịch thành công, nhưng verifier cũ thất bại vì `is_file()` theo liên kết tuyệt đối `/usr/bin/lsusb` ra filesystem của host CI. Binary thật có sẵn tại `/usr/libexec/lsusb-usbutils`. Đã sửa checker để kiểm tra binary và đích liên kết trong ảnh. [Lượt xác minh lại 41974285470](https://github.com/tuanviet200777-lab/iGate-XSW250-NS-mod-and-openwrt/actions/runs/41974285470) thành công trên Ubuntu, dùng nguyên hai ITB với SHA256 trên, verifier commit `700c548f38773b233d18ce336439b6b2a85d5fa6`. Không đóng gói lại ITB để sửa lỗi checker.

## Phần đã xác minh

- Hash FIT, ARM64, board UBI, metadata fwtool/CRC, hai USB root chỉ dùng PHY USB2/high-speed, hai root PCIe Wi-Fi vẫn bật trong DTB.
- Kernel recovery chiếm `0x80200000..0x82680000`; không chồng các vùng reserved-memory, gồm NPU bắt đầu `0x84000000`. Initramfs nhúng gzip có 2.109 entry. Kernel sysupgrade kết thúc tại `0x80f70000`.
- Bản sửa NAND/preinit có trong lower SquashFS; `/etc/fw_env.config` là symlink tmpfs. Chín tệp tùy biến khớp nguồn và khớp giữa sysupgrade/recovery; các module xHCI, mass-storage, UAS và filesystem được kiểm tra ARM64/vermagic/byte giữa hai ảnh. Không mang lại AI/API/chat hoặc JSON hotfix.
- 8 reader + 7 ROM-checker fixture NAND đạt trên Linux. Đây là fixture, không phải reboot NAND thật.
- Rootfs chính xác có SHA256 `e63477007e307d865d21d391821354c3cfeacdb7be35fbc6eefca28da156ea1c`, boot trong lab QEMU với upper ext4 mới: **13/13 dịch vụ**, **31/31 hồi quy bảo mật**, **4/4 NAS** đạt. SMB 3.1.1 có mã hóa truyền/đọc lại 128 KiB và khớp checksum trên đĩa; share chỉ đọc chặn ghi, sai mật khẩu bị từ chối, SMB bind LAN.
- Hai trang LuCI **NAS → Network Shares** và **System → Mount Points** tải được trong lab. Không thay cấu hình qua UI.

QEMU dùng kernel riêng `6.18.55-qemu-virt`, mạng/ổ đĩa ảo và các override chỉ dành cho VM. Kiểm tra LED runtime đặt board name của fixture và chế độ `off`; không có LED vật lý. Không nạp module AN7581 vào kernel QEMU. Tài khoản/share/mật khẩu thử nghiệm chỉ nằm trong upper của VM, không có trong ITB.

Hai lựa chọn `shadow-useradd`/`shadow-groupadd` cũ đã bị Kconfig bỏ do menu shadow-utils chưa bật. Đã bỏ hai dòng không có hiệu lực khỏi cấu hình nguồn, và sửa hướng dẫn NAS dùng `group_add_next`/`user_add` có sẵn trong `/lib/functions.sh`, đã thử thành công. Việc dọn hai dòng này không thay đổi cấu hình resolved hoặc binary đã build. Tạo `smb.conf` trước `smbpasswd -a` để chọn đúng backend Samba.

## Phần cần kiểm tra trên router

USB PHY/đường hàn/nguồn 5 V, ổ cắm thực tế nối USB0 hay USB1, nhận và ngắt ổ, tải dài, thông lượng, hai radio, NAND/overlay qua reboot và link 2.5G lúc idle chưa có bằng chứng phần cứng mới. PON/TEL vẫn chưa được hỗ trợ. Chưa tự khôi phục MAC factory trong r5. Không suy từ tốc độ bus USB 480 Mb/s ra tốc độ NAS.

SHA256/FIT/CRC xác minh tính toàn vẹn; lần rà soát này không xác minh tính xác thực chữ ký mật mã của firmware. Các JSON/log đã lọc nằm ở [evidence/r5-native](../evidence/r5-native). Không công bố NAND dump, console chứa mật khẩu fixture, khóa riêng hay đĩa VM.

Đọc [hướng dẫn NAS](R5-USB-NAS.vi.md) và [hướng dẫn build](BUILD-R5.vi.md). Gói dành cho board `vnpt,xsw250ns-ubi` và layout UBI tương ứng; không dùng trực tiếp làm firmware nâng cấp cho layout hãng.
