# Lyric Match

A semantic music search engine. Enter a phrase, mood, or feeling and get song recommendations whose lyrics match by meaning — not by keyword.

57,650 songs indexed with precomputed sentence embeddings, served via vector similarity search in PostgreSQL.

## How it works

1. Your phrase is encoded into a 384-dimensional vector using `all-MiniLM-L6-v2`
2. pgvector finds the nearest song embeddings using HNSW index cosine similarity
3. Results are returned with a match score and a Spotify link

## Stack

| Layer | Tech |
|---|---|
| Backend | FastAPI + Uvicorn |
| Database | PostgreSQL 16 + pgvector |
| ML | sentence-transformers (`all-MiniLM-L6-v2`) |
| Frontend | React 18 + TypeScript + Vite |
| Prod server | Nginx |
| Infra | Docker Compose |

## Quickstart

**Prerequisites:** Docker and Docker Compose.

```bash
git clone <repo-url>
cd musicRecommender
docker compose up
```

Open [http://localhost:5173](http://localhost:5173).

On first boot the API seeds the database automatically. With precomputed embeddings in `data/precomputed/` this takes ~3 minutes. Without them it falls back to generating embeddings on-the-fly, which takes several hours.

## Precomputed embeddings

The `data/precomputed/` directory (gitignored) holds `.npz` files with precomputed vectors for fast startup. See [PRECOMPUTE.md](PRECOMPUTE.md) for how to generate them from a source CSV.

## Frontend development

```bash
cd frontend
npm install
npm run dev     # http://localhost:5173 — proxies API to localhost:8000
npm run build   # type-check + production build
```

The API must be running separately (`docker compose up api db`) when developing the frontend outside Docker.

## Project layout

```
api/app/       FastAPI backend (routes, DB, embedder, recommender, seeding)
frontend/src/  React frontend (App.tsx, components/, types.ts)
data/          Runtime data — lyrics.csv source, precomputed/ embeddings
```

## Resetting the database

```bash
docker compose exec db psql -U music -d music -c "TRUNCATE TABLE songs RESTART IDENTITY;"
docker compose restart api
```

The API re-seeds on startup whenever the `songs` table is empty.
