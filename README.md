# Multiplication in Z<sub>2<sup>m</sup></sub>[x] on Cortex-M4

This code package contains the software accompanying the paper "_Faster multiplication in Z<sub>2<sup>m</sup></sub>[x] on the Cortex-M4 to speed up NIST PQC candidates_".
Large parts of the benchmarking code in this package and this README document are based on [PQM4](https://github.com/mupq/pqm4).

The implementations of the schemes, Kindi, NTRU-HRSS, NTRUEncrypt, RLizard and Saber, **are included as they were as the time of writing. They will not be maintained here.** The schemes are purely included for demonstration purposes and to keep the results described in the paper easily verifiable. We instead refer to [PQM4](https://github.com/mupq/pqm4) for up-to-date Cortex-M4 implementations.

## Setup and installation
Our target platform is the
[STM32F4 Discovery board](http://www.st.com/en/evaluation-tools/stm32f4discovery.html)
featuring an ARM Cortex-M4 CPU, 1 MiB of Flash, and 192 KiB of RAM.
Connecting the development to the host computer requires a
mini-USB cable and a USB-TTL converter together with a 2-pin dupont / jumper cable.

We rely on [Python](https://www.python.org/) version 3.6 or newer for benchmarking scripts and generation of the assembly code.

### Installing the ARM toolchain
The build system assumes that you have the [arm-none-eabi toolchain](https://launchpad.net/gcc-arm-embedded)
toolchain installed.
On most Linux systems, the correct toolchain gets installed when you install the `arm-none-eabi-gcc` (or `gcc-arm-none-eabi`) package.
On some Linux distributions, you will also have to explicitly install `libnewlib-arm-none-eabi` .

### Installing stlink
To flash binaries onto the development board, we are using [stlink](https://github.com/texane/stlink).
Depending on your operating system, stlink may be available in your package manager -- if not, please
refer to the stlink GitHub page for instructions on how to [compile it from source](https://github.com/texane/stlink/blob/master/doc/compiling.md)
(in that case, be careful to use `libusb-1.0.0-dev`, not `libusb-0.1`).

### Installing pyserial
The host-side Python code requires the [pyserial](https://github.com/pyserial/pyserial) module.
Your package repository might offer `python-serial` or `python-pyserial` directly
(as of writing, this is the case for Ubuntu, Debian and Arch).
Alternatively, this can be easily installed from PyPA by calling `pip install -r requirements.txt`
(or `pip3`, depending on your system).
If you do not have `pip` installed yet, you can typically find it as `python3-pip` using your package manager.

### Connecting the board to the host
Connect the board to your host machine using the mini-USB port.
This provides it with power, and allows you to flash binaries onto the board.
It should show up in `lsusb` as `STMicroelectronics ST-LINK/V2`.

If you are using a UART-USB connector that has a PL2303 chip on board (which appears to be the most common),
the driver should be loaded in your kernel by default. If it is not, it is typically called `pl2303`.
On macOS, you will still need to [install it](http://www.prolific.com.tw/US/ShowProduct.aspx?p_id=229&pcid=41) (and reboot).
When you plug in the device, it should show up as `Prolific Technology, Inc. PL2303 Serial Port` when you type `lsusb`.

Using dupont / jumper cables, connect the `TX`/`TXD` pin of the USB connector to the `PA3` pin on the board, and connect `RX`/`RXD` to `PA2`.
Depending on your setup, you may also want to connect the `GND` pins.

Run `hostside/host_unidirectional.py` to receive and print output from the board.

### libopencm3
We rely on the [libopencm3](https://github.com/libopencm3/libopencm3) firmware to ease development for the STM32F4 Discovery board.
It is included as a submodule.
After cloning the repository, initialize it using `git submodule update --init`.
Then, compile it by calling `make` in the `libopencm3` directory.

## Testing and benchmarking full schemes
To generate the testing and benchmarking binaries for all schemes run `make`.
This will generate optimized polynomial multiplication using the optimal method for each scheme.
For each of the schemes {saber, kindi256342, ntruhrss, ntru-kem-743, rlizard-1024} this will build
- a `test-{scheme}.bin` which runs key generation, encapsulation, and decapsulation and checks if the obtained keys are the same. For each of the schemes this should print `OK KEYS`
- a `benchmarks-{scheme}.bin` which prints the cycle counts spent in key generation, encapsulation, and decapsulation
- a `stack-{scheme}.bin` which prints the stack usage of key generation, encapsulation, and decapsulation

These binaries can be flashed to the board using `st-flash write {binary} 0x8000000`.

To run all benchmarks for all schemes, we also provide `benchmarks.py`

## Testing and benchmarking polynomial multiplication
The optimized polynomial multiplication procedures can also be tested and benchmarked individually.
For this you need to supply the multiplication method, the size of your input polynomials _n_, and the schoolbook threshold _t_.
For dimensions ≤ _t_, schoolbook multiplication will be used.
Our code was tested for 1 ≤  _n_ ≤  1024.
We support four multiplication methods which come with restrictions on the modulus _q_

| method       | possible q | test / benchmark binary             |
| ------------ | ---------- | --------------------------------- |
| `notoom`     | ≤ 2<sup>16</sup>    | `benchmark-karatsuba_{n}_{t}.bin` |
| `toom3`      | ≤ 2<sup>15</sup>    | `benchmark-toom3_{n}_{t}.bin`     |
| `toom4`      | ≤ 2<sup>13</sup>    | `benchmark-toom4_{n}_{t}.bin`     |
| `toom4toom3` | ≤ 2<sup>11</sup>    | `benchmark-toom4toom3_{n}_{t}.bin`|

To test and benchmark these multiplications, you need to specify the method, _n_, and _t_ as given in the table above,
e.g. `make benchmark-toom4_1024_16.bin`. This also validates that the result is actually correct.

We provide scripts for running these benchmarks for all supported _n_ and methods: `benchmark-karatsuba.py`, `benchmark-toom3.py`, `benchmark-toom4.py`, and `benchmark-toom4toom3.py`.
## Generating stand-alone `polymul_asm`
The scripts can also be used to generate optimized polynomial multiplication assembly independent of the five schemes analyzed here.
The signature of the generated `polymul_asm` routine is

```
void polymul_asm(uint16_t r[2*n-1],  const uint16_t a[n], const uint16_t b[n]);
```
To generate the `polymul_asm` corresponding to a specific multiplication method, an input polynomial degree _n_, and the schoolbook threshold _t_, run `make mult_{method}_{n}_{t}.s`, e.g. `make mult_toom4_256_16.s`.

## Benchmark results

Refer to the paper for a more detailed analysis of the benchmarks.
For convenience, we include benchmarks for the small schoolbook multiplications, below.
The cycle counts include an overhead of approximately 50 cycles for benchmarking.

| n  | cycles | | n  | cycles | | n  | cycles | | n  | cycles |
|:--:|-------:|-|:--:|-------:|-|:--:|-------:|-|:--:|-------:|
| 1  | 60     | | 13 | 247    | | 25 | 996    | | 37 | 2 112  |
| 2  | 66     | | 14 | 268    | | 26 | 1 164  | | 38 | 2 113  |
| 3  | 72     | | 15 | 359    | | 27 | 1 160  | | 39 | 2 106  |
| 4  | 79     | | 16 | 360    | | 28 | 1 287  | | 40 | 2 107  |
| 5  | 89     | | 17 | 506    | | 29 | 1 283  | | 41 | 2 478  |
| 6  | 97     | | 18 | 503    | | 30 | 1 285  | | 42 | 2 863  |
| 7  | 110    | | 19 | 549    | | 31 | 1 350  | | 43 | 2 868  |
| 8  | 117    | | 20 | 551    | | 32 | 1 351  | | 44 | 2 864  |
| 9  | 135    | | 21 | 679    | | 33 | 1 569  | | 45 | 3 038  |
| 10 | 144    | | 22 | 677    | | 34 | 1 701  | | 46 | 3 039  |
| 11 | 175    | | 23 | 725    | | 35 | 1 697  | | 47 | 3 032  |
| 12 | 184    | | 24 | 727    | | 36 | 1 699  | | 48 | 3 033  |

## License

All files, except the source code in `pqm4/`, fall under the CC0 Public Domain dedication,
either as a result of licensing through this project or as a consequence of the CC0 Public Domain dedication of [PQM4](https://github.com/mupq/pqm4) or the [eXtended Keccak code package](https://github.com/XKCP/XKCP).
See the [license details of PQM4](https://github.com/mupq/pqm4#license) for more specific information on the licenses that apply to the individual schemes.
