import matplotlib.pyplot as plt

from emulator.rendering.renderer import BG, render_to_ax
from emulator.runtime.architecture import MemoryModel
from emulator.runtime.runner import ProgramRunner


class InteractiveRunner:
    def __init__(self, program, fig=None, ax=None, events=None):
        self.program, self.mem = program, MemoryModel()
        self.runner = ProgramRunner(self.program, self.mem)

        # Use existing window if provided, else create new
        if fig and ax:
            self.fig, self.ax = fig, ax

        else:
            self.fig, self.ax = plt.subplots(figsize=(14, 9), facecolor=BG)
            self.fig.canvas.mpl_connect("key_press_event", self.on_press)

        self.update_display()

        # Only call plt.show() if we created the window here
        if not fig:
            plt.show()

    @property
    def is_finished(self):
        return self.runner.is_finished()

    def on_press(self, event):
        if event.key == "right" and not self.is_finished:
            self.step()
            self.update_display()
        elif self.is_finished:
            exit()

    def step(self):
        try:
            while not self.runner.step():
                pass
        except Exception as e:
            print(e)
            exit()

    def update_display(self):
        self.ax.clear()
        render_to_ax(self.ax, self.mem, self.program, self.runner.pc)
        self.fig.canvas.draw()
