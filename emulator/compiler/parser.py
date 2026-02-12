"""
V2 Compiler/Parser

Parses Rust-like syntax into V2 AST structures.

CHANGE: Added variable type tracking per function to properly handle Vec detection in drop().
"""

import re
from typing import Optional

from emulator.core.base import Instruction
from emulator.core.builtins import MethodCall, Println, RandInt
from emulator.core.expressions import (
    ArrayAccess,
    ArrayLiteral,
    BinaryOp,
    BoxNew,
    Dereference,
    Expression,
    FunctionCall,
    Literal,
    Not,
    Reference,
    Variable,
    VecMacro,
)
from emulator.core.instructions import (
    Assignment,
    CompoundAssignment,
    Drop,
    ExpressionStatement,
    IfElseBlock,
    LetBinding,
    Nop,
    Return,
    WhileLoop,
)
from emulator.core.lvalues import (
    ArrayIndexLValue,
    DereferenceLValue,
    LValue,
    VariableLValue,
)
from emulator.runtime.runner import FunctionDef, Program


class Parser:
    """
    Recursive descent parser for Rust-like syntax.

    This parser builds proper AST nodes with separated expressions and lvalues.
    """

    def __init__(self):
        self.functions = {}
        # NEW: Track variable types for current function being parsed
        self.current_func_vars = {}

    def parse(self, source: str) -> Program:
        """Parse complete program"""
        self.functions = {}

        # Find all function definitions
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
                fn_name, params, body_str, new_i = self._parse_function_def(source, i)
                # NEW: Reset variable tracking for each function
                self.current_func_vars = {}
                body = self._parse_body(body_str)
                self.functions[fn_name] = FunctionDef(params=params, body=body)
                i = new_i
            else:
                i += 1

        return Program(functions=self.functions)

    def _parse_function_def(self, source: str, start: int):
        """Parse function definition"""
        i = start + 2  # Skip 'fn'

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

            if params_str:
                for param in params_str.split(","):
                    param = param.strip()
                    if not param:
                        continue
                    name, _, typ = param.partition(":")
                    params.append((name.strip(), typ.strip() or None))

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

            return fn_name, params, body_str, i

        raise SyntaxError(f"Expected function body at position {i}")

    def _parse_body(self, body_str: str) -> list[Instruction]:
        """Parse function body into list of instructions"""
        instructions = []
        body_str = body_str.strip()

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

            # Check for if statement
            if body_str[i:].startswith("if "):
                instr, new_i = self._parse_if_else(body_str, i)
                instructions.append(instr)
                i = new_i
                continue

            # Check for while loop
            if body_str[i:].startswith("while "):
                instr, new_i = self._parse_while(body_str, i)
                instructions.append(instr)
                i = new_i
                continue

            # Find next semicolon
            stmt_end = self._find_statement_end(body_str, i)
            stmt = body_str[i:stmt_end].strip()

            if stmt:
                instr = self._parse_statement(stmt)
                if instr:
                    instructions.append(instr)

            i = stmt_end + 1

        return instructions

    def _find_statement_end(self, text: str, start: int) -> int:
        """Find the end of a statement"""
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

    def _parse_if_else(self, text: str, start: int):
        """Parse if-else block"""
        # if EXPR { ... } else { ... }
        i = start + 3  # Skip 'if '

        # Find condition (up to '{')
        cond_start = i
        while i < len(text) and text[i] != "{":
            i += 1
        cond_str = text[cond_start:i].strip()
        condition = self._parse_expression(cond_str)

        # Parse then block
        then_end = self._find_matching_brace(text, i)
        then_body_str = text[i + 1 : then_end]
        then_body = self._parse_body(then_body_str)

        # Check for else
        i = then_end + 1
        while i < len(text) and text[i].isspace():
            i += 1

        else_body = None
        if i < len(text) and text[i : i + 4] == "else":
            i += 4
            while i < len(text) and text[i].isspace():
                i += 1

            if i < len(text) and text[i] == "{":
                else_end = self._find_matching_brace(text, i)
                else_body_str = text[i + 1 : else_end]
                else_body = self._parse_body(else_body_str)
                i = else_end + 1

        return IfElseBlock(condition, then_body, else_body), i

    def _parse_while(self, text: str, start: int):
        """Parse while loop"""
        i = start + 6  # Skip 'while '

        # Find condition
        cond_start = i
        while i < len(text) and text[i] != "{":
            i += 1
        cond_str = text[cond_start:i].strip()
        condition = self._parse_expression(cond_str)

        # Parse body
        body_end = self._find_matching_brace(text, i)
        body_str = text[i + 1 : body_end]
        body = self._parse_body(body_str)

        return WhileLoop(condition, body), body_end + 1

    def _find_matching_brace(self, text: str, start: int) -> int:
        """Find matching closing brace"""
        depth = 1
        i = start + 1
        while i < len(text) and depth > 0:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        return i - 1

    def _parse_statement(self, stmt: str) -> Optional[Instruction]:
        """Parse a single statement"""
        stmt = stmt.strip()

        # Return statement
        if stmt.startswith("return"):
            if stmt == "return":
                return Return()
            expr_str = stmt[6:].strip()
            expr = self._parse_expression(expr_str)
            return Return(expr)

        # Drop statement
        match = re.match(r"drop\((\w+)\)", stmt)
        if match:
            var_name = match.group(1)
            # NEW: Check if this variable is a Vec
            typ = self.current_func_vars.get(var_name)
            is_vec = typ is not None and typ.startswith("Vec")
            return Drop(var_name, is_vec=is_vec)

        # Let binding
        if stmt.startswith("let "):
            return self._parse_let(stmt)

        # Compound assignment (+=, -=, etc.)
        match = re.match(r"(.+?)\s*([+\-*/])=\s*(.+)", stmt)
        if match and not stmt.startswith("print"):
            lvalue_str = match.group(1).strip()
            op = match.group(2) + "="
            expr_str = match.group(3).strip()

            lvalue = self._parse_lvalue(lvalue_str)
            expr = self._parse_expression(expr_str)
            return CompoundAssignment(lvalue, op, expr)

        # Assignment
        match = re.match(r"(.+?)\s*=\s*(.+)", stmt)
        if match and not stmt.startswith("print"):
            lvalue_str = match.group(1).strip()
            expr_str = match.group(2).strip()

            lvalue = self._parse_lvalue(lvalue_str)
            expr = self._parse_expression(expr_str)
            return Assignment(lvalue, expr)

        # Expression statement
        expr = self._parse_expression(stmt)
        return ExpressionStatement(expr)

    def _parse_let(self, stmt: str) -> LetBinding:
        """Parse let binding"""
        # let [mut] VAR [: TYPE] [= EXPR]
        stmt = stmt[4:].strip()  # Remove 'let '

        # Remove 'mut' if present
        if stmt.startswith("mut "):
            stmt = stmt[4:].strip()

        # Split by '='
        if "=" in stmt:
            lhs, rhs = stmt.split("=", 1)
            lhs = lhs.strip()
            rhs = rhs.strip()

            # Parse LHS (var : type)
            if ":" in lhs:
                var_name, typ = lhs.split(":", 1)
                var_name = var_name.strip()
                typ = typ.strip()
            else:
                var_name = lhs
                typ = None

            # Parse RHS expression
            expr = self._parse_expression(rhs)

            # NEW: Track variable type
            # Infer type from expression if not explicitly provided
            if typ is None:
                # Check if expression is VecMacro
                if isinstance(expr, VecMacro):
                    typ = "Vec"
                # Add more type inference as needed

            if typ:
                self.current_func_vars[var_name] = typ

            return LetBinding(var_name, typ, expr)
        else:
            # No initialization
            if ":" in stmt:
                var_name, typ = stmt.split(":", 1)
                var_name = var_name.strip()
                typ = typ.strip()
                # NEW: Track variable type
                if typ:
                    self.current_func_vars[var_name] = typ
            else:
                var_name = stmt
                typ = None

            return LetBinding(var_name, typ, None)

    def _parse_lvalue(self, text: str) -> LValue:
        """Parse lvalue (assignment target) with correct precedence"""
        text = text.strip()

        # 1. Check for Array Indexing (highest precedence)
        # We look for a trailing ']' to identify arr[idx]
        if text.endswith("]"):
            # Find matching '[' for the last ']'
            depth = 0
            bracket_pos = -1
            for i in range(len(text) - 1, -1, -1):
                if text[i] == "]":
                    depth += 1
                elif text[i] == "[":
                    depth -= 1
                    if depth == 0:
                        bracket_pos = i
                        break

            if bracket_pos != -1:
                array_str = text[:bracket_pos].strip()
                # If it's (*p)[0], we strip parentheses
                if array_str.startswith("(") and array_str.endswith(")"):
                    array_str = array_str[1:-1].strip()

                index_str = text[bracket_pos + 1 : -1].strip()

                # We parse the base as an EXPRESSION (could be Variable or Dereference)
                array_expr = self._parse_expression(array_str)
                index_expr = self._parse_expression(index_str)
                return ArrayIndexLValue(array_expr, index_expr)

        # 2. Check for Dereference (*ptr)
        if text.startswith("*"):
            stars = 0
            i = 0
            while i < len(text) and text[i] == "*":
                stars += 1
                i += 1
            inner_expr = self._parse_expression(text[i:])
            return DereferenceLValue(inner_expr, stars)

        # 3. Simple Variable
        return VariableLValue(text)

    def _parse_expression(self, text: str) -> Expression:
        """Parse expression (recursive descent)"""
        text = text.strip()
        if text.startswith("(") and text.endswith(")"):
            # Check if opening and closing parens match
            depth = 0
            for i, c in enumerate(text):
                if c == "(":
                    depth += 1
                elif c == ")":
                    depth -= 1
                # If depth hits 0 before the end, they don't match
                if depth == 0 and i < len(text) - 1:
                    break

            # Only strip if we made it to the end with depth 0
            if depth == 0 and i == len(text) - 1:  # type: ignore
                return self._parse_expression(text[1:-1])
        for op in ["||", "&&"]:
            if op in text:
                parts = text.split(op, 1)
                if len(parts) == 2:
                    left = self._parse_expression(parts[0])
                    right = self._parse_expression(parts[1])
                    return BinaryOp(left, op, right)

        # Try to parse as binary operation (lowest precedence first)
        for op in ["<=", ">=", "==", "!=", "<", ">"]:
            if op in text:
                parts = text.split(op, 1)
                if len(parts) == 2:
                    left = self._parse_expression(parts[0])
                    right = self._parse_expression(parts[1])
                    return BinaryOp(left, op, right)

        for op in ["+", "-"]:
            if op in text:
                depth = 0
                # Iterate REVERSED to find the rightmost operator (Left-Associativity)
                for i in range(len(text) - 1, -1, -1):
                    c = text[i]
                    # Note: Brackets are swapped because we are moving backwards
                    if c in ")]":
                        depth += 1
                    elif c in "([":
                        depth -= 1
                    elif c == op and depth == 0 and i > 0:
                        # Find the non-whitespace character to the left
                        prev_idx = i - 1
                        while prev_idx >= 0 and text[prev_idx].isspace():
                            prev_idx -= 1

                        if prev_idx >= 0:
                            prev_char = text[prev_idx]
                            # If it follows an operator, it's unary (e.g., 5 + -3)
                            if prev_char in "+-*/=!<>,(":
                                continue
                        else:
                            # Start of string (e.g., -3)
                            continue

                        # Correct split: everything before is Left, everything after is Right
                        left = self._parse_expression(text[:i])
                        right = self._parse_expression(text[i + 1 :])
                        return BinaryOp(left, op, right)
        for op in ["*", "/"]:
            if op in text:
                depth = 0
                # Iterate REVERSED to maintain left-to-right priority
                for i in range(len(text) - 1, -1, -1):
                    c = text[i]
                    if c in ")]":
                        depth += 1
                    elif c in "([":
                        depth -= 1
                    elif c == op and depth == 0 and i > 0:
                        # Check for infix position (must follow a value)
                        prev_idx = i - 1
                        while prev_idx >= 0 and text[prev_idx].isspace():
                            prev_idx -= 1
                        if prev_idx >= 0:
                            prev_char = text[prev_idx]
                            # If it follows an operator, it's not a binary * or /
                            if prev_char in "+-*/=!<>,(":
                                continue
                        else:
                            # Start of string (invalid for * or / anyway)
                            continue
                        left = self._parse_expression(text[:i])
                        right = self._parse_expression(text[i + 1 :])
                        return BinaryOp(left, op, right)

        # Try primary expressions
        return self._parse_primary(text)

    def _parse_primary(self, text: str) -> Expression:
        """Parse primary expression"""
        text = text.strip()
        if text.startswith("-") and len(text) > 1 and text[1].isdigit():
            try:
                return Literal(int(text))
            except ValueError:
                pass

        if text.startswith("!"):
            # Parse the part after the '!'
            # We call _parse_primary again to handle cases like !!true
            inner_expr = self._parse_primary(text[1:].strip())
            # Assuming you have a UnaryOp or Not class in your core expressions
            # If you don't have a Not class, you can use a BinaryOp with a dummy left side
            # or define a new class. Let's assume a 'Not' class exists:
            return Not(inner_expr)

        if text == "true":
            return Literal(True, "bool")
        if text == "false":
            return Literal(False, "bool")

        # Parenthesized expression
        if text.startswith("(") and text.endswith(")"):
            return self._parse_expression(text[1:-1])

        # Array literal: [1, 2, 3]
        if text.startswith("[") and text.endswith("]"):
            elements_str = text[1:-1]
            elements = [
                self._parse_expression(e.strip())
                for e in elements_str.split(",")
                if e.strip()
            ]
            return ArrayLiteral(elements)

        # Vec macro: vec![1, 2, 3]
        if text.startswith("vec![") and text.endswith("]"):
            elements_str = text[5:-1]
            elements = [
                self._parse_expression(e.strip())
                for e in elements_str.split(",")
                if e.strip()
            ]
            return VecMacro(elements)

        # Box::new(value)
        if text.startswith("Box::new(") and text.endswith(")"):
            value_str = text[9:-1]
            value = self._parse_expression(value_str)
            return BoxNew(value)

        # Reference: &var
        if text.startswith("&"):
            var_name = text[1:].strip()
            return Reference(var_name)

        # Dereference: *ptr
        # 1. Handle Method Calls FIRST (Higher Precedence)
        # We look for the LAST dot that isn't inside parentheses to split the object from the method
        if "." in text and "(" in text:
            # Use rindex to handle cases like a.b.method() correctly
            dot_pos = text.rindex(".")
            obj_str = text[:dot_pos]
            rest = text[dot_pos + 1 :]

            if "(" in rest and rest.endswith(")"):
                paren_pos = rest.index("(")
                method = rest[:paren_pos]
                args_str = rest[paren_pos + 1 : -1]

                # This will recursively call _parse_expression for "*v"
                # which will then hit the Dereference logic below
                obj = self._parse_expression(obj_str)

                args = (
                    [
                        self._parse_expression(a.strip())
                        for a in args_str.split(",")
                        if a.strip()
                    ]
                    if args_str
                    else []
                )
                return MethodCall(obj, method, args)

        # 2. Handle Dereferencing SECOND (Lower Precedence)
        if text.startswith("*"):
            stars = 0
            i = 0
            while i < len(text) and text[i] == "*":
                stars += 1
                i += 1
            # Parse the remainder (e.g., "v")
            inner = self._parse_primary(text[i:])
            return Dereference(inner, stars)
        # Function call: func(args)
        if "(" in text and text.endswith(")"):
            paren_pos = text.index("(")
            func_name = text[:paren_pos].strip()
            args_str = text[paren_pos + 1 : -1]

            # Special built-ins
            if func_name == "rand_int":
                args = [self._parse_expression(a.strip()) for a in args_str.split(",")]
                return RandInt(args[0], args[1])
            elif func_name in ("print!", "println!"):
                # Simplified: just take the expression
                arg = self._parse_expression(args_str)
                return Println(arg, new_line=func_name.endswith("ln!"))

            args = (
                [
                    self._parse_expression(a.strip())
                    for a in args_str.split(",")
                    if a.strip()
                ]
                if args_str
                else []
            )
            return FunctionCall(func_name, args)

        # Array index: arr[index]
        if "[" in text and text.endswith("]"):
            bracket_pos = text.index("[")
            array_str = text[:bracket_pos]
            index_str = text[bracket_pos + 1 : -1]

            array = self._parse_expression(array_str)
            index = self._parse_expression(index_str)
            return ArrayAccess(array, index)

        # Literal number
        try:
            return Literal(int(text))
        except ValueError:
            pass

        # String literal
        if text.startswith('"') and text.endswith('"'):
            return Literal(text[1:-1], "str")

        # Variable
        return Variable(text)


def compile_srs(source: str) -> Program:
    """Compile Rust-like source code to V2 AST"""
    parser = Parser()
    return parser.parse(source)
