"""Validation script testing 5 fraud and 5 genuine transactions through POST /explain.

Executes actual requests against the FastAPI endpoint, validates schemas, verifies citations,
and stores individual and summary output files into tests/results/.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from app.main import app
from app.schemas import ExplainResponse
from app.services.transaction_store import TransactionStore

RESULTS_DIR = PROJECT_ROOT / "tests" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

FRAUD_IDS = ["TXN00001", "TXN00002", "TXN00003", "TXN00004", "TXN00005"]
GENUINE_IDS = ["TXN00006", "TXN00007", "TXN00008", "TXN00009", "TXN00010"]


def run_validation_transactions() -> int:
    client = TestClient(app)
    store = TransactionStore()
    
    summary_records = []
    all_passed = True

    print("=" * 70)
    print("SENTINEL 10-TRANSACTION VALIDATION RUN (5 FRAUD, 5 GENUINE)")
    print("=" * 70)

    # Process 5 Fraud transactions
    for idx, tid in enumerate(FRAUD_IDS, start=1):
        filename = RESULTS_DIR / f"fraud_{idx:02d}.json"
        print(f"\n[FRAUD {idx}/5] Testing {tid}...")
        
        t0 = time.perf_counter()
        response = client.post("/explain", json={"transaction_id": tid})
        elapsed = time.perf_counter() - t0
        
        status_code = response.status_code
        schema_valid = False
        citation_valid = False
        resp_json = {}

        if status_code == 200:
            resp_json = response.json()
            try:
                validated = ExplainResponse.model_validate(resp_json)
                schema_valid = True
                citations = validated.cited_sources
                # Verify citations are non-empty and well-formed
                citation_valid = len(citations) > 0 and all(c.document and c.chunk_id for c in citations)
            except Exception as exc:
                print(f"  Schema validation error: {exc}")
        else:
            all_passed = False
            print(f"  FAILED: HTTP {status_code} - {response.text}")

        record = {
            "transaction_id": tid,
            "ground_truth_label": "FRAUD",
            "http_status": status_code,
            "execution_time_seconds": round(elapsed, 4),
            "schema_validation_passed": schema_valid,
            "citation_validation_passed": citation_valid,
            "response": resp_json,
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)

        summary_records.append(record)
        print(f"  -> HTTP {status_code} | Time: {elapsed:.4f}s | Schema: {schema_valid} | Citations: {citation_valid}")
        print(f"  -> Reason codes fired: {resp_json.get('reason_codes')}")
        print(f"  -> Saved to: {filename.relative_to(PROJECT_ROOT)}")

    # Process 5 Genuine transactions
    for idx, tid in enumerate(GENUINE_IDS, start=1):
        filename = RESULTS_DIR / f"genuine_{idx:02d}.json"
        print(f"\n[GENUINE {idx}/5] Testing {tid}...")
        
        t0 = time.perf_counter()
        response = client.post("/explain", json={"transaction_id": tid})
        elapsed = time.perf_counter() - t0
        
        status_code = response.status_code
        schema_valid = False
        citation_valid = False
        resp_json = {}

        if status_code == 200:
            resp_json = response.json()
            try:
                validated = ExplainResponse.model_validate(resp_json)
                schema_valid = True
                citations = validated.cited_sources
                citation_valid = len(citations) > 0 and all(c.document and c.chunk_id for c in citations)
            except Exception as exc:
                print(f"  Schema validation error: {exc}")
        else:
            all_passed = False
            print(f"  FAILED: HTTP {status_code} - {response.text}")

        record = {
            "transaction_id": tid,
            "ground_truth_label": "GENUINE",
            "http_status": status_code,
            "execution_time_seconds": round(elapsed, 4),
            "schema_validation_passed": schema_valid,
            "citation_validation_passed": citation_valid,
            "response": resp_json,
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)

        summary_records.append(record)
        print(f"  -> HTTP {status_code} | Time: {elapsed:.4f}s | Schema: {schema_valid} | Citations: {citation_valid}")
        print(f"  -> Reason codes fired: {resp_json.get('reason_codes')}")
        print(f"  -> Action: {resp_json.get('recommended_action')}")
        print(f"  -> Saved to: {filename.relative_to(PROJECT_ROOT)}")

    # Summary calculations
    total_count = len(summary_records)
    successful_http = sum(1 for r in summary_records if r["http_status"] == 200)
    schema_passed = sum(1 for r in summary_records if r["schema_validation_passed"])
    citations_passed = sum(1 for r in summary_records if r["citation_validation_passed"])
    avg_latency = sum(r["execution_time_seconds"] for r in summary_records) / total_count

    summary_file = RESULTS_DIR / "validation_summary.json"
    summary_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_transactions_tested": total_count,
        "fraud_transactions_count": len(FRAUD_IDS),
        "genuine_transactions_count": len(GENUINE_IDS),
        "http_200_rate_percent": round((successful_http / total_count) * 100, 2),
        "schema_validation_pass_rate_percent": round((schema_passed / total_count) * 100, 2),
        "citation_validation_pass_rate_percent": round((citations_passed / total_count) * 100, 2),
        "average_latency_seconds": round(avg_latency, 4),
        "all_passed": all_passed and (schema_passed == total_count) and (citations_passed == total_count),
        "results": summary_records,
    }

    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    print("\n" + "=" * 70)
    print(f"VALIDATION COMPLETED: {successful_http}/{total_count} HTTP 200s, {schema_passed}/{total_count} Schemas Valid")
    print(f"Average Latency: {avg_latency:.4f}s")
    print(f"Summary written to: {summary_file.relative_to(PROJECT_ROOT)}")
    print("=" * 70)

    return 0 if summary_data["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(run_validation_transactions())

