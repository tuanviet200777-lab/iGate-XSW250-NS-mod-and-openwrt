# Hardware Specifications: xsw250ns

This document details the core hardware components, SoCs, wireless chipset modules, flash memory, RAM, and supporting integrated circuits of the **xsw250ns** platform.

---

## Architecture & Core Processing

| Component / Function | Part Number / IC Model | Manufacturer / Notes |
| :--- | :--- | :--- |
| **Main SoC (Gateway/Router)** | `EN7573AN` | Econet |
| **Co-Processor / Companion SoC** | `AN7581CT` | Airoha |

---

## Memory & Storage

| Component | Part Number / IC Model | Capacity / Specification |
| :--- | :--- | :--- |
| **NAND Flash Memory** | `WINBOND 25N02KVZEIR` | 2Gb (256MB) Serial SLC NAND Flash |
| **System RAM (DRAM)** | `WINBOND W664GG6RB` | 512MB DDR3 SDRAM |

---

## Wireless & RF Subsystem (Wi-Fi)

| Wireless Band / Standard | Chipset Model | Manufacturer |
| :--- | :--- | :--- |
| **Wi-Fi 6 (802.11ax) - Dual-band / Concurrent** | `MT7976DN` + `MT7916AN` | MediaTek |

---

## Ethernet, PHY & Power/Interface Management

| Component Type | Part Number / Model | Function |
| :--- | :--- | :--- |
| **Ethernet Transceiver (PHY)** | `AIROHA EN8811HN` | High-performance single-port GbE PHY |
| **Voice / SLIC Subsystem** | `MSL SLLV5-SH8SQ.19` | Subscriber Line Interface Circuit (VoIP / Telephony) |
| **Power Management / Switch ICs** | `2x P61089B-2525` | Dual power / load management or switching regulators |

---

## Firmware & Compilation Notes
- **Toolchain / SDK:** Econet / Airoha SDK for EN7573 / AN7581 platforms.
- **Bootloader:** U-Boot customized for Econet/Airoha architecture with SPI/NAND flash support.
