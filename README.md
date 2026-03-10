# Faro – Blockchain Forensic RAG Agent

AI-driven wallet risk investigator: combines **live on-chain data** (Etherscan), **graph relationships** (Neo4j), and **threat intel** (RAG over PDFs) to produce explainable risk reports.

- **Spec:** [SPEC.md](./SPEC.md) – architecture, pipeline, and roadmap.

## Stack

| Layer   | Tech              |
|--------|--------------------|
| Frontend | Vue 3, Pinia, Vite, Tailwind, Biome |
| Backend  | FastAPI (Python)   |
| Data     | Etherscan V2 API  |
| Graph + Vector | Neo4j (optional) |

## Quick start

From the repo root you can use **Make** for common commands: `make env-setup` (copy `.env`), `make up` (Docker), `make dev-backend`, `make dev-frontend`, `make down`, `make logs`.

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

## Project layout

```
faro/
├── SPEC.md           # Technical spec and roadmap
├── README.md
├── docker-compose.yml   # Backend + Neo4j
├── backend/
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

- **Sprint 1:** Neo4j + FastAPI + Etherscan client ✅ (scaffolded)
- **Sprint 2:** Vector index in Neo4j; ingest security PDFs; RAG retrieval + LLM synthesis
- **Sprint 3:** Vue dashboard ✅ (scaffolded); polish UI and chain selector
- **Sprint 4:** Cypher graph traversal (multi-hop to blacklisted/mixer); wire into response

## License

MIT.
