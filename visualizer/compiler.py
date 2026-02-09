"""
Rust-like Language Compiler for Memory Visualizer

Parses Rust-like syntax into Program/FunctionDef/Instruction structures.

Supported syntax:
- let x: i32 = 5;
- let mut v = vec![1, 2, 3];
- let arr: [i32; 5] = [10, 20, 30, 40, 50];
- let p = Box::new(100);
- let r = &x;
- *ptr = 42;
- x += 1; / x -= 1;
- drop(p);
- func(arg1, arg2);
- let result = func(arg1);
- if x == 5 { ... } else { ... }
- return; / return x;
- v.push(10);
- (*ptr).push(10);
"""

import re
from typing import Dict, List, Tuple

from visualizer.ops.instructions import (
    Add,
    AddAssign,
    AssignDeref,
    AssignVar,
    CallFunction,
    Clone,
    Decrement,
    DerefSetArray,
    Div,
    Free,
    FreeVec,
    HeapAlloc,
    IfElse,
    Increment,
    LetVar,
    Mul,
    Nop,
    Print,
    Random,
    Ref,
    ReturnFunction,
    StackVarFromVar,
    StaticArray,
    Sub,
    VecNew,
    VecPush,
    VecPushDeref,
)
from visualizer.program import FunctionDef, Program


class RustCompiler:
    def __init__(self):
        self.functions: Dict[str, FunctionDef] = {}

    def compile(self, source: str) -> Program:
        """Compile Rust-like source code into a Program."""
        self.functions = {}

        # Find all function definitions by parsing character by character
        i = 0
        while i < len(source):
            # Skip whitespace and comments
            while i < len(source) and source[i].isspace():
                i += 1

            if i >= len(source):
                break

            # Skip line comments
            if source[i : i + 2] == "//":
                while i < len(source) and source[i] != "\n":
                    i += 1
                continue

            # Check for function definition
            if source[i : i + 2] == "fn":
                # fn_start = i
                i += 2

                # Skip whitespace
                while i < len(source) and source[i].isspace():
                    i += 1

                # Get function name
                name_start = i
                while i < len(source) and (source[i].isalnum() or source[i] == "_"):
                    i += 1
                fn_name = source[name_start:i]

                # Skip whitespace
                while i < len(source) and source[i].isspace():
                    i += 1

                # Parse parameters
                params = []

                if i < len(source) and source[i] == "(":
                    i += 1
                    param_start = i
                    depth = 1
                    while i < len(source) and depth > 0:
                        if source[i] == "(":
                            depth += 1
                        elif source[i] == ")":
                            depth -= 1
                        i += 1
                    params_str = source[param_start : i - 1].strip()

                    # Parse parameter names
                    params = []
                    if params_str:
                        for param in params_str.split(","):
                            param = param.strip()
                            if not param:
                                continue

                            name, _, param_type = param.partition(":")
                            params.append((name.strip(), param_type.strip() or None))

                # Skip whitespace
                while i < len(source) and source[i].isspace():
                    i += 1

                # Parse body
                if i < len(source) and source[i] == "{":
                    i += 1
                    body_start = i
                    depth = 1
                    while i < len(source) and depth > 0:
                        if source[i] == "{":
                            depth += 1
                        elif source[i] == "}":
                            depth -= 1
                        i += 1
                    body_str = source[body_start : i - 1]

                    # Parse the body
                    body = self._parse_body(body_str)
                    self.functions[fn_name] = FunctionDef(params=params, body=body)
            else:
                i += 1

        return Program(self.functions)

    def _parse_body(self, body_str: str) -> List:
        """Parse function body into list of instructions."""
        instructions = []

        # Remove leading/trailing whitespace and split by statements
        body_str = body_str.strip()
        f_params = {}

        i = 0
        while i < len(body_str):
            # Skip whitespace
            while i < len(body_str) and body_str[i].isspace():
                i += 1

            if i >= len(body_str):
                break

            # Check for comment
            if body_str[i : i + 2] == "//":
                end = body_str.find("\n", i)
                if end == -1:
                    end = len(body_str)
                comment = body_str[i + 2 : end].strip()
                instructions.append(Nop(comment))
                i = end + 1
                continue

            # Check for if-else block
            if body_str[i:].startswith("if "):
                instr, new_i = self._parse_if_else(body_str, i)
                instructions.append(instr)
                i = new_i
                continue

            # Find next semicolon or brace
            stmt_end = self._find_statement_end(body_str, i)
            stmt = body_str[i:stmt_end].strip()

            if stmt:
                instr = self._parse_statement(stmt, f_params)
                if instr:
                    instructions.append(instr)

            i = stmt_end + 1

        return instructions

    def _find_statement_end(self, text: str, start: int) -> int:
        """Find the end of a statement (semicolon or closing brace)."""
        i = start
        depth = 0
        in_string = False

        while i < len(text):
            c = text[i]

            if c == '"' and (i == 0 or text[i - 1] != "\\"):
                in_string = not in_string
            elif not in_string:
                if c in "{[(":
                    depth += 1
                elif c in "}])":
                    depth -= 1
                elif c == ";" and depth == 0:
                    return i

            i += 1

        return len(text)

    def _parse_if_else(self, text: str, start: int) -> Tuple[IfElse, int]:
        """Parse if-else block."""
        # Pattern: if VAR == VALUE { ... } else { ... }
        match = re.match(r"if\s+(\w+)\s*(==|!=)\s*(\d+)\s*\{", text[start:])
        if not match:
            raise SyntaxError(f"Invalid if statement at position {start}")

        var_name = match.group(1)
        op = match.group(2)
        value = int(match.group(3))

        is_equals = op == "=="  # True if ==, False if !=

        # Find the then block
        brace_start = start + match.end() - 1  # Position of opening {
        then_end = self._find_matching_brace(text, brace_start)
        then_body_str = text[brace_start + 1 : then_end]
        then_body = self._parse_body(then_body_str)

        # Check for else
        else_body = []
        i = then_end + 1
        while i < len(text) and text[i].isspace():
            i += 1

        if i < len(text) and text[i : i + 4] == "else":
            i += 4
            while i < len(text) and text[i].isspace():
                i += 1

            if i < len(text) and text[i] == "{":
                else_end = self._find_matching_brace(text, i)
                else_body_str = text[i + 1 : else_end]
                else_body = self._parse_body(else_body_str)
                i = else_end + 1

        return IfElse(
            var_name,
            value,
            then_body,
            else_body if else_body else None,
            equals=is_equals,
        ), i

    def _find_matching_brace(self, text: str, start: int) -> int:
        """Find matching closing brace."""
        depth = 1
        i = start + 1

        while i < len(text) and depth > 0:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1

        return i - 1

    def _parse_statement(self, stmt: str, f_params: dict):
        """Parse a single statement."""
        stmt = stmt.strip()

        if not stmt:
            return None

        # Return statement
        if stmt.startswith("return"):
            match = re.match(r"return\s*(\w*)\s*$", stmt)
            if match:
                ret_var = match.group(1) if match.group(1) else None
                return ReturnFunction(ret_var)
            return ReturnFunction()

        # println! macro
        if stmt.startswith("println!"):
            match = re.match(r'println!\("([^"]*)"\)$', stmt)
            if match:
                return Print(match.group(1))

        # Vec push
        match = re.match(r"(\w+)\.push\(([^)]+)\)$", stmt)
        if match:
            vec_name = match.group(1)
            value = self._parse_value(match.group(2))
            return VecPush(vec_name, value)

        # Deref Vec push: (*ptr).push(value)
        match = re.match(r"\((\*+)(\w+)\)\.push\(([^)]+)\)$", stmt)
        if match:
            stars = match.group(1)
            ptr_name = match.group(2)
            value = self._parse_value(match.group(3))
            return VecPushDeref(stars, ptr_name, value)

        match = re.match(r"drop\((\w+)\)$", stmt)
        if match:
            var_name = match.group(1)
            if var_name in f_params:
                return FreeVec(var_name)
            return Free(var_name)

        # Array index assignment: arr[12] = val or (*arr)[12] = val
        match = re.match(r"\((\*+)(\w+)\)\[(\d+)\]\s*=\s*(.+)$", stmt)
        if match:
            stars = len(match.group(1))
            array_name = match.group(2)
            idx = int(match.group(3))
            value = self._parse_value(match.group(4))
            return DerefSetArray(array_name, idx, value, "*" * stars)

        match = re.match(r"(\w+)\[(\d+)\]\s*=\s*(.+)$", stmt)
        if match:
            array_name = match.group(1)
            idx = int(match.group(2))
            value = self._parse_value(match.group(3))
            return DerefSetArray(array_name, idx, value)

        # Increment/Decrement
        match = re.match(r"(\w+)\s*\+=\s*1$", stmt)
        if match:
            return Increment(match.group(1))

        match = re.match(r"(\w+)\s*-=\s*1$", stmt)
        if match:
            return Decrement(match.group(1))

        match = re.match(r"(\w+)\s*=\s*(\w+)\s*([+\-*/])\s*(\w+)$", stmt)
        if match:
            dest = match.group(1)
            left = match.group(2)
            op = match.group(3)
            right = match.group(4)
            if op == "+":
                return AddAssign(dest, left, right)

        # x = var
        match = re.match(r"^(\w+)\s*=\s*([A-Za-z_][A-Za-z0-9_]*)", stmt)
        if match:
            label = match.group(1)
            var_name = match.group(2)
            return AssignVar(label, var_name)
        # Dereference assignment: *ptr = value or ***ptr = value
        match = re.match(r"^(\**)(\w+)\s*=\s*(.+)$", stmt)
        if match:
            stars = match.group(1)
            var_name = match.group(2)
            value = self._parse_value(match.group(3))
            return AssignDeref(stars, var_name, value)

        ###################################################
        # Function call with full type parsing
        # Step 1: Check if it's a let statement or just a call
        #
        let_match = re.match(
            r"let\s+(\w+)\s*(?::\s*(.+?))?\s*=\s*(\w+)\(([^)]*)\)$", stmt
        )
        call_match = re.match(r"(\w+)\(([^)]*)\)$", stmt) if not let_match else None

        if let_match or call_match:
            if let_match:
                ret_var = let_match.group(1)
                ret_type_str = let_match.group(2)  # Could be None
                func_name = let_match.group(3)
                args_str = let_match.group(4).strip()

                # Parse return type
                if ret_type_str:
                    if "Vec" in ret_type_str:
                        ret = (ret_var, "Vec")
                        f_params[ret_var] = "Vec"
                    elif ret_type_str.startswith("["):
                        # Parse [i32; N]
                        array_match = re.match(r"\[.+;\s*(\d+)\]", ret_type_str)
                        if array_match:
                            size = int(array_match.group(1))
                            ret = (ret_var, size)
                            f_params[ret_var] = size
                        else:
                            ret = ret_var
                    else:
                        # Scalar type (i32, u32, etc.)
                        ret = ret_var
                else:
                    # No type annotation, assume scalar
                    ret = ret_var
            else:
                # No let, just a call
                func_name = call_match.group(1)  # type: ignore
                args_str = call_match.group(2).strip()  # type: ignore
                ret = None

            # Step 2: Parse arguments
            args = []
            if args_str:
                for arg_decl in args_str.split(","):
                    arg_decl = arg_decl.strip()
                    if arg_decl in f_params:
                        args.append((arg_decl, f_params[arg_decl]))
                    else:
                        args.append(arg_decl)
            new_args = []
            for a in args:
                if isinstance(a, tuple):
                    # print(a)
                    a = (self._parse_value(a[0]), a[1])
                else:
                    a = self._parse_value(a)
                new_args.append(a)

            # args = [arg[0] for arg in args]
            if func_name == "rand_int":
                # builtin
                # print(str(ret), *new_args)
                return Random(str(ret), *new_args)
            return CallFunction(func_name, args=new_args, ret=ret)

        # # Function call (possibly with assignment)
        # # Vec return: let v: Vec<i32> = func();
        # func_call_match = re.match(
        #     r"let\s+(\w+)\s*:\s*Vec<[^>]*>\s*=\s*(\w+)\(([^)]*)\)$", stmt
        # )
        # if func_call_match:
        #     ret_var = func_call_match.group(1)
        #     func_name = func_call_match.group(2)
        #     args_str = func_call_match.group(3).strip()

        #     args = []
        #     if args_str:
        #         for arg in args_str.split(","):
        #             arg = arg.strip()
        #             if arg in f_params:
        #                 args.append((arg, f_params[arg]))
        #             else:
        #                 args.append(arg)

        #         f_params[ret_var] = "Vec"
        #         return CallFunction(func_name, args=args, ret=(ret_var, "Vec"))

        #     f_params[ret_var] = "Vec"
        #     return CallFunction(func_name, args=args, ret=(ret_var, "Vec"))

        # # Array return: let arr: [i32; 5] = func();
        # func_call_match = re.match(
        #     r"let\s+(\w+)\s*:\s*\[[^\]]+;\s*(\d+)\]\s*=\s*(\w+)\(([^)]*)\)$", stmt
        # )
        # if func_call_match:
        #     ret_var = func_call_match.group(1)
        #     array_size = int(func_call_match.group(2))
        #     func_name = func_call_match.group(3)
        #     args_str = func_call_match.group(4).strip()
        #     args = []
        #     if args_str:
        #         for arg in args_str.split(","):
        #             arg = arg.strip()
        #             if arg in f_params:
        #                 args.append((arg, f_params[arg]))
        #             else:
        #                 args.append(arg)
        #     return CallFunction(func_name, args=args, ret=(ret_var, array_size))

        # func_call_match = re.match(r"(?:let\s+(\w+)\s*=\s*)?(\w+)\(([^)]*)\)$", stmt)
        # if func_call_match:
        #     ret_var = func_call_match.group(1)
        #     func_name = func_call_match.group(2)
        #     args_str = func_call_match.group(3).strip()
        #     args = []
        #     if args_str:
        #         for arg in args_str.split(","):
        #             arg = arg.strip()
        #             if arg in f_params:
        #                 args.append((arg, f_params[arg]))
        #             else:
        #                 args.append(arg)

        #     return CallFunction(func_name, args=args, ret=ret_var)

        #####################################@
        # Let statement
        if stmt.startswith("let "):
            return self._parse_let(stmt, f_params)

        print("Stmt unrecognized:", stmt)
        return None

    def _parse_let(self, stmt: str, f_params: dict):
        """Parse let statement."""
        # let mut v = vec![1, 2, 3]
        vec_match = re.match(r"let\s+(?:mut\s+)?(\w+)\s*=\s*vec!\[([^\]]*)\]$", stmt)
        if vec_match:
            var_name = vec_match.group(1)
            f_params[var_name] = "Vec"
            values_str = vec_match.group(2)
            values = [
                self._parse_value(v.strip()) for v in values_str.split(",") if v.strip()
            ]
            cap = len(values) if values else 1
            return VecNew(var_name, values, cap)

        # let arr: [i32; N] = [values]
        array_match = re.match(
            r"let\s+(\w+)\s*:\s*\[([^\]]+);\s*\d+\]\s*=\s*\[([^\]]*)\]$", stmt
        )
        if array_match:
            var_name = array_match.group(1)
            values_str = array_match.group(3)
            values = [
                self._parse_value(v.strip()) for v in values_str.split(",") if v.strip()
            ]
            f_params[var_name] = len(values)
            return StaticArray(var_name, values)

        # let p = Box::new(value)
        box_match = re.match(r"let\s+(\w+)\s*=\s*Box::new\(([^)]+)\)$", stmt)
        if box_match:
            var_name = box_match.group(1)
            value = self._parse_value(box_match.group(2))
            return HeapAlloc(var_name, value)

        # let r = &x
        ref_match = re.match(r"let\s+(\w+)\s*=\s*&(\w+(?:\.\w+)?)$", stmt)
        if ref_match:
            var_name = ref_match.group(1)
            target = ref_match.group(2)
            return Ref(var_name, target)

        # let r = b.clone();
        clone_match = re.match(r"let\s+(\w+)\s*=\s*(\w+)\.clone\(\)$", stmt)
        if clone_match:
            var_name = clone_match.group(1)
            var2_name = clone_match.group(2)
            return Clone(var_name, var2_name)

        # Arithmetic: let x = a + b
        match = re.match(r"let\s+(\w+)\s*=\s*(\w+)\s*([+\-*/])\s*(\w+)$", stmt)
        if match:
            dest = match.group(1)
            left = match.group(2)
            op = match.group(3)
            right = match.group(4)
            if op == "+":
                return Add(dest, left, right)
            elif op == "-":
                return Sub(dest, left, right)
            elif op == "*":
                return Mul(dest, left, right)
            elif op == "/":
                return Div(dest, left, right)

        # let x = var
        var_match = re.match(r"let\s+(\w+)\s*=\s*(\w+)$", stmt)
        if var_match:
            var_name = var_match.group(1)
            raw_var = var_match.group(2)

            return StackVarFromVar(var_name, raw_var)

        # let x: type = value
        # let x = value
        # let x: type
        var_match = re.match(
            r"let\s+(\w+)(?:\s*:\s*([0-9a-zA-Z&_]+))?(?:\s*=\s*(.+))?$", stmt
        )
        if var_match:
            print(stmt)
            var_name = var_match.group(1)
            var_type = var_match.group(2) or "i32"  # inferred default
            raw_value = var_match.group(3)

            value = self._parse_value(raw_value) if raw_value else None
            return LetVar(var_name, var_type, value)

        print("Failed parsing:", stmt)
        return None

    def _parse_value(self, value_str: str):
        """Parse a value (int, string, etc.)."""
        value_str = value_str.strip()

        # Try to parse as integer
        try:
            return int(value_str)
        except ValueError:
            pass

        # Try negative integer
        if value_str.startswith("-"):
            try:
                return int(value_str)
            except ValueError:
                pass

        # Return as string (variable name or other)
        return value_str


def compile_rust(source: str) -> Program:
    """Convenience function to compile Rust-like code."""
    compiler = RustCompiler()
    return compiler.compile(source)


# Example usage
if __name__ == "__main__":
    rust_code = """
    fn main() {
        // Initialize bank account
        let bank: i32 = 25000;
        tampering();
        return;
    }

    fn tampering() {
        let x: i32 = 42;
        let arr: [i32; 4] = [1, 2, 3, 4];
        return;
    }
    """

    program = compile_rust(rust_code)
    print("Compiled successfully!")
    print(f"Functions: {list(program.functions.keys())}")
    for fn_name, fn_def in program.functions.items():
        print(f"\n{fn_name}:")
        print(f"  Params: {fn_def.params}")
        print(f"  Instructions: {len(fn_def.body)}")
        for instr in fn_def.body:
            print(f"    - {instr.description}")
