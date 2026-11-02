#!/usr/bin/env python3
"""
Gộp backup stock XSW050-NS thành image all_flash/xsw050ns dùng theo hướng dẫn:
https://github.com/voz188/openwrt-xsw050ns

Ảnh restore 0x51C0000 byte gồm các vùng KHÔNG CHỒNG LẤP:
  0x00000000  0x00080000  bootloader
  0x00080000  0x00040000  romfile
  0x000C0000  0x02300000  tclinux
  0x023C0000  0x02300000  tclinux_slave
  0x046C0000  0x00100000  config
  0x047C0000  0x00A00000  userdata
  end = 0x051C0000 = 85,721,088 bytes

mtd2-kernel/mtd3-rootfs nằm bên trong mtd4-tclinux.
mtd5-kernel_slave/mtd6-rootfs_slave nằm bên trong mtd7-tclinux_slave.
Vì vậy KHÔNG nối các file đó thêm lần nữa.

mtd10-safedata không được đưa vào image 0x51C0000 vì hướng dẫn restore của repo
cắt stock backup đúng tại 0x51C0000.
mtd11-reservearea là phân vùng riêng ngoài all_flash trong layout OpenWrt của repo.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

RESTORE_SIZE = 0x051C0000  # 85,721,088 bytes

# (filename, offset, exact_size)
LAYOUT = [
    ("mtd0-bootloader.bin",    0x00000000, 0x00080000),
    ("mtd1-romfile.bin",       0x00080000, 0x00040000),
    ("mtd4-tclinux.bin",       0x000C0000, 0x02300000),
    ("mtd7-tclinux_slave.bin", 0x023C0000, 0x02300000),
    ("mtd8-config.bin",        0x046C0000, 0x00100000),
    ("mtd9-userdata.bin",      0x047C0000, 0x00A00000),
]

OVERLAP_CHECKS = [
    ("mtd2-kernel.bin",       "mtd4-tclinux.bin",       "kernel"),
    ("mtd3-rootfs.bin",       "mtd4-tclinux.bin",       "rootfs"),
    ("mtd5-kernel_slave.bin", "mtd7-tclinux_slave.bin", "kernel_slave"),
    ("mtd6-rootfs_slave.bin", "mtd7-tclinux_slave.bin", "rootfs_slave"),
]


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def require_file(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Thiếu file: {path}")


def validate_layout(src: Path) -> None:
    print("[1/3] Kiểm tra các partition dùng để ghép...")
    for name, offset, expected_size in LAYOUT:
        p = src / name
        require_file(p)
        size = p.stat().st_size
        if size != expected_size:
            raise ValueError(
                f"{name}: size 0x{size:X}, cần đúng 0x{expected_size:X}"
            )
        print(
            f"  OK  {name:<25} "
            f"offset=0x{offset:08X} size=0x{size:08X}"
        )

    last_name, last_offset, last_size = LAYOUT[-1]
    end = last_offset + last_size
    if end != RESTORE_SIZE:
        raise RuntimeError(
            f"Layout kết thúc tại 0x{end:X}, không phải 0x{RESTORE_SIZE:X}"
        )


def validate_overlap(src: Path) -> None:
    print("[2/3] Kiểm tra kernel/rootfs thực sự nằm trong tclinux...")

    # Đọc 2 container lớn một lần.
    containers = {}
    for _, container_name, _ in OVERLAP_CHECKS:
        if container_name not in containers:
            p = src / container_name
            require_file(p)
            containers[container_name] = p.read_bytes()

    for child_name, container_name, label in OVERLAP_CHECKS:
        child_path = src / child_name
        if not child_path.exists():
            print(f"  SKIP {child_name}: không có file, bỏ qua kiểm tra phụ.")
            continue

        child = child_path.read_bytes()
        container = containers[container_name]

        if not child:
            raise ValueError(f"{child_name} rỗng.")

        # Tìm bằng prefix trước, sau đó xác minh toàn bộ file.
        prefix = child[: min(4096, len(child))]
        pos = container.find(prefix)
        found = -1
        while pos != -1:
            if container[pos : pos + len(child)] == child:
                found = pos
                break
            pos = container.find(prefix, pos + 1)

        if found < 0:
            raise ValueError(
                f"{child_name} không nằm nguyên vẹn trong {container_name}. "
                "Có thể các file backup không cùng một lần backup."
            )

        print(
            f"  OK  {label:<13} nằm trong {container_name} "
            f"tại +0x{found:X}"
        )


def build_image(src: Path, output: Path) -> None:
    print(f"[3/3] Tạo {output} ...")

    output.parent.mkdir(parents=True, exist_ok=True)

    # Ghi đúng offset. Với layout này các vùng liền nhau và phủ kín 0x51C0000.
    with output.open("wb") as out:
        out.truncate(RESTORE_SIZE)

        for name, offset, expected_size in LAYOUT:
            p = src / name
            out.seek(offset)

            written = 0
            with p.open("rb") as inp:
                while True:
                    chunk = inp.read(1024 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
                    written += len(chunk)

            if written != expected_size:
                raise IOError(
                    f"Ghi {name} được 0x{written:X}, cần 0x{expected_size:X}"
                )

    actual = output.stat().st_size
    if actual != RESTORE_SIZE:
        raise IOError(
            f"Output size 0x{actual:X}, cần 0x{RESTORE_SIZE:X}"
        )

    print()
    print("HOÀN TẤT")
    print(f"  File   : {output}")
    print(f"  Size   : {actual} bytes (0x{actual:X})")
    print(f"  SHA256 : {sha256_file(output)}")
    print()
    print("Lưu ý:")
    print("  - mtd2/mtd3 và mtd5/mtd6 KHÔNG được nối thêm vì đã nằm trong tclinux.")
    print("  - mtd10-safedata KHÔNG nằm trong image restore 0x51C0000 này.")
    print("  - mtd11-reservearea KHÔNG nằm trong all_flash; hãy giữ backup riêng.")
    print("  - Giữ nguyên toàn bộ file backup gốc trước khi flash thử.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gộp backup XSW050-NS thành stock all_flash 0x51C0000 byte."
    )
    parser.add_argument(
        "input_dir",
        nargs="?",
        default=".",
        help="Thư mục chứa mtd*.bin (mặc định: thư mục hiện tại)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="all_flash.bin",
        help="Tên file output (mặc định: all_flash.bin)",
    )
    parser.add_argument(
        "--skip-overlap-check",
        action="store_true",
        help="Bỏ kiểm tra mtd2/3/5/6 nằm trong tclinux (không khuyến nghị)",
    )
    args = parser.parse_args()

    src = Path(args.input_dir).resolve()
    output = Path(args.output)
    if not output.is_absolute():
        output = Path.cwd() / output
    output = output.resolve()

    try:
        validate_layout(src)
        if not args.skip_overlap_check:
            validate_overlap(src)
        build_image(src, output)
        return 0
    except Exception as e:
        print(f"\nLỖI: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
