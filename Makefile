OPENCM3DIR  = libopencm3
OPENCM3NAME = opencm3_stm32f4
OPENCM3FILE = $(OPENCM3DIR)/lib/lib$(OPENCM3NAME).a
LDSCRIPT    = stm32f405x6.ld

PREFIX     ?= arm-none-eabi
CC          = $(PREFIX)-gcc
LD          = $(PREFIX)-gcc
OBJCOPY     = $(PREFIX)-objcopy
OBJDUMP     = $(PREFIX)-objdump
GDB         = $(PREFIX)-gdb

ARCH_FLAGS  = -mthumb -mcpu=cortex-m4 -mfloat-abi=hard -mfpu=fpv4-sp-d16
DEFINES     = -DSTM32F4

CFLAGS     += -O3 \
              -Wall -Wextra -Wimplicit-function-declaration \
              -Wredundant-decls -Wmissing-prototypes -Wstrict-prototypes \
              -Wundef -Wshadow \
              -I$(OPENCM3DIR)/include \
              -fno-common $(ARCH_FLAGS) -MD $(DEFINES)
LDFLAGS    += --static -Wl,--start-group -lc -lgcc -lnosys -Wl,--end-group \
              -T$(LDSCRIPT) -nostartfiles -Wl,--gc-sections \
               $(ARCH_FLAGS) -L$(OPENCM3DIR)/lib

COMMONPATH=common

HEADERS = $(COMMONPATH)/fips202.h $(COMMONPATH)/randombytes.h
SOURCES= $(COMMONPATH)/stm32f4_wrapper.c $(COMMONPATH)/fips202.c $(COMMONPATH)/randombytes.c generate-multiplications.py
OBJECTS = stm32f4_wrapper.o randombytes.o fips202.o keccakf1600.o crypto_hash_sha512.o

SCHEMES = kindi256342 ntruhrss701 ntru-kem-743 rlizard-1024-11 saber

NTRU_HRSS_OBJECTS = $(addprefix pqm4/crypto_kem/ntruhrss701/m4/,poly.o cbd.o verify.o owcpa.o ntrukem.o)
SABER_OBJECTS = $(addprefix pqm4/crypto_kem/saber/m4/,cbd.o kem.o pack_unpack.o poly.o recon.o SABER_indcpa.o verify.o poly_mul.o)
RLIZARD_M4_OBJECTS = $(addprefix pqm4/crypto_kem/rlizard-1024-11/m4/,RLizard.o libkeccak/SP800-185.o libkeccak/KeccakSpongeWidth1600.o libkeccak/KeccakP-1600-inplace-32bi-armv7m-le-gcc.s)
KINDI256342_OBJECTS = $(addprefix pqm4/crypto_kem/kindi256342/m4/,core.o gen_randomness.o kem.o poly.o poly_encode.o)
NTRU_KEM_OBJECTS = $(addprefix pqm4/crypto_kem/ntru-kem-743/m4/,NTRUEncrypt.o kem.o packing.o param.o poly.o)

NTRU_HRSS_MULT=mult_toom4_701_11.s
SABER_MULT=mult_toom4_256_16.s
RLIZARD_MULT=mult_toom4_1024_16.s
KINDI256342_MULT=mult_notoom_256_16.s
NTRU_KEM_MULT=mult_toom4_743_12.s


all: test-ntruhrss701.bin test-saber.bin \
     test-rlizard-1024-11.bin test-kindi256342.bin test-ntru-kem-743.bin\
     benchmark-ntruhrss701.bin benchmark-ntru-kem-743.bin\
     benchmark-saber.bin benchmark-rlizard-1024-11.bin\
     benchmark-kindi256342.bin\
     stack-ntruhrss701.bin\
     stack-saber.bin stack-rlizard-1024-11.bin\
     stack-kindi256342.bin


test-ntruhrss701.elf: $(NTRU_HRSS_MULT) ntruhrss701-test.o $(NTRU_HRSS_OBJECTS) $(SOURCES) $(OBJECTS) $(LDSCRIPT)
	$(LD) -o $@ $< ntruhrss701-test.o $(NTRU_HRSS_OBJECTS) $(OBJECTS) $(LDFLAGS) -l$(OPENCM3NAME)
test-saber.elf: $(SABER_MULT) saber-test.o $(SABER_OBJECTS) $(SOURCES) $(OBJECTS) $(LDSCRIPT)
	$(LD) -o $@ $< saber-test.o $(SABER_OBJECTS) $(OBJECTS) $(LDFLAGS) -l$(OPENCM3NAME)
test-rlizard-1024-11.elf: $(RLIZARD_MULT) rlizard-1024-11-test.o $(RLIZARD_M4_OBJECTS) $(SOURCES) $(OBJECTS) $(LDSCRIPT)
	$(LD) -o $@ $< rlizard-1024-11-test.o $(RLIZARD_M4_OBJECTS) $(OBJECTS) $(LDFLAGS) -l$(OPENCM3NAME)
test-kindi256342.elf: $(KINDI256342_MULT) kindi256342-test.o $(KINDI256342_OBJECTS) $(SOURCES) $(OBJECTS) $(LDSCRIPT)
	$(LD) -o $@ $< kindi256342-test.o $(KINDI256342_OBJECTS) $(OBJECTS) $(LDFLAGS) -l$(OPENCM3NAME) -lm
test-ntru-kem-743.elf: $(NTRU_KEM_MULT) ntru-kem-743-test.o $(NTRU_KEM_OBJECTS) $(SOURCES) $(OBJECTS) $(LDSCRIPT)
	$(LD) -o $@ $< ntru-kem-743-test.o $(NTRU_KEM_OBJECTS) $(OBJECTS) $(LDFLAGS) -l$(OPENCM3NAME) -lm


benchmark-ntruhrss701.elf: $(NTRU_HRSS_MULT) ntruhrss701-speed.o $(NTRU_HRSS_OBJECTS) $(SOURCES) $(OBJECTS) $(LDSCRIPT)
	$(LD) -o $@ $< ntruhrss701-speed.o $(NTRU_HRSS_OBJECTS) $(OBJECTS) $(LDFLAGS) -l$(OPENCM3NAME)
benchmark-saber.elf: $(SABER_MULT) saber-speed.o $(SABER_OBJECTS) $(SOURCES) $(OBJECTS)  $(LDSCRIPT)
	$(LD) -o $@ $< saber-speed.o $(SABER_OBJECTS) $(OBJECTS) $(LDFLAGS) -l$(OPENCM3NAME)
benchmark-rlizard-1024-11.elf: $(RLIZARD_MULT) rlizard-1024-11-speed.o $(RLIZARD_M4_OBJECTS) $(SOURCES) $(OBJECTS) $(LDSCRIPT)
	$(LD) -o $@ $< rlizard-1024-11-speed.o $(RLIZARD_M4_OBJECTS) $(OBJECTS) $(LDFLAGS) -l$(OPENCM3NAME)
benchmark-kindi256342.elf: $(KINDI256342_MULT) kindi256342-speed.o $(KINDI256342_OBJECTS) $(SOURCES) $(OBJECTS) $(LDSCRIPT)
	$(LD) -o $@ $< kindi256342-speed.o $(KINDI256342_OBJECTS) $(OBJECTS) $(LDFLAGS) -l$(OPENCM3NAME) -lm
benchmark-ntru-kem-743.elf: $(NTRU_KEM_MULT) ntru-kem-743-speed.o $(NTRU_KEM_OBJECTS) $(SOURCES) $(OBJECTS) $(LDSCRIPT)
	$(LD) -o $@ $< ntru-kem-743-speed.o $(NTRU_KEM_OBJECTS) $(OBJECTS) $(LDFLAGS) -l$(OPENCM3NAME) -lm


stack-ntruhrss701.elf: $(NTRU_HRSS_MULT) ntruhrss701-stack.o $(NTRU_HRSS_OBJECTS) $(SOURCES) $(OBJECTS) $(LDSCRIPT)
	$(LD) -o $@ $< ntruhrss701-stack.o $(NTRU_HRSS_OBJECTS) $(OBJECTS) $(LDFLAGS) -l$(OPENCM3NAME)
stack-saber.elf: $(SABER_MULT) saber-stack.o $(SABER_OBJECTS) $(SOURCES) $(OBJECTS) $(LDSCRIPT)
	$(LD) -o $@ $< saber-stack.o $(SABER_OBJECTS) $(OBJECTS) $(LDFLAGS) -l$(OPENCM3NAME)
stack-rlizard-1024-11.elf: $(RLIZARD_MULT) rlizard-1024-11-stack.o $(RLIZARD_M4_OBJECTS) $(SOURCES) $(OBJECTS) $(LDSCRIPT)
	$(LD) -o $@ $< rlizard-1024-11-stack.o $(RLIZARD_M4_OBJECTS) $(OBJECTS) $(LDFLAGS) -l$(OPENCM3NAME)
stack-kindi256342.elf: $(KINDI256342_MULT) kindi256342-stack.o $(KINDI256342_OBJECTS) $(SOURCES) $(OBJECTS) $(LDSCRIPT)
	$(LD) -o $@ $< kindi256342-stack.o $(KINDI256342_OBJECTS) $(OBJECTS) $(LDFLAGS) -l$(OPENCM3NAME) -lm
stack-ntru-kem-743.elf: $(NTRU_KEM_MULT) ntru-kem-743-stack.o $(NTRU_KEM_OBJECTS) $(SOURCES) $(OBJECTS) $(LDSCRIPT)
	$(LD) -o $@ $< ntru-kem-743-stack.o $(NTRU_KEM_OBJECTS) $(OBJECTS) $(LDFLAGS) -l$(OPENCM3NAME) -lm


# These targets are needed in particular because api.h varies per scheme
$(addsuffix -test.o,$(SCHEMES)): %-test.o: pqm4/crypto_kem/test.c
	$(CC) -I$(COMMONPATH) -I"pqm4/crypto_kem/$*/m4/" $(CFLAGS) -c -o $@ $<
$(addsuffix -speed.o,$(SCHEMES)): %-speed.o: pqm4/crypto_kem/speed.c
	$(CC) -I$(COMMONPATH) -I"pqm4/crypto_kem/$*/m4/" $(CFLAGS) -c -o $@ $<
$(addsuffix -stack.o,$(SCHEMES)): %-stack.o: pqm4/crypto_kem/stack.c
	$(CC) -I$(COMMONPATH) -I"pqm4/crypto_kem/$*/m4/" $(CFLAGS) -c -o $@ $<

benchmark-schoolbook_%.elf: mult_notoom_%_.s benchmark-polymul_%_1024_16.o $(SOURCES) $(OBJECTS) $(LDSCRIPT)
	$(LD) -o $@ benchmark-polymul_$*_1024_16.o $(OBJECTS) $< $(LDFLAGS) -l$(OPENCM3NAME)

# expects e.g. benchmark-karatsuba_128_16.elf, for N=128 and schoolbooks at 16
benchmark-karatsuba_%.elf: mult_notoom_%.s benchmark-polymul_%_16.o $(SOURCES) $(OBJECTS) $(LDSCRIPT)
	$(LD) -o $@ benchmark-polymul_$*_16.o $(OBJECTS) $< $(LDFLAGS) -l$(OPENCM3NAME)

benchmark-toom3_%.elf: mult_toom3_%.s benchmark-polymul_%_15.o $(SOURCES) $(OBJECTS) $(LDSCRIPT)
	$(LD) -o $@ benchmark-polymul_$*_15.o $(OBJECTS) $< $(LDFLAGS) -l$(OPENCM3NAME)

benchmark-toom4_%.elf: mult_toom4_%.s benchmark-polymul_%_13.o $(SOURCES) $(OBJECTS) $(LDSCRIPT)
	$(LD) -o $@ benchmark-polymul_$*_13.o $(OBJECTS) $< $(LDFLAGS) -l$(OPENCM3NAME)

benchmark-toom4toom3_%.elf: mult_toom4toom3_%.s benchmark-polymul_%_12.o $(SOURCES) $(OBJECTS) $(LDSCRIPT)
	$(LD) -o $@ benchmark-polymul_$*_12.o $(OBJECTS) $< $(LDFLAGS) -l$(OPENCM3NAME)

benchmark-polymul_%.o: benchmark-polymul.c
	$(CC) -DDIMENSION=$(word 1, $(subst _, ,$*)) -DTHRESHOLD=$(word 2, $(subst _, ,$*)) -DQ=$(word 3, $(subst _, ,$*)) -I$(COMMONPATH) $(CFLAGS) -c -o $@ $<


stack-polymul_%.elf: mult_%.s stack-polymul_%_11.o $(SOURCES) $(OBJECTS) $(LDSCRIPT)
	$(LD) -o $@ stack-polymul_$*_11.o $(OBJECTS) $< $(LDFLAGS) -l$(OPENCM3NAME)

stack-polymul_%.o: stack-polymul.c
	$(CC) -DDIMENSION=$(word 2, $(subst _, ,$*)) -DTHRESHOLD=$(word 3, $(subst _, ,$*)) -DQ=$(word 4, $(subst _, ,$*)) -I$(COMMONPATH) $(CFLAGS) -c -o $@ $<

%.bin: %.elf
	$(OBJCOPY) -Obinary $(*).elf $(*).bin

%.o: %.c $(HEADERS)
	$(CC) -I$(COMMONPATH) $(CFLAGS) -c -o $@ $<

%.o: %.S $(HEADERS)
	$(CC) -I$(COMMONPATH) $(CFLAGS) -c -o $@ $<

mult_%.s: generate-multiplications.py $(wildcard schoolbooks/*.py) fix-alignment.py generated-file-notice
	python3 generate-multiplications.py $(subst _, ,$*) > $@
	python3 fix-alignment.py $@
	cat generated-file-notice $@ > tmp-$@
	mv tmp-$@ $@

randombytes.o: $(COMMONPATH)/randombytes.c
	$(CC) $(CFLAGS) -o $@ -c $^

fips202.o: $(COMMONPATH)/fips202.c
	$(CC) $(CFLAGS) -o $@ -c $^

crypto_hash_sha512.o: $(COMMONPATH)/crypto_hash_sha512.c
	$(CC) $(CFLAGS) -o $@ -c $^

keccakf1600.o:  common/keccakf1600.S
	$(CC) $(CFLAGS) -o $@ -c $^

stm32f4_wrapper.o:  $(COMMONPATH)/stm32f4_wrapper.c
	$(CC) $(CFLAGS) -o $@ -c $^

.PHONY: clean
.PRECIOUS: $(OBJECTS) mult%.s

clean:
	-rm -f *.d
	-rm -f *.s
	-rm -f *.o
	-find pqm4/crypto_kem -name '*.o' -delete
	-find pqm4/crypto_kem -name '*.d' -delete
	-rm -f *.bin
	-rm -f *.elf
	-find . -name '*.pyc' -delete
	-find . -name '__pycache__' -delete
