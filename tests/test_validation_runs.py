"""Tests verifying validation results and evaluation artifacts."""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_validation_transaction_artifacts_exist():
    """Test 14, 15, 20: 5 fraud and 5 genuine transaction result files exist and pass validation."""
    results_dir = PROJECT_ROOT / "tests" / "results"
    assert results_dir.exists(), "tests/results directory missing"

    for i in range(1, 6):
        fraud_file = results_dir / f"fraud_{i:02d}.json"
        assert fraud_file.exists(), f"Missing {fraud_file}"
        with open(fraud_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["http_status"] == 200
        assert data["schema_validation_passed"] is True
        assert data["citation_validation_passed"] is True
        assert len(data["response"]["reason_codes"]) > 0

    for i in range(1, 6):
        genuine_file = results_dir / f"genuine_{i:02d}.json"
        assert genuine_file.exists(), f"Missing {genuine_file}"
        with open(genuine_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["http_status"] == 200
        assert data["schema_validation_passed"] is True
        assert data["citation_validation_passed"] is True
        assert data["response"]["reason_codes"] == []
        assert "Approve" in data["response"]["recommended_action"]

    summary_file = results_dir / "validation_summary.json"
    assert summary_file.exists(), "validation_summary.json missing"
    with open(summary_file, "r", encoding="utf-8") as f:
        summary = json.load(f)
    assert summary["all_passed"] is True
    assert summary["total_transactions_tested"] == 10
    assert summary["http_200_rate_percent"] == 100.0


def test_retrieval_hit_at_5_artifacts_exist():
    """Test 16, 17: Ten retrieval questions are evaluated and Hit@5 is measured."""
    retrieval_dir = PROJECT_ROOT / "tests" / "retrieval_results"
    assert retrieval_dir.exists(), "tests/retrieval_results directory missing"

    q_file = retrieval_dir / "questions.json"
    r_file = retrieval_dir / "results.json"
    s_file = retrieval_dir / "summary.json"

    assert q_file.exists(), "questions.json missing"
    assert r_file.exists(), "results.json missing"
    assert s_file.exists(), "summary.json missing"

    with open(s_file, "r", encoding="utf-8") as f:
        summary = json.load(f)
    assert summary["total_questions"] == 10
    assert summary["hit_at_5_percent"] >= 80.0
    assert "Hit@5" in summary["metric_definition"]


def test_security_and_secrets_hygiene():
    """Test 19: Verify .env is ignored and no raw secrets appear in tracked files."""
    gitignore_file = PROJECT_ROOT / ".gitignore"
    assert gitignore_file.exists(), ".gitignore missing"
    content = gitignore_file.read_text(encoding="utf-8")
    assert ".env" in content

    # Verify .env.example contains no real credentials
    env_example = PROJECT_ROOT / ".env.example"
    assert env_example.exists()
    example_text = env_example.read_text(encoding="utf-8")
    for line in example_text.splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            assert v.strip() == "" or v.strip().startswith("https://") or v.strip() in {"gpt-5.3-instant", "gemini-embedding-2", "3072", "sentinel_policy_chunks", "neo4j"}

