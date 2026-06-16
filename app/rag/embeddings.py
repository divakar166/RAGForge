"""Embedding provider using any OpenAI-compatible API (OpenAI, vLLM, Ollama, Qdrant Cloud inference, etc.)."""

from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.config import settings


class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed(self, texts: list[str]) -> dict[str, Any]:
        ...

    async def embed_one(self, text: str) -> list[float]:
        result = await self.embed([text])
        return result["embeddings"][0]


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        base_url: str = "",
        api_key: str = "",
        model: str = "",
    ):
        self.base_url = (base_url or settings.LLM_BASE_URL).rstrip("/")
        self.api_key = api_key or settings.LLM_API_KEY or ""
        self.model = model or settings.EMBEDDING_MODEL or "text-embedding-3-small"

    async def embed(self, texts: list[str]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=120) as client:
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            resp = await client.post(
                f"{self.base_url}/embeddings",
                headers=headers,
                json={"input": texts, "model": self.model},
            )
            resp.raise_for_status()
            data = resp.json()
            embeddings = [item["embedding"] for item in data.get("data", [])]
            return {"embeddings": embeddings, "model": data.get("model", self.model)}
