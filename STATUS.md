# Faro – Current State & What Needs to Be Implemented

This file tracks implementation status against [SPEC.md](./SPEC.md) and the roadmap. All four roadmap items (structured ingestion, chain selector, RAG, LLM) are implemented.

---

## ✅ Implemented

| Area | Status |
|------|--------|
| **Sprint 1 – Backend & Etherscan** | FastAPI app, POST `/api/investigate` (address, chain_id → risk_score, summary, evidence). Etherscan V2 client: `get_tx_list`, `get_wallet_summary` (forensic story string). Config (env), CORS from env. |
| **Sprint 1 – Neo4j** | Driver created at startup, stored in `app.state.neo4j_driver`; shared by routes. Connection optional (backend runs without Neo4j). |
| **Sprint 1 – Ops** | Docker Compose (backend + Neo4j), Dockerfile (non-root, healthcheck), Makefile (up, down, dev-backend, dev-frontend, env-setup). |
| **Sprint 3 – Frontend** | Vue 3 + Pinia, Dashboard: address input, Investigate button, display result (risk score band, summary, evidence). Store calls `/api/investigate` with `chain_id` (default 1). |
| **Sprint 1 – Structured ingestion** | `ingest_wallet_transactions`: MERGE Wallet + SENT_FUNDS from Etherscan txs (batched, idempotent). Called from investigate. |
| **Sprint 2 – RAG** | ReportChunk + vector index; `get_rag_context` (OpenAI embed + vector query); POST `/api/ingest-doc` for PDF (chunk, embed, write). |
| **Sprint 2 – LLM** | `synthesize_risk` via OpenAI-compatible API (OpenAI / OpenRouter / self-hosted via `OPENAI_BASE_URL`); else heuristic. |
| **Sprint 3 – Chain selector** | Dashboard: chain dropdown (Ethereum, Base, Arbitrum One); `startInvestigation(address, chainId)`. |
| **Sprint 4 – Graph** | `get_graph_context` Cypher; graph populated by structured ingestion. |

---

## What to implement next

Prioritized by impact and dependency.

### High value (done)

1. **Blacklisted / Mixer seeding** – POST `/api/tag-address` with `{ address, tag: "Blacklisted" | "Mixer" }`; `graph_tags.tag_wallet` MERGEs Wallet and adds the label so graph context can flag "N hops from known bad actor."
2. **Tests** – `backend/tests/`: unit tests for `wallet_story_from_txs`, `format_timestamp`, `_normalize_tx_for_ingest`, `chunk_text`; integration tests for `/api/investigate` (mocked) and `/api/tag-address`. Run with `cd backend && PYTHONPATH=. pytest tests -v`.
3. **Doc-ingest in the UI** – Dashboard section "Upload threat report" with PDF file input, optional source label, and success/error message; calls POST `/api/ingest-doc`.

### Nice to have

4. **`graph_summary` in API response**  
   SPEC §7: expose graph context as a top-level field (e.g. `graph_summary: str | null`) in `InvestigateResponse` so the frontend can show it separately from `evidence`.

5. **Latency &lt;3s (SPEC §5)**  
   Measure end-to-end investigate time; optionally run Etherscan fetch and Neo4j graph + RAG in parallel where possible, and add timeouts so one slow dependency doesn't block the whole response.

6. **Evaluation / KPIs**  
   Labelled set of known bad vs good wallets; compute precision/recall and track "3+ evidence bullets" for high-risk results. Harness can be a script or a small internal endpoint.

### Optional polish

- **Investigation history** in the frontend (e.g. last N addresses + results in Pinia or localStorage).
- **Configurable RAG chunk size/overlap** via env or API params.
- **Health endpoint** that checks Neo4j and (optionally) LLM connectivity and returns degraded status when dependencies are down.
