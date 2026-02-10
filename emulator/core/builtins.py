"""
V2 Built-in Methods and Special Expressions

This includes methods like .push(), .clone(), etc.
"""

from typing import Union

from .base import EvaluationResult, ExecutionContext, ExecutionStatus, Expression


class MethodCall(Expression):
    """
    Method call on an object: obj.method(args...)
    """

    def __init__(self, obj: Expression, method: str, args: list[Expression]):
        self.obj = obj
        self.method = method
        self.args = args
        self.ctx = ExecutionContext()

    def reset_ctx(self):
        self.ctx.reset()
        if hasattr(self.obj, "reset_ctx"):
            self.obj.reset_ctx()  # type: ignore
        for arg in self.args:
            if hasattr(arg, "reset_ctx"):
                arg.reset_ctx()  # type: ignore

    def evaluate(
        self,
        mem,
        prog,
    ) -> Union[EvaluationResult, ExecutionStatus]:
        # Step 0: Evaluate object
        print("Evaluating method call")
        if self.ctx.step == 0:
            obj_result = self.obj.evaluate(mem, prog)
            if obj_result == ExecutionStatus.INCOMPLETE:
                return ExecutionStatus.INCOMPLETE
            self.ctx.store("obj_result", obj_result)
            self.ctx.advance()

        # Steps 1-N: Evaluate arguments
        num_args = len(self.args)
        if self.ctx.step <= num_args:
            arg_idx = self.ctx.step - 1
            arg_result = self.args[arg_idx].evaluate(mem, prog)
            if arg_result == ExecutionStatus.INCOMPLETE:
                return ExecutionStatus.INCOMPLETE
            self.ctx.store(f"arg_{arg_idx}", arg_result)
            self.ctx.advance()
            if self.ctx.step <= num_args:
                return ExecutionStatus.INCOMPLETE

        # Step N+1: Execute method
        obj_result = self.ctx.get("obj_result")

        if self.method == "push":
            try:
                if hasattr(self.obj, "get_target_address"):
                    base_addr = self.obj.get_target_address(mem, prog)  # type: ignore
                else:
                    # Fallback: if it's a simple Variable
                    res = self.obj.evaluate(mem, prog)
                    base_addr = res.get_scalar()  # type: ignore

                self.ctx.store("base_addr", base_addr)
                self.ctx.advance()
            except Exception as e:
                raise ValueError(f"Method call target must have an address: {e}")
            return self._execute_push(mem, base_addr)  # type ignore
        elif self.method == "clone":
            return self._execute_clone(mem, obj_result)
        else:
            raise NotImplementedError(f"Method {self.method} not implemented")

    def _execute_push(self, mem, base_addr):
        """Execute Vec.push(value) using metadata addresses"""

        if base_addr is None:
            raise ValueError(
                f"Could not resolve base address for {self.obj.description()}"
            )

        # 2. Map metadata based on your 3-slot allocation
        # Vec { ptr, len, cap }
        p_addr = base_addr + 2
        l_addr = base_addr + 1
        c_addr = base_addr + 0

        # 3. Fetch current values
        ptr = mem.mem[p_addr].value
        length = mem.mem[l_addr].value
        cap = mem.mem[c_addr].value
        print(base_addr, ptr, length, cap)
        if not (
            isinstance(ptr, int) and isinstance(length, int) and isinstance(cap, int)
        ):
            raise ValueError(f"Vec metadata at {base_addr} is corrupted")

        # 4. Get the argument to push
        arg_result = self.ctx.get("arg_0")
        val = arg_result.get_scalar()

        # 5. Handle Reallocation
        if length >= cap:
            new_cap = cap * 2 if cap > 0 else 4
            # Allocate new buffer on heap
            new_ptr = mem.alloc_heap(None, "i32", new_cap)

            # Move elements to new heap location
            for i in range(length):
                old_cell = mem.mem[ptr + i]
                mem.mem[new_ptr + i].value = old_cell.value
                mem.mem[
                    new_ptr + i
                ].label = f"heap[{new_ptr + i}]"  # Generic heap label

                # Clean up old heap
                old_cell.freed = True
                old_cell.value = "FREED"

            # Update metadata in memory
            mem.mem[p_addr].value = new_ptr
            mem.mem[c_addr].value = new_cap
            ptr = new_ptr

        # 6. Perform the insertion
        mem.mem[ptr + length].value = val
        mem.mem[l_addr].value = length + 1

        return EvaluationResult(values=[None], typ="()")

    def _execute_clone(self, mem, obj_result):
        """Execute Box.clone() or similar"""
        if obj_result.is_pointer:
            # Clone a Box
            ha = obj_result.get_scalar()

            if isinstance(ha, int) and 0 <= ha < len(mem.mem):
                old_value = mem.mem[ha].value

                # Allocate new heap space
                new_ha = mem.alloc_heap("data", "i32")
                mem.mem[new_ha].value = old_value

                return EvaluationResult(
                    values=[new_ha], typ="Box<i32>", is_pointer=True
                )
            else:
                raise ValueError(f"Invalid heap address for clone: {ha}")
        else:
            raise NotImplementedError("Clone for non-pointer types")

    def description(self) -> str:
        args_str = ", ".join(arg.description() for arg in self.args)
        return f"{self.obj.description()}.{self.method}({args_str})"


class RandInt(Expression):
    """Random integer generator: rand_int(min, max)"""

    def __init__(self, min_expr: Expression, max_expr: Expression):
        self.min_expr = min_expr
        self.max_expr = max_expr
        self.ctx = ExecutionContext()

    def reset_ctx(self):
        self.ctx.reset()
        if hasattr(self.min_expr, "reset_ctx"):
            self.min_expr.reset_ctx()  # type: ignore
        if hasattr(self.max_expr, "reset_ctx"):
            self.max_expr.reset_ctx()  # type: ignore

    def evaluate(self, mem, prog) -> Union[EvaluationResult, ExecutionStatus]:
        # Step 0: Evaluate min
        if self.ctx.step == 0:
            min_result = self.min_expr.evaluate(mem, prog)
            if min_result == ExecutionStatus.INCOMPLETE:
                return ExecutionStatus.INCOMPLETE
            self.ctx.store("min_result", min_result)
            self.ctx.advance()

        # Step 1: Evaluate max
        if self.ctx.step == 1:
            max_result = self.max_expr.evaluate(mem, prog)
            if max_result == ExecutionStatus.INCOMPLETE:
                return ExecutionStatus.INCOMPLETE
            self.ctx.store("max_result", max_result)
            self.ctx.advance()

        # Step 2: Generate random number
        min_result = self.ctx.get("min_result")
        max_result = self.ctx.get("max_result")

        import random

        val = random.randint(min_result.get_scalar(), max_result.get_scalar())

        return EvaluationResult(values=[val], typ="i32")

    def description(self) -> str:
        return f"rand_int({self.min_expr.description()}, {self.max_expr.description()})"


class Println(Expression):
    """Print macro: println!("{}", expr)"""

    def __init__(self, expr: Expression):
        self.expr = expr
        self.ctx = ExecutionContext()

    def reset_ctx(self):
        self.ctx.reset()
        if hasattr(self.expr, "reset_ctx"):
            self.expr.reset_ctx()  # type: ignore

    def evaluate(self, mem, prog) -> Union[EvaluationResult, ExecutionStatus]:
        if self.ctx.step == 0:
            result = self.expr.evaluate(mem, prog)
            if result == ExecutionStatus.INCOMPLETE:
                return ExecutionStatus.INCOMPLETE
            self.ctx.store("result", result)
            self.ctx.advance()

        result = self.ctx.get("result")
        # In visualization, we don't actually print, just show the instruction
        # But we could add to a print log if needed
        return EvaluationResult(values=[None], typ="()")

    def description(self) -> str:
        return f'println!("{{}}", {self.expr.description()})'
