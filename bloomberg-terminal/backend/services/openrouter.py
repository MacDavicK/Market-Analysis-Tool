from __future__ import annotations

import asyncio
from typing import Any

import httpx

from backend.core.config import settings


class OpenRouterClient:
    COUNCIL_MODELS = [
        "openai/gpt-5-mini",
        "google/gemini-3-flash-preview",
        "anthropic/claude-sonnet-4-6",
    ]
    CHAIRMAN_MODEL = "anthropic/claude-opus-4-6"

    base_url = "https://openrouter.ai/api/v1"
    referer = "bloomberg-terminal"
    title = "Bloomberg Terminal"

    async def complete(
        self,
        model: str,
        messages: list[dict],
        temperature: float = 0.2,
    ) -> tuple[str, int]:
        # Returns (response_text, tokens_used)
        headers: dict[str, str] = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.referer,
            "X-Title": self.title,
        }

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }

        async with httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=httpx.Timeout(120.0),
        ) as client:
            resp = await client.post("/chat/completions", json=payload)
            resp.raise_for_status()  # Ensure httpx.HTTPStatusError on non-2xx

        data: dict[str, Any] = resp.json()
        response_text = data["choices"][0]["message"]["content"]
        tokens_used = int(data.get("usage", {}).get("total_tokens", 0))
        return response_text, tokens_used

    async def complete_parallel(
        self,
        model_message_pairs: list[tuple[str, list[dict]]],
        temperature: float = 0.2,
    ) -> list[tuple[str, int]]:
        # Run all complete() calls concurrently (same order as input).
        tasks = [
            self.complete(model, messages, temperature=temperature)
            for model, messages in model_message_pairs
        ]
        return list(await asyncio.gather(*tasks))

