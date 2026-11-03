# 🚀 VNPT iGate XSW250-NS — OpenWrt & Hardware Notes

<p align="center">
  <img src="https://img.shields.io/badge/Device-VNPT%20iGate%20XSW250--NS-blue?style=for-the-badge" alt="Device">
  <img src="https://img.shields.io/badge/PON-XGS--PON-orange?style=for-the-badge" alt="XGS-PON">
  <img src="https://img.shields.io/badge/Wi--Fi-Wi--Fi%206-brightgreen?style=for-the-badge" alt="Wi-Fi 6">
  <img src="https://img.shields.io/badge/OpenWrt-Research-informational?style=for-the-badge" alt="OpenWrt Research">
</p>

> [!NOTE]
> Repo OpenWrt này được fork/phát triển dựa trên dự án:
> **[voz188/openwrt-xsw050ns](https://github.com/voz188/openwrt-xsw050ns)**.

> [!WARNING]
> Các thao tác với UART, U-Boot, NAND/MTD và firmware đều có nguy cơ làm thiết bị không khởi động được nếu thực hiện sai.
> **Hãy backup firmware gốc trước khi chỉnh sửa hoặc flash bất kỳ thứ gì.**

---

## 📚 Mục lục

- [🔎 Tổng quan](#-tổng-quan)
- [🧠 Main SoC](#-1-main-soc)
- [💾 Bộ nhớ & lưu trữ](#-2-bộ-nhớ--lưu-trữ)
- [📡 Wi-Fi 6](#-3-hệ-thống-wi-fi-6)
- [🌐 Ethernet, VoIP & XGS-PON](#-4-ethernet-voip--xgs-pon)
- [🧰 Công cụ thường dùng](#-công-cụ-thường-dùng)
- [🔐 Lấy thông tin đăng nhập UART](#-lấy-thông-tin-đăng-nhập-uart)
- [🛟 Backup firmware gốc](#-backup-firmware-gốc)
- [📦 Tạo file `all_flash.bin`](#-tạo-file-all_flashbin)
- [    Cài đặt theo cấu trúc U-Boot của OpenWrt](#-Cài-đặt-theo-cấu-trúc-U-Boot-của-OpenWrt)
- [🔗 Tài liệu tham khảo](#-tài-liệu-tham-khảo)
- [💬 Hỗ trợ / thảo luận](#-hỗ-trợ--thảo-luận)

---

## 🔎 Tổng quan

| Hạng mục | Thông tin |
|---|---|
| **Thiết bị** | VNPT iGate XSW250-NS |
| **Loại thiết bị** | XGS-PON ONT / Router |
| **Wi-Fi** | Wi-Fi 6 / AX3000 |
| **Main SoC** | Airoha `AN7581CT` |
| **RAM** | 512 MB DDR4 |
| **NAND Flash** | 256 MB SLC NAND |
| **Ethernet nổi bật** | 1 × 2.5GbE PHY + 4 x 1GbE qua switch nội SoC |
| **VoIP** | 2 × FXS / RJ11 |

> [!IMPORTANT]
> Các thông số bên dưới được tổng hợp theo quá trình nghiên cứu thiết bị V3. Nếu bạn phát hiện sai khác giữa các revision phần cứng, hãy mở Issue/PR để bổ sung.

---

## 🧠 1. Main SoC

| Thành phần | Mã chip | Cấu trúc / chức năng | Hãng |
|---|---|---|---|
| **Main XGS-PON SoC** | `AN7581CT` | **4 × ARM Cortex-A53 + 8 × RISC-V NPU**; xử lý trung tâm, XGS-PON MAC 10G, switch Gigabit tích hợp và tăng tốc phần cứng gói tin | Airoha |

---

## 💾 2. Bộ nhớ & lưu trữ

| Thành phần | Mã chip | Dung lượng / thông số | Hãng |
|---|---|---|---|
| **RAM hệ thống** | `W664GG6RB-06` | **512 MB (4 Gb) DDR4-2666**; 1333 MHz / 2666 MT/s, cấu trúc 256M × 16, 1.2 V. *khóa 3200 MHz* | Winbond |
| **NAND Flash** | `25N02KVZEIR` | **256 MB (2 Gb) Serial SLC NAND Flash**; SPI/QSPI 104 MHz, tích hợp ECC 8-bit | Winbond |

---

## 📡 3. Hệ thống Wi-Fi 6

**Wireless AX3000 — MediaTek Filogic 630**

| Vai trò | Mã chip | Cấu trúc / thông số | Hãng |
|---|---|---|---|
| **Wi-Fi 6 Baseband / MAC** | `MT7916AN` | MAC/BBP tích hợp 32-bit RISC MCU, PCIe, AX3000; 2×2 2.4 GHz + 3×3/2×2 5 GHz, hỗ trợ 160 MHz | MediaTek |
| **Wi-Fi 6 RF Transceiver** | `MT7976DN` | RF Front-End dual-band; 2.4 GHz 2T2R + 5 GHz 3T3R, tích hợp iPA / iLNA | MediaTek |

---

## 🌐 4. Ethernet, VoIP & XGS-PON

| Thành phần | Mã chip | Chức năng thực tế | Hãng |
|---|---|---|---|
| **2.5GbE Ethernet PHY** | `EN8811HN` | Single-port 2.5GBASE-T PHY; điều khiển cổng LAN/WAN 2.5 Gbps. Các cổng 1 Gbps còn lại nối vào switch nội của `AN7581CT` | Airoha |
| **Dual-Port VoIP SLIC** | `SLLV5-SH8SQ.19` | Dual-channel Voice SLIC + CODEC (`PEF32002`), điều khiển 2 cổng điện thoại **FXS / RJ11** | MaxLinear (Lantiq) |
| **Bảo vệ quá áp cổng TEL** | `2 × P61089B` | Dual Programmable Thyristor Surge Suppressor, 170 V, SOP-8; bảo vệ chống sét/quá áp cho đường dây TEL | YAGEO / ST |
| **XGS-PON Laser Driver** | `EN7573AN` | 10G-PON / XGS-PON BOSA Driver, điều khiển khối thu phát quang 10G đối xứng | EcoNet |

---

## 🧰 Công cụ thường dùng

- **Tera Term / terminal UART**
- **Tftpd32**
- **Python 3**
- Tool `xgs_romfile.py`
- Tool `an758x-stock2ubi`

Cài thư viện cần thiết:

```bash
python -m pip install pycryptodome
```

---

## 🔐 Lấy thông tin đăng nhập UART

Tham khảo project:

👉 **[ResearcherPT/vnptmodemresearch](https://github.com/ResearcherPT/vnptmodemresearch)**

### Bước 1 — Backup `romfile.cfg`

Đăng nhập giao diện web của firmware gốc và tải file backup:

```text
romfile.cfg
```

### Bước 2 — Chuẩn bị tool

Tải `xgs_romfile.py` từ repo `vnptmodemresearch`, sau đó đặt cùng thư mục với file backup.

### Bước 3 — Lấy key theo XPON SN

Mở CMD/PowerShell tại thư mục chứa tool:

```bash
python xgs_romfile.py keys --sn <XPON_SN> -o keys
```

`<XPON_SN>` có thể xem trong giao diện debug hoặc trên tem của router.

### Bước 4 — Xem kết quả

Kiểm tra thư mục/file output `keys` do tool tạo ra.

- Username Linux theo README gốc: `admin`
- Thông tin đăng nhập U-Boot: đọc thông tin trong linux sẽ có.

---

## 🛟 Backup firmware gốc

> [!IMPORTANT]
> Đây là bước **rất nên thực hiện trước khi flash/mod firmware**.

### 1. Đăng nhập Linux qua UART

Chuyển sang thư mục tạm:

```sh
cd /tmp
```

### 2. Tải `an758x-stock2ubi`

Release được README gốc sử dụng:

👉 **[pbs05/an758x-stock2ubi v0.1.14](https://github.com/pbs05/an758x-stock2ubi/releases/tag/v0.1.14)**

Upload binary vào `/tmp` trên router.

### 3. Cấp quyền thực thi

```sh
chmod +x /tmp/an758x-stock2ubi
```

### 4. Chạy tool

```sh
/tmp/an758x-stock2ubi
```

### 5. Mở giao diện backup

Trên máy tính cùng mạng, mở:

```text
http://192.168.1.1:3333/
```

### 6. Tải các file backup về máy

Lưu các partition/MTD cần thiết ở nơi an toàn trước khi tiếp tục chỉnh sửa firmware.

Chú ý không được nhấn next sang trang sau để upload uboot và preloader

---

## 📦 Tạo file `all_flash.bin`   (beta chưa test py)

Sau khi đã có các file `mtd*` backup:

### 1. Chuẩn bị thư mục

Đặt các file MTD và script sau vào cùng một thư mục:

```text
mtd*.bin
build_stock_all_flash.py
```

Ví dụ:

```text
backup/
├── build_stock_all_flash.py
├── mtd0-bootloader.bin
├── mtd1-romfile.bin
├── mtd4-tclinux.bin
├── mtd7-tclinux_slave.bin
├── mtd8-config.bin
└── mtd9-userdata.bin
```

### 2. Ghép thành `all_flash.bin`

Mở CMD/PowerShell tại thư mục trên và chạy:

```bash
python build_stock_all_flash.py . -o all_flash.bin
```

Nếu script hoàn tất mà không báo lỗi, file kết quả sẽ là:

```text
all_flash.bin
```

> [!WARNING]
> `all_flash.bin` chỉ nên được tạo từ **backup đúng của thiết bị/revision tương ứng**. Không nên flash file của máy khác khi chưa biết rõ partition layout, calibration data và dữ liệu riêng của thiết bị.

---

## Cài đặt theo cấu trúc U-Boot của OpenWrt

Đặt các file ảnh OpenWrt lên TFTP server (IP lAN PC: 192.168.1.254): 

```text
openwrt-airoha-an7581-vnpt_xsw-050ns-bl31-uboot.fip
openwrt-airoha-an7581-vnpt_xsw-050ns-initramfs-recovery.itb
openwrt-airoha-an7581-vnpt_xsw-050ns-preloader.bin
```

Kết nối cổng serial console và mở Tera Term trên Windows, thiết lập tốc độ 115200 baud

Giữ (hold) nút Reset (nằm trong lỗ nhỏ trên vỏ máy) và cắm nguồn để vào chế độ recovery

Nhấn phím x trong terminal, sau đó vào File → Transfer → XMODEM → Send

Chọn file BL2

```text
openwrt-airoha-an7581-vnpt_xsw-250ns-preloader.bin
```

Chờ đến khi file được truyền xong và thấy dòng nhắc sau xuất hiện

```text
Press x to load BL31 + U-Boot FIP
```

Nhấn phím x trong terminal, sau đó vào File → Transfer → XMODEM → Send

```text
openwrt-airoha-an7581-vnpt_xsw-250ns-bl31-uboot.fip
```

Sau khi vào uboot nhấn nhanh nút xuống chọn mục `5. Load BL31+U-Boot FIP via TFTP then write to ` 

xong đó chọn mục `6. Load BL2 preloader via TFTP then write to `

xong reset thử lên uboot openwrt

## 🔗 Tài liệu tham khảo

- [voz188/openwrt-xsw050ns](https://github.com/voz188/openwrt-xsw050ns)
- [ResearcherPT/vnptmodemresearch](https://github.com/ResearcherPT/vnptmodemresearch)
- [pbs05/an758x-stock2ubi](https://github.com/pbs05/an758x-stock2ubi)

---

## 💬 Hỗ trợ / thảo luận

Discord:

👉 **https://discord.gg/5XbjNNtRFW**

Nếu bạn có thêm thông tin về phần cứng, pinout, partition layout hoặc quy trình OpenWrt cho **XSW250-NS**, hãy mở **Issue / Pull Request** để cùng bổ sung tài liệu.

---

<p align="center">
  <b>⚡ VNPT iGate XSW250-NS • XGS-PON • Wi-Fi 6 • OpenWrt Research ⚡</b>
</p>
