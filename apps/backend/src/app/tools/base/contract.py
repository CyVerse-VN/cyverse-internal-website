from abc import ABC, abstractmethod
from typing import Any


class InternalTool(ABC):
    name: str

    @abstractmethod
    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute the tool with a validated payload."""

