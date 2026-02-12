import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.backend_tools import Cursors

from emulator.rendering.renderer import BG, TEXT_BRIGHT
from emulator.runtime.interactive import InteractiveRunner


class ProgramLauncher:
    def __init__(self, program_map):
        self.program_map = program_map
        self.fig, self.ax = plt.subplots(figsize=(14, 9), facecolor=BG)
        self.selected_program = None
        self.buttons = []

        self.draw_menu()
        self.runner = None

        # Connect both click AND hover events
        click_event = self.fig.canvas.mpl_connect("button_press_event", self.on_click)
        hover_event = self.fig.canvas.mpl_connect("motion_notify_event", self.on_hover)
        key_event = self.fig.canvas.mpl_connect("key_press_event", self.on_press)
        self.events = [click_event, hover_event, key_event]
        plt.show()

    def on_press(self, event):
        if self.runner is not None:
            self.runner.on_press(event)

    def on_hover(self, event):
        # Use 'pointer' for the standard arrow and 'hand' for the finger
        cursor = Cursors.POINTER

        if event.inaxes == self.ax:
            is_over_button = False
            for x, y, w, h, key in self.buttons:
                if x <= event.xdata <= x + w and y <= event.ydata <= y + h:
                    is_over_button = True
                    break

            if is_over_button:
                cursor = Cursors.HAND

        self.fig.canvas.set_cursor(cursor)

    def draw_menu(self):
        self.ax.clear()
        self.ax.set_facecolor(BG)
        self.ax.set_axis_off()
        self.ax.set_xlim(0, 10)
        self.ax.set_ylim(0, 10)

        self.ax.text(
            5,
            9.8,
            "SELECT A PROGRAM TO VISUALIZE",
            color=TEXT_BRIGHT,
            fontsize=20,
            fontweight="bold",
            ha="center",
            family="monospace",
        )

        # Create a grid of buttons
        cols = 4
        # rows = (len(keys) // cols) + 1

        for idx, (key, val) in enumerate(self.program_map.items()):
            c = idx % cols
            r = idx // cols

            x = 1.0 + c * 2.1
            y = 8.2 - r * 1.0
            width, height = 1.9, 0.6

            # Button background
            color = val[1]
            rect = mpatches.FancyBboxPatch(
                (x, y),
                width,
                height,
                boxstyle="round,pad=0.1",
                facecolor=color,
                alpha=0.8,
                mutation_scale=0.2,
            )
            self.ax.add_patch(rect)
            self.buttons.append((x, y, width, height, key))

            # Program Label
            self.ax.text(
                x + width / 2,
                y + height / 2,
                key,
                color=BG,
                fontsize=12,
                fontweight="bold",
                ha="center",
                va="center",
                family="monospace",
            )

        self.fig.canvas.draw()

    def on_click(self, event):
        if event.inaxes != self.ax:
            return

        for x, y, w, h, key in self.buttons:
            if x <= event.xdata <= x + w and y <= event.ydata <= y + h:
                # 1. Reset the cursor to standard arrow
                self.fig.canvas.set_cursor(Cursors.POINTER)  # type: ignore

                # 2. Launch runner in the SAME window
                (prog_func, _) = self.program_map[key]
                self.runner = InteractiveRunner(prog_func(), fig=self.fig, ax=self.ax)
                # 3. Stop processing menu clicks
                break
