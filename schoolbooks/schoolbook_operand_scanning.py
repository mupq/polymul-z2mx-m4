
def schoolbook_operand_scanning(SRC1, SRC2, DEST, t, n):
    """
    This generates a simple static schoolbook multiplication of n by n;
    assumes SRC1 and SRC2 registers with pointers to where n elements live,
    writes 2n-1 elements to the DEST pointer
    """

    yield "mov r11, #0"
    for i in range(2*n - 1):
        yield f"strh r11, [{DEST}, #{2*i}]"

    for i in range(n):
        yield f"ldrh r10, [{SRC1}, #{2*i}]"
        for j in range(n):
            yield f"ldrh r12, [{SRC2}, #{2*j}]"
            yield f"ldrh r11, [{DEST}, #{2*(i + j)}]"
            yield "mla r11, r10, r12, r11"
            yield f"strh r11, [{DEST}, #{2*(i + j)}]"
