from __future__ import annotations

import json
import logging
import re
from datetime import date
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.core.config import settings
from backend.models.schemas import CouncilRequest, CouncilResponse
from backend.services.council_service import CouncilService

router = APIRouter()

logger = logging.getLogger("bloomberg_terminal.council.router")

@router.post("/council", response_model=None)
async def council(body: dict, request: Request) -> dict:
    webhook_secret = request.headers.get("X-Webhook-Secret")
    if not webhook_secret or webhook_secret != settings.N8N_WEBHOOK_SECRET:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    try:
        def looks_like_council_request_payload(payload: dict[str, Any]) -> bool:
            required_keys = {"report_date", "market_data", "portfolio", "watchlist", "data_quality"}
            return required_keys.issubset(set(payload.keys()))

        def clean_common_numeric_json_issues(text: str) -> str:
            # Replace +<number> with <number> when + is immediately after JSON delimiters/spaces.
            # Avoid exponent notation like 1e+5 (preceded by 'e'/'E', not by JSON delimiters).
            return re.sub(r"([:\[\{,\s])\+(\d+(?:\.\d+)?)", r"\1\2", text)

        def parse_json_with_fallback(text: str) -> Any | None:
            cleaned = clean_common_numeric_json_issues(text)
            try:
                return json.loads(cleaned)
            except Exception:
                pass

            # Best-effort normalization to handle common "almost JSON" issues.
            # Do not execute code; this stays inside json parsing.
            normalized = cleaned
            normalized = normalized.replace("None", "null").replace("True", "true").replace("False", "false")
            normalized = re.sub(r",(\s*[}\]])", r"\1", normalized)  # trailing commas

            # If the payload used single quotes, try converting them.
            normalized_single_to_double = re.sub(r"'", '"', normalized)
            try:
                return json.loads(normalized_single_to_double)
            except Exception:
                return None

        def extract_json_codeblock(output: str) -> str | None:
            match = re.search(
                r"```json\s*(.*?)```",
                output,
                flags=re.IGNORECASE | re.DOTALL,
            )
            if not match:
                return None
            return match.group(1).strip()

        def extract_string_value_from_raw(raw: str, key: str) -> str | None:
            # Handles: "key": "value" and 'key': 'value'
            patterns = [
                rf'"{re.escape(key)}"\s*:\s*"([^"]*)"',
                rf"'{re.escape(key)}'\s*:\s*'([^']*)'",
            ]
            for pat in patterns:
                m = re.search(pat, raw, flags=re.DOTALL)
                if m:
                    return m.group(1).strip()
            return None

        def extract_object_value_from_raw(raw: str, key: str) -> dict[str, Any]:
            # Brace-match a JSON object starting after: <key> : { ... }
            key_patterns = [
                rf'"{re.escape(key)}"\s*:\s*\{{',
                rf"'{re.escape(key)}'\s*:\s*\{{",
            ]
            start_idx = -1
            for kp in key_patterns:
                m = re.search(kp, raw, flags=re.DOTALL)
                if m:
                    start_idx = m.end() - 1  # points at '{'
                    break
            if start_idx == -1:
                return {}

            depth = 0
            i = start_idx
            while i < len(raw):
                if raw[i] == "{":
                    depth += 1
                elif raw[i] == "}":
                    depth -= 1
                    if depth == 0:
                        candidate = raw[start_idx : i + 1]
                        parsed = parse_json_with_fallback(candidate)
                        return parsed if isinstance(parsed, dict) else {}
                i += 1
            return {}

        def preprocess_body_to_council_request(raw_body: dict[str, Any]) -> CouncilRequest:
            # n8n raw format
            if "output" in raw_body:
                raw_output = raw_body.get("output")
                if not isinstance(raw_output, str):
                    raise ValueError("n8n payload 'output' must be a string")

                codeblock = extract_json_codeblock(raw_output)
                json_candidate = codeblock if codeblock is not None else raw_output

                parsed = parse_json_with_fallback(json_candidate)
                if not isinstance(parsed, dict):
                    parsed = {}

                if not parsed:
                    # Parsing failed: extract key fields individually.
                    parsed["report_date"] = extract_string_value_from_raw(raw_output, "report_date")
                    parsed["market_data"] = extract_object_value_from_raw(raw_output, "market_data")
                    parsed["portfolio_summary"] = extract_object_value_from_raw(raw_output, "portfolio_summary")
                    parsed["watchlist_summary"] = extract_object_value_from_raw(raw_output, "watchlist_summary")
                    parsed["data_quality"] = extract_object_value_from_raw(raw_output, "data_quality")

                report_date_value = parsed.get("report_date") or date.today().isoformat()
                market_data_value = parsed.get("market_data") if isinstance(parsed.get("market_data"), dict) else {}
                portfolio_value = (
                    parsed.get("portfolio_summary") if isinstance(parsed.get("portfolio_summary"), dict) else {}
                )
                watchlist_value = (
                    parsed.get("watchlist_summary") if isinstance(parsed.get("watchlist_summary"), dict) else {}
                )
                data_quality_value = (
                    parsed.get("data_quality") if isinstance(parsed.get("data_quality"), dict) else {}
                )

                mapped_payload = {
                    "report_date": str(report_date_value),
                    "market_data": market_data_value,
                    "portfolio": portfolio_value,
                    "watchlist": watchlist_value,
                    "data_quality": data_quality_value,
                }
                return CouncilRequest.model_validate(mapped_payload)

            # Already in CouncilRequest shape
            if looks_like_council_request_payload(raw_body):
                return CouncilRequest.model_validate(raw_body)

            raise ValueError("Invalid council payload: missing expected n8n 'output' or CouncilRequest fields")

        council_request = preprocess_body_to_council_request(body)

        service = CouncilService()
        result = await service.run(council_request.model_dump())
        return CouncilResponse(**result)
    except Exception as e:
        logger.exception("Council pipeline failed")
        return JSONResponse(
            status_code=500,
            content={"error": "Council pipeline failed", "detail": str(e)},
        )

