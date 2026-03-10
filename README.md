# Faro – Blockchain Forensic RAG Agent

AI-driven wallet risk investigator: combines **live on-chain data** (Etherscan), **graph relationships** (Neo4j), and **threat intel** (RAG over PDFs) to produce explainable risk reports.

- **Spec:** [SPEC.md](./SPEC.md) – architecture, pipeline, and roadmap.  
- **Status:** [STATUS.md](./STATUS.md) – what’s implemented and what’s left to build.

## Stack

| Layer   | Tech              |
|--------|--------------------|
| Frontend | Vue 3, Pinia, Vite, Tailwind, Biome |
| Backend  | FastAPI (Python)   |
| Data     | Etherscan V2 API  |
| Graph + Vector | Neo4j (optional) |

## Quick start

From the repo root you can use **Make** for common commands: `make env-setup` (copy `.env`), `make up` (Docker), `make dev-backend`, `make dev-frontend`, `make down`, `make logs`, **`make test`** (run backend tests).

### Running the tests

Most tests **mock** Etherscan and Neo4j, so they run with no services. Two tests are **Neo4j integration** tests: they run **real Cypher** against a running Neo4j so we can verify queries and graph behaviour. Those two are **skipped** when Neo4j is not configured or not reachable.

From the repo root:

```bash
make test
```

- **Without Neo4j:** 20 passed, 2 skipped (fast, no Docker).
- **With Neo4j:** start it first (`make up`), set `NEO4J_PASSWORD` in `backend/.env`, then `make test` again → 22 passed (includes real tag + graph-context Cypher tests).

To run only the Neo4j integration tests when Neo4j is up:

```bash
cd backend && PYTHONPATH=. python -m pytest tests -m neo4j -v
```

Use **Docker Compose** when you want to run the **real app** (backend + Neo4j) or the **full test suite including Neo4j query tests**.

**Why are 2 tests skipped?** Those two are **Neo4j integration tests** (`tests/test_neo4j_integration.py`). They need a real Neo4j (e.g. `make up`) and `NEO4J_PASSWORD` in `backend/.env`. The `neo4j_driver` fixture tries to connect; if Neo4j isn’t there, it calls `pytest.skip(...)` so the test is skipped instead of failing. So: **20 tests** = no services; **22 tests** = with Neo4j running.

**Coverage:** Run `make test-coverage` for a line-coverage report. Current suite gives ~48% over `app/`; gaps are mainly code paths that need live APIs (Etherscan, Neo4j, OpenAI) or the ingest/LLM flows. Adding more unit tests around edge cases and mocked API tests would raise it.

### Option A: Docker (backend + Neo4j)

```bash
make env-setup   # or: cp backend/.env.example backend/.env
make up          # or: docker compose up -d
```
Set `ETHERSCAN_API_KEY` (and optional `NEO4J_PASSWORD`) in `backend/.env`.

- **Backend:** http://localhost:8000  
- **Neo4j Browser:** http://localhost:7474 (default user `neo4j`, password from `NEO4J_PASSWORD` or `neo4j`)

Run the frontend locally (Option B) so the Vue app can proxy to the backend.

### Option B: Local dev

**1. Backend (Python)**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env       # set ETHERSCAN_API_KEY (required for live data)
uvicorn app.main:app --reload --port 8000
```

Get an API key at [etherscan.io](https://etherscan.io/apis) (free tier is enough).

**2. Frontend (Bun)**

```bash
cd frontend
bun install
bun run dev
```

Open [http://localhost:5173](http://localhost:5173). The app proxies `/api` and `/health` to the backend.

**3. Neo4j (optional, for GraphRAG)**

- With Docker: use `docker compose up -d`; the backend uses `bolt://neo4j:7687`.
- Standalone: `docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/yourpassword -d neo4j:5-community`, then set `NEO4J_URI=bolt://localhost:7687` and `NEO4J_PASSWORD` in `backend/.env`.

Without Neo4j, the backend still runs; graph context is unavailable and risk is based on Etherscan-only heuristics.

**4. LLM & embeddings (optional – OpenAI-compatible)**

Risk synthesis and RAG embeddings use any **OpenAI-compatible** API. Set in `backend/.env`:

- **OpenAI:** `OPENAI_API_KEY=sk-...` (default; no base URL).
- **OpenRouter:** `OPENAI_API_KEY=<your-openrouter-key>` and `OPENAI_BASE_URL=https://openrouter.ai/api/v1`; set `OPENAI_LLM_MODEL` / `OPENAI_EMBEDDING_MODEL` to the model IDs you want.
- **Self-hosted (e.g. Ollama, vLLM):** `OPENAI_BASE_URL=http://localhost:11434/v1` (Ollama) and optionally `OPENAI_API_KEY` if the server requires it; set models to the names your server exposes.

If neither key nor base URL is set, the app uses a heuristic (no LLM, no RAG embeddings).

## Project layout

```
faro/
├── SPEC.md             # Technical spec and roadmap
├── README.md
├── Makefile            # make up, dev-backend, dev-frontend, env-setup, down, logs
├── docker-compose.yml  # Backend + Neo4j
├── backend/
│   ├── .dockerignore
│   ├── Dockerfile
│   ├── app/
│   │   ├── api/          # FastAPI routes (e.g. POST /api/investigate)
│   │   ├── core/         # Config
│   │   ├── models/       # Pydantic schemas
│   │   └── services/     # Etherscan client, Neo4j placeholder
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── stores/       # Pinia (e.g. forensic store)
    │   ├── views/        # Dashboard
    │   └── main.ts, App.vue, index.css
    ├── package.json      # Bun-friendly
    ├── biome.json
    ├── tailwind.config.js
    └── vite.config.ts    # Proxy /api → backend
```

## Roadmap (from SPEC)

- **Sprint 1:** Neo4j + FastAPI + Etherscan + **structured ingestion** (Wallet + SENT_FUNDS into Neo4j) ✅
- **Sprint 2:** **RAG** (vector index, PDF ingest via POST `/api/ingest-doc`, `get_rag_context`) + **LLM synthesis** (OpenAI when `OPENAI_API_KEY` set) ✅
- **Sprint 3:** Vue dashboard + **chain selector** (Ethereum, Base, Arbitrum) ✅
- **Sprint 4:** Cypher graph traversal; graph populated by ingestion ✅

See [STATUS.md](./STATUS.md) for details.

## License

MIT.
