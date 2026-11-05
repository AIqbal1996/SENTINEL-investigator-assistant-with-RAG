"""Live EURI connectivity check. It prints no secret values."""

import asyncio
import sys
from pathlib import Path

# Allow direct execution with `python scripts/test_euri_llm.py` from the repo.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.euri_llm import EuriLLMClient, EuriLLMError


async def main() -> int:
    client = EuriLLMClient()
    try:
        result = await client.generate_json('Return only a JSON object: {"status": "success"}.')
    except EuriLLMError as exc:
        print(f"EURI LLM check failed: {exc}")
        return 1
    if result.get("status") != "success":
        print("EURI LLM check failed: response did not contain status=success.")
        return 1
    print("EURI LLM check passed: valid JSON response received.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
