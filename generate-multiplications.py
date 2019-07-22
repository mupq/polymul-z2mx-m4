#!/usr/bin/env python3

import sys
from functools import wraps
from math import ceil, floor
from collections import defaultdict

from schoolbooks import (schoolbook_13, schoolbook_14, schoolbook_15,
                         schoolbook_from8x8, schoolbook_from_next_8x8,
                         schoolbook_small, schoolbook_medium)

DEST = "r0"
SRC1 = "r1"
SRC2 = "r2"

functions = dict()


def fn_name(fn, size):
    return f"{fn.__name__}_{size}x{size}"


def schoolbook(t, n):
    yield "push {lr}"

    if n <= 12:
        yield from schoolbook_small(SRC1, SRC2, DEST, n)
    elif n == 13:
        yield from schoolbook_13(SRC1, SRC2, DEST)
    elif n == 14:
        yield from schoolbook_14(SRC1, SRC2, DEST)
    elif n in [25, 41]:
        yield from schoolbook_from_next_8x8(SRC1, SRC2, DEST, n)
    elif n in [15, 16, 31, 32] or 37 <= n <= 41 or 45 <= n <= 48:  # some are quite close
        yield from schoolbook_from8x8(SRC1, SRC2, DEST, n)
    else:
        yield from schoolbook_medium(SRC1, SRC2, DEST, n)

    yield "pop {lr}"


def render(fn, t, size, *args, **kwargs):
    yield from fn(t, size, *args, **kwargs)
    yield ("bx lr")


def alloc_stack(stack_space, reg):
    if abs(stack_space) < 4096:
        if stack_space >= 0:
            yield f"sub sp, #{stack_space}"
        else:
            yield f"add sp, #{-stack_space}"
    else:
        if stack_space >= 0:
            yield f"movw {reg}, #{stack_space}"
            yield f"sub sp,{reg}"
        else:
            yield f"movw {reg}, #{-stack_space}"
            yield f"add sp, {reg}"

# This only passes args and kwargs for the first occurrence of `call`
# that's generally not a problem, as there is no immediate reason to re-use
# a multiplication function with different args / kwargs
def call(fn, t, size, *args, **kwargs):
    """
    Assumes the custom ABI registers r0-r2 for DEST / SRC1 / SRC2,
    assumes these are callee-saved,
    assumes the rest is caller-saved, for efficiency.
    """
    if fn_name(fn, size) not in functions:
        functions[fn_name(fn, size)] = list(render(fn, t, size, *args, **kwargs))
    yield f"bl {fn_name(fn, size)}"


def karatsuba(t, n, offsets=defaultdict(int), top=False):
    if n <= t:
        # If this is the topmost karatsuba, this creates a little call overhead
        # for all relevant N, however, this is irrelevant.
        if top:
            yield "push {lr}"
        yield from call(schoolbook, t, n)
        if top:
            yield "pop {lr}"
        return

    if top:
        yield "push {lr}"
    yield from karatsuba(t, ceil(n / 2))  # mul alow with blow into DEST_low

    yield f"push {{{SRC1}}}"
    yield f"push {{{SRC2}}}"
    yield f"push {{{DEST}}}"

    yield f"add {SRC1}, {SRC1}, #{2*ceil(n / 2)}"  # move SRC1 pointer to high
    yield f"add {SRC2}, {SRC2}, #{2*ceil(n / 2)}"  # move SRC2 pointer to high
    yield f"add {DEST}, {DEST}, #{2*2*ceil(n / 2)}"  # move DEST pointer to high half

    yield from karatsuba(t, floor(n / 2))  # mul ahigh with bhigh into DESThigh

    # if we don't move it back to the low half
    yield f"sub {SRC1}, {SRC1}, #{2*ceil(n / 2)}"  # move SRC1 pointer to low
    yield f"sub {SRC2}, {SRC2}, #{2*ceil(n / 2)}"  # move SRC2 pointer to low

    # create space for (al + ah), (bl + bh) and z1
    # for the sp, we need to ensure that each block starts at a multiple of 4 bytes
    #   so we ceil the starts of polynomials to multiples of 4
    sp_al_plus_ah_width =  4*ceil(2*ceil(n / 2) / 4)
    sp_z1_width = 4*ceil(2*(2*ceil(n / 2) - 1) / 4)
    yield from alloc_stack(2 * sp_al_plus_ah_width + sp_z1_width, 'r3')

    # 12 free registers to use during add_low_high, to pipeline
    regs = [f"r{r}" for r in range(3,13)] + [DEST, "r14"]

    def add_low_high(lowsrc, out, offset=0):
        i = 0
        while i < floor(n / 2) - 1:
            pairs = []
            # first do all the loads, so that they pipeline
            for rlow, rhigh in [regs[j:j+2] for j in range(0, len(regs), 2)]:
                pairs.append((rlow, rhigh, i))
                # aligning to full words here does not seem to help, as that
                # results in misaligning the output stores and often only fixes
                # one of the two sources (for odd limb sizes)
                yield f"ldr {rlow}, [{lowsrc}, #{2*i}]"  # low
                yield f"ldr {rhigh}, [{lowsrc}, #{2*i + 2*ceil(n / 2)}]"  # high

                i += 2
                if i >= floor(n / 2) - 1:
                    break

            for rlow, rhigh, _ in pairs:
                yield f"uadd16 {rlow}, {rlow}, {rhigh}"  # compute low + high

            for rlow, rhigh, j in pairs:
                yield f"str {rlow}, [{out}, #{offset + 2*j}]"

        # if we could not pair up every addition for uadd16
        if floor(n / 2) & 1:
            i = floor(n / 2) - 1
            yield f"ldrh r5, [{lowsrc}, #{2*i}]"
            yield f"ldrh r6, [{lowsrc}, #{2*i + 2*ceil(n / 2)}]"
            yield "add r5, r5, r6"  # compute low + high
            yield f"strh r5, [{out}, #{offset + 2*i}]"

        # if n was odd, we cannot load the last 'high' position
        # instead we simply assume a zero there, and copy the 'low' value
        # this could've been part of the loop, but that makes conversion to an asm loop harder
        if n & 1:
            yield f"ldrh r5, [{lowsrc}, #{2*(ceil(n / 2) - 1)}]"
            yield f"strh r5, [{out}, #{offset + 2*(ceil(n / 2) - 1)}]"

    yield from add_low_high(SRC1, 'sp')

    yield f"mov {SRC1}, sp"  # point to alow+ahigh

    yield from add_low_high(SRC2, 'sp', sp_al_plus_ah_width)

    yield f"add {SRC2}, sp, #{sp_al_plus_ah_width}"  # point to blow+bhigh
    yield f"add {DEST}, sp, #{2 * sp_al_plus_ah_width}"  # point to DESTination for z1

    yield from karatsuba(t, ceil(n / 2))  # compute z1

    yield f"mov r3, {DEST}"  # keep a pointer to z1
    # grab the original DEST; we cannot move the stack pointer back up to pop,
    # because r3 is still holding a reference to a part of the stack
    if 2 * sp_al_plus_ah_width + sp_z1_width >= 4096:
        # fixes too large offset for N>=1024
        yield f"movw r11, #{2 * sp_al_plus_ah_width + sp_z1_width}"
        yield f"ldr {DEST}, [sp, r11]"
    else:
        yield f"ldr {DEST}, [sp, #{2 * sp_al_plus_ah_width + sp_z1_width}]"

    # for the middle section of the destination;
    # deal with two items at a time to handle mutual exclusive modifications
    for i in range(ceil(n / 2)):
        yield "# <start combine>"
        zero = defaultdict(bool)  # keep track of registers we know must be zero

        # for unbalanced n, the high half needs less additions.
        # check if the final addition is actually within bounds;
        # otherwise it will cancel out, and there is no space to write that to memory
        writing_high_half = i < 2*floor(n / 2) - 1

        yield f"ldrh r5, [r3, #{2*i}]"  # z1low
        if i < ceil(n / 2) - 1:  # the final entry of z1high is an implicit zero
            if writing_high_half:  # we only use it in this case
                yield f"ldrh r6, [r3, #{2*(i + ceil(n / 2))}]"  # z1high
        else:
            zero['r6'] = True

        yield f"ldrh r7, [{DEST}, #{2*i}]"  # z0low
        if i < ceil(n / 2) - 1:  # the final entry of z0high is an implicit zero
            yield f"ldrh r8, [{DEST}, #{2*(i + ceil(n / 2))}]"  # z0high
        else:
            zero['r8'] = True

        # z2low; for odd n, this is actually part of z2's high half in the last iteration
        #  thus we need to be careful to not load out of bounds
        if i < 2*floor(n / 2) - 1:
            yield f"ldrh r9, [{DEST}, #{2*(i + 2*ceil(n / 2))}]"  # z2low
        else:
            zero['r9'] = True
        if i + ceil(n / 2) < 2*floor(n / 2) - 1:  # the final entries of z2high are implicit zeroes
            # need to use ceil(n/2) here even though the midway point of z2 is at floor(n/2);
            #   the polynomial we're adding into has its midway point at ceil(n/2),
            #   i.e. that's the base we're using for Karatsuba's trick
            yield f"ldrh r10, [{DEST}, #{2*(i + 2*ceil(n / 2) + ceil(n / 2))}]"  # z2high
        else:
            zero['r10'] = True

        yield f"sub r11, r5, r7"  # z1low - z0low

        refined = 'r8'
        negated_refine = False
        if zero['r8'] and zero['r9']:
            zero['refined'] = True
        elif not zero['r9'] and zero['r8']:
            refined = 'r9'
            negated_refine = True
        elif not zero['r8'] and zero['r9']:
            pass
        else:
            yield "sub r8, r8, r9"  # z0high - z2low (for refinement)

        if not zero['refined']:
            if negated_refine:
                yield f"sub r11, r11, {refined}"  # - (z2low - z0high)
            else:
                yield f"add r11, r11, {refined}"  # + (z0high - z2low)
        yield f"strh r11, [{DEST}, #{2*(i + ceil(n / 2))}]"
        # check if this addition is actually within bounds;
        # it should cancel out, and there is no space to write that to memory
        if writing_high_half:
            # this block computes z1high - (z0high - z2low) - z2high
            # but all of these components can potentially be zero, so check
            out = None
            if zero['r6']:
                if not zero['refined']:
                    out = refined
                    if not negated_refine:
                        yield f"neg {out}, {refined}"  # z1high - (z0high - z2low)
            else:
                out = 'r6'
                if not zero['refined']:
                    if negated_refine:
                        yield f"add {out}, r6, {refined}"  # z1high - (z0high - z2low)
                    else:
                        yield f"sub {out}, r6, {refined}"  # z1high - (z0high - z2low)
            if not zero['r10']:
                if out:
                    yield f"sub {out}, {out}, r10"  # - z2high
                else:
                    out = 'r10'
            if out is not None:
                # unless the case where 'out' == r9 and is not modified
                if not (zero['r6'] and zero['r10'] and zero['r8']):
                    yield f"strh {out}, [{DEST}, #{2*(i + 2 * ceil(n / 2))}]"
        yield "# <end combine>"

    # now we can restore the stack pointer, and skip past the stored DEST
    yield from alloc_stack(-(2 * sp_al_plus_ah_width + sp_z1_width + 4), "r1")

    yield f"pop {{{SRC2}}}"
    yield f"pop {{{SRC1}}}"
    if top:
        yield "pop {lr}"

def postprocess_karatsuba(instructions):
    # This attempts to merge 'combine blocks' using uadd16 and usub16 operations
    bufs = defaultdict(list)
    state = "idle"
    for ins in instructions:
        # state transitions on the edges of the combine blocks
        if state is 'idle' and 'start combine' in ins:
            state = 1
            continue
        elif state is 1 and 'end combine' in ins:
            state = 'between'
            continue
        elif state is 'between':
            if 'start combine' in ins:
                state = 2
            else:
                yield from bufs[1]
                yield ins
                bufs = defaultdict(list)
                state = 'idle'  # we hit a '1' that had no '2'
            continue
        elif state is 2 and 'end combine' in ins:
            state = 'idle'
            # test if identical up to offset; if identical, merge
            insCs = []
            for insA, insB in zip(bufs[1], bufs[2]):
                insA = insA.split(' ')[0], ' '.join(insA.split(' ')[1:])
                insB = insB.split(' ')[0], ' '.join(insB.split(' ')[1:])
                if insA[0] != insB[0]:
                    yield from bufs[1] + bufs[2]
                    break
                if insA[0] in ['add', 'sub']:
                    if insA != insB:
                        yield from bufs[1] + bufs[2]
                        break
                    insCs.append('u' + insA[0] + '16 ' + insA[1])
                elif insA[0] in ['ldrh', 'strh']:
                    op, offset = insB[1].split("#")
                    offset = int(offset.replace(']', '')) - 2
                    insB = insB[0], op + "#" + str(offset) + ']'
                    if insA != insB:
                        yield from bufs[1] + bufs[2]
                        break
                    insCs.append(insA[0][:3] + ' ' + insA[1])
                else:
                    raise Exception("Unrecognized ins in combine block!")
            else:
                yield from insCs

            bufs = defaultdict(list)
            continue

        if state is 'idle':
            yield ins
        else:
            bufs[state] += [ins]

def toom4(t, n, innermul=karatsuba):
    limb_size = ceil(n/4)
    if limb_size%2 == 1:
      raise Exception("can only handle even limb sizes")
    k = n - (3*limb_size)
    # allocate stack mem
    # evaluation: 2*5 polynomials of limb_size coefficients
    # multiplication: 7 polynomials of 2*limb_size-1

    stack_space_x = (6*limb_size)*2
    stack_space_y = (6*limb_size)*2
    # 2*limbsize - 1 is enough, but for alignment we want multiples of 4
    stack_space_t = 7*(2*limb_size)*2
    yield from alloc_stack(stack_space_x+stack_space_y+stack_space_t, "r4")

    # some offsets
    f0 = g0 = 0
    f1 = g1 = 2*1*limb_size
    f2 = g2 = 2*2*limb_size
    f3 = g3 = 2*3*limb_size

    x1 = 2*0*limb_size
    x2 = 2*1*limb_size
    x3 = 2*2*limb_size
    x4 = 2*3*limb_size
    x5 = 2*4*limb_size
    x6 = 2*5*limb_size

    y = "r3"
    y_offset =  2*6*limb_size
    yield f"add {y}, sp, #{y_offset}"

    y1 = 2*0*limb_size
    y2 = 2*1*limb_size
    y3 = 2*2*limb_size
    y4 = 2*3*limb_size
    y5 = 2*4*limb_size
    y6 = 2*5*limb_size

    t_base = y_offset*2
    t0 = t_base
    t1 = t_base + 2*1*(2*limb_size)
    t2 = t_base + 2*2*(2*limb_size)
    t3 = t_base + 2*3*(2*limb_size)
    t4 = t_base + 2*4*(2*limb_size)
    t5 = t_base + 2*5*(2*limb_size)
    t6 = t_base + 2*6*(2*limb_size)

    # evaluate
    for i in range(0, limb_size, 2):
        yield f"ldr r4, [{SRC1},#{f0 + i*2}]"
        yield f"ldr r5, [{SRC1},#{f1 + i*2}]"
        yield f"ldr r6, [{SRC1},#{f2 + i*2}]"

        if (k%2 == 1 and i<k-1) or (k%2 == 0 and i<k):
          yield f"ldr r7, [{SRC1},#{f3 + i*2}]"
        elif (k%2 == 1 and i<k):
          yield f"ldrh r7, [{SRC1},#{f3 + i*2}]"
        else:
          yield f"mov r7, #0"

        yield f"str r7, [sp, #{x6 + i*2}]"

        def evaluate():
          yield f"uadd16 r14, r4, r6" # tmp0 = f0[i] + f2[i]
          yield f"uadd16 r12, r5, r7" # tmp1 = f1[i] + f3[i]

          yield f"uadd16 r11, r14, r12" # tmp0+tmp1
          yield f"usub16 r12, r14, r12" # tmp0-tmp1

          yield f"uadd16 r14, r6, r6"   # 2*f2[i]
          yield f"uadd16 r14, r14, r14" # 4*f2[i]
          yield f"uadd16 r14, r4, r14"  # tmp0 = f0[i] + 4*f2[i]
          yield f"uadd16 r10, r7, r7"   # f3[i]<<1
          yield f"uadd16 r10, r10, r10" # f3[i]<<2
          yield f"uadd16 r10, r5, r10"  # tmp1 = (f1[i]+ (f3[i] << 2));

          yield f"uadd16 r10, r10, r10"
          yield f"uadd16 r9, r14, r10" # tmp0+2*tmp1
          yield f"usub16 r10,r14, r10" # tmp0-2*tmp1

          yield f"uadd16 r8, r7, r7"  # 2*f3[i]
          yield f"uadd16 r7, r8, r7"  # 3*f3[i]
          yield f"uadd16 r7, r7, r6"   # f2[i] + 3*f3[i]
          yield f"uadd16 r8, r7, r7"  # 2*(f2[i] + 3*f3[i])
          yield f"uadd16 r7, r7, r8"  # 3*(f2[i] + 3*f3[i])
          yield f"uadd16 r7, r7, r5"  # f1[i]+3*(f2[i] + 3*f3[i])
          yield f"uadd16 r8, r7, r7"  # 2*(f1[i]+3*(f2[i] + 3*f3[i]))
          yield f"uadd16 r7, r7, r8" # 3*(f1[i]+3*(f2[i] + 3*f3[i]))
          yield f"uadd16 r7, r7, r4"

        yield from evaluate()

        yield f"str r11, [sp, #{x1 + i*2}]"
        yield f"str r12, [sp, #{x2 + i*2}]"
        yield f"str r9,  [sp, #{x3 + i*2}]"
        yield f"str r10, [sp, #{x4 + i*2}]"
        yield f"str r7,  [sp, #{x5 + i*2}]"

        yield f"ldr r4, [{SRC2},#{g0 + i*2}]"
        yield f"ldr r5, [{SRC2},#{g1 + i*2}]"
        yield f"ldr r6, [{SRC2},#{g2 + i*2}]"

        if (k%2 == 1 and i<k-1) or (k%2 == 0 and i<k):
          yield f"ldr r7, [{SRC2},#{g3 + i*2}]"
        elif (k%2 == 1 and i<k):
          yield f"ldrh r7, [{SRC2},#{g3 + i*2}]"
        else:
          yield f"mov r7, #0"

        yield f"str r7, [{y}, #{y6 + i*2}]"

        yield from evaluate()

        yield f"str r11, [{y}, #{y1 + i*2}]"
        yield f"str r12, [{y}, #{y2 + i*2}]"
        yield f"str r9,  [{y}, #{y3 + i*2}]"
        yield f"str r10, [{y}, #{y4 + i*2}]"
        yield f"str r7,  [{y}, #{y5 + i*2}]"

    # multiply
    yield f"push {{{DEST}}}"
    yield f"push {{{y}}}"




    # innermul(t0,f0,g0);
    yield f"movw r11, #{t0+8}"
    yield f"add {DEST}, sp, r11"
    yield from call(innermul, t, limb_size, top=True)



    # innermul(t1,x1,y1);
    yield f"pop {{{y}}}"
    yield f"add {DEST}, #{2*(2*limb_size)}"
    yield f"add {SRC1}, sp, #{x1+4}"
    yield f"add {SRC2}, {y}, #{y1}"
    yield from call(innermul, t, limb_size, top=True)

    # innermul(t2,x2,y2);
    yield f"add {DEST}, #{2*(2*limb_size)}"
    yield f"add {SRC1}, #{2*limb_size}"
    yield f"add {SRC2}, #{2*limb_size}"
    yield from call(innermul, t, limb_size, top=True)

    # innermul(t3,x3,y3);
    yield f"add {DEST}, #{2*(2*limb_size)}"
    yield f"add {SRC1}, #{2*limb_size}"
    yield f"add {SRC2}, #{2*limb_size}"
    yield from call(innermul, t, limb_size, top=True)

    # innermul(t4,x4,y4);
    yield f"add {DEST}, #{2*(2*limb_size)}"
    yield f"add {SRC1}, #{2*limb_size}"
    yield f"add {SRC2}, #{2*limb_size}"
    yield from call(innermul, t, limb_size, top=True)

    # innermul(t5,x5,y5);
    yield f"add {DEST}, #{2*(2*limb_size)}"
    yield f"add {SRC1}, #{2*limb_size}"
    yield f"add {SRC2}, #{2*limb_size}"
    yield from call(innermul, t, limb_size, top=True)

    # innermul(t6,f3,g3)
    yield f"add {DEST}, #{2*(2*limb_size)}"
    yield f"add {SRC1}, #{2*limb_size}"
    yield f"add {SRC2}, #{2*limb_size}"
    yield from call(innermul, t, limb_size, top=True)


    yield f"pop {{{DEST}}}"


    # interpolation
    is_initialized = dict()

    # we do not need x1-x5 and y1-y5 anymore
    yield from alloc_stack(-(stack_space_x+stack_space_y), "r11")

    # recalc t addresses
    t_base = 0
    t0 = t_base
    t1 = t_base + 2*1*(2*limb_size)
    t2 = t_base + 2*2*(2*limb_size)
    t3 = t_base + 2*3*(2*limb_size)

    # this is too much for immediate offsets
    # so we need a second pointer
    t4_base = "r11"
    yield f"add {t4_base}, sp, #{2*4*(2*limb_size)}"


    t4 = 0
    t5 = t4 + 2*1*(2*limb_size)
    t6 = t4 + 2*2*(2*limb_size)

    inv3 = "r14"
    inv5 = "r12"
    yield f"movw {inv3}, #43691"
    yield f"movw {inv5}, #52429"


    h0 = "r1"
    h1 = "r3"
    h2 = "r8"
    h3 = "r6"
    h4 = "r9"
    h5 = "r5"
    h6 = "r7"
    for i in range(2*limb_size-1):
        yield f"ldrh {h0}, [sp, #{t0 + i*2}]"
        yield f"ldrh r2, [sp, #{t1 + i*2}]"
        yield f"ldrh r3, [sp, #{t2 + i*2}]"
        yield f"ldrh r4, [sp, #{t3 + i*2}]"
        yield f"ldrh r5, [{t4_base}, #{t4 + i*2}]"
        yield f"ldrh r6, [{t4_base}, #{t5 + i*2}]"
        yield f"ldrh {h6}, [{t4_base}, #{t6 + i*2}]"

        #yield f"strh r6, [{DEST}, #{i*2}]" #debug

        # tmp0 = ((t1[i]+t2[i]) >> 1) - t0[i] - t6[i]
        yield f"add r8, r2, r3"
        yield f"lsr r8, r8, #1"
        yield f"sub r8, r8, {h0}"
        yield f"sub r8, r8, {h6}"

        # tmp1 = (t3[i]+t4[i]-(h0[i]<<1)-(h6[i]<<7)) >> 3;
        yield f"add r9, r4, r5"
        yield f"sub r9, r9, {h0}, LSL#1"
        yield f"sub r9, r9, {h6}, LSL#7"
        yield f"lsr r9, r9, #3"


        # h4[i] = DIV3(tmp1-tmp0);
        yield f"sub {h4}, r9, r8"
        yield f"mul {h4}, {h4}, {inv3}"


        # h2[i] = tmp0 - h4[i];
        yield f"sub {h2}, r8, {h4}"

        # tmp0 = (t1[i]-t2[i])>>1;
        yield f"sub r2, r2, r3"
        yield f"lsr r2, r2, #1"

        # tmp1 = DIV3(((t3[i]-t4[i])>>2) - tmp0);
        yield f"sub r3, r4, r5"
        yield f"lsr r3, r3, #2"
        yield f"sub r3, r3, r2"
        yield f"mul r3, r3, {inv3}"


        # tmp2 = ((DIV3(t5[i]-h0[i]-9*(h2[i]+9*(h4[i]+9*h6[i])))-tmp0)>>3)-tmp1;
        yield f"add r4, {h6}, {h6}, lsl#3" # 9*h6[i]
        yield f"add r4, r4, {h4}"          # h4[i] + 9*h6[i]
        yield f"add r4, r4, r4, lsl#3"     # 9*(h4[i] + 9*h6[i])
        yield f"add r4, r4, {h2}"          # h2[i]+9*(h4[i] + 9*h6[i])
        yield f"add r4, r4, r4, lsl#3"     # 9*(h2[i]+9*(h4[i] + 9*h6[i]))
        yield f"add r4, {h0}, r4"          # h0[i]+9*(h2[i]+9*(h4[i] + 9*h6[i]))
        yield f"sub r4, r6, r4"            # t5[i]- h0[i]-9*(h2[i]+9*(h4[i] + 9*h6[i]))
        yield f"mul r4, r4, {inv3}"        # DIV3(t5[i]- h0[i]-9*(h2[i]+9*(h4[i] + 9*h6[i])))
        yield f"sub r4, r4, r2"            # DIV3(t5[i]- h0[i]-9*(h2[i]+9*(h4[i] + 9*h6[i])))-tmp0
        yield f"lsr r4, r4, #3"            # (DIV3(t5[i]- h0[i]-9*(h2[i]+9*(h4[i] + 9*h6[i])))-tmp0)>>3
        yield f"sub r4, r4, r3"

        # h5[i] = DIV5(tmp2);
        yield f"mul {h5}, r4, {inv5}"
        # h3[i] = tmp1 - tmp2;
        yield f"sub {h3}, r3, r4"
        # h1[i] = tmp0 - h3[i] - h5[i];
        yield f"sub {h1}, r2, {h3}"
        yield f"sub {h1}, {h1}, {h5}"


        def stradd(idx,reg):
            if idx > 2*(2*n-2):
                return
            if idx in is_initialized:
                yield f"ldrh r10, [{DEST}, #{idx}]"
                yield f"add {reg}, r10, {reg}"
            yield f"strh {reg}, [{DEST},#{idx}]"
            is_initialized[idx] = True

        yield from stradd(2*(i+0*limb_size), h0)
        yield from stradd(2*(i+1*limb_size), h1)
        yield from stradd(2*(i+2*limb_size), h2)
        yield from stradd(2*(i+3*limb_size), h3)
        yield from stradd(2*(i+4*limb_size), h4)
        yield from stradd(2*(i+5*limb_size), h5)
        yield from stradd(2*(i+6*limb_size), h6)

    # free stack space
    yield from alloc_stack(-stack_space_t, "r11")

def toom3(t,n, innermul=karatsuba, top=False):

    if top:
        # TODO It's unclear why we need to push r8 here
        yield f"push {{{SRC1}, {SRC2}, r8}}"
        yield "push {lr}"

    limb_size = ceil(n/3)
    if limb_size%2 == 1:
      raise Exception("can only handle even limb sizes")
    k = n - (2*limb_size)
    stack_space_x = 3*limb_size*2
    stack_space_y = 3*limb_size*2
    # 2*limbsize - 1 is enough, but for alignment we want multiples of 4
    stack_space_t = 5*(2*limb_size)*2

    yield from alloc_stack(stack_space_x+stack_space_y+stack_space_t, "r4")
    # some offsets
    f0 = g0 = 0
    f1 = g1 = 2*1*limb_size
    f2 = g2 = 2*2*limb_size

    x0 = 2*0*limb_size
    x1 = 2*1*limb_size
    x2 = 2*2*limb_size

    y = "r3"
    y_offset =  2*3*limb_size
    yield f"add {y}, sp, #{y_offset}"

    y0 = 2*0*limb_size
    y1 = 2*1*limb_size
    y2 = 2*2*limb_size

    # copy over the last limb of each argument to pad with zeros
    # for the first k-(k%2) coeffs we can use full words
    # TODO consider what happens we do not need to pad (i.e. n divides nicely)
    for i in range(0, k-(k%2), 2):
        yield f"ldr r5, [{SRC1}, #{f2+i*2}]"
        yield f"str r5, [sp, #{x2+i*2}]"
        yield f"ldr r5, [{SRC2}, #{g2+i*2}]"
        yield f"str r5, [{y}, #{y2+i*2}]"

    yield f"mov r4, #0"
    for i in range(k-(k%2), limb_size):
        if i<k:
            yield f"ldrh r5, [{SRC1}, #{f2+i*2}]"
            yield f"strh r5, [sp, #{x2+i*2}]"
            yield f"ldrh r5, [{SRC2}, #{g2+i*2}]"
            yield f"strh r5, [{y}, #{y2+i*2}]"
        else:
            yield f"strh r4, [sp, #{x2+i*2}]"
            yield f"strh r4, [{y}, #{y2+i*2}]"

    yield f"push {{{DEST}}}"
    yield f"push {{{SRC1}}}"
    yield f"push {{{SRC2}}}"

    # by doing these 2 karatsubas first, we save some stack space

    # innermul(t0, f0, g0);
    yield f"add {DEST}, {y}, #{3*2*limb_size}"
    yield from call(innermul, threshold, limb_size, top=True)

    # innermul(t4, f2, g2);
    yield f"movw r11, #{4*2*(limb_size*2)}"
    yield f"add {DEST}, r11"
    yield f"add {SRC1},sp, #{x2+12}"
    yield f"add {SRC2},{SRC1},#{3*2*limb_size}"
    yield from call(innermul, threshold, limb_size, top=True)


    yield f"pop {{{SRC2}}}"
    yield f"pop {{{SRC1}}}"
    # evaluate
    yield f"add {y}, sp, #{y_offset + 4}"
    for i in range(0, limb_size,2):
        yield f"ldr r4, [{SRC1}, #{x0 + i*2}]"
        yield f"ldr r5, [{SRC1}, #{x1 + i*2}]"
        yield f"ldr r6, [sp, #{x2 + i*2 + 4}]"

        def evaluate():
          yield f"lsl r7, r6, #2"
          yield f"and r7, #0xFFFCFFFC"
          yield f"uadd16 r7, r7, r4"
          yield f"lsl r14, r5, #1"
          yield f"and r14, #0xFFFEFFFE"
          yield f"usub16 r7, r7, r14"
          yield f"uadd16 r6, r6, r4"
          yield f"uadd16 r4, r6, r5"
          yield f"usub16 r5, r6, r5"

        yield from evaluate()

        yield f"str r4, [sp,#{x0 + i*2 + 4}]"
        yield f"str r5, [sp,#{x1 + i*2 + 4}]"
        yield f"str r7, [sp,#{x2 + i*2 + 4}]"

        yield f"ldr r4, [{SRC2}, #{y0 + i*2}]"
        yield f"ldr r5, [{SRC2}, #{y1 + i*2}]"
        yield f"ldr r6, [{y}, #{y2 + i*2}]"

        yield from evaluate()

        yield f"str r4, [{y}, #{y0 + i*2}]"
        yield f"str r5, [{y}, #{y1 + i*2}]"
        yield f"str r7, [{y}, #{y2 + i*2}]"


    # multiply
    t0 = 0
    t1 = 2*(limb_size*2)
    t2 = 2*2*(limb_size*2)

    # innermul(t1, f0, g0);
    yield f"movw r11, #{stack_space_x+stack_space_y+t1+4}"
    yield f"add {DEST}, sp, r11"
    yield f"add {SRC1}, sp, #{4}"
    yield f"add {SRC2}, {SRC1}, #{3*2*limb_size}"
    yield from call(innermul, threshold, limb_size, top=True)

    # innermul(t2, f1, g1);
    yield f"add {DEST}, #{2*(2*limb_size)}"
    yield f"add {SRC1}, #{2*limb_size}"
    yield f"add {SRC2}, #{2*limb_size}"
    yield from call(innermul, threshold, limb_size, top=True)

    # innermul(t3, f2, g2);
    yield f"add {DEST}, #{2*(2*limb_size)}"
    yield f"add {SRC1}, #{2*limb_size}"
    yield f"add {SRC2}, #{2*limb_size}"
    yield from call(innermul, threshold, limb_size, top=True)


    # interpolate
    yield f"pop {{{DEST}}}"


    # free some stack space, so t is on top of stack
    yield from alloc_stack(-(stack_space_x+stack_space_y), "r11")

    t = "sp"
    t3_reg = "r2"
    t3 = 0
    t4 = 1*2*(limb_size*2)
    yield f"movw {t3_reg}, #{3*2*(limb_size*2)}"
    yield f"add {t3_reg}, {t}, {t3_reg}"

    inv3 = "r14"
    yield f"movw {inv3}, #43691"
    is_initialized=dict()
    for i in range(0,2*limb_size-2,2):
        yield f"ldr r3, [{t}, #{t0 + i*2}]"
        yield f"ldr r4, [{t}, #{t1 + i*2}]"
        # for N=1024, this offset gets too large
        if t2 + i*2 >= 4096:
            yield f"movw r6, #{t2 + i*2}"
            yield f"ldr r5, [{t}, r6]"
        else:
            yield f"ldr r5, [{t}, #{t2 + i*2}]"
        yield f"ldr r6, [{t3_reg}, #{t3 + i*2}]"
        yield f"ldr r7, [{t3_reg}, #{t4 + i*2}]"

        # v3 = DIV3(t3[i] - t1[i]);
        yield "usub16 r8, r6, r4"
        yield f"smulbb r12, r8, {inv3}"
        yield f"smultb r8, r8, {inv3}"
        yield f"pkhbt r8,r12,r8,lsl#16"

        # v1 = (t1[i] -  t2[i])>>1;
        yield f"usub16 r9, r4, r5"
        yield f"lsr r9, #1"

        # v2 = (t2[i] - t0[i]);
        yield f"usub16 r10, r5, r3"

        # v3 = (((v2- v3))>>1)+ (t4[i]<<1);
        yield f"usub16 r11, r10, r8"
        yield f"lsr r11, #1"
        yield f"lsl r12, r7, #1"
        yield f"and r12, 0xFFFEFFFE"
        yield f"uadd16 r11,r11,r12"

        # v2 = v2+v1- t4[i];
        yield f"uadd16 r10,r10,r9"
        yield f"usub16 r10,r10,r7"

        # v1 = v1 - v3;
        yield f"usub16 r9,r9,r11"

        def stradd(idx,reg):
            if idx > 2*(2*n-2):
              return
            if idx in is_initialized:
                yield f"ldr r12, [{DEST}, #{idx}]"
                yield f"uadd16 {reg}, r12, {reg}"
            yield f"str {reg}, [{DEST},#{idx}]"
            is_initialized[idx] = True

        yield from stradd(2*(i+0*limb_size), "r3");
        yield from stradd(2*(i+1*limb_size), "r9");
        yield from stradd(2*(i+2*limb_size), "r10");
        yield from stradd(2*(i+3*limb_size), "r11");
        yield from stradd(2*(i+4*limb_size), "r7");
    yield f"ldrh r3, [{t}, #{t0 + (2*limb_size-2)*2}]"
    yield f"ldrh r4, [{t}, #{t1 + (2*limb_size-2)*2}]"

    # for N=1024, this offset is too large for the very last iteration
    if t2 + (2*limb_size-2)*2 >= 4096:
        yield f"movw r8, #{t2 + (2*limb_size-2)*2}"
        yield f"ldrh r5, [{t}, r8]"
    else:
        yield f"ldrh r5, [{t}, #{t2 + (2*limb_size-2)*2}]"
    yield f"ldrh r6, [{t3_reg}, #{t3 + (2*limb_size-2)*2}]"
    yield f"ldrh r7, [{t3_reg}, #{t4 + (2*limb_size-2)*2}]"

    # v3 = DIV3(t3[i] - t1[i]);
    yield "sub r8, r6, r4"
    yield f"mul r8, r8, {inv3}"

    # v1 = (t1[i] -  t2[i])>>1;
    yield f"sub r9, r4, r5"
    yield f"lsr r9, #1"

    # v2 = (t2[i] - t0[i]);
    yield f"sub r10, r5, r3"


    # v3 = (((v2- v3))>>1)+ (t4[i]<<1);
    yield f"sub r11, r10, r8"
    yield f"lsr r11, #1"
    yield f"add r11,r11,r7, lsl#1"

    # v2 = v2+v1- t4[i];
    yield f"add r10, r9"
    yield f"sub r10, r7"

    # v1 = v1 - v3;
    yield f"sub r9, r11"

    def stradd(idx,reg):
        yield f"ldrh r12, [{DEST}, #{idx}]"
        yield f"add {reg}, r12, {reg}"
        yield f"strh {reg}, [{DEST},#{idx}]"

    yield from stradd(2*((2*limb_size-2)+0*limb_size), "r3");
    yield from stradd(2*((2*limb_size-2)+1*limb_size), "r9");
    yield from stradd(2*((2*limb_size-2)+2*limb_size), "r10");
    yield from stradd(2*((2*limb_size-2)+3*limb_size), "r11");
    if 2*((2*limb_size-2)+4*limb_size) <= 2*(2*n-2):
        yield f"strh r7, [{DEST}, #{2*((2*limb_size-2)+4*limb_size)}]"

    yield from alloc_stack(-stack_space_t, "r11")

    if top:
        yield "pop {lr}"
        yield f"pop {{{SRC1}, {SRC2}, r8}}"

p = print

if __name__ == '__main__':
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        exit(1)

    # notoom, toom3, toom4, toom4toom3
    mode = sys.argv[1]
    if mode not in ["notoom", "toom3", "toom4", "toom4toom3"]:
        exit(1)

    n = int(sys.argv[2])
    if len(sys.argv) == 4:
      threshold = int(sys.argv[3])
    else:
      threshold = n
    p(".syntax unified")
    p(".cpu cortex-m4")
    if n == threshold:
        outermult = list(schoolbook(threshold, n))
    elif mode == "notoom":
        outermult = list(postprocess_karatsuba(karatsuba(threshold, n)))
    elif mode == "toom4":
        outermult = list(toom4(threshold, n))
    elif mode == "toom3":
        outermult = list(toom3(threshold, n))
    elif mode == "toom4toom3":
        outermult = list(toom4(threshold, n, innermul=toom3))
    else:
        exit(1)

    for fn, fn_gen in functions.items():
        p(f".global {fn}")
        p(f".type {fn}, %function")
        p(".align 2")
        p(f"{fn}:")
        for statement in postprocess_karatsuba(fn_gen):
          p(statement)

    p(".global polymul_asm")
    p(".type polymul_asm, %function")
    p(".align 2")
    p("polymul_asm:")
    p("push {r4-r12, r14}")

    for statement in outermult:
        p(statement)

    p("pop {r4-r12, r14}")
    p("bx lr")

