from app.tools.base.contract import InternalTool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, InternalTool] = {}

    def register(self, tool: InternalTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> InternalTool:
        return self._tools[name]

