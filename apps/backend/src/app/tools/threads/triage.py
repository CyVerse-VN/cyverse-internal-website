from typing import Protocol

from app.tools.threads.schemas import PostTriage, ThreadsPost


class PostTriageProvider(Protocol):
    async def classify(self, query: str, posts: list[ThreadsPost]) -> dict[str, PostTriage]: ...
