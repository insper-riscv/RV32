# Benchmark da SDRAM na placa

Este documento registra a execução do autoteste (BIST) da SDRAM de 64 MB na DE0-CV, sem o core, e as margens de timing do projeto que foi gravado. Ele complementa o benchmark de simulação em `BENCHMARK_SDRAM.md`, que mede o custo em ciclos de usar a SDRAM como RAM.

## 1. Ambiente

| Item | Valor |
| :--- | :--- |
| Placa | DE0-CV, FPGA Cyclone V `5CEBA4F23` (JTAG `0x02B050DD`) |
| Cabo | USB-Blaster `[3-5]` |
| Memória | SDRAM SDR 32M x 16, 143 MHz |
| Ferramenta | Quartus Prime Lite 25.1std.0, no host |
| Projeto | `sdram-bringup` do TopLevel, branch `feat/sdram-bringup`, commit `e37c149` |
| Controlador e autoteste | Memory, branch `feat/sdram-bist`, commit `4e339b5` |

O projeto liga a SDRAM a um controlador e ao autoteste, sem o core. O PLL gera 142,857 MHz para o controlador e para o pino `DRAM_CLK`, este deslocado em 2750 ps, e 50 MHz para o lado do core, que o autoteste não usa.

## 2. Procedimento

1. Compilar: `quartus_sh --flow compile sdram_bringup`, em `platforms/sdram-bringup/quartus`.
2. Gravar o bitstream na SRAM do FPGA: `quartus_pgm -c "USB-Blaster [3-5]" -m JTAG -o "p;output_files/sdram_bringup.sof"`.
3. Rodar cada modo do autoteste pelo JTAG: `quartus_stp -t jtag/sdram_bist.tcl <modo> 120`, de dentro de `platforms/sdram-bringup`.

A compilação levou 45 s. A gravação é volátil: ao desligar a placa, o FPGA perde a configuração.

## 3. Resultado do autoteste

Cada modo foi executado uma vez, em sequência, depois da gravação. Todos passaram, sem palavra errada e sem estouro do controlador.

| Modo | Teste | Palavras movidas | Palavras erradas | Resultado |
| :--- | :--- | ---: | ---: | :--- |
| 0 | rápido, com máscaras de byte | 458 752 | 0 | PASS |
| 1 | padrões (zeros, uns, `0xAAAAAAAA`, `0x55555555`, bit andando, endereço e complemento) | 1 048 576 | 0 | PASS |
| 2 | varredura do chip inteiro, $2^{24}$ palavras | 67 108 864 | 0 | PASS |
| 3 | endereços pseudo-aleatórios, $2^{20}$ palavras escritas e relidas | 2 097 152 | 0 | PASS |

A varredura completa levou cerca de 6 s; o relógio do script tem resolução de 1 s, então o tempo vale como ordem de grandeza. Ela move $4 \cdot 2^{24}$ palavras (escrita e leitura, com o dado do endereço e com seu complemento), o que dá algo em torno de 11 milhões de palavras por segundo.

O controlador gasta 10 ciclos de 7 ns por acesso de uma palavra (ativar a linha, ler ou escrever em dois ciclos de 16 bits e pré-carregar), ou seja, no máximo

$$
\frac{1}{10 \cdot 7\ \text{ns}} \approx 14{,}3 \text{ milhões de palavras por segundo}
$$

com os tempos provisórios do chip. A taxa medida fica abaixo desse teto, como se espera.

## 4. Timing do projeto gravado

Margens (slack) do Quartus com as restrições de entrada e saída do chip. Valores negativos indicam que o caminho não fecha naquele modelo.

| Verificação | Modelo lento 85 C | Modelo lento 0 C |
| :--- | ---: | ---: |
| Leitura de dado, setup (domínio do controlador) | -0,201 ns | +0,057 ns |
| Comandos e dado de escrita, setup (`DRAM_CLK`) | -0,051 ns | -0,029 ns |
| Comandos e dado de escrita, hold | +2,974 ns | +3,068 ns |
| Hold no domínio do controlador | +0,337 ns | +0,314 ns |

Recursos: 521 ALMs de 18 480 (3 %), 923 registradores, 65 pinos de 224 e nenhum bit de memória em bloco.

## 5. Plataforma completa na placa (core e SDRAM)

A plataforma `sdram` do TopLevel (branch `feat/sdram-platform`, commit `4f2601f`) liga o core a 50 MHz à SDRAM, que é a única RAM, com o controlador a 142,857 MHz. A suíte rodou na placa com o `riscv-tools` dentro da imagem publicada `ghcr.io/insper-riscv/infra-toolchain:latest` (Ubuntu 26.04.1, GHDL 6.0.0, GCC RISC-V 16.1.0 com picolibc, uv 0.13.0, Python 3.14.8), sem nenhuma camada adicional. O Quartus 25.1std do host foi montado em modo leitura nessa imagem, com o servidor JTAG do host acessado pela rede do host; a biblioteca `libglib2.0-0t64`, que as ferramentas do Quartus exigem, já faz parte da imagem. O resultado da seção 5.1 vale para essa execução, e uma execução anterior, com uma camada local que só acrescentava essa biblioteca, deu o mesmo resultado.

Passos, cada um dentro do container:

1. `generate-header` e `compile --emit mif` para as duas configurações (os 89 programas existentes e os 6 da SDRAM); o golden de cada programa C sai do Spike da imagem.
2. `run` da configuração `config.sdram-regression.yaml`: compila o projeto `core_fpga_sdram`, grava a placa e executa cada programa carregando-o pela porta de debug JTAG e lendo o resultado de volta.
3. `run --skip-reconfigure` da configuração `config.sdram.yaml`: os 6 programas que usam a SDRAM, sem regravar a placa.

### 5.1. Resultado

| Verificação | Resultado |
| :--- | :--- |
| Programas existentes | 89 passam, 0 falham |
| Goldens conferidos contra a memória da placa | 82 |
| Programas específicos da SDRAM | 6 passam, 0 falham |
| Compilação do Quartus (dentro do container) | concluída, 0 erros |

Cada programa leva de 2,4 s a 3,0 s na placa. Esse tempo é dominado pelo carregamento e pela leitura pelo JTAG, e não pelo número de ciclos do programa, então ele não serve para calcular a razão contra a RAM interna; essa razão está medida em simulação em `BENCHMARK_SDRAM.md`.

### 5.2. Timing e recursos do projeto gravado

| Verificação | Modelo lento 85 C | Modelo lento 0 C |
| :--- | ---: | ---: |
| Leitura de dado, setup (domínio do controlador) | -0,204 ns | +0,053 ns |
| Comandos e dado de escrita, setup (`DRAM_CLK`) | -0,047 ns | -0,025 ns |
| Domínio do core a 50 MHz, setup | +2,029 ns | +2,026 ns |

Recursos: 3 216 ALMs de 18 480 (17 %), 4 058 registradores, 51 pinos de 224 e 508 416 bits de memória em bloco (16 %).

## 6. Limites desta medição

1. Os tempos do chip nas restrições (setup de entrada 1,5 ns, hold de entrada 0,8 ns, acesso 5,4 ns, hold de saída 2,5 ns) são valores usuais de uma SDR de 143 MHz, ainda não conferidos com o datasheet da peça. As margens negativas dos modelos lentos dependem deles.
2. O autoteste e a suíte passaram na placa mesmo com margem negativa no modelo lento, o que indica que o modelo é conservador; isso não prova folga em outra temperatura, outra placa ou outro lote.
3. Foi uma execução de cada modo e uma da suíte. Não houve repetição para medir variação nem varredura da fase do clock.
4. A suíte na placa mede correção, não ciclos. O custo em ciclos vem da simulação.
