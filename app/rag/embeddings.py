"""Abstract embedding provider and TEI implementation.

Supports TEI (via native API) and any OpenAI-compatible API.
"""

from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.config import settings


class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed(self, texts: list[str]) -> dict[str, Any]:
        """Return dict with 'embeddings' key (list of list[float])."""
        ...

    async def embed_one(self, text: str) -> list[float]:
        result = await self.embed([text])
        return result["embeddings"][0]


class TEIEmbeddingProvider(EmbeddingProvider):
    """Text Embeddings Inference (HuggingFace) provider.

    Uses TEI's native /embed endpoint.
    Also supports the OpenAI-compatible /v1/embeddings endpoint.
    """

    def __init__(
        self,
        endpoint: str = "",
        model: str = "",
        use_openai_compat: bool = False,
    ):
        self.endpoint = (endpoint or settings.TEI_ENDPOINT).rstrip("/")
        self.model = model or settings.EMBEDDING_MODEL
        self.use_openai_compat = use_openai_compat

    async def embed(self, texts: list[str]) -> dict[str, Any]:
        if self.use_openai_compat:
            return await self._embed_openai(texts)
        return await self._embed_native(texts)

    async def _embed_native(self, texts: list[str]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.endpoint}/embed",
                json={"inputs": texts},
            )
            resp.raise_for_status()
            data = resp.json()
            # TEI returns a list of lists
            if isinstance(data, list):
                return {"embeddings": data, "model": self.model}
            # TEI may return {"data": [...]}
            return {"embeddings": data.get("data", []), "model": self.model}

    async def _embed_openai(self, texts: list[str]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.endpoint}/v1/embeddings",
                json={"input": texts, "model": self.model},
            )
            resp.raise_for_status()
            data = resp.json()
            embeddings = [item["embedding"] for item in data.get("data", [])]
            return {"embeddings": embeddings, "model": data.get("model", self.model)}


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI-compatible embedding API (works with OpenAI, vLLM, etc.)."""

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
