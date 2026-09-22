from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

import httpx

from app.tools.research.domain import PaperCandidate
from app.tools.research.errors import ResearchCancelledError


class PaperSource(ABC):
    name: str

    def __init__(
        self,
        client: httpx.AsyncClient,
        is_cancelled: Callable[[], Awaitable[bool]] | None = None,
    ) -> None:
        self.client = client
        self.is_cancelled = is_cancelled

    async def checkpoint(self) -> None:
        if self.is_cancelled is not None and await self.is_cancelled():
            raise ResearchCancelledError

    @abstractmethod
    async def search(self, query: str, *, limit: int, filters: dict[str, object]) -> list[PaperCandidate]:
        """Return normalized candidates without retaining the raw response."""
