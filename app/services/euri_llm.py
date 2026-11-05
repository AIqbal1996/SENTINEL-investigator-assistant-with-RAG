"""Minimal, guarded EURI chat-completions client.

The client follows the OpenAI-compatible request shape supplied by the project
owner.  It keeps transport details configurable and never logs credentials or
model prompts containing sensitive transaction data.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from typing import Any

import httpx

from app.config import Settings, get_settings
from app.services.network import can_connect_outbound


class EuriLLMError(RuntimeError):
    """Safe, non-secret-bearing error raised when EURI generation fails."""


class EuriLLMClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def endpoint(self) -> str:
        return f"{self.settings.euri_api_base_url.rstrip('/')}/chat/completions"

    async def generate_json(self, user_prompt: str, system_prompt: str | None = None) -> dict[str, Any]:
        """Request a JSON object and reject malformed model output."""
        if not can_connect_outbound():
            raise EuriLLMError("Outbound network is restricted or offline.")
        key = self.settings.euri_api_key
        if key is None or not key.get_secret_value().strip():
            raise EuriLLMError("EURI_API_KEY is not configured.")

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})
        payload = {
            "model": self.settings.euri_llm_model,
            "messages": messages,
            "temperature": 0,
        }
        headers = {
            "Authorization": f"Bearer {key.get_secret_value()}",
            "Content-Type": "application/json",
        }

        response: httpx.Response | None = None
        for attempt in range(self.settings.euri_max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.settings.euri_timeout_seconds) as client:
                    response = await client.post(self.endpoint, headers=headers, json=payload)
                if response.status_code not in {408, 429, 500, 502, 503, 504}:
                    response.raise_for_status()
                    break
            except httpx.HTTPError as exc:
                if attempt >= self.settings.euri_max_retries:
                    raise EuriLLMError("EURI generation request failed.") from exc

            if attempt >= self.settings.euri_max_retries:
                status = response.status_code if response is not None else "unknown"
                raise EuriLLMError(f"EURI generation failed with HTTP status {status}.")
            await asyncio.sleep(0.5 * (2**attempt))

        if response is None:
            raise EuriLLMError("EURI generation did not return a response.")
        try:
            body: Mapping[str, Any] = response.json()
            content = body["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise TypeError("content was not text")
            parsed = json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise EuriLLMError("EURI returned an invalid JSON completion.") from exc
        if not isinstance(parsed, dict):
            raise EuriLLMError("EURI JSON completion must be an object.")
        return parsed
