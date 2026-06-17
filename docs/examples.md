# Design Examples

RTL-Gen AI includes a built-in library of **30 proven synthesizable designs** covering common digital logic blocks.

## Arithmetic

| Design | Description | Keywords |
|--------|-------------|----------|
| `adder_8bit` | 8-bit synchronous adder with carry | adder, 8-bit, arithmetic |
| `adder_16bit` | 16-bit synchronous adder | adder, 16-bit, word |
| `alu_8bit` | 8-bit ALU (add/sub/and/or/xor) | alu, arithmetic, logic |
| `multiplier_8` | 8-bit combinational array multiplier | multiplier, product, array |
| `comparator_8` | 8-bit magnitude comparator | comparator, equal, greater |

## Counters & Registers

| Design | Description | Keywords |
|--------|-------------|----------|
| `counter_4bit` | 4-bit up-counter with enable | counter, 4-bit, increment |
| `counter_8bit` | 8-bit up-counter | counter, 8-bit, up |
| `counter_updown` | 8-bit up/down counter | counter, updown, bidirectional |
| `gray_counter` | 4-bit Gray code counter | gray, code, counter |
| `shift_reg_8` | 8-bit shift register | shift, register, serial |
| `reg_file` | 8x8 register file with dual read ports | register, file, bank |

## Communication

| Design | Description | Keywords |
|--------|-------------|----------|
| `uart_tx` | UART transmitter 8N1 | uart, serial, transmit, baud |
| `spi_master` | SPI master with configurable polarity | spi, master, mosi, miso |
| `i2c_master` | I2C master controller | i2c, sda, scl, master |
| `pwm` | 8-bit PWM generator | pwm, pulse, duty, cycle |

## Memory & FIFO

| Design | Description | Keywords |
|--------|-------------|----------|
| `fifo_8` | 8-entry 8-bit FIFO | fifo, queue, buffer |
| `sync_fifo` | Synchronous FIFO with handshake | fifo, sync, handshake |
| `sram_256x8` | 256x8-bit synchronous SRAM | sram, memory, ram |

## Control & FSM

| Design | Description | Keywords |
|--------|-------------|----------|
| `fsm_traffic` | Traffic light FSM | fsm, traffic, light |
| `fsm_vending` | Vending machine FSM | fsm, vending, coin |
| `round_robin_arb` | 4-way round-robin arbiter | arbiter, round, robin |
| `edge_detect` | Rising/falling edge detector | edge, detect, rising |
| `debounce` | Button debouncer with delay | debounce, button, filter |

## Utility

| Design | Description | Keywords |
|--------|-------------|----------|
| `mux_4to1` | 4-to-1 multiplexer | mux, multiplexer, select |
| `decoder_3to8` | 3-to-8 binary decoder | decoder, decode, 3-to-8 |
| `encoder_8to3` | 8-to-3 priority encoder | encoder, priority, 8-to-3 |
| `barrel_shifter` | 8-bit barrel shifter | barrel, shifter, rotate |
| `clk_div` | Configurable clock divider | clock, divider, frequency |
| `parity_gen` | 8-bit parity generator | parity, even, odd |
| `crc8` | CRC-8 calculator | crc, checksum, error |

## Usage

```python
from rag_engine import retrieve, get_example_by_id

# Search for relevant examples
examples = retrieve("8-bit synchronous adder with carry", top_k=3)

# Get a specific example
ex = get_example_by_id("uart_tx")
print(ex["verilog"])
```

## Adding New Examples

Edit `rag_engine.py` and add to the `_EXAMPLES` list:

```python
{"id":"my_design","keywords":["my","design","tags"],
 "desc":"My custom design description",
 "verilog":"""module my_design(...); ... endmodule"""},
```
