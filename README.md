# Hardware Specifications: xsw250ns

This document details the core hardware components, SoCs, wireless chipset modules, flash memory, RAM, and supporting integrated circuits of the **xsw250ns** platform, including core architecture and clock frequencies.

---

## Architecture & Core Processing

| Component / Function | Part Number / IC Model | Architecture / Cores & Clock Speed | Manufacturer / Notes |
| :--- | :--- | :--- | :--- |
| **Main SoC (Gateway/Router)** | `EN7573AN` | **Multi-core ARM/MIPS** *(Standard networking SoC architecture)* | Econet |
| **Co-Processor / Companion SoC** | `AN7581CT` | **Quad-Core ARM CPU + 8-Core RISC-V Network Processor** | Airoha *(10G-PON / High-performance Gateway SoC)* |

---

## Memory & Storage

| Component | Part Number / IC Model | Capacity / Specification | Manufacturer |
| :--- | :--- | :--- | :--- |
| **NAND Flash Memory** | `WINBOND 25N02KVZEIR` | **2Gb (256MB)** Serial SLC NAND Flash | Winbond |
| **System RAM (DRAM)** | `WINBOND W664GG6RB` | **512MB** DDR3 SDRAM | Winbond |

---

## Wireless & RF Subsystem (Wi-Fi)

| Wireless Band / Standard | Chipset Model | Architecture / Processing Units | Manufacturer |
| :--- | :--- | :--- | :--- |
| **Wi-Fi 6 (802.11ax) - Dual-band** | `MT7976DN` + `MT7916AN` | **MT7916AN** (Baseband Processor / MAC) + **MT7976DN** (RF Transceiver / PA/LNA integration) | MediaTek |

---

## Ethernet, PHY & Power/Interface Management

| Component Type | Part Number / Model | Function & Core Specs | Manufacturer |
| :--- | :--- | :--- | :--- |
| **Ethernet Transceiver (PHY)** | `AIROHA EN8811HN` | High-performance single-port GbE PHY transceiver | Airoha |
| **Voice / SLIC Subsystem** | `MSL SLLV5-SH8SQ.19` | Subscriber Line Interface Circuit (VoIP / Telephony control) | MSL |
| **Power Management / Switch ICs** | `2x P61089B-2525` | Dual power management / load switching regulators | — |

---

## Firmware & Compilation Notes
- **Toolchain / SDK:** Econet / Airoha SDK for EN7573 / AN7581 platforms.
- **Bootloader:** U-Boot customized for Econet/Airoha architecture with SPI/NAND flash support.
