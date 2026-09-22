from app.workers.research import ResearchWorker


class JobProcessor:
    """Routes durable research jobs through the configured worker."""

    def __init__(self) -> None:
        self.research = ResearchWorker()

    async def process_next(self) -> bool:
        return await self.research.run_once()
