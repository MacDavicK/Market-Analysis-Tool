from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.core.config import settings
from backend.models.schemas import CouncilRequest, CouncilResponse
from backend.services.council_service import CouncilService

router = APIRouter()

logger = logging.getLogger("bloomberg_terminal.council.router")

@router.post("/council")
async def council(body: CouncilRequest, request: Request) -> CouncilResponse | JSONResponse:
    webhook_secret = request.headers.get("X-Webhook-Secret")
    if not webhook_secret or webhook_secret != settings.N8N_WEBHOOK_SECRET:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    try:
        service = CouncilService()
        result = await service.run(body.model_dump())
        return CouncilResponse(**result)
    except Exception as e:
        logger.exception("Council pipeline failed")
        return JSONResponse(
            status_code=500,
            content={"error": "Council pipeline failed", "detail": str(e)},
        )

