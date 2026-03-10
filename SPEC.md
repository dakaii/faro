# Technical Specification: Blockchain Forensic RAG Agent (Project Faro)

## 1. Executive Summary

**Project objective:** Build a real-time investigation platform that identifies suspicious blockchain wallets by combining:

- **Live transaction data** (Etherscan V2 API)
- **Historical graph relationships** (Neo4j — who sent funds to whom)
- **Unstructured threat intelligence** (PDFs, reports) via vector search

**Key innovation:** Use **GraphRAG** so the system can reason not only about a single wallet but about its position in a network of transactions (e.g. “2 hops from a known mixer”).

---

## 2. Problem Statement

- Existing tools are either **manual** (analyst-heavy) or **rigid** (static blacklists).
- New “burner” wallets used in phishing or rug-pulls are not on blacklists yet.
- **Solution:** An LLM-powered agent that reasons about wallet behaviour using:
  - Proximity to known bad actors (graph)
  - Similarity to documented attack patterns (RAG over reports)

---

## 3. System Architecture & Tech Stack

| Layer        | Technology        | Role |
|-------------|--------------------|------|
| Frontend    | Vue 3 + Pinia      | Dashboard for the “AI Investigator”; reactive investigation state |
| Tooling     | Bun + Biome.js     | Fast dev/build and strict formatting |
| Styling     | Tailwind CSS       | Dark “forensic” UI; monospace for addresses; risk indicators |
| Backend     | FastAPI (Python)   | API bridge between LLM, Etherscan, and Neo4j |
| Graph DB    | Neo4j              | Wallet/address nodes; SENT_FUNDS / relationship edges |
| Vector      | Neo4j vector index | Embeddings of security PDFs and hack reports |
| Data source | Etherscan V2 API   | Multi-chain tx data (Ethereum, Base, Arbitrum, etc.) |

---

## 4. Implementation Logic (GraphRAG Pipeline)

### Phase 1: Data ingestion

- **Unstructured:** Ingest PDFs (REKT, Chainalysis, FBI alerts, etc.) → chunk → embed → store in Neo4j vector index.
- **Structured:** For a given wallet, call Etherscan for last N transactions → create/update nodes and `SENT_FUNDS` (or similar) relationships in Neo4j.

### Phase 2: Investigation (multi-hop + RAG)

- **Graph:** Traverse from the queried wallet to find paths to “Blacklisted” or “Mixer” nodes (configurable hop limit).
- **Semantic:** Query Neo4j vector index with a summary of the wallet’s behaviour (e.g. “high-frequency transfers to new contract”) to retrieve relevant report chunks.
- **Combine:** Pass graph context + retrieved chunks to the LLM.

### Phase 3: Reasoning (LLM synthesis)

- **Input to LLM:** Wallet address, Etherscan-derived “story”, graph context (e.g. “2 hops from flagged mixer”), and RAG chunks (threat patterns).
- **Output:** Risk score (e.g. 0–100), short summary, and 3+ bullet-point evidence items.

---

## 5. Success Metrics (KPIs)

- **Precision/Recall:** Accuracy on a labelled set of known bad vs good wallets.
- **Inference latency:** Target &lt;3s for a full investigation (Etherscan + Neo4j + LLM).
- **Explainability:** Every “High Risk” result must include at least 3 evidence bullets.

---

## 6. Development Roadmap

| Sprint | Focus |
|--------|--------|
| **1**  | Neo4j + FastAPI setup; Etherscan V2 client; fetch and normalize wallet tx data |
| **2**  | Neo4j vector index; ingest security reports; RAG retrieval and prompt wiring |
| **3**  | Vue 3 dashboard (Bun, Biome, Tailwind); Pinia store; call FastAPI investigate endpoint |
| **4**  | Graph traversal (Cypher): mixers, multi-hop to blacklisted nodes; wire into investigation response |

---

## 7. API Contract (Planned)

**POST `/api/investigate`**

- **Request:** `{ "address": "0x...", "chain_id": 1 }`
- **Response:**  
  `{ "address", "risk_score", "summary", "evidence": [...], "graph_summary?" }`

(Exact fields can be refined in Sprint 1–2.)

---

## 8. Data Model (Neo4j)

- **Nodes:** `Wallet { address }`, `Blacklisted`, `Mixer`, etc. (extensible).
- **Relationships:** `(Wallet)-[:SENT_FUNDS { amount, timestamp?, tx_hash? }]->(Wallet)` (and similar).
- **Vector index:** One index over a node type (e.g. `ReportChunk`) with an embedding property; used for semantic search of threat docs.

This document is the single source of truth for scope and architecture; implementation details will live in code and README.
