from fastapi import APIRouter

from app.api.v1 import admin, auth, health, notebooklm, runs, schedules, threads, tools

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(tools.router, prefix="/tools", tags=["tools"])
api_router.include_router(notebooklm.router, prefix="/tools", tags=["notebooklm"])
api_router.include_router(threads.router, prefix="/tools", tags=["threads"])
api_router.include_router(runs.router, prefix="/runs", tags=["runs"])
api_router.include_router(schedules.router, prefix="/schedules", tags=["schedules"])
