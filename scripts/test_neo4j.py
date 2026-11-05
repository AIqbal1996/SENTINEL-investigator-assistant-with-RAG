"""Live, read-only Neo4j AuraDB connectivity test."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.neo4j_service import Neo4jGraphStore, Neo4jServiceError


def main() -> int:
    try:
        Neo4jGraphStore().verify_connection()
    except Neo4jServiceError as exc:
        print(f"Neo4j check failed: {exc}")
        return 1
    print("Neo4j check passed: AuraDB connectivity verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
