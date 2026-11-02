# Thông số kỹ thuật phần cứng: VNPT iGate XSW250-NS (XGS-PON ONT Wi-Fi 6)

Repo Openwrt này đc fork lại từ ( https://github.com/voz188/openwrt-xsw050ns )

Các tool hay sử dụng :tera tera5, tftpd32

Hỏi chi tiết: https://discord.gg/5XbjNNtRFW

---

## 1. Vi xử lý trung tâm (Main SoC)

| Thành phần | Mã Chip | Cấu trúc nhân / Xung nhịp & Chức năng | Hãng sản xuất |
| :--- | :--- | :--- | :--- |
| **Main XGS-PON SoC** | `AN7581CT` | **4 nhân ARM Cortex-A53 + 8 nhân RISC-V NPU** (Xử lý trung tâm, 10G XGS-PON MAC, tích hợp Switch Gigabit & tăng tốc phần cứng gói tin) | Airoha |

---

## 2. Bộ nhớ & Lưu trữ (Memory & Storage)

| Thành phần | Mã Chip | Dung lượng & Thông số kỹ thuật | Hãng sản xuất |
| :--- | :--- | :--- | :--- |
| **RAM hệ thống** | `W664GG6RB-06` | **512MB (4Gb) DDR4-2666** (Xung nhịp thực 1333 MHz / 2666 MT/s, cấu trúc 256M × 16, 1.2V) (khóa ở 3200mhz) | Winbond |
| **Bộ nhớ Flash** | `25N02KVZEIR` | **256MB (2Gb) Serial SLC NAND Flash** (Giao tiếp SPI/QSPI 104 MHz, tích hợp 8-bit ECC) | Winbond |

---

## 3. Hệ thống Wi-Fi 6 (Wireless AX3000 - Filogic 630)

| Vai trò trong cụm Wi-Fi | Mã Chip | Cấu trúc & Thông số kỹ thuật | Hãng sản xuất |
| :--- | :--- | :--- | :--- |
| **Wi-Fi 6 Baseband / MAC** | `MT7916AN` | **Chip xử lý băng tần cơ sở (MAC/BBP)** tích hợp 32-bit RISC MCU, giao tiếp PCIe, chuẩn AX3000 (2×2 2.4GHz + 3×3/2×2 5GHz, 160MHz) | MediaTek |
| **Wi-Fi 6 RF Transceiver** | `MT7976DN` | **Chip thu phát vô tuyến (RF Front-End)** băng tần kép 2.4GHz (2T2R) + 5GHz (3T3R), tích hợp sẵn bộ khuếch đại iPA / iLNA | MediaTek |

---

## 4. Mạng Ethernet, Thoại (VoIP/FXS) & Quang học (PON)

| Thành phần | Mã Chip | Thông số & Chức năng thực tế | Hãng sản xuất |
| :--- | :--- | :--- | :--- |
| **2.5GbE Ethernet PHY** | `EN8811HN` | **Single-port 2.5GBASE-T PHY** (Điều khiển cổng mạng LAN/WAN 2.5Gbps; 4 cổng 1Gbps còn lại nối trực tiếp vào Switch nội của SoC AN7581CT) | Airoha |
| **Dual-Port VoIP SLIC** | `SLLV5-SH8SQ.19` | **Dual-Channel Voice SLIC + CODEC (`PEF32002`)** điều khiển trực tiếp **2 cổng điện thoại bàn (2x FXS / RJ11)** | MaxLinear (Lantiq) |
| **Bảo vệ quá áp cổng Tel** | `2x P61089B` | **2x Dual Programmable Thyristor Surge Suppressor (170V, SOP-8)** — Mạch bảo vệ chống sét/quá áp đường dây cho 2 cổng Tel (SLIC protection) | YAGEO / ST |
| **XGS-PON Laser Driver** | `EN7573AN` | **10G-PON / XGS-PON BOSA Driver** (IC điều khiển công suất thu phát mắt quang 10G đối xứng) | EcoNet |

---

0.Lấy pass uart

1.Cách lấy mật khẩu uart xem : ( https://github.com/ResearcherPT/vnptmodemresearch ) 

Hướng dẫn lấy pass : cài puthon và thư viện ( python -m pip install pycryptodome ) 

1.Vào web fw gốc vào mục backup tải file romfile.cfg

2.Vào vnptmodemresearch tải tool xgs_romfile.py để trong cùng 1 thư mục

3.Mở cmd chạy ( python xgs_romfile.py keys --sn (xponsn) -o keys )    // có thể xem xponsn ở web debug or sau router.

4.Xem key ở dd. (username là admin)

Nếu vào uboot thì username=telecomadmin password=nE7jA%5m

---

I.Backup fw gốc.(rất cần thiết) 

1.Đăng nhập vào linux router thông qua uart vào temp ( cd /tmp )

2.Tải an758x-stock2ubi  ( https://github.com/pbs05/an758x-stock2ubi/releases/tag/v0.1.14 ) upload file lên.

3.Thực thi ( chmod +x /tmp/an758x-stock2ubi )

4.Chạy root ( /tmp/an758x-stock2ubi )

5.Mở web ( http://192.168.1.1:3333/ )

6.Tải file backup về

7.Chú ý không upload preloarder và uboot lên trang .

---

II.Tạo backup

1.Để mtdx vào chung 1 thư mục và cả build_stock_all_flash.py 

2.Chạy lệnh cmd ( python build_stock_all_flash.py . -o all_flash.bin )

3.

---
