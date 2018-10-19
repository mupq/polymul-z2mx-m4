
def schoolbook_11(SRC1, SRC2, DEST):
    a0a1 = "r3"
    a2a3 = "r4"
    a4a5 = "r5"
    a6a7 = "r6"
    a8a9 = "r7"
    a10 = "r8"

    yield f"ldr {a0a1},[{SRC1}, #0]"
    yield f"ldr {a2a3},[{SRC1}, #4]"
    yield f"ldr {a4a5},[{SRC1}, #8]"
    yield f"ldr {a6a7},[{SRC1}, #12]"
    yield f"ldr {a8a9},[{SRC1}, #16]"
    yield f"ldrh {a10},[{SRC1}, #20]"

    yield f"push {{{SRC1}}}"  # this clears up r1

    b0b1 = "r1"
    b2b3 = "r9"
    b4b5 = "r10"
    b6b7 = "r11"
    b8b9 = "r12"
    b10 = "r14"

    yield f"ldr {b0b1},[{SRC2}, #0]"
    yield f"ldr {b2b3},[{SRC2}, #4]"
    yield f"ldr {b4b5},[{SRC2}, #8]"
    yield f"ldr {b6b7},[{SRC2}, #12]"
    yield f"ldr {b8b9},[{SRC2}, #16]"
    yield f"ldrh {b10},[{SRC2}, #20]"

    yield f"push {{{SRC2}}}"  # this clears up r2

    c = "r2"

    # dest is still available in r0

    # now we first compute coeffs for odd exponents, i.e. a0*b1 + a1+b0 etc.
    # since these are currently paired together, i.e. b0b1 and a0a1

    yield f"smuadx {c}, {a0a1}, {b0b1}"
    yield f"strh {c}, [{DEST}, #2]"

    yield f"smuadx {c}, {a0a1}, {b2b3}"
    yield f"smladx {c}, {a2a3}, {b0b1}, {c}"
    yield f"strh {c}, [{DEST}, #6]"

    yield f"smuadx {c}, {a0a1}, {b4b5}"
    yield f"smladx {c}, {a2a3}, {b2b3}, {c}"
    yield f"smladx {c}, {a4a5}, {b0b1}, {c}"
    yield f"strh {c}, [{DEST}, #10]"

    yield f"smuadx {c}, {a0a1}, {b6b7}"
    yield f"smladx {c}, {a2a3}, {b4b5}, {c}"
    yield f"smladx {c}, {a4a5}, {b2b3}, {c}"
    yield f"smladx {c}, {a6a7}, {b0b1}, {c}"
    yield f"strh {c}, [{DEST}, #14]"

    yield f"smuadx {c}, {a0a1}, {b8b9}"
    yield f"smladx {c}, {a2a3}, {b6b7}, {c}"
    yield f"smladx {c}, {a4a5}, {b4b5}, {c}"
    yield f"smladx {c}, {a6a7}, {b2b3}, {c}"
    yield f"smladx {c}, {a8a9}, {b0b1}, {c}"
    yield f"strh {c}, [{DEST}, #18]"

    yield f"smultb {c}, {a0a1}, {b10}"
    yield f"smladx {c}, {a2a3}, {b8b9}, {c}"
    yield f"smladx {c}, {a4a5}, {b6b7}, {c}"
    yield f"smladx {c}, {a6a7}, {b4b5}, {c}"
    yield f"smladx {c}, {a8a9}, {b2b3}, {c}"
    yield f"smlabt {c}, {a10}, {b0b1}, {c}"
    yield f"strh {c}, [{DEST}, #22]"

    yield f"smultb {c}, {a2a3}, {b10}"
    yield f"smladx {c}, {a4a5}, {b8b9}, {c}"
    yield f"smladx {c}, {a6a7}, {b6b7}, {c}"
    yield f"smladx {c}, {a8a9}, {b4b5}, {c}"
    yield f"smlabt {c}, {a10}, {b2b3}, {c}"
    yield f"strh {c}, [{DEST}, #26]"

    yield f"smultb {c}, {a4a5}, {b10}"
    yield f"smladx {c}, {a6a7}, {b8b9}, {c}"
    yield f"smladx {c}, {a8a9}, {b6b7}, {c}"
    yield f"smlabt {c}, {a10}, {b4b5}, {c}"
    yield f"strh {c}, [{DEST}, #30]"

    yield f"smultb {c}, {a6a7}, {b10}"
    yield f"smladx {c}, {a8a9}, {b8b9}, {c}"
    yield f"smlabt {c}, {a10}, {b6b7}, {c}"
    yield f"strh {c}, [{DEST}, #34]"

    yield f"smultb {c}, {a8a9}, {b10}"
    yield f"smlabt {c}, {a10}, {b8b9}, {c}"
    yield f"strh {c}, [{DEST}, #38]"

    # repack b to isolate b0; b2b1, b4b3, b6b5, b8b7, b10b9
    b0 = b0b1
    b2b1 = c
    yield f"pkhtb {b2b1}, {b0b1}, {b2b3}"
    b4b3 = b2b3
    yield f"pkhtb {b4b3}, {b2b3}, {b4b5}"
    b6b5 = b4b5
    yield f"pkhtb {b6b5}, {b4b5}, {b6b7}"
    b8b7 = b6b7
    yield f"pkhtb {b8b7}, {b6b7}, {b8b9}"
    b10b9 = b8b9
    yield f"pkhtb {b10b9}, {b8b9}, {b10}"
    c = b10
    del b0b1, b2b3, b4b5, b6b7, b8b9, b10

    yield f"mul {c}, {a0a1}, {b0}"
    yield f"strh {c}, [{DEST}, #0]"

    yield f"smuad {c}, {a0a1}, {b2b1}"
    yield f"mla {c}, {a2a3}, {b0}, {c}"
    yield f"strh {c}, [{DEST}, #4]"

    yield f"smuad {c}, {a0a1}, {b4b3}"
    yield f"smlad {c}, {a2a3}, {b2b1}, {c}"
    yield f"mla {c}, {a4a5}, {b0}, {c}"
    yield f"strh {c}, [{DEST}, #8]"

    yield f"smuad {c}, {a0a1}, {b6b5}"
    yield f"smlad {c}, {a2a3}, {b4b3}, {c}"
    yield f"smlad {c}, {a4a5}, {b2b1}, {c}"
    yield f"mla {c}, {a6a7}, {b0}, {c}"
    yield f"strh {c}, [{DEST}, #12]"

    yield f"smuad {c}, {a0a1}, {b8b7}"
    yield f"smlad {c}, {a2a3}, {b6b5}, {c}"
    yield f"smlad {c}, {a4a5}, {b4b3}, {c}"
    yield f"smlad {c}, {a6a7}, {b2b1}, {c}"
    yield f"mla {c}, {a8a9}, {b0}, {c}"
    yield f"strh {c}, [{DEST}, #16]"

    yield f"smuad {c}, {a0a1}, {b10b9}"
    yield f"smlad {c}, {a2a3}, {b8b7}, {c}"
    yield f"smlad {c}, {a4a5}, {b6b5}, {c}"
    yield f"smlad {c}, {a6a7}, {b4b3}, {c}"
    yield f"smlad {c}, {a8a9}, {b2b1}, {c}"
    yield f"mla {c}, {a10}, {b0}, {c}"
    yield f"strh {c}, [{DEST}, #20]"

    yield f"smuad {c}, {a2a3}, {b10b9}"
    yield f"smlad {c}, {a4a5}, {b8b7}, {c}"
    yield f"smlad {c}, {a6a7}, {b6b5}, {c}"
    yield f"smlad {c}, {a8a9}, {b4b3}, {c}"
    yield f"mla {c}, {a10}, {b2b1}, {c}"
    yield f"strh {c}, [{DEST}, #24]"

    yield f"smuad {c}, {a4a5}, {b10b9}"
    yield f"smlad {c}, {a6a7}, {b8b7}, {c}"
    yield f"smlad {c}, {a8a9}, {b6b5}, {c}"
    yield f"mla {c}, {a10}, {b4b3}, {c}"
    yield f"strh {c}, [{DEST}, #28]"

    yield f"smuad {c}, {a6a7}, {b10b9}"
    yield f"smlad {c}, {a8a9}, {b8b7}, {c}"
    yield f"mla {c}, {a10}, {b6b5}, {c}"
    yield f"strh {c}, [{DEST}, #32]"

    yield f"smuad {c}, {a8a9}, {b10b9}"
    yield f"mla {c}, {a10}, {b8b7}, {c}"
    yield f"strh {c}, [{DEST}, #36]"

    yield f"mul {c}, {a10}, {b10b9}"
    yield f"strh {c}, [{DEST}, #40]"

    yield f"pop {{{SRC2}}}"  # restore r2
    yield f"pop {{{SRC1}}}"  # restore r1

