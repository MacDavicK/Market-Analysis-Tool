from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    environment: str


class CouncilRequest(BaseModel):
    report_date: str
    market_data: dict
    portfolio: dict
    watchlist: dict
    data_quality: dict
    user_id: str = "default"

class CouncilMemberResponse(BaseModel):
    model: str
    label: str  # "Model A", "Model B", "Model C" — anonymized
    response: str
    tokens_used: int


class PeerReview(BaseModel):
    reviewer_label: str  # which model reviewed
    ranking: list[str]  # ["Model B", "Model A", "Model C"] — best to worst
    critique: str


class CouncilResponse(BaseModel):
    report: str
    disclaimer: str
    council_members: list[CouncilMemberResponse]
    peer_reviews: list[PeerReview]
    chairman_model: str
    stages_completed: int
    total_tokens_used: int
    report_date: str


class RAGQueryRequest(BaseModel):
    query: str
    user_id: str


class RAGQueryResponse(BaseModel):
    answer: str
    sources: list[str]

