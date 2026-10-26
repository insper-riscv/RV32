# RV32IM

🌐 [Português](README.md) · [English](README.en.md)

![Diagrama do pipeline](Core/docs/img/multi-stage-rv32m_pipeline_final-Pipeline.jpg)

SoC RISC-V de 32 bits (RV32I + M) em VHDL, com pipeline em ordem de 5 estágios, suas memórias, periféricos e plataforma de placa, e as ferramentas e testes ao redor. O trabalho é dividido em repositórios da organização [insper-riscv](https://github.com/insper-riscv), um por responsabilidade. Este repositório é o agregador: fixa uma versão de cada um como submódulo git, guarda os relatórios de KPI e a integração contínua conjunta.

## 1. Documentação

- [AUTHORS.md](AUTHORS.md): autores com commits no repositório, com nome e conta do GitHub.
- [CONTRIBUTING.md](CONTRIBUTING.md): regras obrigatórias de contribuição, norma VHDL-2008, norma C23 (ISO/IEC 9899:2024), regras de documentação e verificação antes de abrir Pull Request.
- [CITATION.cff](CITATION.cff): metadados para citação do software.
- [docs/README_kpis.md](docs/README_kpis.md): scripts de KPI (frequência, recursos, CPI e testes) a partir de uma execução do Quartus.
- [docs/BENCHMARK_SDRAM.md](docs/BENCHMARK_SDRAM.md) e [docs/BENCHMARK_SDRAM_PLACA.md](docs/BENCHMARK_SDRAM_PLACA.md): benchmark com SDRAM.

## 2. Repositórios

| Repositório | Responsabilidade | Depende de |
| :--- | :--- | :--- |
| [Infra](https://github.com/insper-riscv/Infra) | A máquina: a imagem de toolchain (GCC com picolibc, Spike, GHDL, uv) em que a integração contínua executa | Nada |
| [Tools](https://github.com/insper-riscv/Tools) | `riscv-tools`: compilar, simular, executar na placa, certificar e verificar | Infra (na execução) |
| [Core](https://github.com/insper-riscv/Core) | O processador em VHDL, por extensão da ISA, perfis e testes por entidade | Nada |
| [Memory](https://github.com/insper-riscv/Memory) | Modelos de simulação e IPs Quartus da placa | Core (interface de memória) |
| [Peripherals](https://github.com/insper-riscv/Peripherals) | GPIO e TIMER, com testes por entidade | Core |
| [TopLevel](https://github.com/insper-riscv/TopLevel) | As plataformas: projeto Quartus, PLL, topo de simulação, runtime, mapa de memória e testbench | Core, Memory, Peripherals, Tools |
| [Tests](https://github.com/insper-riscv/Tests) | Os programas de teste (`asm/`, `c/`), goldens e os fluxos que os executam | TopLevel, Tools |
| [Certification](https://github.com/insper-riscv/Certification) | A suíte oficial ACT4 (riscv-arch-test) | Core, Memory, TopLevel, Tools |

`Core`, `Memory`, `Peripherals`, `TopLevel` e `Tests` são submódulos deste repositório (`Tests` traz o `Tools` junto); `Infra` e `Certification` são usados isoladamente.

## 3. Clonagem e Execução

```bash
git clone --recurse-submodules https://github.com/insper-riscv/RV32IM.git
cd RV32IM
make all        # paths, verificação VHDL, verificações de cada repositório e a suíte de 89 programas
```

As ferramentas vêm da imagem `infra-toolchain` (`ghcr.io/insper-riscv/infra-toolchain`), em que a integração contínua executa.

| Alvo | O que executa |
| :--- | :--- |
| `make paths` | Existência de todos os caminhos listados na configuração (`paths.yaml`, `riscv-tools check-paths`) |
| `make check` | Análise de todos os fontes VHDL da árvore em uma única biblioteca do GHDL |
| `make subrepos` | Caminhos, verificações de sintaxe, perfis, testes por entidade e mapa de memória de `Core`, `Memory`, `Peripherals` e `TopLevel` |
| `make sim` | Suíte de simulação do `Tests`: 89 programas sobre o pipeline |

Os submódulos ficam lado a lado porque se encontram como irmãos (`../Core`, `../Memory`, `../TopLevel`), o mesmo arranjo de quando cada um é clonado ao lado dos demais pela integração contínua.

## 4. Placa

O projeto Quartus é `TopLevel/platforms/internal-mem/quartus/core_fpga_test.qpf` (Cyclone V 5CEBA4F23, com BOOT_ROM, FLASH e RAM dentro da FPGA). A programação e a execução de testes nela são feitas por `riscv-tools run` a partir do `Tests`, conforme [docs/HARDWARE_PROGRAMMING.md do TopLevel](https://github.com/insper-riscv/TopLevel/blob/main/docs/HARDWARE_PROGRAMMING.md).

## 5. KPIs

`scripts/kpi_report.py` e `scripts/compare_kpis.py` geram os relatórios de KPI (clock, recursos, CPI e testes) a partir de uma execução do Quartus, conforme [docs/README_kpis.md](docs/README_kpis.md).

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](LICENSE).
