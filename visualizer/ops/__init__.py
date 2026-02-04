from .base import Instruction
from .instructions import (
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
    VecPushDeref,
    calc_frame_size,
)

__all__ = [
    "CallAssign",
    "Clone",
    "AssignDoubleDeref",
    "AssignDeref",
    "Free",
    "FreeVec",
    "Nop",
    "ReturnFunction",
    "Decrement",
    "CallFunction",
    "HeapAlloc",
    "Ref",
    "StackVar",
    "StaticArray",
    "VecNew",
    "VecPush",
    "ReturnIfEquals",
    "calc_frame_size",
    "VecPushDeref",
]


__all__ = ["Instruction"]
