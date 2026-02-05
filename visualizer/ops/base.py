from typing import Any, List, Optional


class Instruction:
    description: str = ""

    def execute(self, mem, prog) -> Optional[Any]:
        pass
