from emulator.compiler.parser import compile_srs
from emulator.launcher import ProgramLauncher
from emulator.rendering.renderer import FRAME_PALETTE


def load_file(file):
    with open(file) as f:
        text = f.read()
    return compile_srs(text)


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


def p26():
    return load_file("codes/stack/iterative_fibo.srs")


def p27():
    return load_file("codes/functions/array_copy.srs")


def p28():
    return load_file("codes/functions/array_ref.srs")


def p29():
    return load_file("codes/stack/static_array_alone.srs")


def p30():
    return load_file("codes/miscellaneous/bubble_sort.srs")


def p31():
    return load_file("codes/miscellaneous/dicho_search.srs")


def p32():
    return load_file("codes/miscellaneous/search_max.srs")


def p33():
    return load_file("codes/stack/factorial.srs")


def p34():
    return load_file("codes/functions/array_copy_no_ret.srs")


def p35():
    return load_file("codes/heap/vec_by_ret.srs")


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
        "Rec Fibonacci": (p21, FRAME_PALETTE[3]),  # advanced
        "Double free": (p22, FRAME_PALETTE[1]),
        "Double free 2": (p23, FRAME_PALETTE[1]),
        "Reference/copy array": (p24, FRAME_PALETTE[0]),
        "Memory tampering": (p25, FRAME_PALETTE[0]),
        "It Fibonacci": (p26, FRAME_PALETTE[3]),
        "Array copy&ret": (p27, FRAME_PALETTE[2]),
        "&Array": (p28, FRAME_PALETTE[2]),
        "Static Array 2": (p29, FRAME_PALETTE[0]),
        "Bubble sort": (p30, FRAME_PALETTE[3]),
        "Dicho search": (p31, FRAME_PALETTE[3]),
        "Max search": (p32, FRAME_PALETTE[3]),
        "Factorial": (p33, FRAME_PALETTE[0]),
        "Array param": (p34, FRAME_PALETTE[2]),
        "Function vec by ret": (p35, FRAME_PALETTE[1]),  # heap
    }

    ProgramLauncher(PROGS)
