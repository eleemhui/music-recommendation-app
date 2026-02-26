"""
Run once at startup: reads /data/lyrics.csv, embeds lyrics, inserts into songs table.
Skips if the table already has rows.
"""
import os
import sys

import pandas as pd
import psycopg2

# Allow running as a script from the api/ directory
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db import init_db, songs_empty, get_conn, put_conn
from app.embedder import embed_batch

CSV_PATH = "/data/lyrics.csv"


def seed() -> None:
    print("[seed] Initialising database schema...")
    init_db()

    if not songs_empty():
        print("[seed] Songs table already populated — skipping.")
        return

    print(f"[seed] Loading {CSV_PATH}...")
    df = pd.read_csv(CSV_PATH)
    required = {"title", "artist", "lyrics"}
    if not required.issubset(df.columns):
        raise ValueError(f"CSV must contain columns: {required}. Got: {set(df.columns)}")

    df = df.dropna(subset=["title", "artist", "lyrics"])
    print(f"[seed] Embedding {len(df)} songs (this may take a minute)...")
    embeddings = embed_batch(df["lyrics"].tolist())

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            rows = [
                (row["title"], row["artist"], "[" + ",".join(str(x) for x in emb) + "]")
                for (_, row), emb in zip(df.iterrows(), embeddings)
            ]
            cur.executemany(
                "INSERT INTO songs (title, artist, embedding) VALUES (%s, %s, %s::vector);",
                rows,
            )
        conn.commit()
        print(f"[seed] Inserted {len(rows)} songs.")
    finally:
        put_conn(conn)


if __name__ == "__main__":
    seed()
