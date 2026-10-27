# RV32IM

🌐 [Português](README.md) · [English](README.en.md)

![Pipeline diagram](Core/docs/img/multi-stage-rv32m_pipeline_final-Pipeline.jpg)

32-bit RISC-V SoC (RV32I + M) in VHDL, with an in-order 5-stage pipeline, its memories, peripherals, and board platform, plus the tools and tests around them. The work is split across repositories of the [insper-riscv](https://github.com/insper-riscv) organization, one responsibility each. This repository is the aggregator: it pins a version of each one as a git submodule and holds the KPI reports and the joint continuous integration.

## 1. Documentation

- [AUTHORS.en.md](AUTHORS.en.md): authors with commits in the repository, with name and GitHub account.
- [CONTRIBUTING.en.md](CONTRIBUTING.en.md): mandatory contribution rules, VHDL-2008 standard, C23 standard (ISO/IEC 9899:2024), documentation rules, and verification before opening a Pull Request.
- [CITATION.cff](CITATION.cff): software citation metadata.
- [docs/README_kpis.md](docs/README_kpis.md): KPI scripts (clock, resources, CPI, and tests) from a Quartus run.
- [docs/BENCHMARK_SDRAM.md](docs/BENCHMARK_SDRAM.md) and [docs/BENCHMARK_SDRAM_PLACA.md](docs/BENCHMARK_SDRAM_PLACA.md): SDRAM benchmark.

## 2. Repositories

| Repository | Responsibility | Depends on |
| :--- | :--- | :--- |
| [Infra](https://github.com/insper-riscv/Infra) | The machine: the toolchain image (GCC with picolibc, Spike, GHDL, uv) in which continuous integration runs | Nothing |
| [Tools](https://github.com/insper-riscv/Tools) | `riscv-tools`: compile, simulate, run on the board, certify, and verify | Infra (at run time) |
| [Common-Components](https://github.com/insper-riscv/Common-Components) | The generic VHDL blocks (adder, flip-flop, registers, multiplexers, one-hot decoder, and tri-state buffer) that Core, Memory, and Peripherals import | Nothing |
| [Core](https://github.com/insper-riscv/Core) | The processor in VHDL, by ISA extension, profiles, and per-entity tests | Common-Components |
| [Memory](https://github.com/insper-riscv/Memory) | Simulation models and the board Quartus IPs | Core (memory interface) |
| [Peripherals](https://github.com/insper-riscv/Peripherals) | GPIO, TIMER, and UART, with per-entity tests | Common-Components |
| [TopLevel](https://github.com/insper-riscv/TopLevel) | The platforms: Quartus project, PLL, simulation top, runtime, memory map, and testbench | Core, Memory, Peripherals, Tools |
| [Tests](https://github.com/insper-riscv/Tests) | The test programs (`asm/`, `c/`), goldens, and the flows that run them | TopLevel, Tools |
| [Certification](https://github.com/insper-riscv/Certification) | The official ACT4 suite (riscv-arch-test) | Core, Memory, TopLevel, Tools |

`Common-Components`, `Core`, `Memory`, `Peripherals`, `TopLevel`, `Tests`, `Infra`, and `Certification` are submodules of this repository (`Tests` and `Certification` bring `Tools` along).

## 3. Cloning and Running

```bash
git clone --recurse-submodules https://github.com/insper-riscv/RV32.git
cd RV32
make all        # paths, VHDL check, every repository's own checks, and the 89-program suite
```

The tools come from the `ci-elf` image (`ghcr.io/insper-riscv/ci-elf`), in which continuous integration runs.

| Target | What it runs |
| :--- | :--- |
| `make paths` | Existence of every path listed in the configuration (`paths.yaml`, `riscv-tools check-paths`) |
| `make check` | GHDL analysis of every VHDL source of the tree in a single library |
| `make subrepos` | Paths, syntax checks, profiles, per-entity tests, and memory map of `Core`, `Memory`, `Peripherals`, and `TopLevel` |
| `make sim` | Simulation suite of `Tests`: 89 programs on the pipeline |

The submodules sit side by side because they find each other as siblings (`../Core`, `../Memory`, `../TopLevel`), the same layout as when each is cloned next to the others by continuous integration.

## 4. Board

The Quartus project is `TopLevel/platforms/internal-mem/quartus/core_fpga_test.qpf` (Cyclone V 5CEBA4F23, with BOOT_ROM, FLASH, and RAM inside the FPGA). Programming it and running tests on it is done with `riscv-tools run` from `Tests`, as described in [TopLevel's docs/HARDWARE_PROGRAMMING.md](https://github.com/insper-riscv/TopLevel/blob/main/docs/HARDWARE_PROGRAMMING.md).

## 5. KPIs

`scripts/kpi_report.py` and `scripts/compare_kpis.py` build the KPI reports (clock, resources, CPI, and tests) from a Quartus run, as described in [docs/README_kpis.md](docs/README_kpis.md).

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](LICENSE).
