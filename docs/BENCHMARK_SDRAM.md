# Benchmark da plataforma SDRAM em simulação

Este documento mede quanto custa, em ciclos, usar a SDRAM de 64 MB da DE0-CV como única RAM do core, em comparação com a RAM interna do FPGA. O número serve para dimensionar uma cache L1 de dado entre o core e a SDRAM.

## 1. O que foi medido

Cada programa da suíte de testes roda duas vezes no mesmo testbench cocotb, uma em cada plataforma:

| Plataforma | Onde ficam `.data`, `.bss`, heap e pilha |
| :--- | :--- |
| `internal-mem` | RAM interna do FPGA, resposta em 1 ciclo |
| `sdram` | SDRAM externa, resposta em vários ciclos, com o core parando o pipeline até a resposta chegar |

A métrica é o tempo do programa em ticks do clock base de simulação, que valem três por ciclo do core. Na plataforma `sdram`, a espera de inicialização do chip (20 000 ticks) é descontada, porque ela não depende do programa. A razão de cada programa é:

$$
r = \frac{T_{\text{sdram}} - 20\,000}{T_{\text{internal-mem}}}
$$

O modelo de chip da simulação aborta o teste em qualquer violação de timing, de ordem de comandos ou de intervalo de refresh, então um programa que passa também respeitou o protocolo da SDRAM.

## 2. Ambiente

A compilação e a simulação rodaram dentro da imagem `ghcr.io/insper-riscv/infra-toolchain:latest`, com o GHDL 6.0.0, o GCC RISC-V 16.1.0 com picolibc e o Spike da própria imagem. Nada do host foi usado.

Os repositórios foram testados nos commits abaixo, que são as pontas dos pull requests de SDRAM abertos:

| Repositório | Branch | Commit |
| :--- | :--- | :--- |
| Core | `feat/sdram-ready` | `8e15a8e` |
| Memory | `feat/sdram-bist` | `4e339b5` |
| TopLevel | `feat/sdram-platform` | `4f2601f` |
| Testes | `feat/sdram-tests` | `b71df35` |
| Tools | `feat/sdram-debug-backend` | `91e3681` |

Comandos, a partir do projeto de testes e com a configuração de cada plataforma (`config.sdram-regression.yaml` e `config.yaml`):

1. `riscv-tools --config <config> generate-header`
2. `riscv-tools --config <config> compile --emit hex`
3. `riscv-tools --config <config> sim`

## 3. Resultado

Os 89 programas existentes passam nas duas plataformas (178 execuções, 0 falhas).

| Estatística da razão $r$ | Valor |
| :--- | ---: |
| menor | 1,33 |
| mediana | 2,27 |
| média | 2,18 |
| maior | 2,75 |

Distribuição dos 89 programas:

| Faixa de $r$ | Programas |
| :--- | ---: |
| abaixo de 1,5 | 2 |
| de 1,5 a 2,0 | 10 |
| de 2,0 a 2,5 | 76 |
| 2,5 ou mais | 1 |

A SDRAM custa cerca de 2,3 vezes a RAM interna na mediana, e não uma ordem de grandeza a mais: boa parte do tempo de um programa vai para instruções que não acessam a RAM.

### 3.1. Extremos

| Programa | `internal-mem` | `sdram` | $r$ |
| :--- | ---: | ---: | ---: |
| `stdout-printf-int` | 16 994 | 22 685 | 1,33 |
| `div-rem-back-to-back` | 1 049 | 1 553 | 1,48 |
| `mul` | 1 064 | 1 598 | 1,50 |
| `store-word-roundtrip` | 362 | 851 | 2,35 |
| `rodata-lookup-table` | 569 | 1 358 | 2,39 |
| `stdout-truncate` | 188 627 | 518 597 | 2,75 |

Os programas aritméticos longos ficam perto de 1,5 provavelmente porque passam boa parte do tempo na unidade de multiplicação e divisão, que não depende da RAM (não verificado). Os que fazem um load ou um store logo depois de outro ficam perto de 2,35, o que dá o custo de um acesso isolado à SDRAM.

### 3.2. Diferença para os valores publicados no PR

A descrição do PR do Core informa menor 1,31, mediana 2,27, média 2,17 e maior 2,47. Esta medição reproduz a mediana e quase reproduz a média; o máximo é maior.

| Programa | $T_{\text{sdram}}$ no PR | $T_{\text{sdram}}$ aqui |
| :--- | ---: | ---: |
| `add` | 1 175 | 1 175 |
| `mul` | 1 598 | 1 598 |
| `stdout-printf-int` | 22 220 | 22 685 |
| `stdout-truncate` | 465 992 | 518 597 |

Os programas sem saída de texto coincidem exatamente. Só os que usam `stdout` ficam mais lentos aqui. A explicação provável é que, nos branches testados, a saída de texto também envia cada byte à UART JTAG, o que acrescenta acessos a cada caractere. Esta hipótese não foi verificada com uma execução sem a UART.

## 4. Programas específicos da SDRAM

Seis programas exercitam a SDRAM diretamente e só existem na plataforma `sdram`, então não têm baseline. Todos passam. Os ticks abaixo já descontam a inicialização.

| Programa | Ticks |
| :--- | ---: |
| `sdram-bytes` | 10 124 |
| `sdram-loop` | 81 335 |
| `sdram-muldiv` | 119 858 |
| `sdram-refresh` | 128 975 |
| `sdram-copy` | 267 029 |
| `sdram-memtest` | 518 462 |

## 5. Limites desta medição

1. É simulação. O clock do controlador (7 ns) não tem relação fixa com o do core, mas a simulação não modela atraso de pino nem fase de clock, que só a placa mostra.
2. Os tempos do chip no controlador são provisórios, valores usuais de uma peça SDR de 143 MHz que ainda não foram conferidos no datasheet.
3. Não houve execução na placa nem compilação no Quartus nesta rodada.

## 6. Uso como linha de base para a cache

Uma cache L1 de dado deve ser medida com o mesmo procedimento das seções 1 e 2 e comparada com a coluna `sdram` da tabela da seção 7. O teto do ganho é o custo medido aqui: uma cache ideal levaria a razão mediana de 2,27 para 1,0.

## 7. Tabela completa

Ticks por programa, ordenados pela razão. A coluna `sdram` já desconta a inicialização.

| Programa | `internal-mem` | `sdram` | $r$ |
| :--- | ---: | ---: | ---: |
| `stdout-printf-int` | 16994 | 22685 | 1,33 |
| `div-rem-back-to-back` | 1049 | 1553 | 1,48 |
| `mul` | 1064 | 1598 | 1,50 |
| `mulh` | 1064 | 1598 | 1,50 |
| `div` | 1025 | 1568 | 1,53 |
| `rem` | 899 | 1430 | 1,59 |
| `mulhsu` | 821 | 1325 | 1,61 |
| `mulhu` | 821 | 1325 | 1,61 |
| `divu` | 746 | 1241 | 1,66 |
| `remu` | 746 | 1241 | 1,66 |
| `data-init-word-array` | 764 | 1448 | 1,90 |
| `hazard-forwarding-mul` | 461 | 908 | 1,97 |
| `loop` | 803 | 1643 | 2,05 |
| `divide-signed` | 614 | 1265 | 2,06 |
| `divide-unsigned` | 614 | 1265 | 2,06 |
| `remainder-signed` | 614 | 1265 | 2,06 |
| `remainder-unsigned` | 614 | 1265 | 2,06 |
| `example-add` | 608 | 1262 | 2,08 |
| `multiply` | 608 | 1262 | 2,08 |
| `data-initialization` | 497 | 1070 | 2,15 |
| `data-init-word` | 497 | 1070 | 2,15 |
| `jump-jal` | 380 | 824 | 2,17 |
| `jump-jalr` | 380 | 824 | 2,17 |
| `data-init-halfword` | 482 | 1055 | 2,19 |
| `stdout-printf` | 6458 | 14165 | 2,19 |
| `example-integration-mem` | 647 | 1430 | 2,21 |
| `bss-zero` | 476 | 1055 | 2,22 |
| `data-init-byte` | 473 | 1049 | 2,22 |
| `branch-beq` | 362 | 809 | 2,23 |
| `branch-bge` | 362 | 809 | 2,23 |
| `branch-bgeu` | 362 | 809 | 2,23 |
| `branch-blt` | 362 | 809 | 2,23 |
| `branch-bltu` | 362 | 809 | 2,23 |
| `branch-bne` | 362 | 809 | 2,23 |
| `load-store-word` | 488 | 1091 | 2,24 |
| `load-store-byte` | 485 | 1085 | 2,24 |
| `load-store-halfword` | 485 | 1085 | 2,24 |
| `logical-and` | 356 | 803 | 2,26 |
| `logical-or` | 356 | 803 | 2,26 |
| `logical-xor` | 356 | 803 | 2,26 |
| `add-upper-immediate-to-pc` | 353 | 803 | 2,27 |
| `arithmetic-add` | 353 | 803 | 2,27 |
| `arithmetic-sub` | 353 | 803 | 2,27 |
| `compare-slt` | 353 | 803 | 2,27 |
| `compare-sltu` | 353 | 803 | 2,27 |
| `hazard-forwarding-chain` | 353 | 803 | 2,27 |
| `hazard-forwarding-raw` | 353 | 803 | 2,27 |
| `logical-andi` | 353 | 803 | 2,27 |
| `logical-ori` | 353 | 803 | 2,27 |
| `logical-xori` | 353 | 803 | 2,27 |
| `shift-left-logical` | 353 | 803 | 2,27 |
| `shift-right-arithmetic-reg` | 353 | 803 | 2,27 |
| `shift-right-logical-reg` | 353 | 803 | 2,27 |
| `compare-slti` | 350 | 797 | 2,28 |
| `compare-sltiu` | 350 | 797 | 2,28 |
| `shift-left-logical-imm` | 350 | 797 | 2,28 |
| `shift-right-arithmetic-imm` | 350 | 797 | 2,28 |
| `shift-right-logical-imm` | 350 | 797 | 2,28 |
| `not` | 497 | 1133 | 2,28 |
| `x0-readonly` | 350 | 800 | 2,29 |
| `arithmetic-addi-negative` | 347 | 797 | 2,30 |
| `load-upper-immediate` | 347 | 797 | 2,30 |
| `struct-init-heap` | 344 | 791 | 2,30 |
| `struct-init-stack` | 344 | 791 | 2,30 |
| `load-halfword-signed` | 368 | 851 | 2,31 |
| `load-halfword-unsigned` | 368 | 851 | 2,31 |
| `and` | 509 | 1181 | 2,32 |
| `or` | 509 | 1181 | 2,32 |
| `xor` | 509 | 1181 | 2,32 |
| `branch-not-equal` | 506 | 1178 | 2,33 |
| `load-word` | 365 | 851 | 2,33 |
| `store-halfword-roundtrip` | 365 | 851 | 2,33 |
| `shift-left` | 506 | 1181 | 2,33 |
| `add` | 503 | 1175 | 2,34 |
| `branch-equal` | 503 | 1175 | 2,34 |
| `compare-signed` | 503 | 1175 | 2,34 |
| `compare-unsigned` | 503 | 1175 | 2,34 |
| `shift-right-arithmetic` | 503 | 1175 | 2,34 |
| `shift-right-logical` | 503 | 1175 | 2,34 |
| `sub` | 503 | 1175 | 2,34 |
| `hazard-load-use` | 365 | 854 | 2,34 |
| `section6-loadstore` | 359 | 842 | 2,35 |
| `struct-alignment` | 389 | 914 | 2,35 |
| `load-byte-signed` | 362 | 851 | 2,35 |
| `load-byte-unsigned` | 362 | 851 | 2,35 |
| `store-byte-roundtrip` | 362 | 851 | 2,35 |
| `store-word-roundtrip` | 362 | 851 | 2,35 |
| `rodata-lookup-table` | 569 | 1358 | 2,39 |
| `stdout-truncate` | 188627 | 518597 | 2,75 |
