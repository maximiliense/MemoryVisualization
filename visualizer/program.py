from dataclasses import dataclass, field

from visualizer.ops import Instruction


@dataclass
class PC:
    fn_name: str
    line_idx: int
    ret_stack: list[tuple[str, int]] = field(default_factory=list)


@dataclass
class FunctionDef:
    params: list[str] = field(default_factory=list)
    body: list["Instruction"] = field(default_factory=list)
    size: int = 0

    def __post_init__(self):
        if self.size == 0:
            self.size = len(self.params)


@dataclass
class Program:
    functions: dict[str, FunctionDef]
