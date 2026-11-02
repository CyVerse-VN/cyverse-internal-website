import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.auth.errors import AuthenticationError
from app.core.config import settings
from app.core.logging import configure_logging
from app.tools.notebooklm.errors import NotebookImportError
from app.tools.research.config import research_config
from app.tools.research.errors import ResearchError
from app.tools.threads.config import threads_config
from app.tools.threads.errors import ThreadsError
from app.workers.notebooklm import NotebookImportWorker
from app.workers.research import ResearchWorker
from app.workers.threads import ThreadsWorker


@asynccontextmanager
async def lifespan(_application: FastAPI) -> AsyncIterator[None]:
    research_task: asyncio.Task[None] | None = None
    threads_task: asyncio.Task[None] | None = None
    if threads_config.enabled and threads_config.embedded_worker:
        threads_task = asyncio.create_task(
            ThreadsWorker().run_supervised(), name="threads-queue-consumer"
        )
    notebook_task = asyncio.create_task(
        NotebookImportWorker().run_supervised(), name="notebooklm-queue-consumer"
    )
    if research_config.embedded_worker:
        research_task = asyncio.create_task(
            ResearchWorker().run_supervised(),
            name="research-queue-consumer",
        )
    try:
        yield
    finally:
        if threads_task is not None:
            threads_task.cancel()
            with suppress(asyncio.CancelledError):
                await threads_task
        notebook_task.cancel()
        with suppress(asyncio.CancelledError):
            await notebook_task
        if research_task is not None:
            research_task.cancel()
            with suppress(asyncio.CancelledError):
                await research_task


def create_app() -> FastAPI:
    configure_logging()
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

    @application.exception_handler(ThreadsError)
    async def handle_threads_error(_request: Request, error: ThreadsError) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content={"detail": error.detail, "code": error.code},
        )

    @application.exception_handler(NotebookImportError)
    async def handle_notebook_import_error(
        _request: Request, error: NotebookImportError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content={"detail": error.detail, "code": error.code},
        )

    @application.get("/", include_in_schema=False)
    async def root_index() -> dict[str, str]:
        return {
            "name": settings.app_name,
            "status": "online",
            "docs": "/docs",
            "health": "/health",
            "api": settings.api_v1_prefix,
        }

    @application.get("/health", tags=["health"], include_in_schema=False)
    async def root_health_check() -> dict[str, str]:
        return {"status": "ok"}

    if settings.cors_origins or settings.cors_origin_regex:
        allow_credentials = "*" not in settings.cors_origins
        application.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_origin_regex=settings.cors_origin_regex,
            allow_credentials=allow_credentials,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    application.include_router(api_router, prefix=settings.api_v1_prefix)
    return application


app = create_app()
