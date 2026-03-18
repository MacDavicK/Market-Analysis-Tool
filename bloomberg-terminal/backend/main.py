from __future__ import annotations

from fastapi import FastAPI

from backend.core.config import settings
from backend.core.middleware import setup_middleware
from backend.models.schemas import HealthResponse
from backend.routers.council import router as council_router
from backend.routers.rag import router as rag_router
from backend.routers.voice import router as voice_router

app = FastAPI(title="Bloomberg Terminal API")

setup_middleware(app)

app.include_router(council_router)
app.include_router(rag_router)
app.include_router(voice_router)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", environment=settings.ENVIRONMENT)

