import matplotlib.pyplot as plt

from visualizer.architecture import MemoryModel
from visualizer.ops import (
    CallAssign,
    CallFunction,
    ReturnFunction,
    ReturnIfEquals,
    calc_frame_size,
)
from visualizer.ops.instructions import IfElse
from visualizer.program import PC
from visualizer.renderer import BG, render_to_ax


class InteractiveRunner:
    def __init__(self, program):
        self.program, self.mem = program, MemoryModel()
        self.mem.push_frame("main", calc_frame_size(program.functions["main"]))
        self.pc = PC("main", 0)
        self.fig, self.ax = plt.subplots(figsize=(14, 9), facecolor=BG)
        self.fig.canvas.mpl_connect("key_press_event", self.on_press)
        self.update_display()
        plt.show()

    def on_press(self, event):
        if event.key == "right":
            self.step()
            self.update_display()

    def step(self):
        # 1. Determine current context to get the instruction
        if self.pc.block_stack:
            body, _ = self.pc.block_stack[-1]
        else:
            body = self.program.functions[self.pc.fn_name].body

        # 2. Execute the instruction at the current PC
        if self.pc.line_idx < len(body):
            instr = body[self.pc.line_idx]
            if isinstance(instr, IfElse):
                chosen_block = instr.execute(self.mem, self.program)
                # Save the NEXT line of the current scope to resume later
                self.pc.block_stack.append((chosen_block, self.pc.line_idx + 1))
                self.pc.line_idx = 0
                # We stop here so the renderer highlights the first line of the block
                return

            elif isinstance(instr, (CallAssign, CallFunction)):
                # Save context including the block_stack for the return
                self.pc.ret_stack.append(
                    (
                        self.pc.fn_name,
                        self.pc.line_idx + 1,
                        list(self.pc.block_stack),
                    )
                )
                instr.execute(self.mem, self.program)
                self.pc.fn_name, self.pc.line_idx = instr.target, 0
                self.pc.block_stack = []
                return

            elif isinstance(instr, ReturnFunction):
                instr.execute(self.mem, self.program)
                if self.pc.ret_stack:
                    self.pc.fn_name, self.pc.line_idx, self.pc.block_stack = (
                        self.pc.ret_stack.pop()
                    )
                else:
                    self.pc.line_idx = len(body)
                # Don't return yet; we might have returned to the end of a block
            else:
                instr.execute(self.mem, self.program)
                self.pc.line_idx += 1

        # 3. UNWINDING PHASE: Pop until we are no longer at the end of a body
        # This ensures that when 'step' ends, we point to the next real operation.
        while True:
            # Re-evaluate body based on current (possibly popped) stack
            if self.pc.block_stack:
                curr_body, _ = self.pc.block_stack[-1]
            else:
                curr_body = self.program.functions[self.pc.fn_name].body

            # If we are past the end of the current block/function...
            if self.pc.line_idx >= len(curr_body):
                if self.pc.block_stack:
                    # Pop the block and "teleport" to the resume line in the parent
                    _, resume_idx = self.pc.block_stack.pop()
                    self.pc.line_idx = resume_idx
                    continue  # Check the parent body now
                else:
                    # We finished the main function
                    break
            else:
                # We found a valid instruction line!
                break

    def update_display(self):
        self.ax.clear()
        render_to_ax(self.ax, self.mem, self.program, self.pc)
        self.fig.canvas.draw()
