# RV32IM: a RISC-V SoC in VHDL

![Pipeline Diagram](Core/docs/img/multi-stage-rv32m_pipeline_final-Pipeline.jpg)

**Team:**
| Name | Role |
|------|------|
| Henrique Rocha Bomfim | Pipeline: design & implementation |
| Pedro Carvalho Ribeiro Neto | Pipeline: design & implementation |
| Luiz Felipe Borelli Durand | Multdiv, KPIs & Tests |
| Luka Siqueira Ferreira de Figueiredo | Tests, KPIs & multdiv |

**Advisor:** [Rafael Corsi](https://github.com/rafaelcorsi)

---

## What this repository is

A 32-bit RISC-V (RV32I + M) processor with a 5-stage in-order pipeline, its memories,
peripherals and board platform, and the tools and tests around them. The work is split
in repositories of [insper-riscv](https://github.com/insper-riscv), one responsibility
each; **this repository is the parent**: it pins a version of every one of them as a git
submodule, holds the KPI reports and the integration CI, and nothing else.

| Repository | Responsibility | Depends on |
| :--- | :--- | :--- |
| [Infra](https://github.com/insper-riscv/Infra) | the machine: the toolchain image (GCC with picolibc, Spike, GHDL, uv) the CI runs in | nothing |
| [Tools](https://github.com/insper-riscv/Tools) | `riscv-tools`: compile, simulate, run on the board, certify, verify | Infra (when running) |
| [Core](https://github.com/insper-riscv/Core) | the processor in VHDL, by ISA extension (`common/`, `I/`, `M/`), profiles `rv32i` and `rv32im`, entity tests | nothing |
| [Memory](https://github.com/insper-riscv/Memory) | simulation models and the board's Quartus IPs | Core (the memory interface) |
| [Peripherals](https://github.com/insper-riscv/Peripherals) | GPIO and TIMER (UART later), entity tests | Core |
| [TopLevel](https://github.com/insper-riscv/TopLevel) | the platforms: Quartus project, PLL, simulation top, runtime, memory map, testbench | Core, Memory, Peripherals, Tools |
| [Tests](https://github.com/insper-riscv/Tests) | the test programs (`asm/`, `c/`), goldens, and the flows that run them | TopLevel, Tools |
| [Certification](https://github.com/insper-riscv/Certification) | the official ACT4 (riscv-arch-test) suite | Core, Memory, TopLevel, Tools |

`Core`, `Memory`, `Peripherals`, `TopLevel` and `Tests` are submodules here (`Tests`
brings `Tools` along); `Infra` and `Certification` are used on their own.

## Clone and run

```bash
git clone --recurse-submodules https://github.com/insper-riscv/RV32.git
cd RV32
make all        # paths, VHDL check, every repository's own checks, the 89-program suite
```

The tools come from the `infra-toolchain` image of Infra (`ghcr.io/insper-riscv/infra-toolchain`);
the CI runs in it.

| Target | What it runs |
| :--- | :--- |
| `make paths` | every file path the configuration lists exists (`paths.yaml`, `riscv-tools check-paths`) |
| `make check` | GHDL analyzes every VHDL source of the tree in one library |
| `make subrepos` | `Core`, `Memory`, `Peripherals` and `TopLevel`: their own paths, syntax checks, profiles, entity tests and memory-map check |
| `make sim` | the simulation suite of `Tests`: 89 programs on the pipeline |

The submodules sit side by side because they find each other as siblings (`../Core`,
`../Memory`, `../TopLevel`): the same layout when each is cloned on its own next to the
others, as their CI does.

## Board

The Quartus project is `TopLevel/platforms/internal-mem/quartus/core_fpga_test.qpf` (Cyclone V
5CEBA4F23: BOOT_ROM, FLASH and RAM inside the FPGA). Programming it and running tests on it
is `riscv-tools run` from `Tests`; see
[TopLevel's docs/HARDWARE_PROGRAMMING.md](https://github.com/insper-riscv/TopLevel/blob/main/docs/HARDWARE_PROGRAMMING.md).

## KPIs

`scripts/kpi_report.py` and `scripts/compare_kpis.py` build the KPI reports (clock, resources,
CPI, tests) from a Quartus run; see [docs/README_kpis.md](docs/README_kpis.md).

## History

The processor used to live in this repository alone (`src/`, `tests/`, `Tests/` as a
submodule). It was split in 2026; every moved file kept its history and authorship
(`git filter-repo`). Recover any earlier state with git:

| Tag | What it holds |
| :--- | :--- |
| `pre-refactor` | the repositories as they were before the split (also in Infra, Tools, Tests, Certification) |
| `archive/l2ip` | `L2IP/`, the deprecated SoC top with GPIO and LEDs, the reference for the bus design |
| `archive/3stage-core` | `rv32i3stage_core.vhd`, the 3-stage core |
| `archive/ram1port-quartus-build` | `tests/FPGA/RAM1PORT`, a committed Quartus build (56 MB) |
| `archive/stale-memory-ips` | the outdated `src/RAM1PORT`, `ROM1PORT`, `ROM_IP` |
| `archive/legacy-src` | `AndGate`, `RV32M`, `conversorHex7Seg`, `mhu`, `edgeDetector`, old tops and Quartus projects |
| `archive/gpio-rom-simulation` | the stale `ROM_simulation` copy of `src/GPIO` |
| `archive/fpga-core-legacy` | the old JTAG `.tcl` helpers, `output_mifs`, generated Questa output, `clk.sdc`, `qar_info.json` |
| `archive/legacy-env` | `.vscode`, `.devcontainer`, `Dockerfile.quick`, `requirements.txt` (a third-party image, the old cocotb environment) |

`git checkout <tag> -- <path>` brings a path back.

## License

Apache License 2.0, see [LICENSE](LICENSE).
