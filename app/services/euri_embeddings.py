"""EURI Gemini Embedding 2 adapter used by policy indexing and search."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence

import httpx

from app.config import Settings, get_settings
from app.services.network import can_connect_outbound


class EuriEmbeddingError(RuntimeError):
    """Safe, non-secret-bearing embedding service error."""


class EuriEmbeddingClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.vector_size: int | None = None

    async def embed_query(self, text: str) -> list[float]:
        return (await self._embed([text]))[0]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return await self._embed(texts)

    async def _embed(self, inputs: Sequence[str]) -> list[list[float]]:
        if not can_connect_outbound():
            raise EuriEmbeddingError("Outbound network is restricted or offline.")
        key = self.settings.euri_api_key
        if key is None or not key.get_secret_value().strip():
            raise EuriEmbeddingError("EURI_API_KEY is not configured.")
        if not all(isinstance(text, str) and text.strip() for text in inputs):
            raise EuriEmbeddingError("Embedding inputs must be non-empty strings.")
        payload = {"model": self.settings.euri_embedding_model, "input": list(inputs)}
        headers = {"Authorization": f"Bearer {key.get_secret_value()}", "Content-Type": "application/json"}
        response: httpx.Response | None = None
        for attempt in range(self.settings.euri_max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.settings.euri_timeout_seconds) as client:
                    response = await client.post(self.settings.euri_embedding_base_url, headers=headers, json=payload)
                if response.status_code not in {408, 429, 500, 502, 503, 504}:
                    response.raise_for_status()
                    break
            except httpx.HTTPError as exc:
                if attempt >= self.settings.euri_max_retries:
                    raise EuriEmbeddingError("EURI embedding request failed.") from exc
            if attempt >= self.settings.euri_max_retries:
                status = response.status_code if response is not None else "unknown"
                raise EuriEmbeddingError(f"EURI embedding failed with HTTP status {status}.")
            await asyncio.sleep(0.5 * (2**attempt))
        if response is None:
            raise EuriEmbeddingError("EURI embedding did not return a response.")
        try:
            data = response.json()["data"]
            ordered = sorted(data, key=lambda item: item["index"])
            vectors = [item["embedding"] for item in ordered]
        except (KeyError, TypeError, ValueError) as exc:
            raise EuriEmbeddingError("EURI returned an invalid embedding payload.") from exc
        if len(vectors) != len(inputs) or not all(
            isinstance(vector, list) and vector and all(isinstance(value, (int, float)) for value in vector)
            for vector in vectors
        ):
            raise EuriEmbeddingError("EURI returned invalid embedding vectors.")
        dimensions = {len(vector) for vector in vectors}
        if len(dimensions) != 1:
            raise EuriEmbeddingError("EURI returned vectors with inconsistent dimensions.")
        self.vector_size = dimensions.pop()
        return [[float(value) for value in vector] for vector in vectors]
