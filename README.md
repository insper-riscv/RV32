# RV32IM Processor — 5-Stage Pipeline in VHDL

![Pipeline Diagram](docs/img/multi-stage-rv32m_pipeline_final-Pipeline.jpg)

**Team:**
| Name | Role |
|------|------|
| Henrique Rocha Bomfim | Pipeline — design & implementation |
| Pedro Carvalho Ribeiro Neto | Pipeline — design & implementation |
| Luiz Felipe Borelli Durand | Multdiv, KPIs & Tests |
| Luka Siqueira Ferreira de Figueiredo | Tests, KPIs & multdiv |

**Advisor:** [Rafael Corsi](https://github.com/rafaelcorsi)

---

## Overview

This repository implements, in **VHDL**, a **RV32IM** processor (32-bit RISC-V base integer + M extension) organized as a **5-stage in-order pipeline** running at a single clock edge.

The project evolved from a prior RV32I **multi-cycle** core (3 clock cycles per instruction) into a fully pipelined design capable of issuing one instruction per cycle under normal conditions. The pipeline handles all classic hazard classes and integrates a combinational multiply/divide unit in parallel with the ALU.

### What was implemented

| Feature | Module |
|---------|--------|
| 5-stage pipeline (IF → ID → EX → MEM → WB) | `rv32im_pipeline_core.vhd` |
| Pipeline registers with `valid`, `flush` and `stall` | `reg_IF_ID`, `reg_ID_EX`, `reg_EX_MEM`, `reg_MEM_WB` |
| RAW forwarding (EX/MEM → EX, MEM/WB → EX) | `forwarding_unit.vhd` |
| Load-use hazard stall + opcode-aware detection | `hazard_detection_unit.vhd` + `bubble_mux.vhd` |
| Control hazard flush (branch, JAL, JALR) | `reg_IF_ID` + `reg_ID_EX` flush paths |
| Structural hazard elimination | Harvard architecture (separate ROM / RAM) |
| RV32M: MUL, MULH, MULHSU, MULHU, DIV, DIVU, REM, REMU | `multdiv.vhd` (Booth multiplier + non-restoring divider, stall via `muldiv_busy`) |
| Automated unit + integration tests | Cocotb + GHDL |
| FPGA synthesis | Quartus (Cyclone V — DE0-CV) |

---

## Architecture

### Pipeline stages

```
┌──────┐  reg_IF_ID  ┌──────┐  reg_ID_EX  ┌──────┐  reg_EX_MEM  ┌──────┐  reg_MEM_WB  ┌──────┐
│  IF  │ ──────────► │  ID  │ ──────────► │  EX  │ ───────────► │ MEM  │ ────────────► │  WB  │
└──────┘             └──────┘             └──────┘              └──────┘               └──────┘
   ▲                    │                    ▲  ▲                                          │
   │                    ▼                    │  │                                          │
   │              ┌──────────┐    ┌──────────────────┐                                    │
   │              │   HDU    │    │  Forwarding Unit  │                                    │
   │              │ (stall)  │    │  EX/MEM → EX      │                                    │
   │              └──────────┘    │  MEM/WB → EX      │                                    │
   │                              └──────────────────┘                                    │
   └──────────────────────────── wb_data (RegFile write-back) ◄──────────────────────────┘
```

### Hazard handling

#### RAW forwarding — `forwarding_unit.vhd`
Detects read-after-write dependencies between in-flight instructions and drives 3:1 muxes at the EX stage inputs. Priority: EX/MEM > MEM/WB. The forwarding source for MEM/WB is `wb_data` (the final WB mux output — ALU result, PC+4, or extended RAM data), so loads that complete in MEM are also forwarded correctly. The `valid` bit of each pipeline register is ANDed into the forwarding condition to prevent spurious forwarding from bubbles.

Encoding of `forward_A` / `forward_B`:
| Code | Source |
|------|--------|
| `"00"` | ID/EX — value read from RegFile in ID |
| `"10"` | EX/MEM — `exmem_alu_out` |
| `"01"` | MEM/WB — `wb_data` |

#### Load-use stall — `hazard_detection_unit.vhd` + `bubble_mux.vhd`
When a load is in EX (`idex_reRAM = '1'`) and the instruction in ID uses the load's destination register, a 1-cycle stall is inserted:
- PC and IF/ID are frozen (`if_pc_write_en`, `ifid_write_en` → `'0'`)
- A NOP bubble is injected into ID/EX (`id_bubble_sel` → `'1'`)

The HDU decodes the opcode of the instruction in ID to determine which source registers are actually read, preventing false stalls on I-type and load instructions whose `rs2` field encodes part of the immediate.

The `bubble_mux` zeroes only the five signals with side effects — `weReg`, `weRAM`, `reRAM`, `eRAM`, `startMul` — leaving the rest of the ID/EX packet intact.

#### Control hazard flush
Branch outcome and jump targets are resolved in EX. The strategy is **assume-not-taken**: if a branch or jump is confirmed taken, the two instructions already fetched are invalidated by flushing both IF/ID and ID/EX (`flush_if_id`, `flush_id_ex`).

| Instruction | Condition | Target |
|-------------|-----------|--------|
| Branch (`1100011`) | `ex_valid AND alu_branch_flag` | `PC + imm` |
| JAL (`1101111`) | `ex_valid` | `PC + imm` |
| JALR (`1100111`) | `ex_valid` | `(rs1 + imm) AND 0xFFFFFFFE` |

JALR takes priority over branch in the PC source mux.

#### Structural hazard
Avoided by the **Harvard architecture**: instructions are fetched from ROM and data is accessed via a separate RAM, so there is no port conflict between stages.

### RV32M — multiply and divide

The `multdiv.vhd` module implements all eight M-extension operations (MUL, MULH, MULHSU, MULHU, DIV, DIVU, REM, REMU) using a sequential Booth multiplier and a non-restoring divider. While an operation is in progress, `muldiv_busy` freezes the ID/EX, EX/MEM and MEM/WB registers via `muldiv_stall_n` until the result is ready. An extra stall cycle is inserted when `done` pulses, ensuring `saida_capt` has stabilised before the EX/MEM register captures it. The `isMulDiv` control signal selects the MulDiv result instead of the ALU result. Forwarding for M-extension results follows the same path as any other R-type instruction.

---

## Repository Structure

```
.
├── Core/                  # Submodule: the pipeline core in VHDL, by ISA extension
│                          #   (common/, I/, M/, cores/rv32im_pipeline_core.vhd), its per-entity tests
├── Memory/                # Submodule: simulation models (sim/) and the board's Quartus IPs (ips/)
├── Peripherals/           # Submodule: GPIO and TIMER (UART later), with their entity tests
├── TopLevel/              # Submodule: the platform: Quartus project, PLL, simulation top, runtime,
│                          #   memory map, testbench, docs (platforms/internal-mem/)
├── Tests/                 # Submodule: test programs, goldens, simulation/board flows (riscv-tools)
├── scripts/, kpi_*.json   # KPI reports
├── paths.yaml             # every file path the configuration lists (riscv-tools check-paths)
└── L2IP/                  # Deprecated SoC top (kept as reference; tag archive/l2ip)
```

The core, the memories, the peripherals and the platform moved to
[Core](https://github.com/insper-riscv/Core), [Memory](https://github.com/insper-riscv/Memory),
[Peripherals](https://github.com/insper-riscv/Peripherals) and
[TopLevel](https://github.com/insper-riscv/TopLevel), with their
history; the state before the move is the tag `pre-refactor`.

---

## Verification

Tests are written in Python using **Cocotb** and simulated with **GHDL**.

### Unit tests (isolated modules)

| Test | Module under test |
|------|-------------------|
| `ALU` | `ALU.vhd` |
| `bancoRegistradores` | `RegFile.vhd` |
| `ControlUnit` | `control_unit.vhd` |
| `HazardDetectionUnit` | `hazard_detection_unit.vhd` |
| `ForwardingUnit` | `forwarding_unit.vhd` |
| `BubbleMux` | `bubble_mux.vhd` |
| `ExtenderRAM` | `ExtenderRAM.vhd` |
| `ExtenderImm` | `ExtenderImm.vhd` |
| `StoreManager` | `StoreManager.vhd` |
| `RAM`, `ROM` | Memory models |

### Integration tests (full pipeline)

Tests `one` through `six` run RISC-V assembly programs through the complete pipeline (`rv32im_pipeline_core`) and verify register and memory state. Test `MUL` exercises the M-extension instructions.

### Running tests

```bash
# Run all tests
make test

# Run a specific test
make test TEST=ForwardingUnit
make test TEST=MUL
```

Waveforms (`.ghw`) can be opened with **GTKWave**:

```bash
gtkwave Tests/tests/python/sim_build/<toplevel>/waves.ghw
```

---

## FPGA

The design targets the **Cyclone V (5CEBA4F23C7)** on the **DE0-CV** board. Open the Quartus project, compile, and program:

```
TopLevel/platforms/internal-mem/quartus/core_fpga_test.qpf   ← Quartus project
```

The top-level (`core_fpga_test.vhd`) instantiates `rv32im_pipeline_core` alongside the boot ROM, FLASH and RAM Quartus IPs and the PLL.

---

## Development Environment (Dev Container)

This project ships with a ready-to-use VS Code **Dev Container** so you don't have to install Cocotb, GHDL, or Python manually.

### Prerequisites
1. [Docker](https://docs.docker.com/get-docker/) (Desktop on Mac/Windows, Engine on Linux)
2. [Visual Studio Code](https://code.visualstudio.com/)
3. VS Code extension: **Dev Containers** (`ms-vscode-remote.remote-containers`)

### First-time setup
1. Open the folder in VS Code.
2. VS Code will detect `.devcontainer/devcontainer.json` and prompt:

   **"Reopen in Container?"** → click **Yes**.

### Usage inside the container

```bash
# Run all tests
make test

# Open a waveform
gtkwave <file>.ghw
```

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](LICENSE).
