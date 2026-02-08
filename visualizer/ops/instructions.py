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


class LetVar(Instruction):
    def __init__(self, label, typ, value=None, is_pointer=False):
        self.label, self.typ, self.value, self.is_pointer = (
            label,
            typ,
            value,
            is_pointer,
        )

        if not typ.startswith("Option") and value is None:
            self.description = f"let {label}: {typ};"
        else:
            self.description = f"let {label}: {typ} = {value};"

    def execute(self, mem, prog):
        print(self.value)
        mem.alloc_stack_var(self.label, self.typ, self.value, self.is_pointer)


class Random(Instruction):
    def __init__(self, label, min, max):
        self.label, self.min, self.max = label, min, max
        self.description = f"let {label} = rand_int({min}, {max});"

    def execute(self, mem, prog):
        import random

        r = random.randint(self.min, self.max)
        mem.alloc_stack_var(self.label, "i32", r, False)


class StackVarFromVar(Instruction):
    def __init__(self, label, var):
        self.label, self.var = (label, var)
        self.description = f"let {label} = {var};"

    def execute(self, mem, prog):
        t_addr = mem.get_addr(self.var)
        var = mem.mem[t_addr]
        mem.alloc_stack_var(self.label, var.typ, var.value, var.is_pointer)


class AssignVar(Instruction):
    def __init__(self, label, var):
        self.label, self.var = (label, var)
        self.description = f"{label} = {var};"

    def execute(self, mem, prog):
        t_addr = mem.get_addr(self.var)
        v2 = mem.mem[t_addr]
        t_addr = mem.get_addr(self.label)
        v1 = mem.mem[t_addr]
        v1.value = v2.value
        v1.typ = v2.typ
        v1.is_pointer = v2.is_pointer


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


class CallFunction(Instruction):
    """
    Unified function call instruction.

    Args can be:
    - str: simple scalar variable
    - tuple (name, "Vec"): vector variable (3 slots)
    - tuple (name, size): array variable (size slots)

    Return can be:
    - None: no return value
    - str: scalar return variable
    - tuple (name, "Vec"): vector return variable
    - tuple (name, size): array return variable
    """

    def __init__(self, target, args=None, ret=None, display=""):
        self.target = target
        self.args = args or []
        self.ret = ret

        # Build description
        if display:
            self.description = display
        else:
            arg_str = ", ".join(self._arg_name(a) for a in self.args)
            if ret:
                ret_name = self._arg_name(ret)
                self.description = f"let {ret_name} = {target}({arg_str});"
            else:
                self.description = f"{target}({arg_str});"

    @staticmethod
    def _arg_name(arg):
        """Extract display name from arg specification."""
        if isinstance(arg, tuple):
            return arg[0]
        return arg

    def param_size(self):
        """Calculate total stack slots needed for parameters."""
        total = 0
        for arg in self.args:
            if isinstance(arg, tuple):
                _, spec = arg
                if spec == "Vec":
                    total += 3
                else:
                    total += spec  # array size
            else:
                total += 1  # scalar
        return total

    def ret_size(self):
        """Calculate stack slots needed for return value."""
        if not self.ret:
            return 0
        if isinstance(self.ret, tuple):
            _, spec = self.ret
            if spec == "Vec":
                return 3
            else:
                return spec  # array size
        return 1  # scalar

    def execute(self, mem, prog):
        # 1. Collect argument data
        arg_data = []
        for arg in self.args:
            if isinstance(arg, tuple):
                name, spec = arg
                if spec == "Vec":
                    # Vector argument
                    p_addr = mem.get_addr(f"{name}.ptr")
                    l_addr = mem.get_addr(f"{name}.len")
                    c_addr = mem.get_addr(f"{name}.cap")
                    arg_data.append(
                        {
                            "kind": "vec",
                            "ptr": mem.mem[p_addr].value,
                            "len": mem.mem[l_addr].value,
                            "cap": mem.mem[c_addr].value,
                        }
                    )
                else:
                    # Array argument
                    base_addr = mem.get_addr(name)
                    values = [mem.mem[base_addr + i].value for i in range(spec)]
                    arg_data.append(
                        {
                            "kind": "array",
                            "values": values,
                            "size": spec,
                        }
                    )
            else:
                # Scalar argument
                addr = mem.get_addr(arg)
                cell = mem.mem[addr]
                arg_data.append(
                    {
                        "kind": "scalar",
                        "val": cell.value,
                        "typ": cell.typ,
                        "is_ptr": cell.is_pointer,
                    }
                )

        # 2. Push new frame with return info
        func = prog.functions[self.target]
        size = calc_frame_size(func)

        ret_dest = None
        ret_type = None
        ret_size = 1
        if self.ret:
            if isinstance(self.ret, tuple):
                ret_dest = self.ret[0]
                if self.ret[1] == "Vec":
                    ret_type = "vec"
                    ret_size = 3
                else:
                    ret_type = "array"
                    ret_size = self.ret[1]
            else:
                ret_dest = self.ret
                ret_type = "scalar"

        mem.push_frame(
            self.target, size, ret_dest=ret_dest, ret_type=ret_type, ret_size=ret_size
        )

        # 3. Allocate parameters in the new frame
        for (param_name, _), data in zip(func.params, arg_data):
            if data["kind"] == "scalar":
                mem.alloc_stack_var(
                    param_name, data["typ"], data["val"], is_pointer=data["is_ptr"]
                )
            elif data["kind"] == "vec":
                mem.alloc_stack_var(
                    f"{param_name}.ptr", "usize", data["ptr"], is_pointer=True
                )
                mem.alloc_stack_var(f"{param_name}.len", "usize", data["len"])
                mem.alloc_stack_var(f"{param_name}.cap", "usize", data["cap"])
            elif data["kind"] == "array":
                mem.alloc_stack_var(
                    param_name, "array", data["values"], span=data["size"]
                )


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


class Set(Instruction):
    def __init__(self, var_name, value):
        self.var_name, self.value = var_name, value
        self.description = f"{var_name} = {value};"

    def execute(self, mem, prog):
        addr = mem.get_addr(self.var_name)
        mem.mem[addr].value = self.value


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


class AddAssign(Instruction):
    def __init__(self, a, b, c):
        self.a, self.b, self.c = a, b, c
        self.description = f"{a} = {b} + {c};"

    def execute(self, mem, prog):
        addr = mem.get_addr(self.b)
        b = mem.mem[addr]
        addr = mem.get_addr(self.c)
        c = mem.mem[addr]
        addr = mem.get_addr(self.a)
        a = mem.mem[addr]
        if b.typ == c.typ:
            a.value = b.value + c.value
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
        self.description = f"return {ret_var};" if ret_var else "return;"

    def execute(self, mem, prog):
        curr_frame = mem.call_stack[-1]
        dest = curr_frame.ret_dest
        ret_type = curr_frame.ret_type

        if self.ret_var and dest:
            if ret_type == "vec":
                # Vector return
                p = mem.mem[mem.get_addr(f"{self.ret_var}.ptr")].value
                l = mem.mem[mem.get_addr(f"{self.ret_var}.len")].value  # noqa: E741
                c = mem.mem[mem.get_addr(f"{self.ret_var}.cap")].value
                mem.pop_frame()
                mem.alloc_stack_var(f"{dest}.ptr", "ptr", p, is_pointer=True)
                mem.alloc_stack_var(f"{dest}.len", "usize", l)
                mem.alloc_stack_var(f"{dest}.cap", "usize", c)
            elif ret_type == "array":
                # Array return
                base_addr = mem.get_addr(self.ret_var)
                values = [
                    mem.mem[base_addr + i].value for i in range(curr_frame.ret_size)
                ]
                mem.pop_frame()
                mem.alloc_stack_var(dest, "array", values, span=curr_frame.ret_size)
            else:
                # Scalar return
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


class DerefSetArray(Instruction):
    def __init__(self, label, idx, val, stars=""):
        self.label, self.idx, self.val, self.nb_deref = label, idx, val, len(stars)
        if self.nb_deref > 0:
            self.description = f"({stars}{label})[{idx}] = {val}"
        else:
            self.description = f"{label}[{idx}] = {val}"

    def execute(self, mem, prog):
        nb_deref = self.nb_deref
        addr = mem.get_addr(self.label)
        while nb_deref > 0:
            cell = mem.mem[addr]
            addr = cell.value
            nb_deref -= 1

        mem.mem[addr + self.idx].value = self.val


class DerefSetVec(Instruction):
    def __init__(self, label, idx, val, stars=""):
        self.label, self.idx, self.val, self.nb_deref = label, idx, val, len(stars)
        if self.nb_deref > 0:
            self.description = f"({stars}{label})[{idx}] = {val}"
        else:
            self.description = f"{label}[{idx}] = {val}"

    def execute(self, mem, prog):
        nb_deref = self.nb_deref
        if nb_deref == 0:
            addr = mem.get_addr(self.label + ".ptr")
            addr = mem.mem[addr].value
        else:
            addr = mem.get_addr(self.label)
            while nb_deref > 0:
                addr = mem.mem[addr].value
                nb_deref -= 1
            addr = mem.mem[addr + 2].value

        mem.mem[addr + self.idx].value = self.val


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
        push_vec(p_addr, c_addr, l_addr, mem, self.val, self.name)


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

            push_vec(p_addr, c_addr, l_addr, mem, self.val, self.ptr_name)
        else:
            raise ValueError(
                f"Error dereferencing: {p} does not contain a valid address."
            )


class IfElse(Instruction):
    def __init__(
        self, var_name, value, then_body, else_body=None, display="", equals=True
    ):
        self.var_name = var_name
        self.value = value
        self.then_body = then_body
        self.equals = equals
        self.else_body = else_body or None
        # Display shown in the code panel
        op = "==" if equals else "!="
        self.description = display or f"if {var_name} {op} {value} {{"

    def execute(self, mem, prog):
        addr = mem.get_addr(self.var_name)
        if self.equals:
            condition_met = mem.mem[addr].value == self.value
        else:
            condition_met = mem.mem[addr].value != self.value
        return self.then_body if condition_met else self.else_body


def push_vec(p_addr, c_addr, l_addr, mem, val, name):
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
            mem.mem[addr + i].label = f"{name}[{i}]"

        for i in range(length, new_cap):
            mem.mem[addr + i].label = f"{name}[{i}]"
            mem.mem[addr + i].value = None

        mem.mem[p_addr].value = addr
        mem.mem[c_addr].value = new_cap
        ptr = addr

    # 5. Final insertion
    mem.mem[ptr + length].value = val
    mem.mem[l_addr].value = length + 1


def calc_frame_size(func):
    # param's size
    size = func.size
    return max(body_size(func.body) + size, 1)


def body_size(body):
    size = 0
    for i in body:
        if isinstance(
            i,
            (
                LetVar,
                StackVarFromVar,
                Random,
                HeapAlloc,
                Ref,
                Clone,
                Add,
                Sub,
                Mul,
                Div,
            ),
        ):
            size += 1
        elif isinstance(i, StaticArray):
            size += len(i.vals)
        elif isinstance(i, VecNew):
            size += 3
        elif isinstance(i, CallFunction):
            size += i.ret_size()
        elif isinstance(i, IfElse):
            if_size = body_size(i.then_body)
            else_size = body_size(i.else_body) if i.else_body else 0
            size += max(if_size, else_size)
    return size
