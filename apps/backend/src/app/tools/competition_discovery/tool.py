from typing import Any

from app.tools.base.contract import InternalTool


class CompetitionDiscoveryTool(InternalTool):
    name = "competition_discovery"

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("Competition discovery pipeline is not configured")

