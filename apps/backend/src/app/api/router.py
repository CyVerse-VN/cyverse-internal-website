from fastapi import APIRouter

from app.api.v1 import auth, health, runs, schedules, tools

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(tools.router, prefix="/tools", tags=["tools"])
api_router.include_router(runs.router, prefix="/runs", tags=["runs"])
api_router.include_router(schedules.router, prefix="/schedules", tags=["schedules"])

