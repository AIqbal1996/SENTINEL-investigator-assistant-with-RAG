"""Connect to Qdrant Cloud and create SENTINEL's non-destructive policy collection."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.services.qdrant_service import QdrantPolicyStore, QdrantServiceError


def main() -> int:
    settings = get_settings()
    try:
        created = QdrantPolicyStore(settings).ensure_collection()
    except QdrantServiceError as exc:
        print(f"Qdrant setup failed: {exc}")
        return 1
    status = "created" if created else "already existed and was validated"
    print(
        f"Qdrant setup passed: collection '{settings.qdrant_collection}' {status} "
        f"with {settings.euri_embedding_dimension}-dimension cosine vectors and policy indexes."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
