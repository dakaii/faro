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

### 1. Backend (Python)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env       # set ETHERSCAN_API_KEY (required for live data)
uvicorn app.main:app --reload --port 8000
```

Get an API key at [etherscan.io](https://etherscan.io/apis) (free tier is enough).

### 2. Frontend (Bun)

```bash
cd frontend
bun install
bun run dev
```

Open [http://localhost:5173](http://localhost:5173). The app proxies `/api` and `/health` to the backend.

### 3. Neo4j (optional, for GraphRAG)

- **Local:** `docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/yourpassword -d neo4j:community`
- Set `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` in `backend/.env`.

Without Neo4j, the backend still runs; graph context will be “unavailable” and risk is based on Etherscan-only heuristics.

## Project layout

```
faro/
├── SPEC.md           # Technical spec and roadmap
├── README.md
├── backend/
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
