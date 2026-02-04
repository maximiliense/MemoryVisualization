import matplotlib.pyplot as plt

from visualizer.architecture import BG, MemoryModel
from visualizer.ops import (
    CallAssign,
    CallFunction,
    ReturnFunction,
    ReturnIfEquals,
    calc_frame_size,
)
from visualizer.program import PC
from visualizer.renderer import render_to_ax


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
        body = self.program.functions[self.pc.fn_name].body
        if self.pc.line_idx >= len(body):
            return
        instr = body[self.pc.line_idx]

        if isinstance(instr, ReturnIfEquals) and instr.test(self.mem, self.program):
            instr = ReturnFunction()

        if isinstance(instr, (CallAssign, CallFunction)):
            self.pc.ret_stack.append((self.pc.fn_name, self.pc.line_idx + 1))
            instr.execute(self.mem, self.program)
            self.pc.fn_name, self.pc.line_idx = instr.target, 0
        elif isinstance(instr, ReturnFunction):
            instr.execute(self.mem, self.program)
            if self.pc.ret_stack:
                self.pc.fn_name, self.pc.line_idx = self.pc.ret_stack.pop()
            else:
                self.pc.line_idx += 1
        else:
            instr.execute(self.mem, self.program)
            self.pc.line_idx += 1

    def update_display(self):
        self.ax.clear()
        render_to_ax(self.ax, self.mem, self.program, self.pc)
        self.fig.canvas.draw()
