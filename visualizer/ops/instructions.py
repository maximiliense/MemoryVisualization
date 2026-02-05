from visualizer.architecture import MEM_SIZE

from . import Instruction


class Nop(Instruction):
    def __init__(self, text):
        self.description = f"// {text}"


class Print(Instruction):
    def __init__(self, text):
        self.description = f'println!("{text}");'


class Free(Instruction):
    def __init__(self, ptr, size=1):
        self.ptr, self.description, self.size = ptr, f"drop({ptr});", size

    def execute(self, mem, prog):
        pa = mem.get_addr(self.ptr)
        ha = mem.mem[pa].value
        if isinstance(ha, int):
            for addr in range(ha, ha + self.size):
                mem.mem[addr].freed = True
                mem.mem[addr].value = "FREED"
        mem.mem[pa].value = "null"
        mem.mem[pa].is_pointer = False


class FreeVec(Instruction):
    def __init__(self, name):
        self.name = name
        self.description = f"drop({name}); // Vec"

    def execute(self, mem, prog):
        # 1. Retrieve the metadata from the stack variables created by VecNew
        # These were stored as {name}.ptr and {name}.cap
        p_addr = mem.get_addr(f"{self.name}.ptr")
        c_addr = mem.get_addr(f"{self.name}.cap")

        ptr = mem.mem[p_addr].value
        cap = mem.mem[c_addr].value

        # 2. Mark the entire heap range from ptr to ptr + capacity as freed
        if isinstance(ptr, int) and isinstance(cap, int):
            for addr in range(ptr, ptr + cap):
                if 0 <= addr < len(mem.mem):
                    mem.mem[addr].freed = True
                    mem.mem[addr].value = "FREED"

        # 3. Nullify the stack metadata to prevent use-after-free
        mem.mem[p_addr].value = "null"
        mem.mem[p_addr].is_pointer = False
        mem.mem[mem.get_addr(f"{self.name}.len")].value = 0
        mem.mem[c_addr].value = 0


class StackVar(Instruction):
    def __init__(self, label, typ, value=None, is_pointer=False):
        self.label, self.typ, self.value, self.is_pointer = (
            label,
            typ,
            value,
            is_pointer,
        )
        self.description = f"let {label}: {typ} = {value};"

    def execute(self, mem, prog):
        mem.alloc_stack_var(self.label, self.typ, self.value, self.is_pointer)


class Ref(Instruction):
    def __init__(self, label, target_label):
        self.label, self.target_label = label, target_label
        self.description = f"let {label} = &{target_label};"

    def execute(self, mem, prog):
        try:
            t_addr = mem.get_addr(self.target_label)
        except (ValueError, KeyError):
            try:
                t_addr = mem.get_addr(f"{self.target_label}.cap")
            except (ValueError, KeyError):
                raise ValueError(
                    f"Reference failed: '{self.target_label}' not found on stack."
                )

        # 3. Create the reference pointing to that address
        mem.alloc_stack_var(
            self.label, f"&{self.target_label}", t_addr, is_pointer=True
        )


class AssignDeref(Instruction):
    def __init__(self, stars: str, label, value):
        self.label, self.value, self.nb_deref = label, value, len(stars)
        self.description = f"{stars}{label} = {value};"

    def execute(self, mem, prog):
        nb_deref = self.nb_deref
        p = mem.get_addr(self.label)
        while nb_deref > 0:
            if isinstance(p, int) and 0 <= p < MEM_SIZE:
                p = mem.mem[p].value
            else:
                raise ValueError(
                    f"Error dereferencing: {p} does not contain a valid address."
                )
            nb_deref -= 1
        if isinstance(p, int) and 0 <= p < MEM_SIZE:
            mem.mem[p].value = self.value
        else:
            raise ValueError(
                f"Error dereferencing: {p} does not contain a valid address."
            )


class HeapAlloc(Instruction):
    def __init__(self, label, value):
        self.label, self.value = label, value
        self.description = f"let {label} = Box::new({value});"

    def execute(self, mem, prog):
        ha = mem.alloc_heap("data", "i32")
        mem.mem[ha].value = self.value
        mem.alloc_stack_var(self.label, "Box<i32>", ha, is_pointer=True)


class CallAssign(Instruction):
    def __init__(self, dest, target, args=None, is_vec=False):
        self.dest, self.target, self.args, self.is_vec = (
            dest,
            target,
            args or [],
            is_vec,
        )
        self.description = f"let {dest} = {target}(...);" if dest else f"{target}(...);"

    def execute(self, mem, prog):
        arg_data = [
            (
                mem.mem[mem.get_addr(l)].value,
                mem.mem[mem.get_addr(l)].typ,
                mem.mem[mem.get_addr(l)].is_pointer,
            )
            for l in self.args  # noqa: E741
        ]
        func = prog.functions[self.target]
        size = calc_frame_size(func)
        mem.push_frame(self.target, size, ret_dest=self.dest, ret_is_vec=self.is_vec)
        for name, (val, typ, is_ptr) in zip(func.params, arg_data):
            mem.alloc_stack_var(name, typ, val, is_pointer=is_ptr)


class CallFunction(Instruction):
    def __init__(self, target, args=None, display=""):
        self.target, self.args = target, args or []
        self.description = display or f"{target}({', '.join(self.args)});"

    def execute(self, mem, prog):
        arg_data = []
        for label in self.args:
            try:
                # 1. Try to fetch standard variable metadata
                addr = mem.get_addr(label)
                cell = mem.mem[addr]
                arg_data.append(
                    {
                        "kind": "scalar",
                        "val": cell.value,
                        "typ": cell.typ,
                        "is_ptr": cell.is_pointer,
                    }
                )
            except (ValueError, KeyError):
                # 2. Fallback: Check if it's a Vector (check for .ptr suffix)
                try:
                    p_addr = mem.get_addr(f"{label}.ptr")
                    l_addr = mem.get_addr(f"{label}.len")
                    c_addr = mem.get_addr(f"{label}.cap")

                    arg_data.append(
                        {
                            "kind": "vec",
                            "ptr": mem.mem[p_addr].value,
                            "len": mem.mem[l_addr].value,
                            "cap": mem.mem[c_addr].value,
                        }
                    )
                except (ValueError, KeyError):
                    raise ValueError(
                        f"Function call failed: Argument '{label}' not found on stack."
                    )

        func = prog.functions[self.target]
        size = calc_frame_size(func)
        mem.push_frame(self.target, size)

        # 3. Allocation in the NEW frame
        for param_name, data in zip(func.params, arg_data):
            if data["kind"] == "scalar":
                mem.alloc_stack_var(
                    param_name, data["typ"], data["val"], is_pointer=data["is_ptr"]
                )
            elif data["kind"] == "vec":
                # Reconstruct the Vec metadata in the new frame
                # This mimics Rust's move/copy of the Vec struct (ptr, len, cap)
                mem.alloc_stack_var(
                    f"{param_name}.ptr", "usize", data["ptr"], is_pointer=True
                )
                mem.alloc_stack_var(f"{param_name}.len", "usize", data["len"])
                mem.alloc_stack_var(f"{param_name}.cap", "usize", data["cap"])


class ReturnIfEquals(Instruction):
    def __init__(self, var, val):
        self.var, self.val = var, val
        self.description = f"if {var} == {val} {{ return; }}"

    def test(self, mem, _):
        addr = mem.get_addr(self.var)
        return mem.mem[addr].value == self.val

    def execute(self, mem, prog):
        pass


class Decrement(Instruction):
    def __init__(self, var_name):
        self.var_name = var_name
        self.description = f"{var_name} -= 1;"

    def execute(self, mem, prog):
        addr = mem.get_addr(self.var_name)
        val = mem.mem[addr].value
        if isinstance(val, int):
            mem.mem[addr].value = val - 1


class Increment(Instruction):
    def __init__(self, var_name):
        self.var_name = var_name
        self.description = f"{var_name} += 1;"

    def execute(self, mem, prog):
        addr = mem.get_addr(self.var_name)
        val = mem.mem[addr].value
        if isinstance(val, int):
            mem.mem[addr].value = val + 1


class Add(Instruction):
    def __init__(self, a, b, c):
        self.a, self.b, self.c = a, b, c
        self.description = f"let {a} = {b} + {c};"

    def execute(self, mem, prog):
        addr = mem.get_addr(self.b)
        b = mem.mem[addr]
        addr = mem.get_addr(self.c)
        c = mem.mem[addr]
        if b.typ == c.typ:
            mem.alloc_stack_var(self.a, c.typ, b.value + c.value, False)
        else:
            raise ValueError(f"Error: {b.value} and {c.value} have incompatible types")


class Sub(Instruction):
    def __init__(self, a, b, c):
        self.a, self.b, self.c = a, b, c
        self.description = f"let {a} = {b} - {c};"

    def execute(self, mem, prog):
        addr = mem.get_addr(self.b)
        b = mem.mem[addr]
        addr = mem.get_addr(self.c)
        c = mem.mem[addr]
        if b.typ == c.typ:
            mem.alloc_stack_var(self.a, c.typ, b.value - c.value, False)
        else:
            raise ValueError(f"Error: {b.value} and {c.value} have incompatible types")


class Mul(Instruction):
    def __init__(self, a, b, c):
        self.a, self.b, self.c = a, b, c
        self.description = f"let {a} = {b} * {c};"

    def execute(self, mem, prog):
        addr = mem.get_addr(self.b)
        b = mem.mem[addr]
        addr = mem.get_addr(self.c)
        c = mem.mem[addr]
        if b.typ == c.typ:
            mem.alloc_stack_var(self.a, c.typ, b.value * c.value, False)
        else:
            raise ValueError(f"Error: {b.value} and {c.value} have incompatible types")


class Div(Instruction):
    def __init__(self, a, b, c):
        self.a, self.b, self.c = a, b, c
        self.description = f"let {a} = {b} / {c};"

    def execute(self, mem, prog):
        addr = mem.get_addr(self.b)
        b = mem.mem[addr]
        addr = mem.get_addr(self.c)
        c = mem.mem[addr]
        if b.typ == c.typ:
            mem.alloc_stack_var(self.a, c.typ, b.value / c.value, False)
        else:
            raise ValueError(f"Error: {b.value} and {c.value} have incompatible types")


class ReturnFunction(Instruction):
    def __init__(self, ret_var=None):
        self.ret_var = ret_var
        self.description = f"return {ret_var};}}" if ret_var else "}"

    def execute(self, mem, prog):
        curr_frame = mem.call_stack[-1]
        dest = curr_frame.ret_dest
        if self.ret_var and dest:
            if curr_frame.ret_is_vec:
                p = mem.mem[mem.get_addr(f"{self.ret_var}.ptr")].value
                l = mem.mem[mem.get_addr(f"{self.ret_var}.len")].value  # noqa: E741
                c = mem.mem[mem.get_addr(f"{self.ret_var}.cap")].value
                mem.pop_frame()
                mem.alloc_stack_var(f"{dest}.ptr", "ptr", p, is_pointer=True)
                mem.alloc_stack_var(f"{dest}.len", "usize", l)
                mem.alloc_stack_var(f"{dest}.cap", "usize", c)
            else:
                addr = mem.get_addr(self.ret_var)
                val, typ, is_ptr = (
                    mem.mem[addr].value,
                    mem.mem[addr].typ,
                    mem.mem[addr].is_pointer,
                )
                mem.pop_frame()
                mem.alloc_stack_var(dest, typ, val, is_pointer=is_ptr)
        else:
            mem.pop_frame()


class Clone(Instruction):
    def __init__(self, new_l, src_l):
        self.new_l, self.src_l = new_l, src_l
        self.description = f"let {new_l} = {src_l}.clone();"

    def execute(self, mem, prog):
        # 1. Get the address of the source pointer (e.g., the Box on the stack)
        sa = mem.get_addr(self.src_l)
        ha = mem.mem[sa].value  # This is the address in the Heap

        # 2. Verify 'ha' is a valid integer address before indexing
        if isinstance(ha, int) and 0 <= ha < len(mem.mem):
            # 3. Read the value from the old heap location
            old_value = mem.mem[ha].value

            # 4. Allocate new space on the heap and copy the value
            new_ha = mem.alloc_heap("data", "i32")
            mem.mem[new_ha].value = old_value

            # 5. Create the new pointer on the stack
            mem.alloc_stack_var(self.new_l, "Box<i32>", new_ha, is_pointer=True)
        else:
            raise ValueError(
                f"Clone failed: '{self.src_l}' does not point to a valid memory address."
            )


class StaticArray(Instruction):
    def __init__(self, label, vals):
        self.label, self.vals = label, vals
        self.description = f"let {label}: [i32; {len(vals)}] = {vals};"

    def execute(self, mem, prog):
        mem.alloc_stack_var(self.label, "array", self.vals, span=len(self.vals))


class VecNew(Instruction):
    def __init__(self, name, vals, cap):
        self.name, self.vals, self.cap = name, vals, cap
        self.description = f"let mut {name} = vec!{vals};"

    def execute(self, mem, prog):
        base = mem.alloc_heap(None, "i32", self.cap)
        for i, v in enumerate(self.vals):
            mem.mem[base + i].value = v
            mem.mem[base + i].label = f"{self.name}[{i}]"
        mem.alloc_stack_var(f"{self.name}.ptr", "ptr", base, is_pointer=True)
        mem.alloc_stack_var(f"{self.name}.len", "usize", len(self.vals))
        mem.alloc_stack_var(f"{self.name}.cap", "usize", self.cap)


class VecPush(Instruction):
    def __init__(self, name, val):
        self.name, self.val = name, val
        self.description = f"{name}.push({val});"

    def execute(self, mem, prog):
        # 1. Get addresses of the metadata on the stack
        p_addr = mem.get_addr(f"{self.name}.ptr")
        l_addr = mem.get_addr(f"{self.name}.len")
        c_addr = mem.get_addr(f"{self.name}.cap")
        push_vec(p_addr, c_addr, l_addr, mem, self.val)


class VecPushDeref(Instruction):
    def __init__(self, stars, ptr_name, val):
        self.ptr_name, self.val, self.nb_deref = ptr_name, val, len(stars)
        self.description = f"({stars}{ptr_name}).push({val});"

    def execute(self, mem, prog):
        nb_deref = self.nb_deref
        p = mem.get_addr(self.ptr_name)
        while nb_deref > 0:
            if isinstance(p, int) and 0 <= p < MEM_SIZE:
                p = mem.mem[p].value
            else:
                raise ValueError(
                    f"Error dereferencing: {p} does not contain a valid address."
                )
            nb_deref -= 1
        if isinstance(p, int) and 0 <= p < MEM_SIZE:
            p_addr = p + 2
            l_addr = p + 1
            c_addr = p

            push_vec(p_addr, c_addr, l_addr, mem, self.val)
        else:
            raise ValueError(
                f"Error dereferencing: {p} does not contain a valid address."
            )


def push_vec(p_addr, c_addr, l_addr, mem, val):
    ptr = mem.mem[p_addr].value
    length = mem.mem[l_addr].value
    cap = mem.mem[c_addr].value

    if not (isinstance(ptr, int) and isinstance(length, int) and isinstance(cap, int)):
        raise ValueError(f"VecPushDeref failed: metadata at {c_addr} is corrupted.")

    # 4. Reallocation logic (Same as VecPush)
    if length >= cap:
        new_cap = cap * 2

        addr = mem.alloc_heap(None, "i32", new_cap)

        for i in range(length):
            old_cell_idx = ptr + i
            old_val = mem.mem[old_cell_idx].value
            mem.mem[old_cell_idx].freed = True
            mem.mem[old_cell_idx].value = "FREED"
            mem.mem[addr + i].value = old_val
            mem.mem[addr + i].label = f"deref_vec[{i}]"

        for i in range(length, new_cap):
            mem.mem[addr + i].label = f"deref_vec[{i}]"
            mem.mem[addr + i].value = None

        mem.mem[p_addr].value = addr
        mem.mem[c_addr].value = new_cap
        ptr = addr

    # 5. Final insertion
    mem.mem[ptr + length].value = val
    mem.mem[l_addr].value = length + 1


def calc_frame_size(func):
    size = func.size
    for i in func.body:
        if isinstance(i, (StackVar, HeapAlloc, Ref, Clone, Add)):
            size += 1
        elif isinstance(i, StaticArray):
            size += len(i.vals)
        elif isinstance(i, VecNew):
            size += 3
        elif isinstance(i, CallAssign) and i.dest:
            size += 3 if i.is_vec else 1
    return max(size, 1)
