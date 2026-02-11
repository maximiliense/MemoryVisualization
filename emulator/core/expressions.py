"""
V2 Expression System

Expressions are pure computations that produce results.
They can be nested and evaluated recursively.
"""

from typing import Any, Union

from .base import EvaluationResult, ExecutionStatus, Expression


class Literal(Expression):
    """A constant literal value"""

    def __init__(self, value: Any, typ: str = "i32"):
        self.value = value
        self.typ = typ

    def evaluate(self, mem, prog) -> EvaluationResult:
        return EvaluationResult(values=[self.value], typ=self.typ)

    def description(self) -> str:
        if self.typ == "str":
            return f'"{self.value}"'
        return str(self.value)


class Variable(Expression):
    """Reference to a variable (reads its value)"""

    def __init__(self, name: str):
        super().__init__()
        self.name = name

    def evaluate(self, mem, prog) -> EvaluationResult:
        try:
            addr = mem.get_addr(self.name)
            is_vec = False
        except Exception:
            addr = mem.get_addr(f"{self.name}.cap")
            is_vec = True
        cell = mem.mem[addr]

        # CRITICAL: Check if this is an array
        # Arrays are stored as multiple contiguous cells with labels like "arr[0]", "arr[1]", etc.
        # The address we get is the BASE address of the array

        if cell.typ == "array" or "[" in cell.label:
            # This is an array - return the BASE ADDRESS, not the value
            # The address itself is what ArrayAccess needs
            return EvaluationResult(
                values=[addr],  # ← THE ADDRESS
                typ=cell.typ,
                is_pointer=False,  # Not a pointer, but an array
            )
        elif is_vec:
            # Vec is stored as metadata (ptr, len, cap)
            # Return the base address where metadata starts
            return EvaluationResult(values=[addr], typ="Vec", is_pointer=False)
        else:
            # Regular scalar or pointer variable
            return EvaluationResult(
                values=[cell.value], typ=cell.typ, is_pointer=cell.is_pointer
            )

    def description(self) -> str:
        return self.name


class ArrayAccess(Expression):
    """Array element access: arr[index]"""

    def __init__(self, array: Expression, index: Expression):
        self.array = array
        self.index = index

    def evaluate(self, mem, prog) -> Union[EvaluationResult, ExecutionStatus]:
        ctx = self.get_ctx(mem)
        # Step 0: Evaluate array expression
        if ctx.step == 0:
            arr_result = self.array.evaluate(mem, prog)
            if arr_result == ExecutionStatus.INCOMPLETE:
                return ExecutionStatus.INCOMPLETE
            ctx.store("array_result", arr_result)
            ctx.advance()

        # Step 1: Evaluate index expression
        if ctx.step == 1:
            idx_result = self.index.evaluate(
                mem,
                prog,
            )
            if idx_result == ExecutionStatus.INCOMPLETE:
                return ExecutionStatus.INCOMPLETE
            ctx.store("index_result", idx_result)
            ctx.advance()

        # Step 2: Compute final result
        arr_result = ctx.get("array_result")
        idx_result = ctx.get("index_result")

        idx = idx_result.get_scalar()

        # If array result is a pointer, dereference it

        base_addr = arr_result.get_scalar()
        value = mem.mem[base_addr + idx].value
        typ = mem.mem[base_addr + idx].typ

        return EvaluationResult(values=[value], typ=typ)

    def description(self) -> str:
        return f"{self.array.description()}[{self.index.description()}]"


class BinaryOp(Expression):
    """Binary operation: left op right"""

    def __init__(self, left: Expression, op: str, right: Expression):
        self.left = left
        self.op = op
        self.right = right

    def evaluate(self, mem, prog) -> Union[EvaluationResult, ExecutionStatus]:
        ctx = self.get_ctx(mem)
        # Step 0: Evaluate left operand
        if ctx.step == 0:
            left_result = self.left.evaluate(mem, prog)
            if left_result == ExecutionStatus.INCOMPLETE:
                return ExecutionStatus.INCOMPLETE
            ctx.store("left_result", left_result)
            ctx.advance()
        # Step 1: Evaluate right operand
        if ctx.step == 1:
            right_result = self.right.evaluate(mem, prog)
            if right_result == ExecutionStatus.INCOMPLETE:
                return ExecutionStatus.INCOMPLETE
            ctx.store("right_result", right_result)
            ctx.advance()
        # Step 2: Perform operation
        left_result = ctx.get("left_result")
        right_result = ctx.get("right_result")

        left_val = left_result.get_scalar()
        right_val = right_result.get_scalar()
        if self.op == "+":
            result = left_val + right_val
        elif self.op == "-":
            result = left_val - right_val
        elif self.op == "*":
            result = left_val * right_val
        elif self.op == "/":
            result = left_val // right_val
        elif self.op == "==":
            result = 1 if left_val == right_val else 0
        elif self.op == "!=":
            result = 1 if left_val != right_val else 0
        elif self.op == "<":
            result = 1 if left_val < right_val else 0
        elif self.op == ">":
            result = 1 if left_val > right_val else 0
        else:
            raise ValueError(f"Unknown operator: {self.op}")

        return EvaluationResult(values=[result], typ="i32")

    def description(self) -> str:
        return f"{self.left.description()} {self.op} {self.right.description()}"


class FunctionCall(Expression):
    """Function call expression: func(args...)"""

    def __init__(self, func_name: str, args: list[Expression]):
        self.func_name = func_name
        self.args = args

    def evaluate(self, mem, prog) -> Union[EvaluationResult, ExecutionStatus]:
        import re

        ctx = self.get_ctx(mem)
        # Step 0-N: Evaluate each argument
        num_args = len(self.args)
        if ctx.step < num_args:
            arg_idx = ctx.step
            arg_result = self.args[arg_idx].evaluate(mem, prog)
            if arg_result == ExecutionStatus.INCOMPLETE:
                return ExecutionStatus.INCOMPLETE
            func_def = prog.functions.get(self.func_name)
            if func_def and arg_idx < len(func_def.params):
                _, param_type = func_def.params[arg_idx]

                if param_type == "Vec" or (param_type and param_type.startswith("Vec")):
                    base_addr = arg_result.get_scalar()  # type: ignore

                    # Vec is a struct of 3 values: [ptr, len, cap]
                    # We copy these 3 metadata values from memory
                    metadata_values = []
                    for offset in range(3):
                        cell = mem.mem[base_addr + offset]
                        metadata_values.append(cell.value)
                    arg_result = EvaluationResult(
                        values=metadata_values, typ="Vec", is_pointer=False
                    )
                # 2. Check if the parameter expects a fixed-size array [type; size]
                if param_type and param_type.startswith("["):
                    match = re.match(r"\[.+;\s*(\d+)\]", param_type)
                    if match:
                        size = int(match.group(1))
                        base_addr = arg_result.get_scalar()  # type: ignore

                        # 3. Deep copy the values from memory
                        copied_values = []
                        for offset in range(size):
                            cell = mem.mem[base_addr + offset]
                            copied_values.append(cell.value)

                        # Update result to contain the actual data, not the pointer
                        arg_result = EvaluationResult(
                            values=copied_values, typ=param_type, is_pointer=False
                        )
            ctx.store(f"arg_{arg_idx}", arg_result)
            ctx.advance()
            return ExecutionStatus.INCOMPLETE

        # Step N: Make the actual function call
        if ctx.step == num_args:
            # Collect all evaluated arguments
            arg_values = []
            for i in range(num_args):
                arg_result = ctx.get(f"arg_{i}")
                arg_values.append(arg_result.values)

            # This will push a new frame and set up for function execution
            # The actual function execution happens outside this expression
            # We return INCOMPLETE and the runner will handle the call
            ctx.store("ready_to_call", True)
            ctx.store("arg_values", arg_values)
            return ExecutionStatus.INCOMPLETE

        # Step N+1: Function has returned, get result
        if ctx.step == num_args + 1:
            # Result should be stored by the return instruction
            result = ctx.get("function_result")
            return result

        return ExecutionStatus.INCOMPLETE

    def description(self) -> str:
        args_str = ", ".join(arg.description() for arg in self.args)
        return f"{self.func_name}({args_str})"


class Dereference(Expression):
    """Pointer dereference: *ptr or **ptr"""

    def __init__(self, expr: Expression, levels: int = 1):
        self.expr = expr
        self.levels = levels

    def get_target_address(self, mem, prog) -> int:
        """
        L-Value logic: Resolves the pointer to the target address.
        For *p, this returns the value stored in p (which is an address).
        For **p, it returns the value stored at the address pointed to by p.
        """
        # We need to evaluate the inner expression (the pointer variable itself)
        # This is a one-off call, usually not needing the ctx.step state
        # unless the inner expression is complex (like a function call).

        res = self.expr.evaluate(mem, prog)
        if res == ExecutionStatus.INCOMPLETE:
            raise RuntimeError(
                "Complex inner pointer expressions not supported in LValue yet"
            )

        addr = res.get_scalar()  # type: ignore

        # Follow the pointer chain for (levels - 1)
        # If levels = 1 (*p), we just return the address stored in 'p'
        # If levels = 2 (**p), we fetch the value at address 'p' once
        for _ in range(self.levels - 1):
            if not isinstance(addr, int) or addr < 0 or addr >= len(mem.mem):
                raise ValueError(f"Invalid pointer address in chain: {addr}")
            addr = mem.mem[addr].value

        return addr

    def evaluate(self, mem, prog) -> Union[EvaluationResult, ExecutionStatus]:
        """
        R-Value logic: Fetches the actual value at the pointed-to location.
        Used in expressions like: let x = *p + 2;
        """
        ctx = self.get_ctx(mem)
        # Step 0: Handle the async evaluation of the inner pointer expression
        if ctx.step == 0:
            target_addr = self.get_target_address(mem, prog)
            ctx.store("target_addr", target_addr)
            ctx.advance()

        # Step 1: Read the value at that address
        target_addr = ctx.get("target_addr")
        if (
            not isinstance(target_addr, int)
            or target_addr < 0
            or target_addr >= len(mem.mem)
        ):
            raise ValueError(f"Invalid dereference target: {target_addr}")

        cell = mem.mem[target_addr]

        # Return the DATA inside the cell
        return EvaluationResult(
            values=[cell.value], typ=cell.typ, is_pointer=cell.is_pointer
        )

    def description(self) -> str:
        stars = "*" * self.levels
        return f"{stars}{self.expr.description()}"


class Reference(Expression):
    """Address-of operation: &var"""

    def __init__(self, var_name: str):
        self.var_name = var_name

    def evaluate(self, mem, prog) -> EvaluationResult:
        try:
            addr = mem.get_addr(self.var_name)
        except Exception:
            addr = mem.get_addr(f"{self.var_name}.cap")
        return EvaluationResult(values=[addr], typ=f"&{self.var_name}", is_pointer=True)

    def description(self) -> str:
        return f"&{self.var_name}"


class ArrayLiteral(Expression):
    """Array literal: [1, 2, 3]"""

    def __init__(self, elements: list[Expression]):
        self.elements = elements

    def evaluate(self, mem, prog) -> Union[EvaluationResult, ExecutionStatus]:
        ctx = self.get_ctx(mem)
        num_elements = len(self.elements)

        # Evaluate each element
        if ctx.step < num_elements:
            elem_idx = ctx.step
            elem_result = self.elements[elem_idx].evaluate(mem, prog)
            if elem_result == ExecutionStatus.INCOMPLETE:
                return ExecutionStatus.INCOMPLETE
            ctx.store(f"elem_{elem_idx}", elem_result)
            ctx.advance()
            return ExecutionStatus.INCOMPLETE

        # Collect all values
        values = []
        for i in range(num_elements):
            elem_result = ctx.get(f"elem_{i}")
            values.append(elem_result.get_scalar())

        return EvaluationResult(values=values, typ="i32")

    def description(self) -> str:
        elems_str = ", ".join(elem.description() for elem in self.elements)
        return f"[{elems_str}]"


class VecMacro(Expression):
    """Vec macro: vec![1, 2, 3]"""

    def __init__(self, elements: list[Expression]):
        self.elements = elements

    def evaluate(self, mem, prog) -> Union[EvaluationResult, ExecutionStatus]:
        ctx = self.get_ctx(mem)
        # First evaluate all elements like ArrayLiteral
        num_elements = len(self.elements)

        if ctx.step < num_elements:
            elem_idx = ctx.step
            elem_result = self.elements[elem_idx].evaluate(mem, prog)
            if elem_result == ExecutionStatus.INCOMPLETE:
                return ExecutionStatus.INCOMPLETE
            ctx.store(f"elem_{elem_idx}", elem_result)
            ctx.advance()
            return ExecutionStatus.INCOMPLETE

        # Allocate heap space and return Vec metadata (ptr, len, cap)
        values = []
        for i in range(num_elements):
            elem_result = ctx.get(f"elem_{i}")
            values.append(elem_result.get_scalar())

        # The actual heap allocation will be done by the instruction using this expression
        # Return the values to be stored
        return EvaluationResult(values=values, typ="VecLiteral")

    def description(self) -> str:
        elems_str = ", ".join(elem.description() for elem in self.elements)
        return f"vec![{elems_str}]"


class BoxNew(Expression):
    """Box::new(value)"""

    def __init__(self, value: Expression):
        self.value = value

    def evaluate(self, mem, prog) -> Union[EvaluationResult, ExecutionStatus]:
        ctx = self.get_ctx(mem)
        if ctx.step == 0:
            value_result = self.value.evaluate(mem, prog)
            if value_result == ExecutionStatus.INCOMPLETE:
                return ExecutionStatus.INCOMPLETE
            ctx.store("value_result", value_result)
            ctx.advance()

        # Return the value to be boxed
        value_result = ctx.get("value_result")
        return EvaluationResult(
            values=value_result.values,
            typ="Box",
            is_pointer=False,  # Not yet a pointer, assignment will handle allocation
        )

    def description(self) -> str:
        return f"Box::new({self.value.description()})"
