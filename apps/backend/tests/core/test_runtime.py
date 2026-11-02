import asyncio
import sys

from uvicorn import Config


def test_uvicorn_entry_point_uses_a_database_compatible_event_loop() -> None:
    config = Config("app.main:app", loop="app.core.runtime:create_event_loop")
    factory = config.get_loop_factory()
    assert factory is not None
    loop = factory()
    try:
        if sys.platform == "win32":
            assert isinstance(loop, asyncio.SelectorEventLoop)
        assert loop.run_until_complete(asyncio.sleep(0, result="ready")) == "ready"
    finally:
        loop.close()
