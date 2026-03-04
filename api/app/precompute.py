"""
Precompute embeddings for all songs in a CSV and save as chunked .npz files.

Usage (run from repo root, outside Docker):
    python api/app/precompute.py \
        --src /home/eleemhuis/spotify_millsongdata_clean.csv \
        --out data/precomputed \
        --chunk 100000 \
        [--limit 1000]

Output files: data/precomputed/chunk_0000.npz, chunk_0001.npz, ...
Each .npz contains three arrays:
    titles     – (N,)     object/str
    artists    – (N,)     object/str
    embeddings – (N, 384) float32

seed.py will detect these files and use them instead of re-embedding at startup.
"""

import argparse
import math
import os

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

EMBED_DIM = 384
MODEL_NAME = "all-MiniLM-L6-v2"
BATCH_SIZE = 512


def precompute(
    src: str, out_dir: str, chunk_size: int, limit: int | None = None
) -> None:
    print(f"[precompute] Reading {src}...")
    df = pd.read_csv(src, dtype=str)

    # Support both the original schema (song/text) and the normalised schema (title/lyrics)
    if "song" in df.columns and "title" not in df.columns:
        df = df.rename(columns={"song": "title", "text": "lyrics"})
    if "text" in df.columns and "lyrics" not in df.columns:
        df = df.rename(columns={"text": "lyrics"})

    required = {"title", "artist", "lyrics"}
    if not required.issubset(df.columns):
        raise ValueError(f"CSV must contain {required}. Got: {set(df.columns)}")

    df = df.dropna(subset=["title", "artist", "lyrics"])
    df = df[df["lyrics"].str.strip().ne("")]

    if limit is not None:
        df = df.iloc[:limit]
        print(f"[precompute] Limiting to first {limit} rows.")

    total = len(df)
    print(f"[precompute] {total} songs to embed.")

    os.makedirs(out_dir, exist_ok=True)

    print(f"[precompute] Loading model {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)

    n_chunks = math.ceil(total / chunk_size)
    print(
        f"[precompute] Writing {n_chunks} chunk(s) of up to {chunk_size} rows each..."
    )

    for chunk_idx in range(n_chunks):
        start = chunk_idx * chunk_size
        end = min(start + chunk_size, total)
        chunk_df = df.iloc[start:end].reset_index(drop=True)
        n = len(chunk_df)

        print(
            f"[precompute] Chunk {chunk_idx:04d}: rows {start}–{end - 1} ({n} songs) — embedding..."
        )
        lyrics = [t[:1000] for t in chunk_df["lyrics"].tolist()]
        embeddings = model.encode(
            lyrics,
            normalize_embeddings=True,
            batch_size=BATCH_SIZE,
            show_progress_bar=True,
        ).astype(np.float32)

        out_path = os.path.join(out_dir, f"chunk_{chunk_idx:04d}.npz")
        np.savez_compressed(
            out_path,
            titles=chunk_df["title"].to_numpy(dtype=object),
            artists=chunk_df["artist"].to_numpy(dtype=object),
            embeddings=embeddings,
        )
        print(f"[precompute] Saved {out_path}  shape={embeddings.shape}")

    print(f"[precompute] Done. {n_chunks} file(s) in {out_dir}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Precompute song lyric embeddings.")
    parser.add_argument(
        "--src",
        default="/home/eleemhuis/spotify_millsongdata_clean.csv",
        help="Path to source CSV (artist, song/title, text/lyrics columns)",
    )
    parser.add_argument(
        "--out",
        default="data/precomputed",
        help="Output directory for .npz chunk files",
    )
    parser.add_argument(
        "--chunk",
        type=int,
        default=100_000,
        help="Max rows per output file (default 100000)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only process the first N rows (default: all)",
    )
    args = parser.parse_args()
    precompute(args.src, args.out, args.chunk, args.limit)
