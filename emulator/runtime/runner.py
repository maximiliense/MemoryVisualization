"""
V2 Program Structure and Runner

Handles program execution with proper multi-step instruction handling.
"""

from dataclasses import dataclass, field
from typing import Optional

from emulator.core.base import ExecutionStatus, Instruction
from emulator.core.instructions import (
    Assignment,
    CompoundAssignment,
    LetBinding,
    Return,
)


@dataclass
class FunctionDef:
    """Function definition"""

    params: list[tuple[str, Optional[str]]] = field(default_factory=list)
    body: list[Instruction] = field(default_factory=list)

    def param_size(self) -> int:
        """Calculate stack space needed for parameters"""
        total = 0
        for _, typ in self.params:
            if typ and typ.startswith("&"):
                total += 1
            elif typ and "Vec" in typ:
                total += 3
            elif typ and typ.startswith("["):
                # Parse [Type; N]
                import re

                m = re.match(r"\[.+;\s*(\d+)\]", typ)
                if m:
                    total += int(m.group(1))
                else:
                    total += 1
            else:
                total += 1
        return total


@dataclass
class Program:
    """Complete program with all functions"""

    functions: dict[str, FunctionDef] = field(default_factory=dict)


@dataclass
class ProgramCounter:
    """Tracks execution position in the program"""

    fn_name: str
    line_idx: int
    block_stack: list[tuple[list[Instruction], int]] = field(default_factory=list)
    ret_stack: list[tuple[str, int, list]] = field(default_factory=list)


class ProgramRunner:
    """
    Executes a program step-by-step.

    Each call to step() executes one atomic operation, which might be:
    - Completing a simple instruction
    - Evaluating one sub-expression in a complex expression
    - Entering/exiting a block or function call
    """

    def __init__(self, program: Program, memory):
        self.program = program
        self.mem = memory
        self.pc = ProgramCounter("main", 0)

        # Initialize main function frame
        main_fn = program.functions["main"]
        frame_size = self._calc_frame_size(main_fn)
        self.mem.push_frame("main", frame_size)

    def step(self) -> bool:
        """
        Execute one step of the program.
        Returns:
            True if the PC moved to a different line or function.
            False if we are still evaluating the current instruction.
        """
        from emulator.core.expressions import FunctionCall
        from emulator.core.instructions import (
            Assignment,
            ExpressionStatement,
            IfElseBlock,
            LetBinding,
            Return,
            WhileLoop,
        )

        # Get current instruction
        if self.pc.block_stack:
            body, _ = self.pc.block_stack[-1]
        else:
            body = self.program.functions[self.pc.fn_name].body

        if not body or self.pc.line_idx >= len(body):
            # At end of block/function -> Unwinds/Returns (PC MOVES)
            self._handle_block_end()
            return True

        instr = body[self.pc.line_idx]

        # Execute instruction
        status = instr.execute(self.mem, self.program)

        if status == ExecutionStatus.COMPLETE:
            # Move to next instruction (PC MOVES)
            if isinstance(instr, Return):
                self._handle_return(instr)
                return False
            else:
                self.pc.line_idx += 1
                self._unwind_if_needed()
                return True

        elif status == ExecutionStatus.INCOMPLETE:
            # Check for Function Calls inside the current instruction
            target_expr = None
            if isinstance(instr, (ExpressionStatement, Return)):
                target_expr = instr.expr
            elif isinstance(instr, LetBinding):
                target_expr = instr.expr
            elif isinstance(instr, Assignment):
                target_expr = instr.expr

            # If a FunctionCall is ready to fire, we "Jump" (PC MOVES)
            if isinstance(target_expr, FunctionCall) and target_expr.get_ctx(
                self.mem
            ).get("ready_to_call"):
                func_name = target_expr.func_name
                target_ctx = target_expr.get_ctx(self.mem)
                arg_values = target_ctx.get("arg_values")

                # 1. Clear flag and advance expr state to wait for return value
                target_ctx.store("ready_to_call", False)
                target_ctx.advance()

                # 2. Save current PC to return stack
                self.pc.ret_stack.append(
                    (self.pc.fn_name, self.pc.line_idx, list(self.pc.block_stack))
                )

                # 3. Setup new frame
                new_fn_def = self.program.functions[func_name]
                frame_size = self._calc_frame_size(new_fn_def)

                ret_dest = None
                ret_alloc_new = False
                if isinstance(instr, LetBinding):
                    ret_dest = instr.var_name
                    ret_alloc_new = True
                elif isinstance(instr, Assignment):
                    ret_dest = instr.lvalue.description()

                self.mem.push_frame(
                    func_name,
                    frame_size,
                    ret_dest=ret_dest,
                    ret_alloc_new=ret_alloc_new,
                )

                # 4. Map arguments
                for i, (param_name, param_type) in enumerate(new_fn_def.params):
                    vals = arg_values[i]

                    # Determine types
                    is_ptr = param_type and (
                        param_type.startswith("&") or param_type.startswith("*")
                    )
                    is_array = not is_ptr and param_type and param_type.startswith("[")
                    is_vec = not is_ptr and param_type and param_type.startswith("Vec")

                    if is_array:
                        import re

                        match = re.match(r"\[(.+);\s*(\d+)\]", param_type)  # type: ignore
                        if match:
                            size = int(match.group(2))
                            if size != len(vals):
                                raise MemoryError(
                                    f"Stack frame mismatch for {param_name}"
                                )

                            self.mem.alloc_stack_var(
                                param_name,
                                param_type,
                                vals,
                                span=len(vals),
                                is_pointer=False,
                            )
                            print("\t\tALLOCATING ON STACK:", param_type)

                    elif is_vec:
                        # Vec has 3 components: ptr, len, cap
                        if len(vals) != 3:
                            raise MemoryError(f"Invalid Vec metadata for {param_name}")

                        # Allocate individual fields so they are searchable by name
                        fields = [("ptr", "ptr"), ("len", "usize"), ("cap", "usize")]

                        for offset, (suffix, field_type) in enumerate(fields):
                            field_full_name = f"{param_name}.{suffix}"
                            self.mem.alloc_stack_var(
                                field_full_name,
                                field_type,
                                vals[2 - offset],
                                is_pointer=(suffix == "ptr"),
                            )

                        # Optional: Add a base alias for the name itself pointing to the first field
                        # This allows 'param_name' to resolve to the address of 'param_name.ptr'

                    else:
                        # Standard scalar or pointer
                        val = (
                            vals[0]
                            if isinstance(vals, list) and len(vals) > 0
                            else vals
                        )
                        self.mem.alloc_stack_var(
                            param_name, param_type or "i32", val, is_pointer=is_ptr
                        )

                # 5. Jump to the new function
                self.pc.fn_name = func_name
                self.pc.line_idx = 0
                self.pc.block_stack = []
                return True

            # Control Flow: If/Else (PC MOVES)
            if isinstance(instr, IfElseBlock):
                chosen_branch = instr.get_chosen_branch(self.mem)
                if chosen_branch is not None:
                    # Enter branch
                    self.pc.block_stack.append((chosen_branch, self.pc.line_idx + 1))
                    self.pc.line_idx = 0
                    return True
                else:
                    # Condition evaluated but no else branch exists
                    self.pc.line_idx += 1
                    return True

            # Control Flow: While (PC MOVES)
            elif isinstance(instr, WhileLoop):
                if instr.should_continue(self.mem):
                    self.pc.block_stack.append((instr.body, self.pc.line_idx))
                    self.pc.line_idx = 0
                    instr.reset_ctx(self.mem)
                    return True
                else:
                    self.pc.line_idx += 1
                    return True

        # If we got here, status was likely INCOMPLETE but no control flow jump happened.
        # This means we are still evaluating an expression (e.g., 1 + 2 * 3).
        # (PC STAYS on same line)
        return False

    def _handle_block_end(self):
        """Handle reaching the end of a block or function"""
        if self.pc.block_stack:
            # Pop block and resume
            _, resume_idx = self.pc.block_stack.pop()
            self.pc.line_idx = resume_idx
        elif self.pc.ret_stack:
            # Return from function
            self._handle_return(None)
        else:
            # End of main, do nothing
            pass

    def _handle_return(self, return_instr: Optional[Return]):
        """Handle return from function and inject result into the waiting instruction."""
        return_result = None
        if return_instr is not None:
            return_result = return_instr.get_ctx(self.mem).get("return_result")

        # Pop function frame to get back to caller's frame
        # frame = self.mem.call_stack[-1]
        self.mem.pop_frame()

        # Restore caller's position
        if self.pc.ret_stack:
            self.pc.fn_name, self.pc.line_idx, self.pc.block_stack = (
                self.pc.ret_stack.pop()
            )

            # FIND THE WAITING INSTRUCTION
            if self.pc.block_stack:
                body, _ = self.pc.block_stack[-1]
            else:
                body = self.program.functions[self.pc.fn_name].body

            waiting_instr = body[self.pc.line_idx]
            if (
                isinstance(waiting_instr, (LetBinding, Assignment, CompoundAssignment))
                and return_result
            ):
                waiting_ctx = waiting_instr.get_ctx(self.mem)
                waiting_ctx.store("expr_result", return_result)
                waiting_ctx.advance()
        else:
            # Returned from main
            self.pc.line_idx = len(self.program.functions["main"].body)

    def _unwind_if_needed(self):
        """Unwind block stack if we're past the end of current block"""
        while True:
            if self.pc.block_stack:
                curr_body, _ = self.pc.block_stack[-1]
            else:
                curr_body = self.program.functions[self.pc.fn_name].body

            if curr_body is None or self.pc.line_idx >= len(curr_body):
                if self.pc.block_stack:
                    _, resume_idx = self.pc.block_stack.pop()
                    self.pc.line_idx = resume_idx
                    continue
                else:
                    break
            else:
                break

    def _calc_frame_size(self, func: FunctionDef) -> int:
        """Calculate stack frame size needed for function"""
        param_size = func.param_size()
        body_size = self._calc_body_size(func.body)
        return max(param_size + body_size, 1)

    def _calc_body_size(self, body: list[Instruction]) -> int:
        """Calculate stack space needed for instructions, accounting for Vecs and Arrays."""
        import re

        from emulator.core.expressions import ArrayLiteral, VecMacro
        from emulator.core.instructions import IfElseBlock, LetBinding, WhileLoop

        size = 0
        for instr in body:
            if isinstance(instr, LetBinding):
                # 1. Determine size from explicit type annotation (e.g., let v: Vec<i32>)
                if instr.typ:
                    if "Vec" in instr.typ:
                        size += 3
                    elif instr.typ.startswith("["):
                        # Parse array size from "[T; N]"
                        m = re.match(r"\[.+;\s*(\d+)\]", instr.typ)
                        size += int(m.group(1)) if m else 1
                    else:
                        size += 1

                # 2. If no type is provided, infer size from the expression (e.g., let v = vec![...])
                elif instr.expr:
                    if isinstance(instr.expr, VecMacro):
                        size += 3
                    elif isinstance(instr.expr, ArrayLiteral):
                        size += len(instr.expr.elements)
                    else:
                        size += 1

                # 3. Default to scalar size
                else:
                    size += 1

            elif isinstance(instr, IfElseBlock):
                # In branching logic, we take the max possible size needed by either path
                then_size = self._calc_body_size(instr.then_body)
                else_size = self._calc_body_size(instr.else_body)
                size += max(then_size, else_size)

            elif isinstance(instr, WhileLoop):
                # Loops use the same stack slots repeatedly, so we take the body's size
                size += self._calc_body_size(instr.body)

        return size

    def is_finished(self) -> bool:
        """Check if program execution is complete"""
        if self.pc.fn_name != "main":
            return False
        if self.pc.ret_stack:
            return False
        body = self.program.functions["main"].body
        return self.pc.line_idx >= len(body)
