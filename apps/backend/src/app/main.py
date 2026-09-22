import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.auth.errors import AuthenticationError
from app.core.config import settings
from app.tools.research.config import research_config
from app.tools.research.errors import ResearchError
from app.workers.research import ResearchWorker


@asynccontextmanager
async def lifespan(_application: FastAPI) -> AsyncIterator[None]:
    research_task: asyncio.Task[None] | None = None
    if research_config.embedded_worker:
        research_task = asyncio.create_task(
            ResearchWorker().run_supervised(),
            name="research-queue-consumer",
        )
    try:
        yield
    finally:
        if research_task is not None:
            research_task.cancel()
            with suppress(asyncio.CancelledError):
                await research_task


def create_app() -> FastAPI:
    application = FastAPI(title=settings.app_name, lifespan=lifespan)

    @application.exception_handler(AuthenticationError)
    async def handle_authentication_error(
        _request: Request, error: AuthenticationError
    ) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if error.status_code == 401 else None
        return JSONResponse(
            status_code=error.status_code,
            content={"detail": error.detail},
            headers=headers,
        )

    @application.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        _request: Request, error: RequestValidationError
    ) -> JSONResponse:
        safe_errors = [
            {"type": item["type"], "loc": item["loc"], "msg": item["msg"]}
            for item in error.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": safe_errors})

    @application.exception_handler(ResearchError)
    async def handle_research_error(_request: Request, error: ResearchError) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content={"detail": error.detail, "code": error.code},
        )

    application.include_router(api_router, prefix=settings.api_v1_prefix)
    return application


app = create_app()
