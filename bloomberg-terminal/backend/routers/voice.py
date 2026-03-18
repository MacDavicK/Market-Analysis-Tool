from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.post("/voice/transcribe")
async def transcribe(audio: bytes) -> dict:
    # Stub only. Audio processing implemented in Sprint 4.
    _ = audio  # unused for stub
    return {
        "status": "not_implemented",
        "message": "Voice transcribe endpoint — Sprint 4",
    }


@router.post("/voice/speak")
async def speak(payload: dict) -> dict:
    # Stub only. TTS implemented in Sprint 4.
    _ = payload  # unused for stub
    return {
        "status": "not_implemented",
        "message": "Voice speak endpoint — Sprint 4",
    }

