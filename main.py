"""
============================================================
  PEDAGOGICAL MEMORY VISUALIZER  v6.6 (Final)
  ──────────────────────────────────
  • Optimized Stack Sizing: No more wasted space.
  • Inline Returns: `let x = func();` syntax.
  • Full Instruction Set: Includes original Deref logic.
============================================================
"""

from visualizer.compiler import compile_rust
from visualizer.launcher import ProgramLauncher
from visualizer.renderer import FRAME_PALETTE


def load_file(file):
    with open(file) as f:
        text = f.read()
    return compile_rust(text)


def p0():
    return load_file("codes/stack/stack_variables.srs")


def p1():
    return load_file("codes/heap/heap_variables.srs")


def p2():
    return load_file("codes/heap/clone_and_drop.srs")


def p3():
    return load_file("codes/functions/basic_call.srs")


def p4():
    return load_file("codes/heap/vec_growth.srs")


def p5():
    return load_file("codes/stack/static_array.srs")


def p6():
    return load_file("codes/stack/references.srs")


def p7():
    return load_file("codes/functions/call_with_params.srs")


def p8():
    return load_file("codes/functions/nested_calls.srs")


def p9():
    return load_file("codes/functions/recursive.srs")


def p10():
    return load_file("codes/stack/shadowing.srs")


def p11():
    return load_file("codes/heap/mix.srs")


def p12():
    return load_file("codes/stack/ref_to_ref.srs")


def p13():
    return load_file("codes/functions/overflow.srs")


def p14():
    return load_file("codes/functions/return_values.srs")


def p15():
    return load_file("codes/heap/memory_leak.srs")


def p16():
    return load_file("codes/heap/clean_alloc.srs")


def p17():
    return load_file("codes/heap/vec_by_val.srs")


def p18():
    return load_file("codes/heap/vec_by_ref.srs")


def p19():
    return load_file("codes/functions/basic_with_params.srs")


def p20():
    return load_file("codes/heap/vec_realloc.srs")


def p21():
    return load_file("codes/functions/fibo.srs")


def p22():
    return load_file("codes/heap/double_free.srs")


def p23():
    return load_file("codes/heap/double_free_bis.srs")


def p24():
    return load_file("codes/stack/ref_copy_arr.srs")


def p25():
    return load_file("codes/stack/tampering.srs")


if __name__ == "__main__":
    PROGS = {
        "Stack variables": (p0, FRAME_PALETTE[0]),  # stack
        "Heap variables": (p1, FRAME_PALETTE[1]),  # heap
        "Clone and drop": (p2, FRAME_PALETTE[1]),  # heap
        "Basic function call": (p3, FRAME_PALETTE[2]),  # functions
        "Vec realloc": (p4, FRAME_PALETTE[1]),  # heap
        "Static array": (p5, FRAME_PALETTE[0]),  # stack
        "References": (p6, FRAME_PALETTE[0]),  # stack
        "Function with params": (p7, FRAME_PALETTE[2]),  # functions
        "Nested calls": (p8, FRAME_PALETTE[2]),  # functions
        "Recursive stack": (p9, FRAME_PALETTE[2]),  # functions
        "Shadowing": (p10, FRAME_PALETTE[0]),  # stack
        "Heap objects": (p11, FRAME_PALETTE[1]),  # heap
        "Many references": (p12, FRAME_PALETTE[0]),  # stack
        "Stack overflow": (p13, FRAME_PALETTE[2]),  # functions
        "Returning values": (p14, FRAME_PALETTE[2]),  # functions
        "Memory leak": (p15, FRAME_PALETTE[1]),  # heap
        "Clean heap alloc": (p16, FRAME_PALETTE[1]),  # heap
        "Function vec by copy": (p17, FRAME_PALETTE[1]),  # heap
        "Function vec by ref": (p18, FRAME_PALETTE[1]),  # heap
        "Basic func & params": (p19, FRAME_PALETTE[2]),  # function
        "Complex realloc": (p20, FRAME_PALETTE[1]),  # heap
        "Fibonacci": (p21, FRAME_PALETTE[3]),  # advanced
        "Double free": (p22, FRAME_PALETTE[1]),
        "Double free 2": (p23, FRAME_PALETTE[1]),
        "Reference/copy array": (p24, FRAME_PALETTE[0]),
        "Memory tampering": (p25, FRAME_PALETTE[0]),
    }

    ProgramLauncher(PROGS)
