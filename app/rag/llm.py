"""OpenAI-compatible LLM client using httpx with Langfuse tracing."""

import json
import logging
from typing import Any, AsyncGenerator

import httpx

from app.core.config import settings
from app.monitoring.tracing import get_langfuse, observe

logger = logging.getLogger(__name__)


class LLMClient:
    """HTTP client for any OpenAI-compatible LLM API.

    Works with: OpenAI, vLLM, Ollama, Modal, Azure OpenAI, etc.
    Supports Langfuse tracing for generation observability.
    """

    def __init__(
        self,
        base_url: str = "",
        api_key: str = "",
        model: str = "",
        max_tokens: int = 0,
        temperature: float = 0.0,
    ):
        self.base_url = (base_url or settings.LLM_BASE_URL).rstrip("/")
        self.api_key = api_key or settings.LLM_API_KEY or ""
        self.model = model or settings.LLM_MODEL
        self.max_tokens = max_tokens or settings.LLM_MAX_TOKENS
        self.temperature = temperature if temperature > 0 else settings.LLM_TEMPERATURE

    @observe(name="llm_generate")
    async def generate(
        self,
        messages: list[dict[str, str]],
        stream: bool = False,
    ) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        body = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": stream,
        }

        # Report LLM usage to Langfuse via the generation observation
        lf = get_langfuse()
        if lf is not None:
            try:
                lf.update_current_generation(
                    input=messages,
                    model=self.model,
                    model_parameters={"max_tokens": self.max_tokens, "temperature": self.temperature},
                )
            except Exception:
                pass

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()

            # Report output + token usage to Langfuse
            if lf is not None:
                try:
                    usage = data.get("usage", {})
                    lf.update_current_generation(
                        output=data.get("choices", [{}])[0].get("message", {}).get("content", ""),
                        usage={
                            "input": usage.get("prompt_tokens", 0),
                            "output": usage.get("completion_tokens", 0),
                            "unit": "TOKENS",
                        },
                    )
                except Exception:
                    pass

            return data

    async def generate_stream(
        self,
        messages: list[dict[str, str]],
    ) -> AsyncGenerator[str, None]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        body = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=body,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
