# Precomputing Song Embeddings

`api/app/precompute.py` generates embedding files from a lyrics CSV and saves
them as compressed `.npz` files in `data/precomputed/`. When the API container
starts, `seed.py` detects these files and loads them directly — skipping the
slow on-the-fly embedding step entirely.

---

## Prerequisites

This script runs **outside Docker**, in the dedicated `precompute` conda
environment that was set up to support the Quadro M1200 GPU (CUDA sm_50).

```bash
export PATH="/home/eleemhuis/miniconda3/bin:$PATH"
conda activate precompute
```

---

## Input CSV format

The source CSV must contain at minimum these columns (case-sensitive):

| Column | Description |
|--------|-------------|
| `artist` | Artist name |
| `song` or `title` | Song title |
| `text` or `lyrics` | Full song lyrics |

The script automatically renames `song` → `title` and `text` → `lyrics` if
the original column names are present.

The cleaned source file used in this project is:

```
/home/eleemhuis/spotify_millsongdata_clean.csv
```

This was produced from `spotify_millsongdata.csv.zip` with embedded newlines
in the lyrics column replaced by spaces.

---

## Running precompute

Run from the repo root (`/home/eleemhuis/musicRecommender`):

```bash
export PATH="/home/eleemhuis/miniconda3/bin:$PATH"
cd /home/eleemhuis/musicRecommender

conda run -n precompute python api/app/precompute.py \
    --src /home/eleemhuis/spotify_millsongdata_clean.csv \
    --out data/precomputed \
    --chunk 100000
```

### Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--src` | `/home/eleemhuis/spotify_millsongdata_clean.csv` | Path to source CSV |
| `--out` | `data/precomputed` | Output directory for `.npz` files |
| `--chunk` | `100000` | Max rows per output file |
| `--limit` | *(all rows)* | Only process the first N rows (useful for testing) |

### Test run (1 000 rows)

```bash
conda run -n precompute python api/app/precompute.py \
    --src /home/eleemhuis/spotify_millsongdata_clean.csv \
    --out data/precomputed \
    --chunk 100000 \
    --limit 1000
```

---

## Output

Each output file is a compressed NumPy archive:

```
data/precomputed/
└── chunk_0000.npz      # up to 100 000 songs per file
    ├── titles      (N,)      str   – song titles
    ├── artists     (N,)      str   – artist names
    └── embeddings  (N, 384)  f32   – all-MiniLM-L6-v2 vectors
```

With the full 57 650-song dataset, all songs fit in a single file
(`chunk_0000.npz`).

---

## Applying to the database

After generating the `.npz` files, truncate the existing data and restart the
API to trigger a fresh seed:

```bash
cd /home/eleemhuis/musicRecommender

docker compose exec db psql -U music -d music -c \
    "TRUNCATE TABLE songs RESTART IDENTITY;"

docker compose restart api
```

Watch progress in the API logs:

```bash
docker compose logs api -f
```

Expected output (6 commit checkpoints for 57 650 songs):

```
2026/02/27 17:12:03 INFO     [seed] Found 1 precomputed chunk(s) — skipping embedding step.
2026/02/27 17:12:03 INFO     [seed]   Loading /data/precomputed/chunk_0000.npz (57650 rows)...
2026/02/27 17:12:45 INFO     [seed]     committed 10,000 / 57,650 rows
2026/02/27 17:13:12 INFO     [seed]     committed 20,000 / 57,650 rows
...
2026/02/27 17:15:58 INFO     [seed]     committed 57,650 / 57,650 rows
2026/02/27 17:15:58 INFO     [seed]   Inserted 57650 rows (running total: 57650).
2026/02/27 17:15:58 INFO     [seed] Done — 57650 songs inserted from precomputed files.
```

---

## GPU note

The `precompute` conda environment uses **PyTorch 1.13.1 + CUDA 11.7**, which
is the last PyTorch release to support CUDA compute capability **sm_50**
(Quadro M1200 / Maxwell architecture). cuBLASLt is disabled via
`DISABLE_ADDMM_CUDA_LT=1` to work around a known incompatibility with sm_50.

The Docker containers (API, DB, frontend) use a separate Python 3.12
environment and are unaffected by this.
