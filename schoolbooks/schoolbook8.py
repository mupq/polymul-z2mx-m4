
def schoolbook_8(SRC1, SRC2, DEST):
    a0a1 = "r3"
    a2a3 = "r4"
    a4a5 = "r5"
    a6a7 = "r6"

    yield f"ldr {a0a1},[{SRC1}, #0]"
    yield f"ldr {a2a3},[{SRC1}, #4]"
    yield f"ldr {a4a5},[{SRC1}, #8]"
    yield f"ldr {a6a7},[{SRC1}, #12]"

    b0b1 = "r7"
    b2b3 = "r8"
    b4b5 = "r9"
    b6b7 = "r10"

    yield f"ldr {b0b1},[{SRC2}, #0]"
    yield f"ldr {b2b3},[{SRC2}, #4]"
    yield f"ldr {b4b5},[{SRC2}, #8]"
    yield f"ldr {b6b7},[{SRC2}, #12]"

    c = "r11"

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

    yield f"smuadx {c}, {a2a3}, {b6b7}"
    yield f"smladx {c}, {a4a5}, {b4b5}, {c}"
    yield f"smladx {c}, {a6a7}, {b2b3}, {c}"
    yield f"strh {c}, [{DEST}, #18]"

    yield f"smuadx {c}, {a4a5}, {b6b7}"
    yield f"smladx {c}, {a6a7}, {b4b5}, {c}"
    yield f"strh {c}, [{DEST}, #22]"

    yield f"smuadx {c}, {a6a7}, {b6b7}"
    yield f"strh {c}, [{DEST}, #26]"

    # repack b to isolate b0; b2b1, b4b3, b6b5, b8b7, b10b9
    b0 = b0b1
    b2b1 = c
    yield f"pkhtb {b2b1}, {b0b1}, {b2b3}"
    b4b3 = b2b3
    yield f"pkhtb {b4b3}, {b2b3}, {b4b5}"
    b6b5 = b4b5
    yield f"pkhtb {b6b5}, {b4b5}, {b6b7}"
    bxb7 = b6b7
    c = "r12"
    del b0b1, b2b3, b4b5, b6b7

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

    yield f"smultt {c}, {a0a1}, {bxb7}"
    yield f"smlad {c}, {a2a3}, {b6b5}, {c}"
    yield f"smlad {c}, {a4a5}, {b4b3}, {c}"
    yield f"smlad {c}, {a6a7}, {b2b1}, {c}"
    yield f"strh {c}, [{DEST}, #16]"

    yield f"smultt {c}, {a2a3}, {bxb7}"
    yield f"smlad {c}, {a4a5}, {b6b5}, {c}"
    yield f"smlad {c}, {a6a7}, {b4b3}, {c}"
    yield f"strh {c}, [{DEST}, #20]"

    yield f"smultt {c}, {a4a5}, {bxb7}"
    yield f"smlad {c}, {a6a7}, {b6b5}, {c}"
    yield f"strh {c}, [{DEST}, #24]"

    yield f"smultt {c}, {a6a7}, {bxb7}"
    yield f"strh {c}, [{DEST}, #28]"

