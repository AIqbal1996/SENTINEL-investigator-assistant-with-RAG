"""Test script verifying health and explain endpoints with TestClient."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from app.main import app


def main() -> int:
    client = TestClient(app)

    print("1. Testing GET /health...")
    r_health = client.get("/health")
    print("Health response:", r_health.status_code, r_health.json())
    assert r_health.status_code == 200, f"Health check failed: {r_health.status_code}"
    assert r_health.json()["status"] == "ok"

    print("\n2. Testing POST /explain with Fraud transaction (TXN00001)...")
    r_fraud = client.post("/explain", json={"transaction_id": "TXN00001"})
    print("Fraud status:", r_fraud.status_code)
    fraud_data = r_fraud.json()
    print("Fraud body:", fraud_data)
    assert r_fraud.status_code == 200, f"Fraud explain failed: {r_fraud.status_code}"
    assert fraud_data["transaction_id"] == "TXN00001"
    assert len(fraud_data["reason_codes"]) > 0
    assert len(fraud_data["cited_sources"]) > 0

    print("\n3. Testing POST /explain with Genuine transaction (TXN00006)...")
    r_genuine = client.post("/explain", json={"transaction_id": "TXN00006"})
    print("Genuine status:", r_genuine.status_code)
    genuine_data = r_genuine.json()
    print("Genuine body:", genuine_data)
    assert r_genuine.status_code == 200, f"Genuine explain failed: {r_genuine.status_code}"
    assert genuine_data["transaction_id"] == "TXN00006"
    assert genuine_data["reason_codes"] == []
    assert "Approve" in genuine_data["recommended_action"]

    print("\n4. Testing POST /explain with 404 Unknown transaction...")
    r_404 = client.post("/explain", json={"transaction_id": "TXN_NONEXISTENT"})
    print("404 status:", r_404.status_code, r_404.json())
    assert r_404.status_code == 404, f"Expected 404, got {r_404.status_code}"

    print("\n5. Testing POST /explain with 422 Invalid payload...")
    r_422 = client.post("/explain", json={"wrong_key": 123})
    print("422 status:", r_422.status_code)
    assert r_422.status_code == 422, f"Expected 422, got {r_422.status_code}"

    print("\n>>> ALL PIPELINE TESTS PASSED SUCCESSFULLY! <<<")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

