"""
============================================================
  PEDAGOGICAL MEMORY VISUALIZER  v6.6 (Final)
  ──────────────────────────────────
  • Optimized Stack Sizing: No more wasted space.
  • Inline Returns: `let x = func();` syntax.
  • Full Instruction Set: Includes original Deref logic.
============================================================
"""

from visualizer.ops import (
    Add,
    AssignDeref,
    AssignDoubleDeref,
    CallAssign,
    CallFunction,
    Clone,
    Decrement,
    Free,
    FreeVec,
    HeapAlloc,
    Nop,
    Ref,
    ReturnFunction,
    ReturnIfEquals,
    StackVar,
    StaticArray,
    VecNew,
    VecPush,
)
from visualizer.ops.instructions import Increment, Print, VecPushDeref
from visualizer.program import FunctionDef, Program
from visualizer.runner import InteractiveRunner


def p0():
    return Program(
        {
            "main": FunctionDef(
                body=[
                    Nop("x is set to be at an offset of 2 "),
                    Nop("from the (reversed) top of stack"),
                    StackVar("x", "i32", 5),
                    Nop("y is at an offset of 1"),
                    StackVar("y", "i32", -12),
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
                    StackVar("x", "i32", 5),
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
            "add": FunctionDef(body=[StackVar("a", "i32", 5), ReturnFunction()]),
            "main": FunctionDef(
                body=[
                    Nop("Function Calls"),
                    StackVar("x", "i32", 1),
                    CallFunction("add"),
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
                    StackVar("before", "i32", 7),
                    StaticArray("arr", [10, 20, 30]),
                    StackVar("after", "i32", 9),
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
                    StackVar("x", "i32", 42),
                    Ref("ptr", "x"),
                    AssignDeref("ptr", 99),
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
                    StackVar("x", "i32", 10),
                    StackVar("y", "i32", 20),
                    Ref("y_ref", "y"),
                    CallFunction("process", ["x", "y_ref"]),
                    ReturnFunction(),
                ]
            ),
            "process": FunctionDef(
                params=["val", "ptr"],
                body=[
                    Nop("val is a copy, ptr points to main frame"),
                    AssignDeref("ptr", 999),
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
                    StackVar("a", "i32", 1),
                    CallFunction("level1"),
                    StackVar("b", "i32", 2),
                    ReturnFunction(),
                ]
            ),
            "level1": FunctionDef(
                body=[
                    StackVar("l1", "i32", 10),
                    CallFunction("level2"),
                    ReturnFunction(),
                ]
            ),
            "level2": FunctionDef(body=[StackVar("l2", "i32", 20), ReturnFunction()]),
        }
    )


def p9():
    return Program(
        {
            "main": FunctionDef(
                body=[
                    Nop("Recursive Stack"),
                    StackVar("s", "i32", 5),
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
                    StackVar("x", "i32", 1),
                    Ref("p1", "x"),
                    StackVar("x", "i32", 2),
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
                    StackVar("a", "i32", 10),
                    Ref("ra", "a"),
                    Ref("rra", "ra"),
                    AssignDoubleDeref("rra", 20),
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
                    StackVar("s", "i32", 2),
                    CallFunction("rec"),
                    ReturnFunction(),
                ]
            ),
            "rec": FunctionDef(
                body=[
                    StackVar("s", "i32", 2),
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
                    CallAssign("x", "get_val"),
                    CallAssign("v", "get_vec", is_vec=True),
                    FreeVec("v"),
                    ReturnFunction(),
                ]
            ),
            "get_val": FunctionDef(
                body=[StackVar("a", "i32", 99), ReturnFunction("a")]
            ),
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
                    StackVar("a", "i32", 99),
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
                    StackVar("a", "i32", 99),
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
                    CallFunction("process", ["v"]),
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
                    VecPushDeref("ptr", 42),
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
                    StackVar("x", "i32", 10),
                    StackVar("y", "i32", 20),
                    CallFunction("process", ["x", "y"]),
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


if __name__ == "__main__":
    # Theme Colors
    CYAN = "\033[96m"
    YELLOW = "\033[93m"
    MAGENTA = "\033[95m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    PROGS = {
        "0": p0,
        "1": p1,
        "2": p2,
        "3": p3,
        "4": p4,
        "5": p5,
        "6": p6,
        "7": p7,
        "8": p8,
        "9": p9,
        "10": p10,
        "11": p11,
        "12": p12,
        "13": p13,
        "14": p14,
        "15": p15,
        "16": p16,
        "17": p17,
        "18": p18,
        "19": p19,
    }

    # Header
    print(f"\n{MAGENTA}{BOLD} ═══ MEMORY VISUALIZER EXAMPLES ═══{RESET}")

    # Grid Layout
    menu = [
        (
            f"{CYAN}0{RESET}: Simple Var",
            f"{CYAN}1{RESET}: Box (Heap)",
            f"{CYAN}2{RESET}: Clone/Drop",
        ),
        (
            f"{CYAN}3{RESET}: Call Stack",
            f"{CYAN}4{RESET}: Vec Growth",
            f"{CYAN}5{RESET}: Static Array",
        ),
        (
            f"{CYAN}6{RESET}: References",
            f"{CYAN}7{RESET}: Params",
            f"{CYAN}8{RESET}: Nested Calls",
        ),
        (
            f"{CYAN}9{RESET}: Recursion",
            f"{CYAN}10{RESET}: Shadowing",
            f"{CYAN}11{RESET}: Mix All",
        ),
        (
            f"{CYAN}12{RESET}: Ref to Ref",
            f"{RED}13{RESET}: Stack Overflow",
            f"{GREEN}14{RESET}: Return Values",
        ),
        (
            f"{YELLOW}15{RESET}: Memory Leak",
            f"{GREEN}16{RESET}: Memory Clean",
            f"{CYAN}17{RESET}: Vec in param",
        ),
        (f"{CYAN}18{RESET}: &Vec in param", f"{RED}19{RESET}: Simple params", ""),
    ]
    for row in menu:
        print(f"  {row[0]:<25} {row[1]:<25} {row[2]}")

    print(f"{MAGENTA}{BOLD} ══════════════════════════════════{RESET}")

    try:
        c = input(f"{YELLOW}Select an illustration ID > {RESET}").strip()
        if c in PROGS:
            print(f"\n{GREEN}🚀 Launching Illustration {c}...{RESET}\n")
            InteractiveRunner(PROGS[c]())
        else:
            print(f"\n{RED}❌ Invalid ID. Please run again and select 0-16.{RESET}")
    except KeyboardInterrupt:
        print(f"\n{RED}👋 Exiting...{RESET}")
