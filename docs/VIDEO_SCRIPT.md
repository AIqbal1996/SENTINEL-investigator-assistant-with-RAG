# SENTINEL Video Demonstration Script (5–10 Minutes)

Use this script for your YouTube video demonstration. You can read it naturally while sharing your screen.

---

## [0:00 - 1:00] Introduction & Problem Statement

**Visual:** Show project title and `README.md` on GitHub or VS Code.

> "Hello everyone! Today I am presenting **SENTINEL**, an Intelligent Fraud Investigator Assistant built with Python, FastAPI, and Retrieval-Augmented Generation (RAG).
> 
> In modern financial fraud detection, investigators face a big challenge: transaction features, device connections, and bank policies are stored in separate systems. Machine learning models often alert investigators with high risk scores, but they don't explain *why* or cite which policy rule was broken.
> 
> SENTINEL solves this. It takes a transaction ID, retrieves features from Supabase, checks device-sharing relationships in Neo4j, calculates transparent reason codes, finds the exact relevant compliance policies in Qdrant vector store, and uses Gemini to generate a grounded, auditable explanation with verified citations."

---

## [1:00 - 2:30] System Architecture & Database Roles

**Visual:** Scroll to the Mermaid Architecture Diagram in `README.md`.

> "Let's look at our architecture:
> 
> 1. **FastAPI**: Serves our core endpoints, including `GET /health` and `POST /explain`.
> 2. **Supabase**: Holds our transaction records—such as transaction ID, customer ID, amount, timestamp, location, and velocity.
> 3. **Neo4j AuraDB**: Acts as our graph database. It tracks customer-device relationships. For instance, if a fraudster is using one phone to access three different victim accounts, Neo4j flags that shared device syndicate immediately.
> 4. **Qdrant Cloud**: Our vector database storing policy chunks embedded with Gemini Embedding 2 at 3,072 dimensions.
> 5. **Gemini LLM**: Generates a structured JSON response using *only* the retrieved evidence.
> 
> Notice we also have an offline policy ingestion path that chunks bank guidelines and indexes them into Qdrant."

---

## [2:30 - 4:00] Code Walkthrough

**Visual:** Open VS Code editor and highlight the core files.

> "Now let's look at the codebase:
> 
> - In `app/main.py`: We have our FastAPI application exposing `POST /explain` with Pydantic request and response models.
> - In `app/services/transaction_store.py`: We fetch transaction features from Supabase with a deterministic local fallback.
> - In `app/services/neo4j_service.py`: We execute Cypher queries to extract device-sharing counts and build structured graph context.
> - In `app/services/fraud_rules.py`: Our deterministic rule engine calculates fired reason codes such as `HIGH_TRANSACTION_AMOUNT`, `NEW_DEVICE`, and `SHARED_SUSPICIOUS_DEVICE`. Crucially, ground-truth labels are never leaked to the AI prompt.
> - In `app/services/qdrant_service.py`: We perform top-k vector search to retrieve relevant policy chunks.
> - In `app/services/investigation_service.py`: We assemble the full context, prompt Gemini, and strictly validate that cited documents and chunk IDs actually exist."

---

## [4:00 - 6:00] Live API Demonstration in Swagger UI

**Visual:** Open browser to `http://127.0.0.1:8000/docs`.

> "Let's test the live API in Swagger UI!
> 
> First, let's test `GET /health`. Click 'Try it out' and 'Execute'.
> It returns HTTP 200 with status 'ok' and confirms that all services are ready.
> 
> Now, let's test `POST /explain` with a **Fraud Transaction**: `TXN00001`.
> Let's execute.
> 
> Look at the response:
> - HTTP Status: **200 OK**
> - Transaction ID: `TXN00001`
> - Fired Reason Codes: `HIGH_DEVICE_RISK`, `HIGH_TRANSACTION_AMOUNT`, `HIGH_TRANSACTION_VELOCITY`, `NEW_DEVICE`, `SHARED_SUSPICIOUS_DEVICE`, `UNUSUAL_LOCATION`.
> - Recommended Action: `Freeze account and escalate to senior investigator`.
> - Cited Sources: It cites `Transaction_Amount_Risk_Policy` chunk `POL001_CHUNK001`.
> 
> Now let's test a **Genuine Transaction**: `TXN00006`.
> Let's execute.
> - HTTP Status: **200 OK**
> - Fired Reason Codes: An empty array `[]` because no fraud rules were broken!
> - Recommended Action: `Approve transaction`.
> - Cited Source: `Genuine_Transaction_Clearance_Policy`.
> 
> Finally, let's test a non-existent transaction `TXN99999`:
> - It cleanly returns **HTTP 404 Not Found** with a clear error message."

---

## [6:00 - 7:30] 10-Transaction Validation & Retrieval Benchmark

**Visual:** Open the terminal in VS Code.

> "To guarantee production quality and meet all assignment requirements, we created automated evaluation scripts.
> 
> Let's run `python scripts/test_validation_transactions.py`.
> 
> Notice how it processes 5 fraud and 5 genuine transactions:
> - All 10 returned HTTP 200.
> - 100% passed Pydantic schema validation.
> - 100% passed citation verification.
> - Every individual result is saved under `tests/results/`.
> 
> Next, let's run `python scripts/evaluate_retrieval.py`.
> This benchmarks 10 known-answer fraud policy questions against our Qdrant policy store.
> 
> Look at the output:
> - Questions 1 through 10 all retrieved the expected policy document in Rank 1!
> - **Hit@5 Metric is 100.0%**.
> - All evaluation metrics are saved under `tests/retrieval_results/summary.json`."

---

## [7:30 - 8:30] Pytest Suite & Security

**Visual:** Run `pytest -v` in the terminal.

> "Let's also run our complete automated test suite with `pytest -v`.
> 
> Look at the test output:
> - All 14 tests pass!
> - Testing API endpoints, 404 handling, 422 validation, database lookups, fraud rules, graph context, citation validation, evaluation files, and secrets hygiene.
> 
> In terms of security:
> - All API keys and database passwords are kept in a Git-ignored `.env` file.
> - We use Pydantic `SecretStr` so credentials are never exposed in logs or API responses.
> - Cypher and SQL queries are parameterized to prevent injection attacks."

---

## [8:30 - 9:30] Conclusion & Assignment Compliance

**Visual:** Return to the Assignment Compliance table in `README.md`.

> "To conclude:
> - Our initial submission scored 4/15 due to missing endpoints, lack of transaction lookup, and absent validation runs.
> - We have now implemented every single missing component:
>   1. FastAPI application and `POST /explain` (3 marks)
>   2. Transaction store, Neo4j graph context, and Qdrant search (4 marks)
>   3. Grounded structured risk response with citation validation (3 marks)
>   4. 10 validation transaction responses saved to disk (1 mark)
>   5. 10-question retrieval Hit@5 benchmark (1 mark)
>   6. Complete UTF-8 README with Mermaid architecture diagram (1 mark)
>   7. Comprehensive setup docs and security hygiene (2 marks)
> - All 15 marks are addressed with verified code and saved artifacts.
> 
> Thank you for watching!"

