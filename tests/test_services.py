"""Unit tests for individual SENTINEL services, stores, and fraud rules."""

import pytest

from app.schemas import ExplainResponse
from app.services.fraud_rules import (
    CODE_HIGH_AMOUNT,
    CODE_HIGH_DEVICE_RISK,
    CODE_HIGH_VELOCITY,
    CODE_NEW_DEVICE,
    CODE_SHARED_DEVICE,
    CODE_UNUSUAL_LOCATION,
    evaluate_fraud_rules,
)
from app.services.investigation_service import InvestigationService
from app.services.neo4j_service import Neo4jGraphStore, build_graph_context
from app.services.qdrant_service import QdrantPolicyStore
from app.services.transaction_store import TransactionNotFoundError, TransactionStore


def test_transaction_lookup_existing():
    """Test 7: Transaction lookup retrieves existing record."""
    store = TransactionStore()
    txn = store.get_transaction("TXN00001")
    assert txn["transaction_id"] == "TXN00001"
    assert "amount" in txn
    assert "customer_id" in txn


def test_transaction_lookup_unknown_raises_404_error():
    """Test 7b: Transaction lookup raises TransactionNotFoundError on missing record."""
    store = TransactionStore()
    with pytest.raises(TransactionNotFoundError):
        store.get_transaction("TXN_UNKNOWN_XYZ")


def test_neo4j_graph_lookup_and_context_builder():
    """Test 8: Neo4j graph lookup and context building."""
    graph_store = Neo4jGraphStore()
    raw = graph_store.get_neighborhood("TXN00001")
    assert raw is not None
    assert "customer_id" in raw

    ctx = build_graph_context(raw)
    assert ctx["customer_id"] == "CUST_101"
    assert ctx["is_shared_device"] is True
    assert len(ctx["signals"]) > 0


def test_qdrant_policy_search():
    """Test 9: Qdrant retrieval returns top-5 policy chunks with required metadata."""
    policy_store = QdrantPolicyStore()
    results = policy_store.search_policy("unrecognized device high risk", top_k=5)
    assert len(results) > 0
    assert len(results) <= 5
    top = results[0]
    assert "document_id" in top
    assert "chunk_id" in top
    assert "text" in top
    assert "score" in top
    assert top["document_id"] == "POL002"  # Device Fraud Policy


def test_fraud_rules_evaluation():
    """Test 12: Deterministic fraud rules evaluation across various feature combinations."""
    # Test high amount and velocity
    txn = {
        "amount": 7500.0,
        "velocity_1h": 8.0,
        "location": "Domestic",
    }
    codes = evaluate_fraud_rules(txn)
    assert CODE_HIGH_AMOUNT in codes
    assert CODE_HIGH_VELOCITY in codes
    assert CODE_UNUSUAL_LOCATION not in codes

    # Test genuine low risk (empty fired codes)
    genuine_txn = {
        "amount": 45.0,
        "velocity_1h": 1.0,
        "is_new_device": False,
        "location": "Domestic",
    }
    assert evaluate_fraud_rules(genuine_txn) == []


@pytest.mark.asyncio
async def test_investigation_service_orchestration_and_citations():
    """Test 10, 11, 13: End-to-end investigation, JSON schema, and citation grounding."""
    service = InvestigationService()
    result = await service.investigate_transaction("TXN00001")
    assert isinstance(result, ExplainResponse)
    assert result.transaction_id == "TXN00001"
    assert len(result.reason_codes) > 0
    assert len(result.cited_sources) > 0
    for citation in result.cited_sources:
        assert citation.document
        assert citation.chunk_id

