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

> [!IMPORTANT]
> Đã có bản thử nghiệm PON driver
> Thử nghiệm 1:Build mới hoàn toàn bằng openwrt sử dụng drive (`ponwrt`) — cần tìm người test trên hạ tầng XGS-PON (pre-release1).
> Thử nghiệm 2:Build dạng Hybrid/dualboot thay đổi slot phụ tclinux_slave thành openwrt nối vào slot chính - cần tìm người test trên hạ tầng XGS-PON (pre-release2).

---

## 📚 Mục lục

- [🔎 Tổng quan](#-tổng-quan)
- [🧠 1. Main SoC](#-1-main-soc)
- [💾 2. Bộ nhớ & lưu trữ](#-2-bộ-nhớ--lưu-trữ)
- [📡 3. Hệ thống Wi-Fi 6](#-3-hệ-thống-wi-fi-6)
- [🌐 4. Ethernet, VoIP & XGS-PON](#-4-ethernet-voip--xgs-pon)
- [🧰 Công cụ thường dùng](#-công-cụ-thường-dùng)
- [🔐 Lấy thông tin đăng nhập UART](#-lấy-thông-tin-đăng-nhập-uart)
- [🛟 Backup firmware gốc](#-backup-firmware-gốc)
- [📦 Tạo file `all_flash.bin`](#-tạo-file-all_flashbin)
- [⚡ Cài đặt U-Boot của OpenWrt](#-cài-đặt-u-boot-của-openwrt)
- [🛠️ Nạp firmware OpenWrt vào NAND](#️-nạp-firmware-openwrt-vào-nand)
- [♻️ Khôi phục firmware gốc (Rollback to Stock)](#️-khôi-phục-firmware-gốc-rollback-to-stock)
- [🌐 Cấu hình mạng: Bản chưa có PON vs. Bản có PON](#-cấu-hình-mạng-bản-chưa-có-pon-vs-bản-có-pon)
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
| **Ethernet nổi bật** | 1 × 2.5GbE PHY + 4 × 1GbE qua switch nội SoC |
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
| **RAM hệ thống** | `W664GG6RB-06` | **512 MB (4 Gb) DDR4-2666**; 1333 MHz / 2666 MT/s, cấu trúc 256M × 16, 1.2 V (*khóa 3200 MHz*) | Winbond |
| **NAND Flash** | `25N02KVZEIR` | **256 MB (2 Gb) Serial SLC NAND Flash**; SPI/QSPI 104 MHz, tích hợp ECC 8-bit | Winbond |

---

## 📡 3. Hệ thống Wi-Fi 6

**Wireless AX3000 — MediaTek Filogic 630**

| Vai trò | Mã chip | Cấu trúc / chức năng | Hãng |
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

- **Tera Term / PuTTY / MobaXterm** (terminal UART)
- **Tftpd32 / Tftpd64** (TFTP Server trên Windows)
- **Python 3**
- Tool `xgs_romfile.py`
- Tool `an758x-stock2ubi`

Cài thư viện Python cần thiết:

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

`<XPON_SN>` có thể xem trong giao diện debug hoặc trên tem dán dưới đáy router.

### Bước 4 — Xem kết quả

Kiểm tra thư mục/file output `keys` do tool tạo ra:

- **Username Linux theo README gốc:** `admin`
- **Thông tin đăng nhập U-Boot:** chạy lệnh `cat /proc/cmdline` trong shell Linux

---

## 🛟 Backup firmware gốc

> [!IMPORTANT]
> Đây là bước **bắt buộc nên thực hiện trước khi flash/mod firmware**.

### 1. Đăng nhập Linux qua UART

Chuyển sang thư mục tạm:

```sh
cd /tmp
```

### 2. Tải `an758x-stock2ubi`

Release được sử dụng:

👉 **[pbs05/an758x-stock2ubi v0.1.14](https://github.com/pbs05/an758x-stock2ubi/releases/tag/v0.1.14)**

Upload binary vào `/tmp` trên router.

### 3. Cấp quyền thực thi và chạy tool

```sh
chmod +x /tmp/an758x-stock2ubi
/tmp/an758x-stock2ubi
```

### 4. Mở giao diện backup và tải toàn bộ phân vùng MTD

Trên máy tính cùng mạng LAN, mở trình duyệt truy cập:

```text
http://192.168.1.1:3333/
```

Tải toàn bộ các partition/MTD về máy tính và lưu ở nơi an toàn (đặc biệt là `romfile` và `reservearea` chứa dữ liệu hiệu chuẩn laser BOB + địa chỉ MAC).

> [!WARNING]
> **Chú ý:** Không được nhấn *Next* sang trang sau để upload U-Boot và Preloader trên công cụ này.

---

## 📦 Tạo file `all_flash.bin`

*(Dùng khi muốn gộp các phân vùng backup thành một ảnh duy nhất để khôi phục về firmware gốc theo cách bên XSW050-NS).*

Sau khi đã có các file `mtd*` backup:

### 1. Chuẩn bị thư mục

Đặt các file MTD và script `build_stock_all_flash.py` vào cùng một thư mục:

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

Nếu script hoàn tất mà không báo lỗi, file kết quả sẽ là `all_flash.bin` (dung lượng chuẩn **`85,721,088` bytes / `0x051C0000`**).

> [!WARNING]
> `all_flash.bin` chỉ nên được tạo từ **backup đúng của thiết bị/revision tương ứng**. Không flash file của máy khác khi chưa biết rõ partition layout, calibration data và dữ liệu riêng của thiết bị.

---

## ⚡ Cài đặt U-Boot của OpenWrt

1. **Chuẩn bị TFTP Server:**
   - Đặt IP tĩnh cho card mạng LAN của PC là **`192.168.1.254`** (Subnet mask `255.255.255.0`).
   - Mở **Tftpd32 / Tftpd64** trỏ vào thư mục chứa các tệp khởi động sau:
     ```text
     openwrt-airoha-an7581-vnpt_xsw250ns-ubi-preloader.bin
     openwrt-airoha-an7581-vnpt_xsw250ns-ubi-bl31-uboot.fip
     openwrt-airoha-an7581-vnpt_xsw250ns-ubi-initramfs-recovery.itb
     ```

2. **Nạp tạm BL2 Preloader & BL31+U-Boot qua XMODEM:**
   - Kết nối cáp UART (3.3V TX/RX/GND) vào bo mạch và mở **Tera Term** ở tốc độ **`115200 8N1`**.
   - **Nhấn giữ nút Reset** (nằm trong lỗ nhỏ trên vỏ máy) đồng thời cắm nguồn cho router để vào chế độ recovery UART.
   - Nhấn phím **`x`** trong cửa sổ terminal, sau đó chọn **File → Transfer → XMODEM → Send** và gửi tệp:
     ```text
     openwrt-airoha-an7581-vnpt_xsw250ns-ubi-preloader.bin
     ```
   - Chờ truyền xong, khi thấy dòng nhắc `Press x to load BL31 + U-Boot FIP` xuất hiện, nhấn tiếp phím **`x`** và gửi qua **XMODEM** tệp:
     ```text
     openwrt-airoha-an7581-vnpt_xsw250ns-ubi-bl31-uboot.fip
     ```

3. **Ghi vĩnh viễn U-Boot và Preloader vào NAND:**
   - Sau khi thiết bị boot vào giao diện menu U-Boot của OpenWrt, dùng phím mũi tên xuống chọn lần lượt:
     - Mục **`5. Load BL31+U-Boot FIP via TFTP then write to flash`** (nhập tên file `openwrt-airoha-an7581-vnpt_xsw250ns-ubi-bl31-uboot.fip`).
     - Mục **`6. Load BL2 preloader via TFTP then write to flash`** (nhập tên file `openwrt-airoha-an7581-vnpt_xsw250ns-ubi-preloader.bin`).
   - Khởi động lại router để kiểm tra đã lên thẳng U-Boot của OpenWrt.

---

## 🛠️ Nạp firmware OpenWrt vào NAND

Sau khi đã cài đặt xong U-Boot của OpenWrt ở bước trên, bạn chọn tải bộ 2 tệp firmware tương ứng với nhu cầu sử dụng từ mục **Releases**:
- **Bản ổn định (chưa có PON):** Dùng làm router chính / AP / Bridge qua cổng mạng RJ45.
- **Bản thử nghiệm có PON (`ponwrt`):** Tích hợp driver quang XGS-PON để cắm trực tiếp dây nhảy quang vào thiết bị.

### 1. Khởi động bản Initramfs Recovery qua TFTP

Đặt tệp `*-initramfs-recovery.itb` vào thư mục TFTP Server (`192.168.1.254`). Trong menu U-Boot (hoặc U-Boot console), tải ảnh recovery vào RAM và boot:

```bash
setenv ipaddr 192.168.1.1
setenv serverip 192.168.1.254
tftpboot 0x46000000 openwrt-airoha-an7581-vnpt_xsw250ns-ubi-initramfs-recovery.itb
bootm 0x46000000
```

Đợi khoảng 30–60 giây để OpenWrt khởi động tạm thời trên RAM.

### 2. Nạp bản Initramfs Recovery qua Uboot openwrt (Khuyên dùng)

Giống như cách 1 mà tự động:)) lệnh 2.Boot system via TFTP

Hoặc ghi thẳng vào nand thì 4. Load production system via TFTP then write to NAND

---

## ♻️ Khôi phục firmware gốc (Rollback to Stock)

> [!IMPORTANT]
> Bản OpenWrt / `initramfs` của XSW250-NS không khai báo phân vùng `all_flash` trong `/proc/mtd` và khóa ghi phân vùng `bl2` (`flags = 0x0`). Vì vậy, cách khôi phục trực tiếp và an toàn nhất là **nạp file `all_flash.bin` từ U-Boot qua UART + TFTP**.

### 1. Chuẩn bị TFTP Server trên máy tính

1. Nối cáp mạng LAN từ PC vào router, đặt IP tĩnh cho PC là **`192.168.1.254`**.
2. Mở **Tftpd32 / Tftpd64**:
   - **Current Directory:** chọn thư mục chứa file `all_flash.bin` (`85,721,088` bytes, tạo ở mục [Tạo file `all_flash.bin`](#-tạo-file-all_flashbin)).
   - **Server interfaces:** chọn card mạng `192.168.1.254`.
   - Tắt tạm Windows Firewall (hoặc mở cổng UDP 69) để router tải được file.

### 2. Vào dòng lệnh U-Boot (`AN7581>`) qua UART

Kết nối UART (`115200 8N1`), khởi động lại router và vào dấu nhắc `AN7581>`. Kiểm tra thiết bị MTD và biến môi trường trước khi xóa:

```bash
mtd list
printenv ipaddr serverip loadaddr
```

Xác nhận layout trên `spi-nand0` và địa chỉ RAM:
- `0x000000000000-0x000000020000` : `"bl2"`
- `0x000000020000-0x00000ddc0000` : `"ubi"`
- `0x00000ddc0000-0x00000e000000` : `"reservearea"`
- `ipaddr=192.168.1.1`, `serverip=192.168.1.254`, `loadaddr=0x90000000`

### 3. Tải vào RAM, xóa vùng OpenWrt và ghi lại firmware gốc

Chạy lần lượt từng lệnh sau trên `AN7581>` (đợi lệnh trước hoàn tất hẳn mới chạy lệnh sau, **tuyệt đối không tắt nguồn trong lúc xóa/ghi**):

1. Tải `all_flash.bin` vào RAM tại `0x90000000`:
   ```bash
   tftpboot 0x90000000 all_flash.bin
   ```
   Phải thấy log báo truyền đủ: `Bytes transferred = 85721088 (51c0000 hex)`.

2. Xóa sạch vùng `bl2` + `ubi` của OpenWrt (`0x0` → `0x0ddc0000`, dừng ngay trước `reservearea` để giữ nguyên dữ liệu quang BOB & `romfile` backup):
   ```bash
   mtd erase spi-nand0 0x0 0x0ddc0000
   ```

3. Ghi `all_flash.bin` (`0x051c0000` bytes) từ RAM lên `spi-nand0` tại offset `0x0`:
   ```bash
   mtd write spi-nand0 0x90000000 0x0 0x051c0000
   ```

4. Khởi động lại router:
   ```bash
   reset
   ```

### 4. Kiểm tra sau khi khởi động lại

Quan sát log UART sau khi `reset` để xác nhận thiết bị đã về firmware gốc hoàn chỉnh:
- Bootloader về `U-Boot 2014.04-rc1` và kernel `Linux 5.4.55` (`econet,en7581`), nhận đủ 12 phân vùng MTD gốc.
- Đọc thành công dữ liệu hiệu chuẩn quang `en7572_bob.conf` (`MD32 BOB load data done!`), xPON/OMCI đạt `OMCI_STATE_RUN`.
- PHY 2.5GbE `EN8811H`, các cổng LAN (`eth0.1`–`eth0.4`), Wi-Fi 2.4G/5G (`ra0`/`rai0`), DHCP (`udhcpd`) và giao diện web gốc (`http://192.168.1.1`) hoạt động bình thường.

---

## 🌐 Cấu hình mạng: Bản chưa có PON vs. Bản có PON

### Trường hợp 1: Cài bản CHƯA CÓ PON (Dùng làm Router chính qua cổng 2.5GbE)

Phù hợp khi đường truyền của bạn đang chạy hạ tầng **GPON** (bước sóng 1490/1310 nm — không tương thích vật lý với mắt quang XGS-PON 1577/1270 nm trên XSW250-NS) hoặc khi bạn muốn dùng một modem nhà mạng riêng ở chế độ Bridge.

- **Sơ đồ cổng mặc định:**
  - **Cổng WAN (`lan2p5`):** Cổng **2.5GbE** — cắm dây mạng từ modem Bridge của nhà mạng vào cổng này.
  - **Cổng LAN (`lan1` – `lan4`):** 4 cổng **1GbE** + Wi-Fi 6 (`MT7916AN`).
- **Các bước cấu hình quay số PPPoE:**
  1. Truy cập giao diện web LuCI tại **`http://192.168.1.1`**.
  2. Vào **Network → Interfaces** → bấm **Edit** ở giao diện **`wan`** (đang gắn với thiết bị `lan2p5`).
  3. Đổi **Protocol** sang **PPPoE**, nhập **PAP/CHAP username** và **password** của đường truyền Internet → bấm **Save & Apply**.
  4. *(Tùy chọn)* Nếu muốn chuyển cổng 2.5GbE sang làm cổng LAN tốc độ cao cho mạng nội bộ, vào **Network → Interfaces → Devices → `br-lan` → Configure**, thêm `lan2p5` vào danh sách Bridge ports và chuyển giao diện `wan` sang một trong các cổng `lan1`–`lan4`.

---

### Trường hợp 2: Cài bản CÓ PON (Cắm trực tiếp sợi quang XGS-PON)

> [!NOTE]
> Áp dụng cho bản build thử nghiệm (`ponwrt`, kernel 6.18) tích hợp bộ driver quang mã nguồn mở (`airoha-xpon`, `airoha-en7572`, `airoha-pon-frontend`), công cụ **`ponctl`** và giao diện **`luci-app-pon`**. Chỉ hoạt động trên hạ tầng **XGS-PON**.

#### 1. Chuẩn bị 3 thông số định danh ONU

| Thông số | Cách lấy |
|---|---|
| **SN (Serial Number)** | In trên tem mặt đáy router (dạng 16 ký tự hex, VD: `4152435XXXXXXXXX` hoặc dạng `ARCBXXXXXXXX`) |
| **Registration ID** | Thường giống SN hoặc để trống (tùy tổng đài OLT từng khu vực) |
| **Mode PON** | `xgspon` |

#### 2. Khai báo thông số PON qua SSH (`ponctl`)

Kết nối SSH vào router (`ssh root@192.168.1.1`) và chạy lần lượt các lệnh sau:

```sh
# 1. Đặt chế độ XGS-PON (các mode hỗ trợ: xgspon, xgpon, epon-1g, epon-10g-1g, epon-10g-10g)
ponctl mode set xgspon

# 2. Khai báo Serial Number của thiết bị (16 hex digits hoặc VEND + 8 hex)
ponctl identity set --serial 4152435XXXXXXXXX

# (Tùy chọn) Nếu ISP yêu cầu Registration ID
ponctl identity set --registration-id 4152435XXXXXXXXX
```

*(Hoặc bạn có thể cấu hình trực quan trên giao diện web tại **LuCI → Network → PON**)*.

#### 3. Kiểm tra trạng thái đồng bộ quang (O-State) & quay số WAN

1. Cắm sợi quang vào cổng PON của router và kiểm tra trạng thái:
   ```sh
   ponctl status
   ```
   - `active_mode`: hiển thị `xgspon`.
   - `serial_configured`: hiển thị `true`.
   - **O-State:** Hiển thị **`O5`** nghĩa là module quang đã đăng ký và đồng bộ thành công với tổng đài OLT.
2. **Tạo kết nối Internet trên giao diện quang (`pon0`):**
   - Vào **LuCI → Network → Interfaces** → tạo mới (hoặc sửa) giao diện **`wan`** gắn với thiết bị **`pon0`** (hoặc `pon0.<VLAN_ID>` theo VLAN Internet của nhà mạng, ví dụ `pon0.35` hoặc `pon0.11`).
   - Chọn **Protocol** là **PPPoE** (hoặc DHCP tùy gói cước), nhập tài khoản PPPoE → bấm **Save & Apply**.

#### 4. Gỡ rối nhanh & Lưu ý dữ liệu hiệu chuẩn (Factory Data)

| Triệu chứng | Nguyên nhân & Cách xử lý |
|---|---|
| `ponctl: no pon device` | Driver `airoha-xpon` chưa load: kiểm tra `dmesg \| grep -i xpon` và `ls /sys/class/pon/` |
| `serial_configured=false` | Chưa khai báo SN → chạy `ponctl identity set --serial <SN>` |
| O-state dừng ở `O2` / `O3` / `O4` | Sai mã SN, sai mode PON, suy hao quang lớn hoặc tuyến cáp khu vực đó chưa nâng cấp lên XGS-PON |
| Lên `O5` nhưng không có mạng | Kiểm tra lại VLAN ID gắn trên thiết bị `pon0` (ví dụ `pon0.35`) và thông số PPPoE |

- **Dữ liệu hiệu chuẩn laser (BOB calibration):** Nằm tại offset `0x0` (512 bytes) của phân vùng `reservearea` (`en7572_bob.conf`). Không được xóa phân vùng này; nếu mất hoặc lỗi công suất laser, cần khôi phục lại từ bản backup gốc.

---

## 🔗 Tài liệu tham khảo

- [voz188/openwrt-xsw050ns](https://github.com/voz188/openwrt-xsw050ns)
- [ResearcherPT/vnptmodemresearch](https://github.com/ResearcherPT/vnptmodemresearch)
- [pbs05/an758x-stock2ubi](https://github.com/pbs05/an758x-stock2ubi)

---

## 💬 Hỗ trợ / thảo luận

Discord:

👉 **https://discord.gg/5XbjNNtRFW**

Nếu bạn có thêm thông tin về phần cứng, pinout, partition layout hoặc kết quả thử nghiệm OpenWrt / XGS-PON cho **XSW250-NS**, hãy mở **Issue / Pull Request** để cùng bổ sung tài liệu.

---
<p align="center">
  <b>⚡ VNPT iGate XSW250-NS • XGS-PON • Wi-Fi 6 • OpenWrt Research ⚡</b>
</p>
