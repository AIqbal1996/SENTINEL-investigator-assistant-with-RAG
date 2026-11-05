# SENTINEL Debugging Audit & Gap Analysis

**Date:** 2026-11-05  
**Auditor:** Senior Python Engineer & Independent Code Evaluator  
**Baseline Score:** 4/15 Marks  
**Target:** 15/15 Marks Compliance  

---

## 1. Executive Summary

A comprehensive inspection of the SENTINEL repository was performed. The prior submission scored **4/15** because it only contained baseline adapter wrappers and configuration skeletons without an executable FastAPI application, transaction store, policy indexing/search, orchestrator, validation runs, retrieval evaluation, or complete documentation.

Every finding, impacted component, severity level, and required resolution is documented below.

---

## 2. Component-by-Component Audit Findings

| Component / Requirement | Initial Status | Severity | Problem Description | Required Fix | Verification |
|---|---|---|---|---|---|
| **FastAPI Application & `/explain`** | MISSING (0/3) | **CRITICAL** | `app/main.py` does not exist. No FastAPI app is exposed. No `GET /health` or `POST /explain` endpoints. | Create `app/main.py` with FastAPI, Pydantic schemas, `/health`, `/explain`, and middleware/error handlers. | `test_api.py` and `uvicorn app.main:app` test with TestClient. |
| **Transaction Database Lookup** | MISSING (Part of 2/4) | **CRITICAL** | `app/services/transaction_store.py` does not exist. No Supabase or local deterministic repository exists. | Create `TransactionStore` supporting Supabase REST API with local deterministic seed fallback for testing and offline resilience. | Unit and integration tests for existing/unknown/404 transactions. |
| **Graph Context & Relationships** | INCOMPLETE (Part of 2/4) | HIGH | `Neo4jGraphStore.get_neighborhood` exists but has no context formatter, and AuraDB connection is blocked by TLS interception on some environments. | Implement `build_graph_context` formatter, handle TLS connection gracefully with fallback or `neo4j+ssc://`, and seed deterministic graph relationships. | Integration test verifying formatted customer/device context. |
| **Qdrant Policy Search** | INCOMPLETE (Part of 2/4) | **CRITICAL** | `QdrantPolicyStore` only creates the collection. There is no chunking, document indexing, or semantic top-k retrieval method. | Implement `index_policy_chunks` and `search_policy(query, top_k=5)` with payload preservation (`document_id`, `chunk_id`, etc.). | Integration test retrieving relevant policy chunks with cosine scores. |
| **Investigation Orchestration** | MISSING (Part of 1/3) | **CRITICAL** | No pipeline exists to coordinate Transaction -> Graph -> Rules -> Query Embedding -> Qdrant -> Grounded Prompt -> LLM -> Validation. | Implement `app/services/investigation_service.py` orchestrating all stages with dependency injection. | End-to-end execution of full pipeline. |
| **Fraud Reason Codes** | MISSING (Part of 1/3) | HIGH | No deterministic rule engine exists. LLMs cannot be allowed to fabricate reason codes. | Create `app/services/fraud_rules.py` with transparent rules (high amount, velocity, new device, shared device, location). | Unit tests across boundary conditions, single/multiple/no indicators. |
| **Grounded LLM & Citation Validation** | INCOMPLETE (Part of 1/3) | **CRITICAL** | `EuriLLMClient` exists, but there are no Pydantic output schemas, strict citation validation, or hallucination guards. | Create `app/schemas.py` and response validator ensuring cited documents/chunks exist in retrieved Qdrant context. | Unit tests validating valid JSON and rejecting invented citations. |
| **10 Validation Transactions** | MISSING (0/1) | **CRITICAL** | No saved outputs for 5 fraud and 5 genuine transactions. | Create `scripts/test_validation_transactions.py` executing 10 transactions through `/explain` and saving JSONs in `tests/results/`. | 10 JSON output files and `validation_summary.json` generated. |
| **Retrieval Hit@5 Evaluation** | MISSING (0/1) | **CRITICAL** | No 10-question evaluation or Hit@5 calculation script. | Create `scripts/evaluate_retrieval.py` testing 10 policy queries against Qdrant and computing Hit@5 %. | `tests/retrieval_results/questions.json`, `results.json`, and `summary.json`. |
| **README & Architecture Diagram** | DEFICIENT (0/1) | HIGH | Encoding issues and missing detailed setup, architecture, and live run instructions. | Rebuild `README.md` in clean UTF-8 with GitHub Mermaid diagram, database descriptions, and API guides. | Render check in GitHub/VS Code. |
| **Setup, Config & Secrets** | INCOMPLETE (1/2) | MEDIUM | `app/config.py` lacks Supabase settings. Missing pytest suite and test configs. | Update `app/config.py`, `.env.example`, `requirements.txt`, and create comprehensive pytest suite. | Clean `pytest -v` run. |
| **Beginner Explanation & Script** | MISSING | MEDIUM | No beginner-friendly video walkthrough script or simple architecture documentation. | Create `docs/SIMPLE_PROJECT_EXPLANATION.md` and `docs/VIDEO_SCRIPT.md`. | Verification of documents. |

---

## 3. Immediate Action Plan

1. **Phase 2**: Implement `app/main.py` and `app/schemas.py`.
2. **Phase 3**: Implement `app/services/transaction_store.py` with Supabase support and synthetic seed data.
3. **Phase 4**: Implement `app/services/fraud_rules.py` and enhance `Neo4jGraphStore` context building.
4. **Phase 5**: Extend `app/services/qdrant_service.py` with policy chunk indexing and top-k search; create policy corpus.
5. **Phase 6 & 8**: Build `app/services/investigation_service.py` with strict grounding and citation validation.
6. **Phase 9 & 10**: Run 10 validation transactions and Hit@5 retrieval evaluation.
7. **Phase 11–15**: Build test suite (`pytest`), repair `README.md`, write video script/simple explanations, and deliver final evaluation audit.

