"""Tests for FastAPI endpoints (/health, /explain, schema validation)."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import ExplainResponse, HealthResponse


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_health_endpoint(client):
    """Test 1 & 2: FastAPI starts and /health returns 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "api" in data["services"]
    HealthResponse.model_validate(data)


def test_explain_endpoint_exists(client):
    """Test 3: /explain is accessible and visible in OpenAPI schema."""
    openapi = app.openapi()
    assert "/explain" in openapi["paths"]
    assert "post" in openapi["paths"]["/explain"]


def test_explain_valid_fraud_transaction(client):
    """Test 4: Valid transaction returns HTTP 200 with schema matching."""
    response = client.post("/explain", json={"transaction_id": "TXN00001"})
    assert response.status_code == 200
    data = response.json()
    validated = ExplainResponse.model_validate(data)
    assert validated.transaction_id == "TXN00001"
    assert len(validated.reason_codes) > 0
    assert len(validated.cited_sources) > 0


def test_explain_missing_transaction_404(client):
    """Test 5: Missing transaction returns HTTP 404."""
    response = client.post("/explain", json={"transaction_id": "TXN_NOT_EXIST_999"})
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_explain_invalid_request_422(client):
    """Test 6: Invalid request structure returns HTTP 422."""
    response = client.post("/explain", json={"wrong_attribute": 12345})
    assert response.status_code == 422

