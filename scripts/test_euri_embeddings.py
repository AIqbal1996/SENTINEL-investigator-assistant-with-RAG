"""Live Gemini Embedding 2 connectivity/dimensionality check."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.euri_embeddings import EuriEmbeddingClient, EuriEmbeddingError


async def main() -> int:
    client = EuriEmbeddingClient()
    try:
        query_vector = await client.embed_query("How should high-value transactions be reviewed?")
        document_vectors = await client.embed_documents([
            "High-value transactions require a risk review.",
            "A shared device may indicate coordinated fraud.",
        ])
    except EuriEmbeddingError as exc:
        print(f"EURI embedding check failed: {exc}")
        return 1
    if len(query_vector) != client.vector_size or any(len(vector) != client.vector_size for vector in document_vectors):
        print("EURI embedding check failed: inconsistent vector dimensions.")
        return 1
    print(f"EURI embedding check passed: Gemini Embedding 2 returned {client.vector_size}-dimension vectors.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
