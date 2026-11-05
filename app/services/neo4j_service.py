"""Neo4j AuraDB adapter with parameterized, read-only investigation queries."""

from __future__ import annotations

from typing import Any

from neo4j import GraphDatabase

from app.config import Settings, get_settings


class Neo4jServiceError(RuntimeError):
    """Safe Neo4j error which never includes credentials."""


class Neo4jGraphStore:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _driver(self):
        password = self.settings.neo4j_password
        if not self.settings.neo4j_uri or password is None or not password.get_secret_value().strip():
            raise Neo4jServiceError("NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD must be configured.")
        return GraphDatabase.driver(
            self.settings.neo4j_uri,
            auth=(self.settings.neo4j_username, password.get_secret_value().strip()),
            connection_timeout=self.settings.euri_timeout_seconds,
        )

    def verify_connection(self) -> None:
        try:
            with self._driver() as driver:
                driver.verify_connectivity()
        except Neo4jServiceError:
            raise
        except Exception as exc:
            raise Neo4jServiceError("Neo4j connectivity verification failed.") from exc

    def get_neighborhood(self, transaction_id: str) -> dict[str, Any] | None:
        """Retrieve customer/device signals with parameterized Cypher only."""
        query = """
        MATCH (t:Transaction {transaction_id: $transaction_id})
        OPTIONAL MATCH (c:Customer)-[:MADE]->(t)
        OPTIONAL MATCH (t)-[:USED_DEVICE]->(d:Device)
        OPTIONAL MATCH (other:Customer)-[:USES]->(d)
        WITH t, c, d, count(DISTINCT other) AS shared_customer_count
        OPTIONAL MATCH (c)-[:USES]->(customer_device:Device)
        RETURN c.customer_id AS customer_id,
               d.device_id AS device_id,
               shared_customer_count,
               count(DISTINCT customer_device) AS customer_device_count
        """
        try:
            with self._driver() as driver:
                records, _, _ = driver.execute_query(
                    query,
                    transaction_id=transaction_id,
                    database_=self.settings.neo4j_database,
                )
            if not records:
                return None
            return records[0].data()
        except Exception as exc:
            raise Neo4jServiceError("Neo4j neighborhood retrieval failed.") from exc
