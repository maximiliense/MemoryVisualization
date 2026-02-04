# ═══════════════════════════════════════════════════════════
#  CONSTANTS & THEME
# ═══════════════════════════════════════════════════════════
from dataclasses import dataclass, field

MEM_SIZE = 24
STACK_TOP = MEM_SIZE - 1
HEAP_BOTTOM = 1
STACK_LIMIT = 12

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

# ═══════════════════════════════════════════════════════════
#  MODELS
# ═══════════════════════════════════════════════════════════


@dataclass
class MemCell:
    value: object = None
    label: str = ""
    typ: str = ""
    freed: bool = False
    is_pointer: bool = False
    frame_idx: int = -1


@dataclass
class StackFrame:
    name: str
    base_addr: int
    size: int
    vars_map: dict[str, int] = field(default_factory=dict)
    slots_allocated: int = 0
    ret_dest: str | None = None
    ret_is_vec: bool = False


class MemoryModel:
    def __init__(self):
        self.mem: list[MemCell] = [MemCell() for _ in range(MEM_SIZE)]
        self.call_stack: list[StackFrame] = []
        self._sp = STACK_TOP + 1
        self._hp = HEAP_BOTTOM

    def push_frame(self, name: str, size: int, ret_dest=None, ret_is_vec=False):
        new_sp = self._sp - size
        if new_sp < STACK_LIMIT:
            raise MemoryError("Stack Overflow")
        idx = len(self.call_stack)
        frame = StackFrame(
            name=name,
            base_addr=new_sp,
            size=size,
            ret_dest=ret_dest,
            ret_is_vec=ret_is_vec,
        )
        self.call_stack.append(frame)
        self._sp = new_sp
        for addr in range(frame.base_addr, frame.base_addr + size):
            self.mem[addr] = MemCell(frame_idx=idx)

    def pop_frame(self):
        if not self.call_stack:
            return
        frame = self.call_stack.pop()
        for addr in range(frame.base_addr, frame.base_addr + frame.size):
            self.mem[addr] = MemCell()
        self._sp += frame.size

    def alloc_stack_var(self, label, typ, value=None, is_pointer=False, span=1):
        frame = self.call_stack[-1]
        addr = (frame.base_addr + frame.size - span) - frame.slots_allocated
        for i in range(span):
            curr_addr = addr + i
            slot_label = f"{label}[{i}]" if span > 1 else label
            val = value[i] if (isinstance(value, list) and i < len(value)) else value
            self.mem[curr_addr] = MemCell(
                val,
                slot_label,
                typ,
                False,
                is_pointer,
                frame_idx=len(self.call_stack) - 1,
            )
            if i == 0:
                frame.vars_map[label] = addr
        frame.slots_allocated += span
        return addr

    def alloc_heap(self, label, typ, value) -> int:
        addr = self._hp
        if addr >= STACK_LIMIT:
            raise MemoryError("Heap Overflow")
        self._hp += 1
        self.mem[addr] = MemCell(value=value, label=label, typ=typ, frame_idx=-1)
        return addr

    def get_addr(self, label) -> int:
        for f in reversed(self.call_stack):
            if label in f.vars_map:
                return f.vars_map[label]
        for a, c in enumerate(self.mem):
            if c.label == label and c.frame_idx == -1:
                return a
        raise KeyError(f"Variable '{label}' not found.")
