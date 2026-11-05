"""Qdrant Cloud collection management for SENTINEL policy chunks."""

from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.config import Settings, get_settings


class QdrantServiceError(RuntimeError):
    """Safe error that never exposes the cluster URL or API key."""


class QdrantPolicyStore:
    """Manages the single policy-chunk collection without destructive resets."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _client(self) -> QdrantClient:
        key = self.settings.qdrant_api_key
        if not self.settings.qdrant_url or key is None or not key.get_secret_value().strip():
            raise QdrantServiceError("QDRANT_URL and QDRANT_API_KEY must be configured.")
        return QdrantClient(
            url=self.settings.qdrant_url,
            # Environment editors can leave a trailing newline inside quoted values.
            api_key=key.get_secret_value().strip(),
            timeout=self.settings.euri_timeout_seconds,
        )

    def ensure_collection(self) -> bool:
        """Connect and create the collection/indexes. Returns True if newly created."""
        try:
            client = self._client()
            existing = {item.name for item in client.get_collections().collections}
            created = self.settings.qdrant_collection not in existing
            if created:
                client.create_collection(
                    collection_name=self.settings.qdrant_collection,
                    vectors_config=models.VectorParams(
                        size=self.settings.euri_embedding_dimension,
                        distance=models.Distance.COSINE,
                    ),
                )
            else:
                info = client.get_collection(self.settings.qdrant_collection)
                vector_config = info.config.params.vectors
                if not isinstance(vector_config, models.VectorParams) or vector_config.size != self.settings.euri_embedding_dimension:
                    raise QdrantServiceError(
                        "Existing Qdrant collection has a vector size incompatible with Gemini Embedding 2."
                    )
            for field_name in ("document_id", "document_name", "chunk_id", "section"):
                client.create_payload_index(
                    collection_name=self.settings.qdrant_collection,
                    field_name=field_name,
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )
            return created
        except QdrantServiceError:
            raise
        except Exception as exc:
            raise QdrantServiceError("Qdrant connection or collection setup failed.") from exc
