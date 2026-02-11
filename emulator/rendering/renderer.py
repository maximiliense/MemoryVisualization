import re

import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch

from emulator.core.instructions import IfElseBlock, WhileLoop

# Adjusting imports for the V2 Architecture
from emulator.runtime.architecture import (
    HEAP_BOTTOM,
    MEM_SIZE,
    STACK_LIMIT,
    STACK_TOP,
    MemoryModel,
)
from emulator.runtime.runner import Program, ProgramCounter

BG = "#1E1E2E"
HEAP_COL = "#C08050"
FREE_COL = "#4A4A5A"
EMPTY_COL = "#2A2B3D"
PTR_COL = "#E8506A"
TEXT_BRIGHT = "#CDD6F4"
TEXT_DIM = "#585B70"
TEXT_MID = "#A6ADC8"
CURR_LINE = "#F9E2AF"
STRIP_EDGE = "#45475A"

FRAME_PALETTE = [
    "#5B8DB8",
    "#7B68AE",
    "#4CAF7B",
    "#D4845A",
    "#E8506A",
    "#5BB8D4",
    "#C9A84C",
]


def darken_hex_color(hex_color, factor=0.7):
    """
    Darkens a hex color by a given factor.
    :param hex_color: String like '#121212'
    :param factor: Multiply RGB values by this (0.0 to 1.0)
    :return: Darkened hex string
    """
    # Remove '#' if present
    hex_color = hex_color.lstrip("#")

    # Convert hex to RGB (0-255)
    rgb = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

    # Apply factor and ensure it stays within [0, 255]
    darkened_rgb = tuple(max(0, int(c * factor)) for c in rgb)

    # Convert back to hex
    return "#{:02x}{:02x}{:02x}".format(*darkened_rgb)


def group_name(label: str) -> str:
    return re.split(r"[.\[]", label, maxsplit=1)[0]


def modulate_luminance(color, factor):
    r, g, b = mcolors.to_rgb(color)
    return (min(r * factor, 1.0), min(g * factor, 1.0), min(b * factor, 1.0))


def draw_code_block(
    ax,
    instructions,
    start_y,
    pc: ProgramCounter,
    fn_name,
    is_active_fn,
    indent=0,
    is_root=False,
):
    """Recursive helper to draw instructions and nested blocks (If, While)."""
    y = start_y
    for i, instr in enumerate(instructions):
        is_pc_here = False

        if is_active_fn:
            # 1. We are in a nested block
            if pc.block_stack:
                active_block_instrs, _ = pc.block_stack[-1]
                if pc.line_idx == i and instructions is active_block_instrs:
                    is_pc_here = True
            # 2. We are in the root function body
            elif is_root:
                if pc.line_idx == i:
                    is_pc_here = True

        color = CURR_LINE if is_pc_here else (TEXT_BRIGHT if is_active_fn else TEXT_DIM)

        # Dim comments or specific instruction types if needed
        desc = instr.description()
        if desc.startswith("//") and not is_pc_here:
            color = TEXT_DIM

        prefix = "▶ " if is_pc_here else "  "
        indent_str = "    " * indent

        ax.text(
            0.4,
            y,
            f"{prefix}{indent_str}{desc}",
            color=color,
            family="monospace",
            fontsize=10,
            style="italic" if desc.startswith("//") else "normal",
            va="center",
        )
        y -= 0.22

        # Handle nested blocks for IfElseBlock
        if isinstance(instr, IfElseBlock):
            # Then block
            y = draw_code_block(
                ax, instr.then_body, y, pc, fn_name, is_active_fn, indent + 1, False
            )

            # Else block
            if instr.else_body:
                ax.text(
                    0.4,
                    y,
                    f"  {indent_str}}} else {{",
                    color=color,
                    family="monospace",
                    fontsize=10,
                    va="center",
                )
                y -= 0.22
                y = draw_code_block(
                    ax, instr.else_body, y, pc, fn_name, is_active_fn, indent + 1, False
                )

            ax.text(
                0.4,
                y,
                f"  {indent_str}}}",
                color=color,
                family="monospace",
                fontsize=10,
                va="center",
            )
            y -= 0.22

        # Handle nested blocks for WhileLoop
        elif isinstance(instr, WhileLoop):
            y = draw_code_block(
                ax, instr.body, y, pc, fn_name, is_active_fn, indent + 1, False
            )
            ax.text(
                0.4,
                y,
                f"  {indent_str}}}",
                color=color,
                family="monospace",
                fontsize=10,
                va="center",
            )
            y -= 0.22

    return y


def render_to_ax(ax, mem: MemoryModel, program: Program, pc: ProgramCounter):
    ax.set_facecolor(BG)
    ax.set_axis_off()

    # --- TITLE ---
    ax.text(
        6.1,
        8.1,
        "MEMORY VISUALIZER (V2)",
        color=TEXT_BRIGHT,
        fontsize=17,
        fontweight="bold",
        ha="center",
        family="monospace",
    )
    ax.text(
        6.1,
        7.9,
        "Press [RIGHT ARROW] to step forward",
        color=TEXT_MID,
        fontsize=8,
        ha="center",
        family="monospace",
    )

    # --- CODE PANEL ---
    cursor_y = 7.5
    fn_list = list(program.functions.keys())

    for fn_name, fdef in program.functions.items():
        is_active_fn = fn_name == pc.fn_name
        is_in_stack = any(f[0] == fn_name for f in pc.ret_stack)

        hdr_col = FRAME_PALETTE[fn_list.index(fn_name) % len(FRAME_PALETTE)]

        # Function Header
        ax.add_patch(mpatches.Rectangle((0.2, cursor_y - 0.3), 5.0, 0.3, color=hdr_col))
        params_str = ", ".join([p[0] for p in fdef.params])
        ax.text(
            0.3,
            cursor_y - 0.2,
            f"fn {fn_name}({params_str}) {{",
            color=BG,
            fontweight="bold",
            family="monospace",
            fontsize=12,
        )

        # RECURSIVE CALL for body
        new_y = draw_code_block(
            ax, fdef.body, cursor_y - 0.5, pc, fn_name, is_active_fn, is_root=True
        )

        # Closing function brace
        ax.text(
            0.3,
            new_y,
            "}",
            color=hdr_col if (is_active_fn or is_in_stack) else TEXT_DIM,
            fontweight="bold",
            family="monospace",
            fontsize=12,
        )

        cursor_y = new_y - 0.6

    # --- MEMORY PANEL ---
    CELL_W, ROW, CELL_H = 2.6, 0.28, 0.22

    def addr_y(a):
        return 7.7 - ((MEM_SIZE - 1) - a) * ROW

    # Sections labels
    ax.text(
        6.8,
        addr_y(STACK_TOP),
        "STACK",
        color=TEXT_MID,
        fontsize=14,
        fontweight="bold",
        rotation=90,
        va="top",
        ha="right",
    )
    ax.text(
        6.8,
        addr_y(HEAP_BOTTOM) - 0.3,
        "HEAP",
        color=HEAP_COL,
        fontsize=14,
        fontweight="bold",
        rotation=90,
        va="bottom",
        ha="right",
    )

    group_lut, next_group_idx = {}, 0
    GROUP_BG_BASE = (1, 1, 1, 0.15)
    GROUP_BG_ALT = (1, 1, 1, 0.35)

    for a in range(MEM_SIZE):
        cy = addr_y(a)
        cell = mem.mem[a]

        # Determine Cell Color
        if getattr(cell, "freed", False):
            fc = FREE_COL
        elif cell.frame_idx >= 0:
            fn_name = mem.call_stack[cell.frame_idx].name

            color = fn_list.index(fn_name)
            if cell.frame_idx % 2 != 0:
                fc = darken_hex_color(FRAME_PALETTE[color % len(FRAME_PALETTE)])
            else:
                fc = FRAME_PALETTE[color % len(FRAME_PALETTE)]
        elif cell.label != "":
            fc = HEAP_COL
        else:
            fc = EMPTY_COL

        # Group Highlighting (Arrays/Vecs)
        if (
            cell.label
            and ("." in cell.label or "[" in cell.label)
            and not getattr(cell, "freed", False)
        ):
            base_name = group_name(cell.label)
            group_key = (cell.frame_idx, base_name)
            if group_key not in group_lut:
                group_lut[group_key] = next_group_idx
                next_group_idx += 1
            bg_col = GROUP_BG_BASE if (group_lut[group_key] % 2 == 0) else GROUP_BG_ALT
            ax.add_patch(
                mpatches.FancyBboxPatch(
                    (7.45, cy - CELL_H / 2 - 0.03),
                    CELL_W + 0.1,
                    CELL_H + 0.06,
                    boxstyle="round,pad=0.04",
                    facecolor=bg_col,
                    edgecolor="none",
                    zorder=0.5,
                )
            )

        # Main Cell Patch
        ax.add_patch(
            mpatches.FancyBboxPatch(
                (7.5, cy - CELL_H / 2),
                CELL_W,
                CELL_H,
                boxstyle="round,pad=0.02",
                facecolor=fc,
                edgecolor=STRIP_EDGE,
                zorder=1,
            )
        )

        # Address Text (Hex)
        ax.text(
            7.3,
            cy - 0.015,
            f"0x{a:02X}",
            color=TEXT_MID,
            ha="right",
            va="center",
            family="monospace",
            fontsize=9,
        )

        # Value Text
        if cell.value is not None:
            v = (
                f"0x{cell.value:02X}"
                if (cell.is_pointer and isinstance(cell.value, int))
                else str(cell.value)
            )
            ax.text(
                7.5 + CELL_W / 2,
                cy,
                v,
                color=TEXT_BRIGHT,
                ha="center",
                va="center",
                fontweight="bold",
                fontsize=10,
                zorder=2,
            )

        # Label Text
        if cell.label:
            ax.text(
                7.5 + CELL_W + 0.2,
                cy,
                cell.label,
                color=TEXT_MID,
                va="center",
                fontsize=9,
            )

        # Pointer Arrows
        if (
            cell.is_pointer
            and isinstance(cell.value, int)
            and 0 <= cell.value < MEM_SIZE
        ):
            ax.add_patch(
                FancyArrowPatch(
                    (7.5 + CELL_W, cy),
                    (7.5 + CELL_W, addr_y(cell.value)),
                    connectionstyle="arc3,rad=-0.5",
                    arrowstyle="-|>",
                    color=PTR_COL,
                    lw=1.5,
                    mutation_scale=10,
                    zorder=5,
                )
            )

    # Boundary Line
    sep_y = (addr_y(STACK_LIMIT) + addr_y(STACK_LIMIT - 1)) / 2
    ax.plot(
        [6.5, 7.5 + CELL_W + 1.2],
        [sep_y, sep_y],
        color="white",
        linestyle="--",
        linewidth=1,
        alpha=0.4,
        zorder=0,
    )
    ax.text(
        6.4,
        sep_y,
        "LIMIT",
        color=TEXT_DIM,
        fontsize=8,
        ha="right",
        va="center",
        family="monospace",
        fontweight="bold",
    )

    # --- STACK FRAMES (RIGHT SIDE BRACKETS) ---
    for fidx, frame in enumerate(mem.call_stack):
        y_hi, y_lo = addr_y(frame.base_addr + frame.size - 1), addr_y(frame.base_addr)
        fn_name = frame.name

        color = fn_list.index(fn_name)
        if fidx % 2 != 0:
            col = darken_hex_color(FRAME_PALETTE[color % len(FRAME_PALETTE)])
        else:
            col = FRAME_PALETTE[color % len(FRAME_PALETTE)]
        ax.plot([11.05, 11.05], [y_lo - 0.05, y_hi + 0.05], color=col, lw=2)
        ax.text(
            11.25,
            (y_hi + y_lo) / 2,
            frame.name,
            color=col,
            fontweight="bold",
            fontsize=11,
            va="center",
        )

    # --- LEGEND ---
    legend_y = -0.1
    legend_items = [
        (HEAP_COL, "Heap Data"),
        (FRAME_PALETTE[0], "Stack Frame"),
        (FREE_COL, "Freed/Dropped"),
        (EMPTY_COL, "Unallocated"),
    ]
    for i, (color, label) in enumerate(legend_items):
        lx = 1.0 + (i * 2.8)
        ax.add_patch(mpatches.Rectangle((lx, legend_y), 0.4, 0.2, color=color))
        ax.text(
            lx + 0.45,
            legend_y + 0.05,
            label,
            color=TEXT_MID,
            fontsize=10,
            family="monospace",
        )

    ax.set_xlim(0, 12.5)
    ax.set_ylim(-0.5, 8.5)
