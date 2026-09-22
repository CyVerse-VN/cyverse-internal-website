import asyncio

import pytest
from fastapi import FastAPI

from app import main as main_module


@pytest.mark.asyncio
async def test_lifespan_starts_and_stops_embedded_research_consumer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started = asyncio.Event()
    stopped = asyncio.Event()

    class FakeResearchWorker:
        async def run_supervised(self) -> None:
            started.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                stopped.set()
                raise

    monkeypatch.setattr(main_module.research_config, "embedded_worker", True)
    monkeypatch.setattr(main_module, "ResearchWorker", FakeResearchWorker)

    async with main_module.lifespan(FastAPI()):
        await asyncio.wait_for(started.wait(), timeout=1)

    assert stopped.is_set()


@pytest.mark.asyncio
async def test_lifespan_can_disable_embedded_research_consumer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class UnexpectedResearchWorker:
        def __init__(self) -> None:
            raise AssertionError("The research consumer should remain disabled")

    monkeypatch.setattr(main_module.research_config, "embedded_worker", False)
    monkeypatch.setattr(main_module, "ResearchWorker", UnexpectedResearchWorker)

    async with main_module.lifespan(FastAPI()):
        pass
