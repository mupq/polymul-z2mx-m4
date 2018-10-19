from math import ceil

from .common import schoolbook_postprocess


def schoolbook_from8x8(SRC1, SRC2, DEST, n):
    instructions = schoolbook_from_next_8x8(SRC1, SRC2, DEST, 8*ceil(n / 8))
    yield from schoolbook_postprocess(SRC1, SRC2, DEST, instructions, n)


def schoolbook_from_next_8x8(SRC1, SRC2, DEST, n):
    a0 = "r6"; a1 = "r12"; a2 = "r3"; a3 = "r10";
    b0 = "r7"; b1 = "r8"; b2 = "r4"; b3 = "r14";
    tmp1 = "r9"; c = "r5";
    tmp0 = "r11";

    # {DEST} cannot be assumed to be zeroed
    # to improve performance, we initialize them on-the-fly by
    # keeping track which coeffs have already been set
    is_initialized = dict()

    for i in range(n//8):
        yield f"ldr {a0},[{SRC1},#{i*16}]"
        yield f"ldr {a1},[{SRC1},#{i*16+4}]"
        yield f"ldr {a2},[{SRC1},#{i*16+8}]"
        yield f"ldr {a3},[{SRC1},#{i*16+12}]"

        #       --- ---            --- ---
        #      | 3 | 1 |          | 4 | 1 |
        #   --- --- ---  -->   --- --- ---
        #  | 4 | 2 |          | 3 | 2 |
        #   --- ---            --- ---
        # so we can keep the coeffs of {SRC2} in registers when 2->3
        if i%2 == 0:
            r = range(n//8)
        else:
            r = range(n//8-1,-1, -1)
        for j in r:
            if i == 0 or (i%2 == 0 and j != 0) or (i%2 == 1 and j != n//8-1):
                yield f"ldr {b0}, [{SRC2},#{j*16}]"
                yield f"ldr {b1}, [{SRC2},#{j*16+4}]"
                yield f"ldr {b2}, [{SRC2},#{j*16+8}]"
                yield f"ldr {b3}, [{SRC2},#{j*16+12}]"

            # c0, c1
            if i*16+j*16 in is_initialized:
                yield f"ldr {tmp1}, [{DEST},#{i*16+j*16}]"


            if i*16+j*16+4 in is_initialized:
                yield f"ldr {c}, [{DEST},#{i*16+j*16+4}]"

            if i*16+j*16 in is_initialized:
                yield f"lsr {tmp0}, {tmp1}, #16"
                yield f"smlabb {tmp1}, {b0}, {a0}, {tmp1}"
                yield f"smladx {tmp0}, {b0}, {a0}, {tmp0}"
            else:
                yield f"smulbb {tmp1}, {b0}, {a0}"
                yield f"smuadx {tmp0}, {b0}, {a0}"
                is_initialized[i*16+j*16] = True

            yield f"pkhbt {tmp1}, {tmp1}, {tmp0}, lsl#16"
            yield f"str {tmp1}, [{DEST}, #{i*16+j*16}]"

            # c2, c3
            if i*16+j*16+4 in is_initialized:
                yield f"lsr {tmp0},{c},#16"
                yield f"smladx {tmp0}, {b0}, {a1}, {tmp0}"
                yield f"smlabb {c}, {b0}, {a1}, {c}"
            else:
                yield f"smuadx {tmp0}, {b0}, {a1}"
                yield f"smulbb {c}, {b0}, {a1}"
                is_initialized[i*16+j*16+4] = True

            yield f"pkhbt {tmp1}, {b1}, {b0}"
            yield f"smladx {tmp0}, {b1}, {a0}, {tmp0}"
            yield f"smlad {c}, {tmp1}, {a0}, {c}"
            yield f"pkhbt {tmp0}, {c}, {tmp0}, lsl #16"

            if i*16+j*16+8 in is_initialized:
                yield f"ldr {c}, [{DEST},#{i*16+j*16+8}]"

            # stores after loads are pipelined and thus take 1 instead of 2 cycles
            yield f"str {tmp0}, [{DEST},#{i*16+j*16+4}]"


            # c4, c5
            if i*16+j*16+8 in is_initialized:
                yield f"lsr {tmp0},{c},#16"
                yield f"smlabb {c}, {a2}, {b0}, {c}"
                yield f"smladx {tmp0}, {a2}, {b0}, {tmp0}"
            else:
                yield f"smulbb {c}, {a2}, {b0}"
                yield f"smuadx {tmp0}, {a2}, {b0}"
                is_initialized[i*16+j*16+8] = True


            yield f"smlad {c}, {tmp1}, {a1}, {c}"
            yield f"pkhbt {tmp1}, {b2}, {b1}"
            yield f"smlad {c}, {tmp1}, {a0}, {c}"

            yield f"smladx {tmp0}, {b1}, {a1}, {tmp0}"
            yield f"smladx {tmp0}, {b2}, {a0}, {tmp0}"
            yield f"pkhbt {tmp0}, {c}, {tmp0}, lsl #16"
            if i*16+j*16+12 in is_initialized:
                yield f"ldr {c}, [{DEST},#{i*16+j*16+12}]"
            yield f"str {tmp0}, [{DEST},#{i*16+j*16+8}]"

            # c6, c7

            if i*16+j*16+12 in is_initialized:
                yield f"lsr {tmp0}, {c}, #16"
                yield f"smlabb {c}, {a3}, {b0}, {c}"
                yield f"smladx {tmp0}, {a3}, {b0}, {tmp0}"
            else:
                yield f"smulbb {c}, {a3}, {b0}"
                yield f"smuadx {tmp0}, {a3}, {b0}"
                is_initialized[i*16+j*16+12] = True

            yield f"smlad {c}, {a1}, {tmp1}, {c}"
            yield f"pkhbt {tmp1}, {b1}, {b0}"
            yield f"smlad {c}, {a2}, {tmp1}, {c}"
            yield f"pkhbt {tmp1}, {b3}, {b2}"
            yield f"smlad {c}, {a0}, {tmp1}, {c}"

            yield f"smladx {tmp0}, {a2}, {b1}, {tmp0}"
            yield f"smladx {tmp0}, {a1}, {b2}, {tmp0}"
            yield f"smladx {tmp0}, {a0}, {b3}, {tmp0}"
            yield f"pkhbt {tmp0}, {c}, {tmp0}, lsl #16"
            if i*16+j*16+16 in is_initialized:
                yield f"ldr {c}, [{DEST},#{i*16+j*16+16}]"

            yield f"str {tmp0}, [{DEST},#{i*16+j*16+12}]"

            # c8,c9
            if i*16+j*16+16 in is_initialized:
                yield f"lsr {tmp0}, {c}, #16"
                yield f"smlatt {c}, {a0},{b3},{c}"
                yield f"smladx {tmp0}, {a3}, {b1}, {tmp0}"
            else:
                yield f"smultt {c}, {a0},{b3}"
                yield f"smuadx {tmp0}, {a3}, {b1}"
                is_initialized[i*16+j*16+16] = True

            yield f"smlad {c}, {a1},{tmp1},{c}"
            yield f"pkhbt {tmp1}, {b1}, {b0}"
            yield f"smlad {c}, {a3},{tmp1},{c}"
            yield f"pkhbt {tmp1}, {b2}, {b1}"
            yield f"smlad {c}, {a2},{tmp1},{c}"

            yield f"smladx {tmp0}, {a2}, {b2}, {tmp0}"
            yield f"smladx {tmp0}, {a1}, {b3}, {tmp0}"
            yield f"pkhbt {tmp0}, {c}, {tmp0}, lsl #16"

            if i*16+j*16+20 in is_initialized:
                yield f"ldr {c}, [{DEST},#{i*16+j*16+20}]"
            yield f"str {tmp0}, [{DEST},#{i*16+j*16+16}]"

            # c10,c11
            if i*16+j*16+20 in is_initialized:
                yield f"lsr {tmp0}, {c}, #16"
                yield f"smlatt {c}, {a1},{b3},{c}"
                yield f"smladx {tmp0}, {a3}, {b2}, {tmp0}"
            else:
                yield f"smultt {c}, {a1},{b3}"
                yield f"smuadx {tmp0}, {a3}, {b2}"
                is_initialized[i*16+j*16+20] = True

            yield f"smlad {c},{a3},{tmp1},{c}"
            yield f"pkhbt {tmp1}, {b3}, {b2}"
            yield f"smlad {c},{a2},{tmp1},{c}"

            yield f"smladx {tmp0}, {a2}, {b3}, {tmp0}"
            yield f"pkhbt {tmp0}, {c}, {tmp0}, lsl #16"

            if i*16+j*16+24 in is_initialized:
                yield f"ldr {c}, [{DEST},#{i*16+j*16+24}]"
            yield f"str {tmp0}, [{DEST},#{i*16+j*16+20}]"

            # c12,c13
            if i*16+j*16+24 in is_initialized:
                yield f"lsr {tmp0}, {c}, #16"
                yield f"smlad {c},{a3},{tmp1},{c}"
                yield f"smladx {tmp0},{a3},{b3},{tmp0}"
            else:
                yield f"smuad {c},{a3},{tmp1}"
                yield f"smuadx {tmp0},{a3},{b3}"
                is_initialized[i*16+j*16+24] = True

            yield f"smlatt {c}, {a2},{b3},{c}"
            yield f"pkhbt {tmp0}, {c}, {tmp0}, lsl #16"

            if i*16+j*16+28 in is_initialized:
                yield f"ldrh {c}, [{DEST}, #{i*16+j*16+28}]"
            yield f"str {tmp0}, [{DEST},#{i*16+j*16+24}]"

            # c14
            if i*16+j*16+28 in is_initialized:
                yield f"smlatt {tmp0},{a3},{b3},{c}"
                yield f"strh {tmp0}, [{DEST}, #{i*16+j*16+28}]"
            else:
                yield f"smultt {tmp0},{a3},{b3}"
                # if this is the final coefficient, we should not exceed bounds
                if i*16+j*16+28 + 4 > 2 * (2 * n - 1):
                    yield f"strh {tmp0}, [{DEST}, #{i*16+j*16+28}]"
                else:
                    yield f"movt {tmp0}, #0"
                    yield f"str {tmp0}, [{DEST}, #{i*16+j*16+28}]"
                is_initialized[i*16+j*16+28] = True


    # this loop is only for n that are not multiples of 8
    # the preprocessing wrapper makes this a no-op

    for j in range(n%8):
      # load a8+j and b8+j
      offset = (n//8)*16
      yield f"ldrh {a0},[{SRC1}, #{offset+j*2}]"
      yield f"ldrh {b0},[{SRC2}, #{offset+j*2}]"
      for i in range(n):
          yield f"ldrh {a1},[{SRC1}, #{i*2}]"
          yield f"ldrh {b1},[{SRC2}, #{i*2}]"
          if j*2+i*2+offset in is_initialized or i+j<(n//8)*8:
              yield f"ldrh {tmp0},[{DEST}, #{j*2+i*2+offset}]"
              yield f"mla {tmp0},{a1},{b0},{tmp0}"
          else:
              yield f"mul {tmp0},{a1},{b0}"
              is_initialized[j*2+i*2+offset] = True
          if i < (n//8)*8:
            yield f"mla {tmp0},{b1},{a0},{tmp0}"
          yield f"strh {tmp0},[{DEST}, #{j*2+i*2+offset}]"
