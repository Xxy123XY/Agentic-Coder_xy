from fastapi import APIRouter
from app.api.routes import issues, jobs, webhooks

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(issues.router)
api_router.include_router(jobs.router)
api_router.include_router(webhooks.router)