import re
from dataclasses import dataclass, field
from typing import Optional, Tuple

from visualizer.ops import Instruction


@dataclass
class PC:
    fn_name: str
    line_idx: int
    block_stack: list[tuple[list, int]] = field(default_factory=list)
    ret_stack: list[tuple[str, int, list]] = field(
        default_factory=list
    )  # (fn_name, line_idx, block_stack)


@dataclass
class FunctionDef:
    params: list[Tuple[str, Optional[str]]] = field(default_factory=list)
    body: list["Instruction"] = field(default_factory=list)
    size: int = 0

    def __post_init__(self):
        if self.size == 0:
            self.size = sum([self.param_size(p) for (_, p) in self.params])

    def param_size(self, param_type: Optional[str]) -> int:
        if not param_type:
            return 1

        param_type = param_type.strip()

        # Vec<...> → 3
        if re.match(r"Vec\s*<.*>", param_type):
            return 3

        # [Type; N] → N (but NOT &[Type; N])
        m = re.match(r"\[(.+);\s*(\d+)\]$", param_type)
        if m:
            return int(m.group(2))

        return 1


@dataclass
class Program:
    functions: dict[str, FunctionDef]
