# Plano de implementação da UART

## Estado

- Atualizado em: 2026-10-26.
- Branch de trabalho no repositório-pai: `UART`.
- IP OpenCores baixado em `../uartCheck/uart2bus/trunk`.
- Validação standalone na DE0-CV: **concluída em hardware**.
- `UART.vhd` e seus testes unitários isolados: **concluídos (9/9 testes)**.
- Novo mapa com endereços separados de TX e RX: **simulação integrada e
  validação física concluídas**.
- Rajadas, `RX_OVERRUN`, `TX_DROPPED` e limpeza W1C: **validados em simulação
  e na placa**.

## Decisão de arquitetura

A UART será um **periférico controlado pelo processador RV32IM**, e não uma
ponte externa que atua como mestre do barramento.

O processador acessará registradores da UART em `0xC0000000`. O software
escreverá bytes para transmissão, consultará o estado do transmissor e lerá
bytes recebidos. Na primeira versão, o software usará polling; não será
necessário acrescentar `ready` ao barramento nem alterar o pipeline do core.

A Raspberry Pi Pico/Debug Probe continua sendo a ponte elétrica USB-UART entre
o computador e a FPGA, mas não interpreta comandos nem acessa diretamente o
barramento do SoC:

Assim, os comandos texto/binário do `uart2bus` (`r`, `w`, NOP, ACK `0x5A`
etc.) pertencem apenas ao teste standalone. No SoC integrado, o terminal recebe
e transmite os bytes produzidos/consumidos pelo programa executado no RV32IM.

## O que foi validado no standalone

O projeto standalone está em `../uartCheck/standalone` e usa o clock de 50 MHz
da DE0-CV com UART em 115200 baud, 8N1. O arquivo programado no Cyclone V foi
gerado e carregado com sucesso pelo Quartus/USB-Blaster.

Ligação usada:

| Sinal | Pico/Debug Probe | DE0-CV | Pino FPGA |
| :--- | :--- | :--- | :--- |
| TX do adaptador -> RX da FPGA | laranja | GPIO_0 pino físico 3 | `PIN_M16` |
| RX do adaptador <- TX da FPGA | amarelo | GPIO_0 pino físico 4 | `PIN_C16` |
| GND comum | preto | GPIO_0 pino físico 30 | GND |

O script `../uartCheck/standalone/tools/test_uart2bus.py` passou em hardware nos
seguintes grupos:

- protocolos texto e binário;
- leituras, escritas e recuperação do parser;
- comandos consecutivos e quadro enviado com pausa;
- acessos de 1, 4 e 256 bytes;
- incremento automático ligado e desligado;
- escrita sem ACK;
- wrap de endereço de `0xFFFF` para `0x0000`.

Foram registradas duas divergências do RTL original em relação à
especificação:

1. um caractere não hexadecimal no endereço textual pode disparar uma leitura
   em vez de invalidar o comando;
2. o NOP binário devolve `0x5A` mesmo quando o bit de solicitação de ACK está
   desabilitado.

Essas divergências não afetam o periférico final, pois o parser `uart2bus` não
será integrado ao SoC.

## Partes do OpenCores que serão reutilizadas

Reutilizar a implementação VHDL da camada UART física:

- `baudGen.vhd`: gera o clock-enable de 16 vezes o baud rate;
- `uartRx.vhd`: recebe quadros seriais e entrega um byte com `newRxData`;
- `uartTx.vhd`: transmite um byte e informa `txBusy`;
- `uartTop.vhd`: agrega os três blocos anteriores.

Não integrar:

- `uartParser.vhd`;
- `uart2BusTop.vhd` e sua interface de mestre de barramento;
- protocolos de comando texto e binário do `uart2bus`.

Os fontes necessários serão copiados para a área do periférico com a licença
e a atribuição originais preservadas. O pacote baixado permanecerá intacto;
correções de compatibilidade e a interface com o SoC ficarão em uma cópia
vendorizada ou em wrappers do projeto.

## Clock, reset e serial

- Clock do periférico: `pll_clk_idexmem`, no mesmo domínio de 50 MHz do
  estágio MEM e da RAM.
- Configuração inicial: 115200 baud, 8 bits, sem paridade e 1 stop bit.
- Constantes para 50 MHz/115200: `baudFreq = 0x240` e
  `baudLimit = 0x3AC9`.
- Reset: `core_reset`, assíncrono e ativo em nível alto na interface do IP.
- Entrada serial: `UART_RX`; saída serial: `UART_TX`.

Os pinos `PIN_M16` e `PIN_C16` estão reservados em comentários do projeto
principal para uma possível SPI flash futura. Eles podem ser usados nesta etapa,
mas o conflito deve ser revisto se a SPI flash externa for implementada.

## Interface proposta de `UART.vhd`

`UART.vhd` será o escravo memory-mapped que envolve `uartTop`. Sua interface
seguirá o padrão já usado por GPIO e TIMER:

```vhdl
generic (
  DATA_WIDTH : natural := 32;
  BAUD_FREQ  : natural := 16#240#;
  BAUD_LIMIT : natural := 16#3AC9#
);
port (
  clock    : in  std_logic;
  clear    : in  std_logic;
  data_in  : in  std_logic_vector(DATA_WIDTH - 1 downto 0);
  address  : in  std_logic_vector(1 downto 0);
  write    : in  std_logic;
  read     : in  std_logic;
  data_out : out std_logic_vector(DATA_WIDTH - 1 downto 0);
  irq      : out std_logic;
  uart_rx  : in  std_logic;
  uart_tx  : out std_logic
);
```

O endereço local é um índice de palavra (`ram_addr(3 downto 2)`). A primeira
versão de software usará somente acessos alinhados de 32 bits, embora o dado
UART ocupe apenas os oito bits menos significativos.

Não há FIFO nesta versão. RX mantém somente o byte pendente mais recente e TX
aceita um novo byte apenas quando `TX_READY = 1`.

## Mapa de registradores

Base da UART: `0xC0000000` (id de periférico `4`, conforme o contrato do
barramento).

| Endereço | Nome | Acesso | Semântica |
| :--- | :--- | :--- | :--- |
| `0xC0000000` | `TX_DATA` | W | Escrita em bits `[7:0]` inicia TX se livre. Leitura devolve zero. |
| `0xC0000004` | `RX_DATA` | R | Leitura devolve o byte RX em `[7:0]` e consome `RX_VALID`. Escrita não tem efeito. |
| `0xC0000008` | `STATUS` | R/W1C | Estado e erros sticky descritos abaixo. |
| `0xC000000C` | `CONTROL` | R/W | Bit 0 habilita a solicitação de interrupção de RX. |

Bits de `STATUS`:

| Bit | Nome | Significado |
| :--- | :--- | :--- |
| 0 | `RX_VALID` | Existe um byte recebido ainda não consumido. |
| 1 | `TX_READY` | O transmissor aceita um novo byte (`not txBusy`). |
| 2 | `RX_OVERRUN` | Chegou outro byte antes do anterior ser consumido. Sticky, limpo escrevendo 1 neste bit. |
| 3 | `TX_DROPPED` | Houve escrita em `TX_DATA` enquanto TX estava ocupado. Sticky, limpo escrevendo 1 neste bit. |

Comportamento definido para os casos de borda:

- se outro byte chegar enquanto `RX_VALID = 1`, o byte mais recente substitui
  o anterior e `RX_OVERRUN` é ativado;
- se a leitura de `RX_DATA` e a chegada de um byte acontecerem no mesmo ciclo, a
  leitura consome o byte anterior e o novo permanece armazenado com
  `RX_VALID = 1`;
- escrever em `TX_DATA` com `TX_READY = 0` não interrompe o quadro em andamento;
  o novo byte é descartado e `TX_DROPPED` é ativado;
- `irq = RX_VALID and RX_IRQ_ENABLE`, mas a saída ficará desconectada na
  primeira integração, pois o caminho de interrupção/CSR ainda não existe.

## Integração no top-level

A primeira integração será local ao top-level
`TopLevel/platforms/internal-mem/quartus/core_fpga_test.vhd`, sem antecipar a
refatoração completa do interconnect:

1. Decodificar UART quando `ram_addr(31) = '1'` e
   `ram_addr(30 downto 28) = "100"`.
2. Gerar `uart_write` e `uart_read` a partir de `ram_wren`/`ram_rden` e da
   seleção da UART.
3. Entregar `ram_addr(3 downto 2)` como endereço local de registrador.
4. Bloquear `rden` e `wren` da RAM física durante acessos à UART. Isso evita que
   endereços `0xC...`, que hoje chegariam truncados à RAM, causem alias.
5. Separar a saída da RAM do sinal `ram_rdata` do core e inserir o mux de
   leitura RAM/UART.
6. Registrar a seleção e o dado lido do periférico para preservar a latência de
   exatamente um ciclo esperada pelo estágio WB.
7. Adicionar `UART_RX` e `UART_TX` à entidade de topo e reativar as atribuições
   de `PIN_M16`/`PIN_C16` no `.qsf` com I/O de 3,3 V.

O barramento atual não possui `ready`. Isso é suficiente para esta versão:
acessos aos registradores completam em um ciclo, enquanto a latência da linha
serial é tratada pelo software através de `TX_READY` e `RX_VALID`.

## Software inicial

O suporte mínimo pode começar com acesso direto por ponteiros `volatile`:

```c
#define UART_BASE    0xC0000000u
#define UART_TX_DATA (*(volatile unsigned int *)(UART_BASE + 0x00u))
#define UART_RX_DATA (*(volatile unsigned int *)(UART_BASE + 0x04u))
#define UART_STATUS  (*(volatile unsigned int *)(UART_BASE + 0x08u))

#define UART_RX_VALID (1u << 0)
#define UART_TX_READY (1u << 1)

static void uart_putc(unsigned char value)
{
    while ((UART_STATUS & UART_TX_READY) == 0u) {
    }
    UART_TX_DATA = value;
}

static unsigned char uart_getc(void)
{
    while ((UART_STATUS & UART_RX_VALID) == 0u) {
    }
    return (unsigned char)UART_RX_DATA;
}
```

Depois da validação, esses endereços devem ir para o YAML da plataforma e para
um cabeçalho/driver comum, em vez de permanecer duplicados nos programas de
teste.

## Roteiro de implementação

### Fase 1 - importar e compilar a camada física (concluída)

1. Registrar a origem, revisão e licença do OpenCores junto aos fontes
   vendorizados.
2. Copiar somente `baudGen`, `uartRx`, `uartTx`, `uartTop` e as declarações
   estritamente necessárias.
3. Auditar os fontes VHDL antigos para compilação estrita com `numeric_std` e
   com as ferramentas atuais (GHDL e Quartus).
4. Confirmar em simulação que as constantes escolhidas produzem 115200 baud
   com clock de 50 MHz.

### Fase 2 - implementar e testar `UART.vhd` (concluída)

1. Implementar o banco de registradores e instanciar `uartTop`, sem parser.
2. Criar teste unitário cobrindo:
   - estado depois do reset (`TX_READY = 1`, demais bits em zero);
   - recepção, leitura de `RX_DATA` e limpeza de `RX_VALID`;
   - transmissão e formato serial 8N1;
   - overrun de RX e descarte durante TX ocupado;
   - limpeza W1C dos erros;
   - leitura e chegada simultâneas;
   - separação e ausência de efeitos colaterais entre `TX_DATA` e `RX_DATA`;
   - `CONTROL` e geração de `irq`.

Atualização em 2026-10-26: os nove testes Cocotb de `UART` passaram com GHDL.
Oito testes usam `BAUD_FREQ = 1` e `BAUD_LIMIT = 0`, preservando os 16 pulsos
por bit do datapath real, mas acelerando a simulação. Eles incluem a verificação
de que uma leitura de `TX_DATA` e uma escrita em `RX_DATA` não produzem efeitos
colaterais. Um teste adicional usa os valores padrão e um clock de 50 MHz para
medir 115200 baud. A análise VHDL conjunta de todos os periféricos também passou.

### Fase 3 - integrar ao SoC em simulação (concluída)

1. Instanciar o periférico e a decodificação no top-level.
2. Atualizar a lista e a ordem de fontes de simulação e do Quartus.
3. Adicionar a UART ao mapa da plataforma com base `0xC0000000`.
4. Executar toda a regressão existente para comprovar que RAM, FLASH, boot e
   mailbox continuam funcionando.
5. Executar um programa RV32 que transmita uma mensagem e outro que receba e
   devolva caracteres, verificando a linha serial no testbench.

Resultado em 2026-10-26: `uart-tx` e `uart-echo` passaram no top de FPGA
simulado usando, respectivamente, `TX_DATA` e `RX_DATA` em endereços separados.

### Fase 4 - validar no hardware integrado (concluída)

1. Compilar e programar o novo `.sof`.
2. Manter a mesma ligação de três fios já validada no standalone.
3. Abrir `/dev/ttyACM0` em 115200 8N1 com `picocom`.
4. Confirmar uma mensagem de inicialização enviada pelo processador.
5. Executar um firmware de echo e testar bytes comuns, `CR`, `LF`, rajadas e
   recuperação após overrun.
6. Automatizar o teste de hardware com Python, agora enviando dados crus ao
   firmware em vez dos comandos do parser `uart2bus`.

Resultado em 2026-10-26: com o `.sof` do novo mapa previamente carregado, o
harness `uart_hardware_test.py --skip-program` passou nos dois firmwares. O
`uart-echo` devolveu exatamente `RX test\r\n`; em seguida, o harness carregou
`uart-tx` pela memória JTAG e recebeu exatamente `UART OK\r\n`. Ambos os
firmwares finalizaram com `MAILBOX=1`, produzindo o resultado final
`INTEGRATED UART HARDWARE TEST: PASS (uart-echo, uart-tx)`. Isso valida na placa
o caminho CPU -> registradores separados `TX_DATA`/`RX_DATA` -> pinos seriais,
incluindo o polling de `STATUS`.

Atualização em 2026-10-26: o firmware `uart-errors` e o harness coordenado
passaram tanto no top FPGA simulado quanto na placa. O teste provocou uma
escrita durante TX ocupado e recebeu `ATR`, confirmando `TX_DROPPED`, o descarte
do segundo byte e sua limpeza W1C. Em seguida, enviou `0x12 0x34` sem consumir o
primeiro byte e recebeu `OB`, confirmando `RX_OVERRUN`, retenção do byte mais
recente e sua limpeza W1C. Por fim, o firmware devolveu exatamente a rajada crua
de 32 bytes `0x00` a `0x1f`, seguida por `P`, sem novas flags de erro. O teste
terminou com `MAILBOX=1` e
`INTEGRATED UART HARDWARE TEST: PASS (uart-echo, uart-errors)`.

Com esse resultado, os critérios da primeira versão da UART foram atendidos em
simulação e em hardware, incluindo TX, RX, polling, endereços separados,
comportamento de sobrecarga e flags sticky com limpeza W1C.

## Critérios de aceite

A primeira versão da UART estará concluída quando:

- o wrapper e a camada física passarem nos testes unitários;
- toda a regressão existente do RV32 continuar passando;
- Quartus compilar sem erro e o pinout corresponder à fiação validada;
- um programa executado pelo RV32 transmitir e receber bytes pela Pico;
- o teste automatizado de hardware validar TX, RX, polling e flags de erro;
- nenhum acesso à UART escrever ou ler acidentalmente a RAM por alias.

## Evoluções adiadas

Ficam explicitamente fora da primeira entrega:

- integrar `irq` ao core e implementar o suporte CSR/interrupções;
- adicionar FIFOs de RX/TX;
- baud rate configurável por registrador;
- controle de paridade, tamanho de palavra ou quantidade de stop bits;
- sinal `ready` e periféricos de latência variável;
- refatoração completa do interconnect e da decodificação atualmente feita
  dentro do core;
- coexistência com uma SPI flash externa nos mesmos pinos.

Esses itens podem ser adicionados depois que o caminho mínimo
CPU -> registradores UART -> pinos seriais estiver comprovado em simulação e
na placa.
