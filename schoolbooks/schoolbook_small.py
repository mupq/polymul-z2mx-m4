from math import ceil

from .common import schoolbook_inner, Registers


def schoolbook_small(SRC1, SRC2, DEST, n):
    assert n <= 12, "Can only handle n <= 12"

    # reverse to prioritize low registers (as these have 16-bit loads)
    regs = Registers(reversed([f'r{i}' for i in range(0, 13)] + ["r14"]))

    # consider SRC1, SRC2 and DEST allocated
    regs.alloc(SRC1)
    regs.alloc(SRC2)
    regs.alloc(DEST)

    # allocate registers for a and b
    a = [regs.alloc() for _ in range(ceil(n / 2))]
    for i, r in enumerate(a):
        if i == n // 2 and n & 1:
            yield f"ldrh {r}, [{SRC1}, #{i * 4}]"
        else:
            yield f"ldr {r}, [{SRC1}, #{i * 4}]"

    if n >= 11:
        # we cannot afford to keep these pointers around
        yield f"push {{{SRC1}}}"
        regs.free(SRC1)

    b = [regs.alloc() for _ in range(ceil(n / 2))]
    for i, r in enumerate(b):
        # if it's the last coefficient for odd n, load only one halfword
        if i == n // 2 and n & 1:
            yield f"ldrh {r}, [{SRC2}, #{i * 4}]"
        else:
            yield f"ldr {r}, [{SRC2}, #{i * 4}]"

    if n >= 11:
        yield f"push {{{SRC2}}}"
        regs.free(SRC2)

    yield from schoolbook_inner(n, a, b, DEST, regs)

    if n >= 11:
        yield f"pop {{{SRC2}}}"
        yield f"pop {{{SRC1}}}"
