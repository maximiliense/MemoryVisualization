"""
V2 Instruction System

Instructions perform side effects and can execute over multiple steps.
"""

from typing import Optional

from .base import (
    EvaluationResult,
    ExecutionStatus,
    Instruction,
)
from .expressions import Expression
from .lvalues import LValue


class Nop(Instruction):
    """No-operation (comment)"""

    def __init__(self, comment: str):
        self.comment = comment

    def execute(self, mem, prog) -> ExecutionStatus:
        return ExecutionStatus.COMPLETE

    def description(self) -> str:
        return f"// {self.comment}"


class LetBinding(Instruction):
    """
    Variable declaration with initialization.
    Syntax: let var: type = expr

    This handles the full pipeline:
    1. Evaluate the expression
    2. Allocate stack space
    3. Store the result
    """

    def __init__(self, var_name: str, typ: Optional[str], expr: Optional[Expression]):
        self.var_name = var_name
        self.typ = typ
        self.expr = expr

    def execute(self, mem, prog) -> ExecutionStatus:
        ctx = self.get_ctx(mem)
        # Step 0: Evaluate the expression (if any)
        if ctx.step == 0:
            if self.expr is None:
                # Uninitialized variable
                mem.alloc_stack_var(self.var_name, self.typ or "i32", None)
                return ExecutionStatus.COMPLETE

            result = self.expr.evaluate(mem, prog)  # type: ignore
            if result == ExecutionStatus.INCOMPLETE:
                return ExecutionStatus.INCOMPLETE

            ctx.store("expr_result", result)
            ctx.advance()

        # Step 1: Allocate and store
        result: EvaluationResult = ctx.get("expr_result")

        # Special handling for different types
        if result.typ == "Vec":
            if len(result.values) == 3:
                cap_val, len_val, ptr_val = result.values
            else:
                # Fallback for safety if metadata is malformed
                raise ValueError("Expected Vec metadata (ptr, len, cap)")

            # Copy metadata to new stack slots
            mem.alloc_stack_var(f"{self.var_name}.ptr", "ptr", ptr_val, is_pointer=True)
            mem.alloc_stack_var(f"{self.var_name}.len", "usize", len_val)
            mem.alloc_stack_var(f"{self.var_name}.cap", "usize", cap_val)
        elif result.typ == "VecLiteral":
            # Allocate heap for vec data
            cap = len(result.values) if result.values else 1
            base = mem.alloc_heap(None, "i32", cap)
            for i, v in enumerate(result.values):
                mem.mem[base + i].value = v
                mem.mem[base + i].label = f"{self.var_name}[{i}]"

            # Allocate stack metadata
            mem.alloc_stack_var(f"{self.var_name}.ptr", "ptr", base, is_pointer=True)
            mem.alloc_stack_var(f"{self.var_name}.len", "usize", len(result.values))
            mem.alloc_stack_var(f"{self.var_name}.cap", "usize", cap)

        elif result.typ == "Box":
            # Allocate heap for boxed value
            ha = mem.alloc_heap("data", "i32")
            mem.mem[ha].value = result.get_scalar()
            mem.alloc_stack_var(self.var_name, "Box<i32>", ha, is_pointer=True)

        elif len(result.values) > 1:
            # Array
            mem.alloc_stack_var(
                self.var_name,
                self.typ or "array",
                result.values,
                span=len(result.values),
            )

        else:
            # Scalar
            mem.alloc_stack_var(
                self.var_name,
                result.typ,
                result.get_scalar(),
                is_pointer=result.is_pointer,
            )

        return ExecutionStatus.COMPLETE

    def description(self) -> str:
        typ_str = f": {self.typ}" if self.typ else ""
        expr_str = f" = {self.expr.description()}" if self.expr else ""
        return f"let {self.var_name}{typ_str}{expr_str};"


class Assignment(Instruction):
    """
    Assignment to existing variable or memory location.
    Syntax: lvalue = expr
    """

    def __init__(self, lvalue: LValue, expr: Expression):
        self.lvalue = lvalue
        self.expr = expr

    def execute(self, mem, prog) -> ExecutionStatus:
        ctx = self.get_ctx(mem)
        # Step 0: Evaluate the expression
        if ctx.step == 0:
            result = self.expr.evaluate(mem, prog)  # type: ignore
            if result == ExecutionStatus.INCOMPLETE:
                return ExecutionStatus.INCOMPLETE
            ctx.store("expr_result", result)
            ctx.advance()

        # Step 1: Get address and handle storage based on type
        result: EvaluationResult = ctx.get("expr_result")

        # Get the target base address
        # For a Vec, this should be the address of the .ptr field
        addr = self.lvalue.get_address(mem, prog)

        # 1. Handle Vec Assignment (Copying Metadata)
        if result.typ == "Vec":
            if len(result.values) == 3:
                # result.values is [ptr, len, cap]
                # We overwrite the 3 contiguous slots starting at addr
                for offset in range(3):
                    mem.mem[addr + offset].value = result.values[offset]  # type: ignore
            else:
                raise ValueError("Expected 3 metadata values for Vec assignment")

        # 2. Handle Array Assignment (Deep Copying elements)
        elif len(result.values) > 1 or (result.typ and result.typ.startswith("[")):
            # We assume the LValue addr is the start of a span
            for i, val in enumerate(result.values):
                target_cell_addr = addr + i  # type: ignore
                if target_cell_addr < len(mem.mem):
                    mem.mem[target_cell_addr].value = val

        # 3. Handle Scalar / Pointer / Box Assignment
        else:
            # Single address update
            mem.mem[addr].value = result.get_scalar()
            mem.mem[addr].is_pointer = result.is_pointer
            # Update type if necessary
            if result.typ and not mem.mem[addr].typ:
                mem.mem[addr].typ = result.typ

        return ExecutionStatus.COMPLETE

    def description(self) -> str:
        return f"{self.lvalue.description()} = {self.expr.description()};"


class CompoundAssignment(Instruction):
    """
    Compound assignment: lvalue op= expr
    Examples: x += 1, y *= 2
    """

    def __init__(self, lvalue: LValue, op: str, expr: Expression):
        self.lvalue = lvalue
        self.op = op
        self.expr = expr

    def execute(self, mem, prog) -> ExecutionStatus:
        ctx = self.get_ctx(mem)
        # Step 0: Evaluate the expression
        if ctx.step == 0:
            result = self.expr.evaluate(mem, prog)  # type: ignore
            if result == ExecutionStatus.INCOMPLETE:
                return ExecutionStatus.INCOMPLETE
            ctx.store("expr_result", result)
            ctx.advance()

        # Step 1: Perform operation and store
        result: EvaluationResult = ctx.get("expr_result")
        addr = self.lvalue.get_address(mem, prog)

        current_val = mem.mem[addr].value
        new_val = result.get_scalar()

        if self.op == "+=":
            mem.mem[addr].value = current_val + new_val
        elif self.op == "-=":
            mem.mem[addr].value = current_val - new_val
        elif self.op == "*=":
            mem.mem[addr].value = current_val * new_val
        elif self.op == "/=":
            mem.mem[addr].value = current_val // new_val
        else:
            raise ValueError(f"Unknown compound operator: {self.op}")

        return ExecutionStatus.COMPLETE

    def description(self) -> str:
        return f"{self.lvalue.description()} {self.op} {self.expr.description()};"


class ExpressionStatement(Instruction):
    """
    Standalone expression as a statement (for side effects).
    Example: func(); or vec.push(5);
    """

    def __init__(self, expr: Expression):
        self.expr = expr

    def execute(self, mem, prog) -> ExecutionStatus:
        result = self.expr.evaluate(mem, prog)
        if result == ExecutionStatus.INCOMPLETE:
            return ExecutionStatus.INCOMPLETE
        # Discard the result
        return ExecutionStatus.COMPLETE

    def description(self) -> str:
        return f"{self.expr.description()};"


class IfElseBlock(Instruction):
    """
    Conditional execution.
    Syntax: if condition { then_body } else { else_body }
    """

    def __init__(
        self,
        condition: Expression,
        then_body: list[Instruction],
        else_body: Optional[list[Instruction]] = None,
    ):
        self.condition = condition
        self.then_body = then_body
        self.else_body = else_body or []

    def execute(self, mem, prog) -> ExecutionStatus:
        ctx = self.get_ctx(mem)
        # Step 0: Evaluate condition
        if ctx.step == 0:
            result = self.condition.evaluate(mem, prog)
            if result == ExecutionStatus.INCOMPLETE:
                return ExecutionStatus.INCOMPLETE
            ctx.store("condition_result", result)
            ctx.advance()

        # Step 1: Determine which branch to execute
        condition_result: EvaluationResult = ctx.get("condition_result")

        # Return the appropriate branch for the runner to execute
        # This is handled specially by the runner
        if condition_result.get_scalar():
            ctx.store("chosen_branch", "then")
            return ExecutionStatus.INCOMPLETE  # Signal runner to enter block
        else:
            ctx.store("chosen_branch", "else")
            return ExecutionStatus.INCOMPLETE

    def get_chosen_branch(self, mem) -> list[Instruction]:
        """Get the branch to execute based on condition"""
        ctx = self.get_ctx(mem)
        branch = ctx.get("chosen_branch")
        if branch == "then":
            return self.then_body
        else:
            return self.else_body

    def description(self) -> str:
        cond_str = self.condition.description()
        return f"if {cond_str} {{"
        # cond_str = self.condition.description()
        # if self.else_body:
        #     return f"if {cond_str} {{ ... }} else {{ ... }}"
        # return f"if {cond_str} {{ ... }}"


class WhileLoop(Instruction):
    """
    While loop.
    Syntax: while condition { body }
    """

    def __init__(self, condition: Expression, body: list[Instruction]):
        self.condition = condition
        self.body = body

    def execute(self, mem, prog) -> ExecutionStatus:
        ctx = self.get_ctx(mem)
        # Evaluate condition each iteration
        result = self.condition.evaluate(mem, prog)
        if result == ExecutionStatus.INCOMPLETE:
            return ExecutionStatus.INCOMPLETE
        cond_ctx = self.condition.get_ctx(mem)  # type: ignore
        cond_ctx.reset()
        ctx.store("condition_result", result)
        return ExecutionStatus.INCOMPLETE  # Signal runner to handle loop

    def should_continue(self, mem) -> bool:
        """Check if loop should continue"""
        ctx = self.get_ctx(mem)
        result: EvaluationResult = ctx.get("condition_result")
        return bool(result.get_scalar())

    def description(self) -> str:
        return f"while {self.condition.description()} {{"
        # return f"while {self.condition.description()} {{ ... }}"


class Return(Instruction):
    """
    Return from function.
    Syntax: return expr
    """

    def __init__(self, expr: Optional[Expression] = None):
        self.expr = expr

    def execute(self, mem, prog) -> ExecutionStatus:
        if self.expr is None:
            # Void return
            return ExecutionStatus.COMPLETE

        # 1. Evaluate return expression
        result = self.expr.evaluate(mem, prog)  # type: ignore
        if result == ExecutionStatus.INCOMPLETE:
            return ExecutionStatus.INCOMPLETE
        result: EvaluationResult = result
        # 2. Handle Return-by-Value for Arrays
        # If the return type is [type; size], we must pull the values from memory
        if result.typ and result.typ.startswith("["):
            import re

            match = re.match(r"\[.+;\s*(\d+)\]", result.typ)
            if match:
                size = int(match.group(1))
                base_addr = result.get_scalar()

                # Fetch the actual data from the current stack frame
                return_values = []
                for offset in range(size):
                    # We read the values before the frame is popped
                    cell = mem.mem[base_addr + offset]
                    return_values.append(cell.value)

                # Update the result to hold the actual values instead of the address
                # This 'result' is now portable and safe from frame-popping
                result = EvaluationResult(
                    values=return_values, typ=result.typ, is_pointer=False
                )
        elif result.typ == "Vec" or (result.typ and result.typ.startswith("Vec")):
            # The result from evaluate() is the base address of the Vec metadata
            base_addr = result.get_scalar()

            # Extract the 3 specific components: ptr, len, cap
            # These are guaranteed to be contiguous based on your ProgramRunner allocation
            ptr = mem.mem[base_addr + 0].value
            length = mem.mem[base_addr + 1].value
            cap = mem.mem[base_addr + 2].value

            # Pack them into a portable result
            result = EvaluationResult(
                values=[ptr, length, cap], typ="Vec", is_pointer=False
            )
        # 3. Store result for caller
        ctx = self.get_ctx(mem)
        ctx.store("return_result", result)
        return ExecutionStatus.COMPLETE

    def description(self) -> str:
        if self.expr:
            return f"return {self.expr.description()};"
        return "return;"


class Drop(Instruction):
    """
    Drop (free) a value.
    Syntax: drop(var)
    """

    def __init__(self, var_name: str, is_vec: bool = False):
        self.var_name = var_name
        self.is_vec = is_vec

    def execute(self, mem, prog) -> ExecutionStatus:
        if self.is_vec:
            # Free Vec

            p_addr = mem.get_addr(f"{self.var_name}.ptr")
            c_addr = mem.get_addr(f"{self.var_name}.cap")

            ptr = mem.mem[p_addr].value
            cap = mem.mem[c_addr].value

            if isinstance(ptr, int) and isinstance(cap, int):
                for addr in range(ptr, ptr + cap):
                    if 0 <= addr < len(mem.mem):
                        mem.mem[addr].freed = True
                        mem.mem[addr].value = "FREED"
                        mem.mem[addr].label = None

            mem.mem[p_addr].value = "null"
            mem.mem[p_addr].is_pointer = False
            mem.mem[mem.get_addr(f"{self.var_name}.len")].value = 0
            mem.mem[c_addr].value = 0
        else:
            # Free Box or other pointer
            pa = mem.get_addr(self.var_name)
            ha = mem.mem[pa].value

            if isinstance(ha, int):
                mem.mem[ha].freed = True
                mem.mem[ha].label = None
                mem.mem[ha].value = "FREED"

            mem.mem[pa].value = "null"
            mem.mem[pa].is_pointer = False

        return ExecutionStatus.COMPLETE

    def description(self) -> str:
        suffix = " // Vec" if self.is_vec else ""
        return f"drop({self.var_name});{suffix}"
