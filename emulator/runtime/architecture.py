# ═══════════════════════════════════════════════════════════
#  CONSTANTS & THEME
# ═══════════════════════════════════════════════════════════
from dataclasses import dataclass, field

from emulator.core.base import ExecutionContext

MEM_SIZE = 26
STACK_TOP = MEM_SIZE - 1
HEAP_BOTTOM = 1
STACK_LIMIT = 12


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
    contexts: dict[int, ExecutionContext] = field(default_factory=dict)
    ret_dest: str | None = None
    ret_type: str | None = None
    ret_size: int | None = None
    ret_alloc_new: bool = False


class MemoryModel:
    def __init__(self):
        self.mem: list[MemCell] = [MemCell() for _ in range(MEM_SIZE)]
        self.call_stack: list[StackFrame] = []
        self._sp = STACK_TOP + 1

    def push_frame(
        self,
        name: str,
        size: int,
        ret_dest=None,
        ret_type=None,
        ret_size=None,
        ret_alloc_new=False,
    ):
        new_sp = self._sp - size
        if new_sp < STACK_LIMIT:
            raise MemoryError("Stack Overflow")
        idx = len(self.call_stack)
        frame = StackFrame(
            name=name,
            base_addr=new_sp,
            size=size,
            ret_dest=ret_dest,
            ret_type=ret_type,
            ret_size=ret_size,
            ret_alloc_new=ret_alloc_new,
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

    def alloc_heap(self, label, typ, size=1) -> int:
        addr = HEAP_BOTTOM
        while not self._has_enough_space(addr, size):
            addr += 1
            if addr >= STACK_LIMIT:
                raise MemoryError("Heap Overflow")
        for a in range(addr, addr + size):
            self.mem[a] = MemCell(value=None, label=label, typ=typ, frame_idx=-1)
        return addr

    def _has_enough_space(self, addr, size) -> bool:
        i = 0
        if addr + size > STACK_LIMIT:
            return False

        while i < size:
            if self.mem[addr + i].value is not None and not self.mem[addr + i].freed:
                return False
            i += 1
        return True

    def get_addr(self, label) -> int:
        for f in reversed(self.call_stack):
            if label in f.vars_map:
                return f.vars_map[label]
        for a, c in enumerate(self.mem):
            if c.label == label and c.frame_idx == -1:
                return a
        raise KeyError(f"Variable '{label}' not found.")
