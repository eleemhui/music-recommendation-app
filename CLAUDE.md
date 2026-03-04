# Lyric Match — Claude Context

## Project Overview

Semantic music search engine: users enter a phrase or mood and receive song recommendations matched by lyrical meaning using vector similarity, not keyword search. 57,650 songs indexed with precomputed embeddings.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.x, FastAPI, Uvicorn |
| Database | PostgreSQL 16 + pgvector extension |
| ML Model | sentence-transformers (`all-MiniLM-L6-v2`) |
| Frontend | React 18, TypeScript 5, Vite 5 |
| Prod server | Nginx (reverse proxy + static files) |
| Infra | Docker Compose (3 services: `db`, `api`, `frontend`) |

## Key Directories

```
api/app/          Core backend — main.py (routes), db.py, embedder.py,
                  recommender.py (service), seed.py (init), precompute.py
frontend/src/     React app — App.tsx (root state), types.ts, components/
data/precomputed/ Precomputed .npz embedding chunks (excluded from git,
                  mounted into Docker; absence triggers slow CSV fallback)
```

## Essential Commands

**Run everything (standard workflow):**
```bash
docker compose up          # starts db → api (seeds on first run) → frontend
docker compose up --build  # rebuild images after dependency changes
```

**Frontend development (hot reload):**
```bash
cd frontend
npm install
npm run dev       # Vite dev server; proxies /recommend and /health to localhost:8000
npm run build     # tsc + vite build (type-check included)
```

**Precompute embeddings (run outside Docker, one-time):**
```bash
conda run -n precompute python api/app/precompute.py \
    --src /path/to/spotify_millsongdata_clean.csv \
    --out data/precomputed \
    --chunk 100000
```

**Reset database (re-seeds on next `docker compose up`):**
```bash
docker compose exec db psql -U music -d music -c "TRUNCATE TABLE songs RESTART IDENTITY;"
docker compose restart api
```

**API health check:**
```bash
curl http://localhost:8000/health
```

## Startup Sequence

On `docker compose up`, the API container runs `seed.py` before Uvicorn:
1. Checks if `songs` table is empty
2. If `data/precomputed/chunk_*.npz` files exist → fast load (~57s)
3. Otherwise → slow path: reads `lyrics.csv`, generates embeddings on-the-fly (hours)

## Key Files for Reference

- Entry point: [api/app/main.py](api/app/main.py) — FastAPI routes, Pydantic models, middleware
- Recommendation logic: [api/app/recommender.py](api/app/recommender.py)
- DB pool + schema: [api/app/db.py](api/app/db.py)
- Embedder singleton: [api/app/embedder.py](api/app/embedder.py)
- Seed/init: [api/app/seed.py](api/app/seed.py)
- Root component + API call: [frontend/src/App.tsx](frontend/src/App.tsx)
- Shared types: [frontend/src/types.ts](frontend/src/types.ts)
- Nginx routing: [frontend/nginx.conf](frontend/nginx.conf)
- Environment config template: [.env.example](.env.example)

## Additional Documentation

Check these files when working on relevant areas:

| Topic | File |
|---|---|
| Architectural patterns (singleton, service layer, batch processing, etc.) | [.claude/docs/architectural_patterns.md](.claude/docs/architectural_patterns.md) |
| Precomputation pipeline details | [PRECOMPUTE.md](PRECOMPUTE.md) |
