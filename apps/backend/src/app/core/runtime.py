"""Event-loop configuration shared by local API entry points."""

import asyncio
import sys


def create_event_loop() -> asyncio.AbstractEventLoop:
    # Psycopg async requires Selector on Windows; browser subprocesses use their own thread.
    if sys.platform == "win32":
        return asyncio.SelectorEventLoop()
    return asyncio.new_event_loop()
