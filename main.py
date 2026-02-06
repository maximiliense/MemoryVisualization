"""
============================================================
  PEDAGOGICAL MEMORY VISUALIZER  v6.6 (Final)
  ──────────────────────────────────
  • Optimized Stack Sizing: No more wasted space.
  • Inline Returns: `let x = func();` syntax.
  • Full Instruction Set: Includes original Deref logic.
============================================================
"""

from visualizer.launcher import ProgramLauncher
from visualizer.ops import (
    Add,
    AssignDeref,
    CallFunction,
    Clone,
    Decrement,
    Free,
    FreeVec,
    HeapAlloc,
    LetVar,
    Nop,
    Ref,
    ReturnFunction,
    ReturnIfEquals,
    StaticArray,
    VecNew,
    VecPush,
)
from visualizer.ops.instructions import (
    AddAssign,
    AssignVar,
    DerefSetArray,
    DerefSetVec,
    IfElse,
    Increment,
    Print,
    Random,
    Set,
    StackVarFromVar,
    VecPushDeref,
)
from visualizer.program import FunctionDef, Program
from visualizer.renderer import FRAME_PALETTE


def p0():
    return Program(
        {
            "main": FunctionDef(
                body=[
                    Nop("x is set to be at an offset of 2 "),
                    Nop("from the (reversed) top of stack"),
                    LetVar("x", "i32", 5),
                    Nop("y is at an offset of 1"),
                    LetVar("y", "i32", -12),
                    Nop("Type of a i32 and a is at an offset of 0"),
                    Add("a", "x", "y"),
                    Print("a = {a}"),
                    ReturnFunction(),
                ]
            )
        }
    )


def p1():
    return Program(
        {
            "main": FunctionDef(
                body=[
                    Nop("Simple Box"),
                    HeapAlloc("p", 100),
                    LetVar("x", "i32", 5),
                    Free("p"),
                    ReturnFunction(),
                ]
            )
        }
    )


def p2():
    return Program(
        {
            "main": FunctionDef(
                body=[
                    Nop("Clone & Drop"),
                    HeapAlloc("v1", 10),
                    Clone("v2", "v1"),
                    Free("v1"),
                    ReturnFunction(),
                ]
            )
        }
    )


def p3():
    return Program(
        {
            "hello_world": FunctionDef(
                body=[LetVar("a", "i32", 5), Print("Hello, world!"), ReturnFunction()]
            ),
            "main": FunctionDef(
                body=[
                    Nop("Function Calls"),
                    LetVar("x", "i32", 1),
                    CallFunction("hello_world"),
                    ReturnFunction(),
                ]
            ),
        }
    )


def p4():
    return Program(
        {
            "main": FunctionDef(
                body=[
                    Nop("Vec Realloc"),
                    VecNew("v", [10], cap=1),
                    VecPush("v", 20),
                    VecPush("v", 30),
                    VecPush("v", 40),
                    FreeVec("v"),
                    ReturnFunction(),
                ]
            )
        }
    )


def p5():
    return Program(
        {
            "main": FunctionDef(
                body=[
                    Nop("Static Array"),
                    LetVar("before", "i32", 7),
                    StaticArray("arr", [10, 20, 30]),
                    LetVar("after", "i32", 9),
                    ReturnFunction(),
                ]
            )
        }
    )


def p6():
    return Program(
        {
            "main": FunctionDef(
                body=[
                    Nop("References"),
                    LetVar("x", "i32", 42),
                    Ref("ptr", "x"),
                    AssignDeref("*", "ptr", 99),
                    ReturnFunction(),
                ]
            )
        }
    )


def p7():
    return Program(
        {
            "main": FunctionDef(
                body=[
                    Nop("Setup parameters"),
                    LetVar("x", "i32", 10),
                    LetVar("y", "i32", 20),
                    Ref("y_ref", "y"),
                    CallFunction("process", ["x", "y_ref"]),
                    ReturnFunction(),
                ]
            ),
            "process": FunctionDef(
                params=["val", "ptr"],
                body=[
                    Nop("val is a copy, ptr points to main frame"),
                    AssignDeref("*", "ptr", 999),
                    ReturnFunction(),
                ],
            ),
        }
    )


def p8():
    return Program(
        {
            "main": FunctionDef(
                body=[
                    Nop("Nested Calls"),
                    LetVar("a", "i32", 1),
                    CallFunction("level1"),
                    LetVar("b", "i32", 2),
                    ReturnFunction(),
                ]
            ),
            "level1": FunctionDef(
                body=[
                    LetVar("l1", "i32", 10),
                    CallFunction("level2"),
                    ReturnFunction(),
                ]
            ),
            "level2": FunctionDef(body=[LetVar("l2", "i32", 20), ReturnFunction()]),
        }
    )


def p9():
    return Program(
        {
            "main": FunctionDef(
                body=[
                    Nop("Recursive Stack"),
                    LetVar("s", "i32", 5),
                    CallFunction("rec", ["s"]),
                    ReturnFunction(),
                ]
            ),
            "rec": FunctionDef(
                params=["n"],
                body=[
                    ReturnIfEquals("n", 0),
                    Decrement("n"),
                    CallFunction("rec", ["n"]),  # Recursive Step
                    Nop("Backtracking..."),
                    ReturnFunction(),
                ],
            ),
        }
    )


def p10():
    return Program(
        {
            "main": FunctionDef(
                body=[
                    Nop("Shadowing & Pointers"),
                    LetVar("x", "i32", 1),
                    Ref("p1", "x"),
                    LetVar("x", "i32", 2),
                    Ref("p2", "x"),
                    ReturnFunction(),
                ]
            )
        }
    )


def p11():
    return Program(
        {
            "main": FunctionDef(
                body=[
                    Nop("Complex Heap Object"),
                    VecNew("v", [1, 2], cap=2),
                    HeapAlloc("b", 50),
                    Ref("r", "v.len"),
                    FreeVec("v"),
                    Free("b"),
                    ReturnFunction(),
                ]
            )
        }
    )


def p12():
    return Program(
        {
            "main": FunctionDef(
                body=[
                    Nop("Deep Reference chain"),
                    LetVar("a", "i32", 10),
                    Ref("ra", "a"),
                    Ref("rra", "ra"),
                    Ref("rrra", "rra"),
                    Ref("rrrra", "rrra"),
                    Ref("rrrrra", "rrrra"),
                    AssignDeref("*****", "rrrrra", 42),
                    ReturnFunction(),
                ]
            )
        }
    )


def p13():
    return Program(
        {
            "main": FunctionDef(
                body=[
                    Nop("Recursive Stack"),
                    LetVar("s", "i32", 2),
                    CallFunction("rec"),
                    ReturnFunction(),
                ]
            ),
            "rec": FunctionDef(
                body=[
                    LetVar("s", "i32", 2),
                    CallFunction("rec"),  # Recursive Step
                    ReturnFunction(),
                ],
            ),
        }
    )


def p14():
    return Program(
        {
            "main": FunctionDef(
                body=[
                    CallFunction("get_val", ret="x"),
                    CallFunction("get_vec", ret="v"),
                    FreeVec("v"),
                    ReturnFunction(),
                ]
            ),
            "get_val": FunctionDef(body=[LetVar("a", "i32", 99), ReturnFunction("a")]),
            "get_vec": FunctionDef(
                body=[VecNew("my_v", [7, 8], cap=2), ReturnFunction("my_v")]
            ),
        }
    )


def p15():
    return Program(
        {
            "main": FunctionDef(
                body=[
                    CallFunction(
                        "heap_alloc",
                    ),
                    CallFunction(
                        "heap_alloc",
                    ),
                    CallFunction(
                        "heap_alloc",
                    ),
                    LetVar("a", "i32", 99),
                    ReturnFunction(),
                ]
            ),
            "heap_alloc": FunctionDef(
                body=[VecNew("my_v", [7, 8], cap=2), ReturnFunction()]
            ),
        }
    )


def p16():
    return Program(
        {
            "main": FunctionDef(
                body=[
                    CallFunction(
                        "heap_alloc",
                    ),
                    LetVar("a", "i32", 99),
                    ReturnFunction(),
                ]
            ),
            "heap_alloc": FunctionDef(
                body=[
                    VecNew("my_v", [7, 8], cap=2),
                    FreeVec("my_v"),
                    ReturnFunction(),
                ]
            ),
        }
    )


def p17():
    return Program(
        {
            "main": FunctionDef(
                body=[
                    Nop("Setup parameters"),
                    VecNew("v", [1, 2], cap=2),
                    CallFunction("process", [("v", "Vec")]),
                    Nop("In rust, v can't be used here, after process..."),
                    ReturnFunction(),
                ]
            ),
            "process": FunctionDef(
                size=3,
                params=["ptr"],
                body=[
                    Nop("ptr is a copy of the stack variable v from main"),
                    VecPush("ptr", 42),
                    ReturnFunction(),
                ],
            ),
        }
    )


def p18():
    return Program(
        {
            "main": FunctionDef(
                body=[
                    Nop("Setup parameters"),
                    VecNew("v", [1, 2], cap=2),
                    Ref("ptr", "v"),
                    CallFunction("process", ["ptr"]),
                    FreeVec("v"),
                    ReturnFunction(),
                ]
            ),
            "process": FunctionDef(
                size=1,
                params=["ptr"],
                body=[
                    Nop("ptr is a reference to the stack variable in main"),
                    VecPushDeref("*", "ptr", 42),
                    ReturnFunction(),
                ],
            ),
        }
    )


def p19():
    return Program(
        {
            "main": FunctionDef(
                body=[
                    Nop("Setup parameters"),
                    LetVar("x", "i32", 10),
                    LetVar("y", "i32", 20),
                    Nop("Calling `process` with params x & y"),
                    CallFunction("process", ["x", "y"]),
                    Print("x={x}, y={y}"),
                    ReturnFunction(),
                ]
            ),
            "process": FunctionDef(
                params=["x", "y"],
                body=[
                    Nop("x and y are copies of their original counter part"),
                    Increment("x"),
                    Increment("y"),
                    ReturnFunction(),
                ],
            ),
        }
    )


def p20():
    return Program(
        {
            "main": FunctionDef(
                body=[
                    Nop("Vec Realloc"),
                    VecNew("v", [10], cap=1),
                    VecPush("v", 20),
                    HeapAlloc("p", 100),
                    AssignDeref("*", "p", 1000),
                    FreeVec("v"),
                    Free("p"),
                    ReturnFunction(),
                ]
            )
        }
    )


def p21():
    return Program(
        {
            "main": FunctionDef(
                body=[
                    LetVar("n", "i32", 4),
                    CallFunction("fibonacci", args=["n"], ret="f"),
                    Print("Fibo({n})={f}"),
                    ReturnFunction(),
                ]
            ),
            "fibonacci": FunctionDef(
                size=4,
                params=["n"],
                body=[
                    LetVar("res", "i32", 0),
                    IfElse(
                        "n",
                        1,
                        [Set("res", 1)],
                        [
                            IfElse(
                                "n",
                                2,
                                [Set("res", 1)],
                                [
                                    Decrement("n"),
                                    CallFunction("fibonacci", args=["n"], ret="f1"),
                                    Decrement("n"),
                                    CallFunction("fibonacci", args=["n"], ret="f2"),
                                    AddAssign("res", "f1", "f2"),
                                ],
                            )
                        ],
                    ),
                    ReturnFunction("res"),
                ],
            ),
        }
    )


def p22():
    return Program(
        {
            "main": FunctionDef(
                body=[
                    HeapAlloc("p1", 42),
                    StackVarFromVar("p2", "p1"),
                    Free("p2"),
                    Nop("Drop p1; ?????"),
                    ReturnFunction(),
                ]
            )
        }
    )


def p23():
    return Program(
        {
            "main": FunctionDef(
                body=[
                    HeapAlloc("p1", 42),
                    CallFunction("ma_func", args=["p1"], ret="p2"),
                    Free("p2"),
                    Nop("Drop p1; ?????"),
                    ReturnFunction(),
                ]
            ),
            "ma_func": FunctionDef(
                size=4,
                params=["p"],
                body=[
                    LetVar("res", "&i32"),
                    Random("r", 0, 1),
                    IfElse(
                        "r",
                        0,
                        [AssignVar("res", "p")],
                        [HeapAlloc("p2", "88"), AssignVar("res", "p2")],
                    ),
                    ReturnFunction("res"),
                ],
            ),
        }
    )


def p24():
    return Program(
        {
            "main": FunctionDef(
                body=[
                    StaticArray("arr", [1, 2]),
                    CallFunction("func_copy", args=[("arr", 2)]),
                    Ref("p", "arr"),
                    CallFunction("func_ref", args=["p"]),
                    ReturnFunction(),
                ]
            ),
            "func_copy": FunctionDef(
                size=2,
                params=["arr"],
                body=[DerefSetArray("arr", 0, 42), ReturnFunction()],
            ),
            "func_ref": FunctionDef(
                params=["arr"],
                body=[DerefSetArray("arr", 0, 42, stars="*"), ReturnFunction()],
            ),
        }
    )


def p25():
    return Program(
        {
            "main": FunctionDef(
                body=[
                    LetVar("bank", "i32", 25000),
                    CallFunction("tampering"),
                    ReturnFunction(),
                ]
            ),
            "tampering": FunctionDef(
                body=[
                    LetVar("x", "i32", 42),
                    StaticArray("arr", [1, 2, 3, 4]),
                    DerefSetArray("arr", 5, -99),
                    ReturnFunction(),
                ]
            ),
        }
    )


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
