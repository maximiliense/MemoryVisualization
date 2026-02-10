"""
V2 Base Instruction System

Key design principles:
1. Expressions evaluate to results (arrays of values)
2. Instructions can be incomplete and require multiple execution steps
3. Clear separation between LValue (destination) and RValue (source)
4. Recursive evaluation of nested expressions
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Union


class ExecutionStatus(Enum):
    """Status of instruction execution"""

    COMPLETE = "complete"  # Instruction finished
    INCOMPLETE = "incomplete"  # Needs more steps (e.g., waiting for function return)
    BLOCKED = "blocked"  # Waiting for async operation


@dataclass
class EvaluationResult:
    """Result of evaluating an expression"""

    values: list[Any]  # Array of values produced
    typ: str = "i32"  # Type of the values
    is_pointer: bool = False  # Whether values are pointers

    def is_scalar(self) -> bool:
        """Check if this is a single value"""
        return len(self.values) == 1

    def get_scalar(self) -> Any:
        """Get single value (asserts scalar)"""
        assert self.is_scalar(), "Expected scalar result"
        return self.values[0]


@dataclass
class ExecutionContext:
    """
    Context tracking execution state of an instruction.
    Allows instructions to maintain state across multiple steps.
    """

    step: int = 0  # Current execution step
    temp_results: dict[str, Any] = None  # type:ignore

    def __post_init__(self):
        if self.temp_results is None:
            self.temp_results = {}

    def advance(self):
        """Move to next step"""
        self.step += 1

    def reset(self):
        """Reset context"""
        self.step = 0
        self.temp_results.clear()

    def store(self, key: str, value: Any):
        """Store temporary result"""
        self.temp_results[key] = value

    def get(self, key: str, default=None) -> Any:
        """Retrieve temporary result"""
        return self.temp_results.get(key, default)


class ContextObjects(ABC):
    def get_ctx(self, mem) -> ExecutionContext:
        """
        Retrieves the execution context for this specific expression
        instance from the current stack frame.
        """
        if not mem.call_stack:
            raise RuntimeError("No active stack frame to retrieve context.")

        frame = mem.call_stack[-1]
        obj_id = id(self)

        if obj_id not in frame.contexts:
            from emulator.core.base import ExecutionContext

            frame.contexts[obj_id] = ExecutionContext()

        return frame.contexts[obj_id]

    def reset_ctx(self, mem):
        """
        Recursively resets contexts for this node and all sub-nodes
        stored in attributes or lists of attributes.
        """
        # 1. Reset the context for 'self' in the current frame
        ctx = self.get_ctx(mem)
        ctx.reset()

        # 2. Inspect all attributes of this instance
        for attr_name, attr_value in vars(self).items():
            # Scenario A: The attribute is a single object (e.g., self.expr)
            if hasattr(attr_value, "reset_ctx"):
                attr_value.reset_ctx(mem)

            # Scenario B: The attribute is a list (e.g., self.body or self.args)
            elif isinstance(attr_value, list):
                for item in attr_value:
                    if hasattr(item, "reset_ctx"):
                        item.reset_ctx(mem)


class Expression(ContextObjects):
    """
    Base class for all expressions (RValues).
    Expressions evaluate to results without side effects.
    """

    @abstractmethod
    def evaluate(self, mem, prog) -> Union[EvaluationResult, ExecutionStatus]:
        """
        Evaluate the expression.

        Returns:
            - EvaluationResult: If evaluation completes
            - ExecutionStatus.INCOMPLETE: If needs more steps
        """
        pass

    @abstractmethod
    def description(self) -> str:
        """Human-readable description for visualization"""
        pass


class LValue(ContextObjects):
    """
    Base class for locations that can be assigned to.
    LValues represent "where" to store values.
    """

    @abstractmethod
    def get_address(self, mem, prog) -> Union[int, list[int]]:
        """Get memory address(es) for this lvalue"""
        pass

    @abstractmethod
    def description(self) -> str:
        """Human-readable description"""
        pass


class Instruction(ContextObjects):
    """
    Base class for all instructions (statements with side effects).
    Instructions modify memory and can be incomplete.
    """

    @abstractmethod
    def execute(self, mem, prog) -> ExecutionStatus:
        """
        Execute the instruction.

        Returns:
            ExecutionStatus indicating if execution is complete
        """
        pass

    @abstractmethod
    def description(self) -> str:
        """Human-readable description for visualization"""
        pass
