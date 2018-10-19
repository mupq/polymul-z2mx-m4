from math import ceil

from .common import schoolbook_inner, Registers, schoolbook_postprocess
import sys


def schoolbook_medium(SRC1, SRC2, DEST, n):
    parts = ceil(n / 12)
    npart = ceil(n / parts)

    instructions = schoolbook_even_medium(SRC1, SRC2, DEST, npart * parts)
    yield from schoolbook_postprocess(SRC1, SRC2, DEST, instructions, n,
                                      stack_src=True)


def schoolbook_even_medium(SRC1, SRC2, DEST, n):
    # the idea here is that we need to divide neatly into schoolbook blocks
    # for n <= 12, it's simply one schoolbook
    # for 12 < n <= 24, we divide into 2x2 schoolbooks (so require even n)
    # for 24 < n <= 36, we divide into 3x3 schoolbooks (so require n % 3 == 0)
    # etc.
    assert n % ceil(n / 12) == 0, "Can only handle n that divide into schoolbooks"

    # reverse to prioritize low registers (as these have 16-bit loads)
    regs = Registers(reversed([f'r{i}' for i in range(0, 13)] + ["r14"]))

    # consider SRC1, SRC2 and DEST allocated
    regs.alloc(SRC1)
    regs.alloc(SRC2)
    regs.alloc(DEST)

    # these can be flexible, do not need to be r0 and r1 after first re-alloc
    src1 = SRC1
    src2 = SRC2

    parts = ceil(n / 12)
    npart = n // parts

    # note that these offsets shouldnt exceed 4096 (i.e. n shouldnt be huge)
    dest_offset = 0
    a_offset = 0
    b_offset = 0

    def blockload(addr, regs, n, offset=0):
        for i, r in enumerate(regs):
            # if it's the last coefficient for odd n, load only one halfword
            if i == n // 2 and n & 1:
                yield f"ldrh {r}, [{addr}, #{i * 4 + offset}]"
            else:
                yield f"ldr {r}, [{addr}, #{i * 4 + offset}]"

    # allocate registers for a and b
    a = [regs.alloc() for _ in range(ceil(npart / 2))]
    yield from blockload(src1, a, npart, a_offset)

    if npart >= 11:
        # we cannot afford to keep these pointers around
        yield f"push {{{src1}}}"
        regs.free(src1)

    b = [regs.alloc() for _ in range(ceil(npart / 2))]
    yield from blockload(src2, b, npart, b_offset)

    if npart >= 11:
        yield f"push {{{src2}}}"
        regs.free(src2)

    initialized = set()

    for col in range(parts):
        for row in (range(parts - 1, -1, -1) if col & 1 else range(parts)):
            lastrow = not (col & 1) and row == parts-1 or (col & 1) and row == 0

            yield from schoolbook_inner(npart, a, b, DEST, regs, initialized,
                restore_b=not lastrow, dest_offset=dest_offset)

            if col & 1:  # for odd columns, go 'back up' instead of down
                dest_offset -= 2 * npart
            else:
                dest_offset += 2 * npart

            # if it's the last part in this col, don't load new src1 inputs
            if lastrow:
                if row == 0:  # if we just finished a back-and-forth
                    dest_offset += 2 * 2 * npart
                continue

            if npart >= 11:
                src1 = regs.alloc()
                yield f"ldr {src1}, [sp, #4]"
            if col & 1:  # for odd columns, go 'back up' instead of down
                a_offset -= 2 * npart
            else:
                a_offset += 2 * npart

            yield from blockload(src1, a, npart, a_offset)

            if npart >= 11:
                yield f"str {src1}, [sp, #4]"
                regs.free(src1)

        if col == parts-1:
            # if it's the last part, don't load new src2 inputs
            continue

        if npart >= 11:
            src2 = regs.alloc()
            yield f"ldr {src2}, [sp, #0]"
        b_offset += 2 * npart

        regs.free(*set(b))  # free; for some n there's one extra after repacking
        b = [regs.alloc() for _ in range(ceil(npart / 2))]
        yield from blockload(src2, b, npart, b_offset)

        if npart >= 11:
            yield f"str {src2}, [sp, #0]"
            regs.free(src2)

    regs.free(*set(a))
    regs.free(*set(b))

    if npart >= 11:
        yield f"pop {{{SRC2}}}"
        yield f"pop {{{SRC1}}}"
