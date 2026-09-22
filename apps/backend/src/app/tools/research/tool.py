from typing import Any

from app.tools.base.contract import InternalTool
from app.tools.research.pipeline import ResearchPipeline
from app.tools.research.schemas import ResearchSettingsInput


class ResearchTool(InternalTool):
    name = "research"

    def __init__(self, pipeline: ResearchPipeline | None = None) -> None:
        self.pipeline = pipeline or ResearchPipeline()

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        query = str(payload["query"])
        research_settings = ResearchSettingsInput.model_validate(payload["settings"])

        async def ignore_progress(
            _stage: str,
            _progress: float,
            _message: str,
            _metadata: dict[str, object] | None,
        ) -> None:
            return None

        async def never_cancelled() -> bool:
            return False

        result = await self.pipeline.run(
            query=query,
            settings=research_settings,
            on_progress=ignore_progress,
            is_cancelled=never_cancelled,
        )
        return result.model_dump(mode="json")
