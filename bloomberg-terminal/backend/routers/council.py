from __future__ import annotations

import json
import logging
import re
from datetime import date
from pathlib import Path
import time
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.core.config import settings
from backend.models.schemas import CouncilRequest, CouncilResponse
from backend.services.council_service import CouncilService

router = APIRouter()

logger = logging.getLogger("bloomberg_terminal.council.router")

@router.post("/council", response_model=None)
async def council(request: Request) -> dict:
    webhook_secret = request.headers.get("X-Webhook-Secret")
    if not webhook_secret or webhook_secret != settings.N8N_WEBHOOK_SECRET:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    try:
        DEBUG_LOG_PATH = "/Users/kavishjaiswal/Downloads/Personal/Market-Analysis-Tool/.cursor/debug-015c04.log"

        def debug_ndjson(hypothesis_id: str, location: str, message: str, data: dict[str, Any] | None = None) -> None:
            # Runtime-evidence only; do not log raw portfolio/market data content.
            payload = {
                "sessionId": "015c04",
                "runId": "n8n-output-preprocess",
                "hypothesisId": hypothesis_id,
                "location": location,
                "message": message,
                "data": data or {},
                "timestamp": int(time.time() * 1000),
            }
            try:
                Path(DEBUG_LOG_PATH).open("a", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False) + "\n")
            except Exception:
                return

        def looks_like_council_request_payload(payload: dict[str, Any]) -> bool:
            required_keys = {"report_date", "market_data", "portfolio", "watchlist", "data_quality"}
            return required_keys.issubset(set(payload.keys()))

        body = await request.json()
        if not isinstance(body, dict):
            raise ValueError("Invalid council payload: expected a JSON object at root")

        # Unwrap n8n "Body" envelope if present
        if "Body" in body and isinstance(body["Body"], dict): body = body["Body"]

        if looks_like_council_request_payload(body):
            council_request = CouncilRequest.model_validate(body)
        elif "output" in body:
            output_str = body.get("output")
            if not isinstance(output_str, str):
                raise ValueError("Invalid n8n payload: 'output' must be a string")

            match = re.search(r"```json\s*([\s\S]*?)\s*```", output_str)
            if not match:
                raise ValueError("Invalid n8n payload: could not find ```json ... ``` fenced block in output")

            json_str = match.group(1)
            cleaned_json_str = re.sub(r'(?<=[^\w"])\+(?=\d)', '', json_str)
            cleaned_json_str = cleaned_json_str.replace("\r\n", " ").replace("\n", " ")

            try:
                parsed = json.loads(cleaned_json_str)
            except Exception as e:
                # Response includes what was attempted (user-directed); debug log keeps content minimal.
                debug_ndjson(
                    "A",
                    "council.output.json.loads",
                    "json.loads failed (content redacted in logs)",
                    {"prefix_len": min(500, len(cleaned_json_str)), "error": str(e)[:200]},
                )
                attempted_prefix = cleaned_json_str[:500]
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": "Failed to parse embedded JSON from n8n output via json.loads",
                        "detail": {
                            "attempted_prefix_500_chars": attempted_prefix,
                            "json_error": str(e),
                        },
                    },
                )

            if not isinstance(parsed, dict):
                raise ValueError("Parsed embedded JSON is not an object")

            report_date_value = parsed.get("report_date") or date.today().isoformat()
            market_data_value = parsed.get("market_data") or {}
            portfolio_value = parsed.get("portfolio_summary") or {}
            watchlist_value = parsed.get("watchlist_summary") or {}
            data_quality_value = parsed.get("data_quality") or {}

            mapped_payload = {
                "report_date": report_date_value,
                "market_data": market_data_value,
                "portfolio": portfolio_value,
                "watchlist": watchlist_value,
                "data_quality": data_quality_value,
            }
            council_request = CouncilRequest.model_validate(mapped_payload)
        else:
            raise ValueError("Invalid council payload: missing n8n 'output' key and not matching CouncilRequest shape")

        service = CouncilService()
        result = await service.run(council_request.model_dump())
        return CouncilResponse(**result)
    except Exception as e:
        logger.exception("Council pipeline failed")
        return JSONResponse(
            status_code=500,
            content={"error": "Council pipeline failed", "detail": str(e)},
        )

