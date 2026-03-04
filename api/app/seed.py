"""
Run once at startup: seeds the songs table.

Priority:
  1. /data/precomputed/chunk_*.npz  – pre-computed embeddings, fastest path
  2. /data/lyrics.csv               – raw CSV, embeddings computed on the fly

Skips entirely if the songs table already has rows.
"""

import glob
import logging
import os
import sys

import numpy as np
import pandas as pd
from psycopg2.extras import execute_values

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # noqa: E402

from app.db import init_db, songs_empty, get_conn, put_conn  # noqa: E402
from app.embedder import embed_batch  # noqa: E402

log = logging.getLogger("seed")
if not log.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)-8s %(message)s", datefmt="%Y/%m/%d %H:%M:%S"
        )
    )
    log.addHandler(_h)
log.setLevel(logging.INFO)

CSV_PATH = "/data/lyrics.csv"
PRECOMPUTED_DIR = "/data/precomputed"
COMMIT_BATCH = 10_000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _insert_rows(conn, rows: list[tuple]) -> None:
    """Bulk-insert rows in commits of COMMIT_BATCH to keep transactions small."""
    for offset in range(0, len(rows), COMMIT_BATCH):
        batch = rows[offset : offset + COMMIT_BATCH]
        with conn.cursor() as cur:
            execute_values(
                cur,
                "INSERT INTO songs (title, artist, embedding) VALUES %s",
                batch,
                template="(%s, %s, %s::vector)",
                page_size=1000,
            )
        conn.commit()
        log.info(f"[seed]     committed {offset + len(batch):,} / {len(rows):,} rows")


# ---------------------------------------------------------------------------
# Fast path: pre-computed .npz files
# ---------------------------------------------------------------------------


def _seed_from_precomputed(chunks: list[str]) -> None:
    chunks = sorted(chunks)
    log.info(
        f"[seed] Found {len(chunks)} precomputed chunk(s) — skipping embedding step."
    )
    conn = get_conn()
    try:
        total = 0
        for path in chunks:
            data = np.load(path, allow_pickle=True)
            titles: np.ndarray = data["titles"]
            artists: np.ndarray = data["artists"]
            embeddings: np.ndarray = data["embeddings"]  # shape (N, 384)
            n = len(titles)
            log.info(f"[seed]   Loading {path} ({n} rows)...")

            rows = [
                (
                    str(titles[i]),
                    str(artists[i]),
                    "[" + ",".join(f"{x:.6f}" for x in embeddings[i]) + "]",
                )
                for i in range(n)
            ]
            _insert_rows(conn, rows)
            total += n
            log.info(f"[seed]   Inserted {n} rows (running total: {total}).")
    finally:
        put_conn(conn)
    log.info(f"[seed] Done — {total} songs inserted from precomputed files.")


# ---------------------------------------------------------------------------
# Slow path: CSV + on-the-fly embedding
# ---------------------------------------------------------------------------


def _seed_from_csv() -> None:
    log.info(f"[seed] Loading {CSV_PATH}...")
    df = pd.read_csv(CSV_PATH)
    required = {"title", "artist", "lyrics"}
    if not required.issubset(df.columns):
        raise ValueError(
            f"CSV must contain columns: {required}. Got: {set(df.columns)}"
        )

    df = df.dropna(subset=["title", "artist", "lyrics"])
    log.info(f"[seed] Embedding {len(df)} songs (this may take a while)...")
    embeddings = embed_batch(df["lyrics"].tolist())

    rows = [
        (
            row["title"],
            row["artist"],
            "[" + ",".join(str(x) for x in emb) + "]",
        )
        for (_, row), emb in zip(df.iterrows(), embeddings)
    ]

    conn = get_conn()
    try:
        _insert_rows(conn, rows)
    finally:
        put_conn(conn)
    log.info(f"[seed] Inserted {len(rows)} songs from CSV.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def seed() -> None:
    log.info("[seed] Initialising database schema...")
    init_db()

    if not songs_empty():
        log.info("[seed] Songs table already populated — skipping.")
        return

    chunks = sorted(glob.glob(os.path.join(PRECOMPUTED_DIR, "chunk_*.npz")))
    if chunks:
        _seed_from_precomputed(chunks)
    else:
        _seed_from_csv()


if __name__ == "__main__":
    seed()
