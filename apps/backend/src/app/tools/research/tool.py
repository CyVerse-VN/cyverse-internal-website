from typing import Any

from app.tools.base.contract import InternalTool


class ResearchTool(InternalTool):
    name = "research"

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("Research pipeline is not configured")

