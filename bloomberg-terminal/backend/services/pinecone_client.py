from __future__ import annotations


class PineconeClient:
    async def upsert(self, vectors: list) -> None:
        # Implemented in Sprint 3
        raise NotImplementedError("PineconeClient.upsert — Sprint 3")

    async def query(self, vector: list, top_k: int) -> list:
        # Implemented in Sprint 3
        raise NotImplementedError("PineconeClient.query — Sprint 3")

