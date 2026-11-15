# XSW250-NS r4: chẩn đoán chi tiết, đã gỡ AI và hotfix

Build ID: `xsw250ns-20261104-r4-diag-nand1`.

Mở **Hệ thống → Chẩn đoán hệ thống** trong LuCI, bấm **Thu thập toàn bộ chẩn đoán**. Sáu nhóm có bảng trạng thái, cảnh báo kèm bằng chứng và dữ liệu chi tiết có thể mở rộng:

1. Hệ thống: phiên bản, CPU online/cpufreq nếu driver có cung cấp, RAM, load, thời gian, cảm biến nhiệt và LED.
2. Lưu trữ: bảng MTD đang chạy, mount, dung lượng, UBI device/volume, bad PEB/corrupted/upd_marker, reader U-Boot, build ID trong `/rom` và MAC environment nếu đọc được.
3. Mạng: trạng thái từng cổng, MAC/kiểu gán, carrier/speed/duplex/MTU, bộ đếm lỗi và thay đổi carrier, interface LAN/WAN/VPN, IPv4/IPv6, DNS/route, ethtool cổng 2.5G, EEE và thống kê PHY nếu driver hỗ trợ.
4. Wi-Fi: trạng thái radio, khởi tạo thất bại, band/channel/country/htmode/txpower, interface/mode/encryption, module và thông tin `iw`. Không xuất mật khẩu hay toàn bộ cấu hình wireless.
5. Dịch vụ: trạng thái procd của DNS/DHCP/NTP/web/SSH/firewall/VPN/SQM/PBR, DNS resolver, bảng nft và mức sử dụng conntrack. Không thấy một dịch vụ chưa đủ kết luận nó bị lỗi.
6. Log: tối đa 160 sự kiện kernel phù hợp và 180 dòng syslog gần đây, có giới hạn kích thước. Trạng thái thiếu công cụ, không hỗ trợ hoặc hết thời gian được thể hiện trong kết quả.

Các nhóm được lấy lần lượt. Một nhóm lỗi không chặn các nhóm khác; dữ liệu cũ được bỏ khi thu thập lại. Báo cáo JSON ghi cả lỗi thu thập và thời điểm trình duyệt. Trang không tự thu thập khi mở và không có nút lưu/áp dụng cấu hình.

## Phần đã gỡ

Đã bỏ trang Hotfix & AI, nhà cung cấp/model/API key, hỏi đáp, worker gọi mạng, nhập/xem trước/áp dụng/xác nhận/hoàn tác JSON, ACL ghi, RPC cũ, module policy và dịch vụ khôi phục hotfix S18. Việc chẩn đoán không gửi dữ liệu ra Internet, không ping, không tự sửa lỗi hay ghi flash.

Khi boot bản mới, dịch vụ dọn phần cũ chạy sau mount_root và trước S18 cũ. Nó xóa đúng các đường dẫn của tính năng đã bỏ, kể cả khóa API, trạng thái giao dịch và backup của add-on. Không thay cấu hình network/firewall/wireless. Nếu trước đây cài add-on, marker build trong overlay được cập nhật từ `/rom` mới khi có.

**Trước khi nâng cấp từ bản cũ, hoàn tất xác nhận hoặc hoàn tác mọi giao dịch hotfix đang chờ.** Bản mới không tiếp tục bộ đếm hoàn tác; nó giữ cấu hình mạng hiện có và xóa tính năng cũ theo yêu cầu. Sao lưu riêng những cấu hình bạn cần trước khi cài.

## Firmware trong gói

Gói này chỉ phát hành **sysupgrade UBI r4**, dành cho máy XSW250-NS đã chạy chuỗi U-Boot UBI tương thích như log hiện tại. Không kèm recovery cũ vì recovery đó vẫn chứa giao diện đã bỏ. Mã nguồn đầy đủ có thể build cả recovery và sysupgrade mới trên Linux.

Image được đóng gói lại từ sysupgrade r3-nand1 đã kiểm tra: giữ nguyên byte kernel/DTB, thay userland. Đây chưa phải build Linux mới. Bản sửa preinit NAND nằm trực tiếp trong lower SquashFS; không có installer add-on để thay thế image.

Qua LuCI, vào System → Backup / Flash Firmware, chọn image sysupgrade trong `firmware/`, đọc kết quả tương thích. Không bỏ qua lỗi kiểm tra. Không cần thay BL2/FIP cho lần thay đổi này. Thao tác flash/reboot router không được thực hiện trong phiên làm việc này.

Sau boot, kiểm tra build ID, chạy checker trong thư mục `kiem-tra/` và thu log UART từ đầu boot. Sau đó mở trang chẩn đoán, thử lưu một cấu hình vô hại rồi reboot bình thường để kiểm chứng overlay giữ cấu hình.

## Giới hạn cần giữ rõ

Trang có thể chỉ ra dấu hiệu, không tự kết luận linh kiện hỏng. SquashFS read-only là bình thường. UBI có 0 PEB chưa phân bổ không tự chứng minh filesystem đầy. Bad block có thể có từ nhà máy; cần theo dõi thay đổi và lỗi ECC. Link xuống có thể do chưa cắm dây; EEE không đọc được có thể do driver không hỗ trợ.

MAC Ethernet ngẫu nhiên, hiện tượng link flap khi idle, GPIO/LED và cảm biến vẫn cần kiểm chứng trên router. Bản r4 này không tự gán MAC theo backup và không thay driver/DTB để che triệu chứng. PON/TEL vẫn chưa được hỗ trợ.

Log đã được lọc khóa/mật khẩu, giá trị nhạy cảm trong UCI và loại bỏ dòng kernel command line/bootargs. **Báo cáo vẫn có MAC/IP, trạng thái mạng và log; xem lại trước khi gửi người khác.** Không kèm NAND dump, romfile, cấu hình VPN đầy đủ hoặc file API.

Kết quả kiểm tra cụ thể và phạm vi máy ảo nằm trong `ky-thuat/`; kiểm tra trên QEMU virt không thay cho boot từ NAND/UBIFS trên AN7581 thật.
