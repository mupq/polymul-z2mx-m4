from .common import Registers


def schoolbook_13(SRC1, SRC2, DEST):
    # reverse to prioritize low registers (as these have 16-bit loads)
    regs = Registers(reversed([f'r{i}' for i in range(0, 13)] + ["r14"]))

    # consider SRC1, SRC2 and DEST allocated
    regs.alloc(SRC1)
    regs.alloc(SRC2)
    regs.alloc(DEST)

    # these can be flexible, do not need to be r0 and r1 after first re-alloc
    src1 = SRC1
    src2 = SRC2

    a0a1 = regs.alloc()
    a2a3 = regs.alloc()
    a4a5 = regs.alloc()
    a6a7 = regs.alloc()
    a8a9 = regs.alloc()
    a10a11 = regs.alloc()
    a12 =  regs.alloc()

    yield f"ldr {a0a1},[{SRC1}, #0]"
    yield f"ldr {a2a3},[{SRC1}, #4]"
    yield f"ldr {a4a5},[{SRC1}, #8]"
    yield f"ldr {a6a7},[{SRC1}, #12]"
    yield f"ldr {a8a9},[{SRC1}, #16]"
    yield f"ldr {a10a11},[{SRC1}, #20]"
    yield f"ldrh {a12},[{SRC1}, #24]"

    yield f"push {{{SRC1}}}"  # this clears up r1
    regs.free(SRC1)

    # we do not have space to keep a fully in registers; must store a or b
    # intuitively we prefer to keep b in registers, since it's repacked
    yield f"push {{{a10a11}}}"
    yield f"push {{{a12}}}"
    regs.free(a10a11)
    regs.free(a12)

    b0b1 = regs.alloc()
    b2b3 = regs.alloc()
    b4b5 = regs.alloc()
    b6b7 = regs.alloc()
    b8b9 = regs.alloc()
    b10b11 = regs.alloc()
    b12 =  regs.alloc()

    yield f"ldr {b0b1},[{SRC2}, #0]"
    yield f"ldr {b2b3},[{SRC2}, #4]"
    yield f"ldr {b4b5},[{SRC2}, #8]"
    yield f"ldr {b6b7},[{SRC2}, #12]"
    yield f"ldr {b8b9},[{SRC2}, #16]"
    yield f"ldr {b10b11},[{SRC2}, #20]"
    yield f"ldrh {b12},[{SRC2}, #24]"

    yield f"push {{{SRC2}}}"  # this clears up r2
    regs.free(SRC2)

    c = regs.alloc()

    # dest is still available in r0

    # now we first compute coeffs for odd exponents, i.e. a0*b1 + a1+b0 etc.
    # since these are currently paired together, i.e. b0b1 and a0a1

    #1
    yield f"smuadx {c}, {a0a1}, {b0b1}"
    yield f"strh {c}, [{DEST}, #2]"

    #3
    yield f"smuadx {c}, {a0a1}, {b2b3}"
    yield f"smladx {c}, {a2a3}, {b0b1}, {c}"
    yield f"strh {c}, [{DEST}, #6]"

    #5
    yield f"smuadx {c}, {a0a1}, {b4b5}"
    yield f"smladx {c}, {a2a3}, {b2b3}, {c}"
    yield f"smladx {c}, {a4a5}, {b0b1}, {c}"
    yield f"strh {c}, [{DEST}, #10]"

    #7
    yield f"smuadx {c}, {a0a1}, {b6b7}"
    yield f"smladx {c}, {a2a3}, {b4b5}, {c}"
    yield f"smladx {c}, {a4a5}, {b2b3}, {c}"
    yield f"smladx {c}, {a6a7}, {b0b1}, {c}"
    yield f"strh {c}, [{DEST}, #14]"

    #9
    yield f"smuadx {c}, {a0a1}, {b8b9}"
    yield f"smladx {c}, {a2a3}, {b6b7}, {c}"
    yield f"smladx {c}, {a4a5}, {b4b5}, {c}"
    yield f"smladx {c}, {a6a7}, {b2b3}, {c}"
    yield f"smladx {c}, {a8a9}, {b0b1}, {c}"
    yield f"strh {c}, [{DEST}, #18]"

    #11
    yield f"smuadx {c}, {a0a1}, {b10b11}"
    yield f"smladx {c}, {a2a3}, {b8b9}, {c}"
    yield f"smladx {c}, {a4a5}, {b6b7}, {c}"
    yield f"smladx {c}, {a6a7}, {b4b5}, {c}"
    yield f"smladx {c}, {a8a9}, {b2b3}, {c}"

    yield f"push {{{a4a5}}}"
    regs.free(a4a5)  # an a[i] in the middle avoids potential pipeline issues?
    a10a11 = regs.alloc()
    yield f"ldr {a10a11}, [sp, #12]"

    yield f"smladx {c}, {a10a11}, {b0b1}, {c}"
    yield f"strh {c}, [{DEST}, #22]"

    #13
    # since we now have a10a11 around, we first do that mult;
    yield f"smuadx {c}, {a10a11}, {b2b3}"
    yield f"smlatb {c}, {a0a1}, {b12}, {c}"
    yield f"smladx {c}, {a2a3}, {b10b11}, {c}"

    # we push a0a1 since we won't need it for a long time
    yield f"str {a0a1}, [sp, #12]"
    regs.free(a0a1)
    # and now we need to retrieve a4a5
    a4a5 = regs.alloc()
    yield f"pop {{{a4a5}}}"

    yield f"smladx {c}, {a4a5}, {b8b9}, {c}"
    yield f"smladx {c}, {a6a7}, {b6b7}, {c}"
    yield f"smladx {c}, {a8a9}, {b4b5}, {c}"

    # again need to make space need everything so storing a4a5 again
    yield f"push {{{a4a5}}}"
    regs.free(a4a5)
    # and now we need to retrieve a12
    a12 = regs.alloc()
    yield f"ldrh {a12}, [sp, #8]"

    yield f"smlabt {c}, {a12}, {b0b1}, {c}"
    yield f"strh {c}, [{DEST}, #26]"

    #15
    yield f"smultb {c}, {a2a3}, {b12}"
    yield f"smladx {c}, {a6a7}, {b8b9}, {c}"
    yield f"smladx {c}, {a8a9}, {b6b7}, {c}"
    yield f"smladx {c}, {a10a11}, {b4b5}, {c}"
    yield f"smlabt {c}, {a12}, {b2b3}, {c}"

    # missing a4a5, so have delayed that; can now overwrite a2a3
    yield f"str {a2a3}, [sp, #8]"
    regs.free(a2a3)
    a4a5 = regs.alloc()
    yield f"pop {{{a4a5}}}"

    yield f"smladx {c}, {a4a5}, {b10b11}, {c}"
    yield f"strh {c}, [{DEST}, #30]"

    #17
    yield f"smultb {c}, {a4a5}, {b12}"
    yield f"smladx {c}, {a6a7}, {b10b11}, {c}"
    yield f"smladx {c}, {a8a9}, {b8b9}, {c}"
    yield f"smladx {c}, {a10a11}, {b6b7}, {c}"
    yield f"smlabt {c}, {a12}, {b4b5}, {c}"
    yield f"strh {c}, [{DEST}, #34]"

    #19
    yield f"smultb {c}, {a6a7}, {b12}"
    yield f"smladx {c}, {a8a9}, {b10b11}, {c}"
    yield f"smladx {c}, {a10a11}, {b8b9}, {c}"
    yield f"smlabt {c}, {a12}, {b6b7}, {c}"
    yield f"strh {c}, [{DEST}, #38]"

    #21
    yield f"smultb {c}, {a8a9}, {b12}"
    yield f"smladx {c}, {a10a11}, {b10b11}, {c}"
    yield f"smlabt {c}, {a12}, {b8b9}, {c}"
    yield f"strh {c}, [{DEST}, #42]"

    #23
    yield f"smultb {c}, {a10a11}, {b12}"
    yield f"smlabt {c}, {a12}, {b10b11}, {c}"
    yield f"strh {c}, [{DEST}, #46]"

    # repack b to isolate b0; b2b1, b4b3, b6b5, b8b7, b10b9, b12b11
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
    yield f"pkhtb {b10b9}, {b8b9}, {b10b11}"
    b12b11 = b10b11
    yield f"pkhtb {b12b11}, {b10b11}, {b12}"
    c = b12
    del b0b1, b2b3, b4b5, b6b7, b8b9, b10b11, b12

    # currently have a0a1 and a2a3 on the stack, so go in descending order

    # 24
    yield f"mul {c}, {a12}, {b12b11}"
    yield f"strh {c}, [{DEST}, #48]"

    # 22
    yield f"smuad {c}, {a10a11}, {b12b11}"
    yield f"mla {c}, {a12}, {b10b9}, {c}"
    yield f"strh {c}, [{DEST}, #44]"

    # 20
    yield f"smuad {c}, {a8a9}, {b12b11}"
    yield f"smlad {c}, {a10a11}, {b10b9}, {c}"
    yield f"mla {c}, {a12}, {b8b7}, {c}"
    yield f"strh {c}, [{DEST}, #40]"

    # 18
    yield f"smuad {c}, {a6a7}, {b12b11}"
    yield f"smlad {c}, {a8a9}, {b10b9}, {c}"
    yield f"smlad {c}, {a10a11}, {b8b7}, {c}"
    yield f"mla {c}, {a12}, {b6b5}, {c}"
    yield f"strh {c}, [{DEST}, #36]"

    # 16
    yield f"smuad {c}, {a4a5}, {b12b11}"
    yield f"smlad {c}, {a6a7}, {b10b9}, {c}"
    yield f"smlad {c}, {a8a9}, {b8b7}, {c}"
    yield f"smlad {c}, {a10a11}, {b6b5}, {c}"
    yield f"mla {c}, {a12}, {b4b3}, {c}"
    yield f"strh {c}, [{DEST}, #32]"

    # 14
    yield f"mul {c}, {a12}, {b2b1}"
    yield f"smlad {c}, {a10a11}, {b4b3}, {c}"
    yield f"smlad {c}, {a8a9}, {b6b5}, {c}"
    yield f"smlad {c}, {a6a7}, {b8b7}, {c}"
    yield f"smlad {c}, {a4a5}, {b10b9}, {c}"

    yield f"push {{{a6a7}}}"
    regs.free(a6a7)  # an a[i] in the middle avoids potential pipeline issues?
    a2a3 = regs.alloc()
    yield f"ldr {a2a3}, [sp, #8]"

    yield f"smlad {c}, {a2a3}, {b12b11}, {c}"
    yield f"strh {c}, [{DEST}, #28]"

    # 12
    yield f"mul {c}, {a12}, {b0}"

    # no longer need a12 from this point on
    regs.free(a12)
    a6a7 = regs.alloc()
    yield f"pop {{{a6a7}}}"

    yield f"smlad {c}, {a10a11}, {b2b1}, {c}"
    yield f"smlad {c}, {a8a9}, {b4b3}, {c}"
    yield f"smlad {c}, {a6a7}, {b6b5}, {c}"
    yield f"smlad {c}, {a4a5}, {b8b7}, {c}"
    yield f"smlad {c}, {a2a3}, {b10b9}, {c}"

    yield f"push {{{a6a7}}}"
    regs.free(a6a7)  # an a[i] in the middle avoids potential pipeline issues?
    a0a1 = regs.alloc()
    yield f"ldr {a0a1}, [sp, #12]"

    yield f"smlad {c}, {a0a1}, {b12b11}, {c}"
    yield f"strh {c}, [{DEST}, #24]"

    # 10
    yield f"mul {c}, {a10a11}, {b0}"

    # no longer need a10a11 from this point on
    regs.free(a10a11)
    a6a7 = regs.alloc()
    yield f"pop {{{a6a7}}}"

    yield f"smlad {c}, {a8a9}, {b2b1}, {c}"
    yield f"smlad {c}, {a6a7}, {b4b3}, {c}"
    yield f"smlad {c}, {a4a5}, {b6b5}, {c}"
    yield f"smlad {c}, {a2a3}, {b8b7}, {c}"
    yield f"smlad {c}, {a0a1}, {b10b9}, {c}"
    yield f"strh {c}, [{DEST}, #20]"

    # 8
    yield f"smuad {c}, {a0a1}, {b8b7}"
    yield f"smlad {c}, {a2a3}, {b6b5}, {c}"
    yield f"smlad {c}, {a4a5}, {b4b3}, {c}"
    yield f"smlad {c}, {a6a7}, {b2b1}, {c}"
    yield f"mla {c}, {a8a9}, {b0}, {c}"
    yield f"strh {c}, [{DEST}, #16]"

    # 6
    yield f"smuad {c}, {a0a1}, {b6b5}"
    yield f"smlad {c}, {a2a3}, {b4b3}, {c}"
    yield f"smlad {c}, {a4a5}, {b2b1}, {c}"
    yield f"mla {c}, {a6a7}, {b0}, {c}"
    yield f"strh {c}, [{DEST}, #12]"

    # 4
    yield f"smuad {c}, {a0a1}, {b4b3}"
    yield f"smlad {c}, {a2a3}, {b2b1}, {c}"
    yield f"mla {c}, {a4a5}, {b0}, {c}"
    yield f"strh {c}, [{DEST}, #8]"

    # 2
    yield f"smuad {c}, {a0a1}, {b2b1}"
    yield f"mla {c}, {a2a3}, {b0}, {c}"
    yield f"strh {c}, [{DEST}, #4]"

    # 0
    yield f"mul {c}, {a0a1}, {b0}"
    yield f"strh {c}, [{DEST}, #0]"

    yield f"pop {{{SRC2}}}"  # restore r2
    yield f"add sp, #8"  # discard remaining temporary inputs on the stack
    yield f"pop {{{SRC1}}}"  # restore r1
