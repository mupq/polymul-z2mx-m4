from math import ceil, floor


class Registers(object):
    registers = []

    def __init__(self, registers=None):
        self.registers = list(registers)

    def free(self, *regs):
        for x in regs:
            if x in self.registers:
                raise Exception(f"Register-variable {x} is already freed")
            self.registers.append(x)

    def alloc(self, reg=None):
        if not self.registers:
            raise Exception("No more registers available!")
        if reg:
            try:
                self.registers.remove(reg)
                return reg
            except ValueError:
                raise Exception(f"Cannot allocate specific register {reg}")
        return self.registers.pop()

    def __repr__(self):
        return repr(self.registers)


def schoolbook_inner(n, a, b, dest, regs, initialized=None, restore_b=False,
                     dest_offset=0):
    if initialized is None:
        initialized = set()

    # allocate an accumulation register
    c = regs.alloc()

    def initmul(ins, init_ins, offset, a, b, c):
        if offset not in initialized:
            yield f"{ins} {c}, {a}, {b}"
            initialized.add(offset)
        else:
            yield f"ldrh {c}, [{dest}, #{offset}]"
            yield f"{init_ins} {c}, {a}, {b}, {c}"

    # compute x^1, x^3, x^5, ... x^(n-1)
    for i in range(n // 2):
        offset = 2 + i*4 + dest_offset
        for j in range(i + 1):
            if j == 0:
                yield from initmul('smuadx', 'smladx', offset, a[j], b[i - j], c)
            else:
                yield f"smladx {c}, {a[j]}, {b[i - j]}, {c}"
        yield f"strh {c}, [{dest}, #{offset}]"

    if n & 1:
        # compute x^n, .. x^2n-2
        for i in range(n // 2):
            offset = 2 + 4*(n // 2 + i) + dest_offset
            for j in range(i, n // 2 + 1):
                if j == i:
                    yield from initmul('smultb', 'smlatb', offset, a[j], b[n // 2 + i - j], c)
                elif j == n // 2:
                    yield f"smlabt {c}, {a[j]}, {b[n // 2 + i - j]}, {c}"
                else:
                    yield f"smladx {c}, {a[j]}, {b[n // 2 + i - j]}, {c}"
            yield f"strh {c}, [{dest}, #{offset}]"
    else:
        # compute x^(n+1), .. x^(2n-1)
        for i in range(n // 2 - 1):
            offset = 2 + 4*(n // 2 + i) + dest_offset
            for j in range(i + 1, n // 2):
                if j == i + 1:
                    yield from initmul('smuadx', 'smladx', offset, a[j], b[n // 2 + i - j], c)
                else:
                    yield f"smladx {c}, {a[j]}, {b[n // 2 + i - j]}, {c}"
            yield f"strh {c}, [{dest}, #{offset}]"

    # repack b to isolate, e.g. for n=8: b0; b2b1, b4b3, b6b5, b7;
    brepack = [None] * (n // 2 + 1)

    regs.free(c)

    brepack[0] = b[0]  # don't free the first register; half of it is useful
    for i in range(1, ceil(n / 2)):
        brepack[i] = regs.alloc()
        yield f"pkhtb {brepack[i]}, {b[i-1]}, {b[i]}"
        if n & 1 == 1 or i < ceil(n / 2) - 1:  # don't free the last register; half of it is useful
            regs.free(b[i])

    if not n & 1:
        if n in [10, 12]:
            # we cannot afford to waste two half-empty registers
            # so we combine the isolated b0 and and b9 elements
            yield f"pkhbt {brepack[0]}, {b[0]}, {b[n // 2 - 1]}"
            regs.free(b[n // 2 - 1])
            # the highest and lowest isolated coefficient are now together
            brepack[n // 2] = brepack[0]
        else:
            # otherwise the highest coefficient is simply by itself
            brepack[n // 2] = b[n // 2 - 1]

    c = regs.alloc()
    # rename repacked b for convenience, but preserve the original b-list
    while len(b) > 0:
        del b[0]
    for reg in brepack:
        b.append(reg)

    # the first multiplication is exceptional, since it's never 2 in parallel
    yield from initmul("mul", "mla", dest_offset, a[0], b[0], c)
    yield f"strh {c}, [{dest}, #{dest_offset}]"

    # compute x^2, x^4, .. x^(n-2); n-1 for odd n
    for i in range(1, ceil(n / 2)):
        offset = i*4 + dest_offset
        for j in range(i + 1):
            if j == 0:
                yield from initmul('smuad', 'smlad', offset, a[j], b[i - j], c)
            elif j == i:
                yield f"mla {c}, {a[j]}, {b[i - j]}, {c}"
            else:
                yield f"smlad {c}, {a[j]}, {b[i - j]}, {c}"
        yield f"strh {c}, [{dest}, #{offset}]"

    if n & 1:
        # compute x^(n+1), ..., x^(2n - 1)
        for i in range(1, ceil(n / 2)):
            offset = 4*(n // 2 + i) + dest_offset
            for j in range(i, ceil(n / 2)):
                if j == i:
                    yield from initmul('smuad', 'smlad', offset, a[j], b[n // 2 + i - j], c)
                elif j == n // 2:
                    yield f"mla {c}, {a[j]}, {b[n // 2 + i - j]}, {c}"
                else:
                    yield f"smlad {c}, {a[j]}, {b[n // 2 + i - j]}, {c}"
            yield f"strh {c}, [{dest}, #{offset}]"

    else:
        # compute x^n, ..., x^(2n - 2)
        for i in range(n // 2):
            offset = 4*(n // 2 + i) + dest_offset
            for j in range(i, n // 2):
                if j == i:
                    yield from initmul('smultt', 'smlatt', offset, a[j], b[n // 2 + i - j], c)
                else:
                    yield f"smlad {c}, {a[j]}, {b[n // 2 + i - j]}, {c}"
            yield f"strh {c}, [{dest}, #{offset}]"

    regs.free(c)

    # In principle it's possible to not have to do this, by simply using
    #  b the other way around in the next call. That makes the code a bit more
    #  complex, at the gain of a getting rid of a few pkhtb instructions.
    #  Consider doing this if this method is record-breaking for relevant n.
    # For now, the added complexity does not seem worth it.
    if restore_b:
        # undo the repacking of b, as it may be needed the other way around next
        if n in [10, 12]:  # in this case the highest is packed with b[0]
            # we need to break the circular dependency chain;
            # we now have a register to do that, since c was freed.
            b[-1] = regs.alloc()
            yield f"mov {b[-1]}, {b[0]}"
        for i in range(floor(n / 2)):
            yield f"pkhtb {b[i]}, {b[i+1]}, {b[i]}"
        if n & 1 == 0:
            regs.free(b[-1])


def schoolbook_postprocess(SRC1, SRC2, DEST, instructions, n, stack_src=False):
    """ This function takes an odd n, and a list of instructions that compute
    the next highest 8x8, and returns a list of instructions that perform
    a smaller multiplication by replacing illegal memory ops by no-ops
    Note that this is silly, as it still leaves multiplications by zero."""
    for ins in instructions:
        ins_sp = ins.split(" ")
        if ins_sp[0] in ['ldr', 'str', 'strh', 'ldrh']:
            destreg = ins_sp[1].split(',')[0]
            offset = int(ins_sp[-1].split(',')[-1][:-1][1:])
            src = ins.split('[')[1].split(',')[0]
            # some schoolbook methods re-allocate the SRC1 and SRC2 registers
            if stack_src and src == 'sp':
                if offset == 0:
                    SRC2 = destreg
                elif offset == 4:
                    SRC1 = destreg
            if src in [SRC1, SRC2]:  # if we're loading input
                if ins_sp[0] == 'ldr':
                    if offset + 4 > n * 2:
                        if offset + 2 > n * 2:
                            yield f"mov {destreg}, #0"
                            continue
                        yield f"ldrh {destreg}, [{src}, #{offset}]"
                        continue
                if ins_sp[0] == 'ldrh':
                    if offset + 2 > n * 2:
                        yield f"mov {destreg}, #0"
                        continue
            elif src == DEST:
                if ins_sp[0] == 'ldr':
                    if offset + 4 > 2 * (2 * n - 1):
                        if offset + 2 > 2 * (2 * n - 1):
                            yield f"mov {destreg}, #0"
                            continue
                        yield f"ldrh {destreg}, [{src}, #{offset}]"
                        continue
                elif ins_sp[0] == 'ldrh':
                    if offset + 2 > 2 * (2 * n - 1):
                        yield f"mov {destreg}, #0"
                        continue
                elif ins_sp[0] == 'str':
                    if offset + 4 > 2 * (2 * n - 1):
                        if offset + 2 > 2 * (2 * n - 1):
                            # no-op
                            continue
                        yield f"strh {destreg}, [{src}, #{offset}]"
                        continue
                elif ins_sp[0] == 'strh':
                    if offset + 2 > 2 * (2 * n - 1):
                        # no-op
                        continue
        yield ins
