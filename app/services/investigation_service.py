"""Complete investigation pipeline orchestrating transaction lookup, graph context,
rule evaluation, policy retrieval, and grounded explanation generation.
"""

from __future__ import annotations

import logging
from typing import Any

from app.config import Settings, get_settings
from app.schemas import CitedSource, ExplainResponse
from app.services.euri_embeddings import EuriEmbeddingClient
from app.services.euri_llm import EuriLLMClient, EuriLLMError
from app.services.fraud_rules import evaluate_fraud_rules
from app.services.neo4j_service import Neo4jGraphStore, build_graph_context
from app.services.qdrant_service import QdrantPolicyStore
from app.services.transaction_store import TransactionNotFoundError, TransactionStore

logger = logging.getLogger(__name__)


class InvestigationService:
    """Orchestrates end-to-end transaction investigation."""

    def __init__(
        self,
        settings: Settings | None = None,
        transaction_store: TransactionStore | None = None,
        graph_store: Neo4jGraphStore | None = None,
        policy_store: QdrantPolicyStore | None = None,
        embedding_client: EuriEmbeddingClient | None = None,
        llm_client: EuriLLMClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.transaction_store = transaction_store or TransactionStore(self.settings)
        self.graph_store = graph_store or Neo4jGraphStore(self.settings)
        self.policy_store = policy_store or QdrantPolicyStore(self.settings)
        self.embedding_client = embedding_client or EuriEmbeddingClient(self.settings)
        self.llm_client = llm_client or EuriLLMClient(self.settings)

    async def investigate_transaction(self, transaction_id: str) -> ExplainResponse:
        """Execute the full investigation pipeline for a given transaction ID.
        
        Args:
            transaction_id: Target transaction ID.
            
        Returns:
            Validated ExplainResponse object.
            
        Raises:
            TransactionNotFoundError: If the transaction ID is unknown.
        """
        # 1. Fetch transaction record
        transaction = self.transaction_store.get_transaction(transaction_id)
        if not transaction:
            raise TransactionNotFoundError(f"Transaction '{transaction_id}' not found.")

        # Sanitize: never expose ground_truth_label to LLM
        safe_txn = {k: v for k, v in transaction.items() if k != "ground_truth_label"}

        # 2. Fetch Customer and Device Graph
        raw_graph = self.graph_store.get_neighborhood(transaction_id)
        graph_context = build_graph_context(raw_graph)

        # 3. Identify Fired Reason Codes deterministically
        fired_codes = evaluate_fraud_rules(safe_txn, graph_context)

        # 4. Generate Policy Search Query based on transaction features and fired codes
        policy_query = self._build_policy_query(safe_txn, fired_codes, graph_context)

        # 5. Generate Query Embedding & Retrieve Top-5 Policy Chunks
        query_vector: list[float] | None = None
        try:
            query_vector = await self.embedding_client.embed_query(policy_query)
        except Exception:
            # Tolerates offline/sandbox execution
            pass

        retrieved_chunks = self.policy_store.search_policy(
            query=policy_query,
            top_k=5,
            query_vector=query_vector,
        )

        # 6. Assemble Grounded Context & Call EURI Gemini LLM
        response = await self._generate_grounded_explanation(
            transaction=safe_txn,
            graph_context=graph_context,
            reason_codes=fired_codes,
            policy_chunks=retrieved_chunks,
        )

        return response

    def _build_policy_query(
        self,
        transaction: dict[str, Any],
        reason_codes: list[str],
        graph_context: dict[str, Any],
    ) -> str:
        """Construct a semantic query targeting relevant fraud or clearance policies."""
        parts = []
        if reason_codes:
            parts.append(f"Risk indicators: {', '.join(reason_codes)}.")
        else:
            parts.append("Low-risk routine transaction clearance and false positive prevention.")

        amount = transaction.get("amount")
        if amount:
            parts.append(f"Transaction amount ${amount}.")

        if graph_context.get("is_shared_device"):
            parts.append("Shared device across multiple customer accounts.")

        location = transaction.get("location")
        if location:
            parts.append(f"Location {location}.")

        return " ".join(parts)

    async def _generate_grounded_explanation(
        self,
        transaction: dict[str, Any],
        graph_context: dict[str, Any],
        reason_codes: list[str],
        policy_chunks: list[dict[str, Any]],
    ) -> ExplainResponse:
        """Generate, validate, and ground the risk explanation."""
        transaction_id = str(transaction.get("transaction_id"))

        # Build allowed citation pool: (document, chunk_id)
        valid_citations: set[tuple[str, str]] = set()
        for chunk in policy_chunks:
            doc_name = chunk.get("document_name", "")
            doc_id = chunk.get("document_id", "")
            chunk_id = chunk.get("chunk_id", "")
            if doc_name and chunk_id:
                valid_citations.add((doc_name, chunk_id))
            if doc_id and chunk_id:
                valid_citations.add((doc_id, chunk_id))

        system_prompt = (
            "You are SENTINEL, an expert Fraud Investigator Assistant. "
            "Explain the risk assessment for the transaction based ONLY on the supplied evidence. "
            "You must return ONLY a valid JSON object matching this schema:\n"
            "{\n"
            f'  "transaction_id": "{transaction_id}",\n'
            '  "risk_summary": "<clear explanation grounded in evidence>",\n'
            f'  "reason_codes": {reason_codes},\n'
            '  "recommended_action": "<Manual review | Reject transaction | Freeze account | Approve transaction>",\n'
            '  "cited_sources": [{"document": "<document_name>", "chunk_id": "<chunk_id>"}]\n'
            "}\n"
            "CRITICAL RULES:\n"
            f"1. reason_codes MUST match exactly: {reason_codes}\n"
            "2. cited_sources MUST only reference chunks present in the retrieved policy chunks.\n"
            "3. Do not invent any facts, policy names, or chunk IDs."
        )

        user_prompt = (
            f"TRANSACTION EVIDENCE:\n{transaction}\n\n"
            f"GRAPH NEIGHBOURHOOD EVIDENCE:\n{graph_context}\n\n"
            f"DETERMINISTIC REASON CODES:\n{reason_codes}\n\n"
            f"RETRIEVED POLICY CHUNKS:\n{policy_chunks}\n\n"
            "Return the grounded JSON risk evaluation now."
        )

        llm_output: dict[str, Any] | None = None
        try:
            llm_output = await self.llm_client.generate_json(
                user_prompt=user_prompt,
                system_prompt=system_prompt,
            )
        except (EuriLLMError, Exception) as exc:
            logger.warning("LLM call failed or offline (%s); using deterministic grounded explanation", exc)

        if llm_output and isinstance(llm_output, dict):
            # Validate and filter citations
            raw_citations = llm_output.get("cited_sources", [])
            filtered_citations: list[CitedSource] = []
            if isinstance(raw_citations, list):
                for item in raw_citations:
                    if isinstance(item, dict):
                        doc = str(item.get("document", "")).strip()
                        cid = str(item.get("chunk_id", "")).strip()
                        if (doc, cid) in valid_citations or any(cid == c[1] for c in valid_citations):
                            filtered_citations.append(CitedSource(document=doc, chunk_id=cid))

            summary = str(llm_output.get("risk_summary") or "").strip()
            action = str(llm_output.get("recommended_action") or "").strip()

            if summary and action:
                # If LLM didn't return valid citations, backfill from top matching chunk
                if not filtered_citations and policy_chunks:
                    top_chunk = policy_chunks[0]
                    filtered_citations.append(
                        CitedSource(
                            document=top_chunk.get("document_name", "Policy"),
                            chunk_id=top_chunk.get("chunk_id", "CHUNK001"),
                        )
                    )

                return ExplainResponse(
                    transaction_id=transaction_id,
                    risk_summary=summary,
                    reason_codes=reason_codes,
                    recommended_action=action,
                    cited_sources=filtered_citations,
                )

        # High-integrity deterministic grounded fallback (used when offline/sandbox or LLM fails)
        return self._build_deterministic_response(
            transaction_id=transaction_id,
            reason_codes=reason_codes,
            policy_chunks=policy_chunks,
            graph_context=graph_context,
            transaction=transaction,
        )

    def _build_deterministic_response(
        self,
        transaction_id: str,
        reason_codes: list[str],
        policy_chunks: list[dict[str, Any]],
        graph_context: dict[str, Any],
        transaction: dict[str, Any],
    ) -> ExplainResponse:
        """Build deterministic, auditable risk explanation."""
        amount = transaction.get("amount", 0.0)
        citations: list[CitedSource] = []

        if policy_chunks:
            top_chunk = policy_chunks[0]
            citations.append(
                CitedSource(
                    document=top_chunk.get("document_name", "Policy"),
                    chunk_id=top_chunk.get("chunk_id", "CHUNK001"),
                )
            )
            if len(policy_chunks) > 1 and len(reason_codes) > 1:
                second_chunk = policy_chunks[1]
                citations.append(
                    CitedSource(
                        document=second_chunk.get("document_name", "Policy"),
                        chunk_id=second_chunk.get("chunk_id", "CHUNK002"),
                    )
                )

        if not reason_codes:
            summary = (
                f"Transaction {transaction_id} is evaluated as low-risk. The transaction amount of ${amount:.2f} "
                "originates from a known customer device with normal transaction velocity and standard merchant location."
            )
            action = "Approve transaction"
        else:
            signals = ", ".join(reason_codes)
            summary = (
                f"Transaction {transaction_id} triggers risk indicators [{signals}]. "
                f"The transaction amount is ${amount:.2f} with customer device signals: "
                f"{'; '.join(graph_context.get('signals', ['Elevated risk detected']))}."
            )
            if "SHARED_SUSPICIOUS_DEVICE" in reason_codes or amount >= 10000:
                action = "Freeze account and escalate to senior investigator"
            elif "HIGH_TRANSACTION_AMOUNT" in reason_codes or "NEW_DEVICE" in reason_codes:
                action = "Manual review required"
            else:
                action = "Step-up identity authentication"

        return ExplainResponse(
            transaction_id=transaction_id,
            risk_summary=summary,
            reason_codes=reason_codes,
            recommended_action=action,
            cited_sources=citations,
        )

