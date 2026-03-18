from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.post("/rag/query")
async def rag_query(payload: dict) -> dict:
    # Stub only. Shape TBD in Sprint 3.
    return {
        "status": "not_implemented",
        "message": "RAG endpoint — Sprint 3",
    }

