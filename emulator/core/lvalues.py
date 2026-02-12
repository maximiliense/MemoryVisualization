"""
V2 LValue System

LValues represent memory locations that can be assigned to.
"""

from .base import ExecutionStatus, LValue
from .expressions import Dereference, Expression, Variable


class VariableLValue(LValue):
    """Simple variable as assignment target"""

    def __init__(self, name: str):
        self.name = name

    def get_address(self, mem, prog) -> int:
        try:
            addr = mem.get_addr(self.name)
        except Exception:
            addr = mem.get_addr(f"{self.name}.cap")

        return addr

    def description(self) -> str:
        return self.name


class DereferenceLValue(LValue):
    """Dereferenced pointer as assignment target: *ptr or **ptr"""

    def __init__(self, expr: Expression, levels: int = 1):
        self.expr = expr
        self.levels = levels

    def get_address(self, mem, prog) -> int:
        # Evaluate the expression to get the pointer
        expr_result = self.expr.evaluate(mem, prog)
        if expr_result == ExecutionStatus.INCOMPLETE:
            raise RuntimeError("LValue evaluation should not be incomplete")

        addr = expr_result.get_scalar()  # type: ignore (exception otherwise)
        # Follow the pointer chain
        for _ in range(1, self.levels):
            if not isinstance(addr, int) or addr < 0 or addr >= len(mem.mem):
                raise ValueError(f"Invalid dereference: {addr}")
            addr = mem.mem[addr].value
        return addr

    def description(self) -> str:
        stars = "*" * self.levels
        return f"{stars}{self.expr.description()}"


class ArrayIndexLValue(LValue):
    """Array element as assignment target: arr[index]"""

    def __init__(self, array: Expression, index: Expression):
        self.array = array
        self.index = index

    def get_address(self, mem, prog) -> int:
        # 1. Resolve the base address of the array
        if isinstance(self.array, Dereference):
            # For (*p)[idx], we need the address STORED in p
            # We use a specialized method to avoid fetching the actual data
            base_addr = self.array.get_target_address(mem, prog)
        elif isinstance(self.array, Variable):
            # For arr[idx], Variable.evaluate returns the address of the first element
            res = self.array.evaluate(mem, prog)
            base_addr = res.get_scalar()
        else:
            # Fallback for complex expressions that result in a pointer
            res = self.array.evaluate(mem, prog)
            if res == ExecutionStatus.INCOMPLETE:
                raise RuntimeError("LValue evaluation should not be incomplete")
            base_addr = res.get_scalar()  # type: ignore

        # 2. Resolve the index (standard R-Value evaluation)
        idx_result = self.index.evaluate(mem, prog)
        if idx_result == ExecutionStatus.INCOMPLETE:
            raise RuntimeError("LValue index evaluation should not be incomplete")

        idx = idx_result.get_scalar()  # type: ignore

        if base_addr is None:
            raise ValueError(
                f"Could not resolve base address for {self.array.description()}"
            )

        return base_addr + idx

    def description(self) -> str:
        return f"{self.array.description()}[{self.index.description()}]"


class FieldLValue(LValue):
    """Struct field as assignment target: obj.field"""

    def __init__(self, obj: Expression, field: str):
        self.obj = obj
        self.field = field

    def get_address(self, mem, prog) -> int:
        # Evaluate the object expression
        obj_result = self.obj.evaluate(mem, prog)
        if obj_result == ExecutionStatus.INCOMPLETE:
            raise RuntimeError("LValue evaluation should not be incomplete")

        # For Vec, fields are .ptr, .len, .cap
        if obj_result.typ == "Vec":  # type: ignore (exception otherwise)
            base_name = self.obj.description()
            field_name = f"{base_name}.{self.field}"
            return mem.get_addr(field_name)

        raise NotImplementedError(f"Field access for type {obj_result.typ}")  # type: ignore

    def description(self) -> str:
        return f"{self.obj.description()}.{self.field}"
