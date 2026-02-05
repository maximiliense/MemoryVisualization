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
        just_exited_block = False
        while True:
            # 1. Determine current context
            if self.pc.block_stack:
                body, _ = self.pc.block_stack[-1]

            else:
                body = self.program.functions[self.pc.fn_name].body
                _ = None

            instr = body[self.pc.line_idx]

            if isinstance(instr, IfElse):
                chosen_block = instr.execute(self.mem, self.program)
                self.pc.block_stack.append((chosen_block, self.pc.line_idx + 1))
                self.pc.line_idx = 0
                return  # Yield to renderer: Arrow shows on the 'if' line

            # 4. If we just exited a block, show the arrow on this line before executing
            if just_exited_block:
                just_exited_block = False
                return  # Show arrow on the next instruction after block

            # 5. Standard Instructions
            from visualizer.ops import CallAssign, CallFunction, ReturnFunction

            # EXECUTE the current instruction
            if isinstance(instr, (CallAssign, CallFunction)):
                self.pc.ret_stack.append(
                    (self.pc.fn_name, self.pc.line_idx + 1, self.pc.block_stack)
                )
                self.pc.block_stack = []
                instr.execute(self.mem, self.program)
                self.pc.fn_name, self.pc.line_idx = instr.target, 0
            elif isinstance(instr, ReturnFunction):
                instr.execute(self.mem, self.program)
                if self.pc.ret_stack:
                    self.pc.fn_name, self.pc.line_idx, self.pc.block_stack = (
                        self.pc.ret_stack.pop()
                    )
                    self.pc.block_stack = []
                else:
                    self.pc.line_idx = len(body)
            else:
                instr.execute(self.mem, self.program)
                self.pc.line_idx += 1

                # if block complete, go out
                if self.pc.line_idx >= len(body):
                    if self.pc.block_stack:
                        # EXIT the block and jump to the parent's resume line
                        _, target_line = self.pc.block_stack.pop()
                        # TODO: line_idx + Block length
                        self.pc.line_idx = target_line
                        just_exited_block = True
                    return  # End of program

            # PC now points to the NEXT instruction
            return

    def update_display(self):
        self.ax.clear()
        render_to_ax(self.ax, self.mem, self.program, self.pc)
        self.fig.canvas.draw()
