# XSW250NS r5 USB 2.0 / NAS — đang kiểm thử

Build ID: `xsw250ns-20261104-r5-usb-nas`. Đây là cấu hình build native mới, chưa phải xác nhận đã nhận USB trên router thật.

Đã đọc ảnh và ghi chú tại `mod/usb` trên nhánh main của repo. Sơ đồ chỉ có D+/D− và VBUS 5 V; không có đường SuperSpeed. Source bật hai USB2 root ở chế độ high-speed, chỉ khai báo PHY USB2 và tắt cổng USB3 của xHCI. Ảnh chưa xác định USB0 hay USB1 nên cần UART thực tế để xác nhận root nối ra giắc. Không đoán GPIO nguồn; nguồn 5 V do mạch mod ngoài cấp.

Gói `kmod-usb3` có tên như vậy vì AN7581 dùng bộ điều khiển xHCI/MediaTek cho cả USB2; không có nghĩa giắc mod thành USB3. USB core, xHCI MTK, mass-storage, UAS, ext4/exFAT/FAT/NTFS3 và NLS được build cùng kernel. Có `block-mount`, `blockd`, `lsusb`, công cụ filesystem và trang điểm gắn kết LuCI. Bổ sung CDC Ethernet/NCM, RNDIS, ACM và serial CH341/CP210x/FTDI để dùng điện thoại hoặc thiết bị USB tương ứng khi được cấu hình.

NAS dùng Samba4 userspace và LuCI. Mặc định chỉ bind LAN, SMB2.1 đến SMB3.1.1, không SMB1/NTLMv1, không mật khẩu rỗng hoặc tự hạ thành guest; chưa có thư mục chia sẻ và dịch vụ chưa bật tự khởi động. Không mở cổng NAS từ WAN. Không có mật khẩu NAS dùng chung trong firmware.

Sau khi kiểm tra USB nhận đúng: vào System → Mount Points, chọn partition theo UUID và đặt điểm gắn `/mnt/...`; không bật tự định dạng. Tạo tài khoản NAS và mật khẩu riêng qua SSH (`groupadd nas`, `useradd -M -g nas -s /bin/false nas`, rồi `smbpasswd -a nas`), cấp quyền thư mục cho tài khoản đó. Xác nhận ổ đã mount trước khi tạo thư mục để tránh vô tình ghi dữ liệu vào NAND. Sau đó vào Services → Network Shares, tạo share đúng điểm gắn, giới hạn người dùng, tắt guest và force-root; bật Samba tại System → Startup. Firmware không tự tạo user hay mật khẩu thay bạn. Ổ dùng chủ yếu cho NAS nên chọn ext4; exFAT/NTFS/FAT có sẵn cho ổ dùng cùng Windows.

Phần bảo mật kế thừa bản vá FIFO gây treo diagnostics và giới hạn API cổng 2.5G để không lộ cấu hình VPN. LED trạng thái đọc qua RPC có phạm vi cố định. Startup không chạy kiểm tra sống của từng init script khi chỉ cần danh sách bật/tắt. OpenVPN lên 2.7.8 để bao gồm bản vá CVE-2026-84790.

Giới hạn: VM kiểm thử userland/API, lưu trữ và mạng ảo; không xác nhận hàn, điện áp/dòng tải, PHY Airoha, độ ổn định USB thật hay thông lượng NAS. Không suy ra tốc độ 480 Mb/s là tốc độ sao chép tệp thực tế. Kết quả build, checksum và trạng thái kiểm thử phải xem trong evidence của đúng bản.
