from app.ai.providers.base import AIProvider


class OpenRouterProvider(AIProvider):
    async def complete(self, prompt: str) -> str:
        raise NotImplementedError("OpenRouter client is not configured")

