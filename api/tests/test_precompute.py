"""Unit tests for app/precompute.py"""
import math
import os

import numpy as np
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch


def _make_csv(tmp_path, rows, columns=("title", "artist", "lyrics")):
    df = pd.DataFrame(rows, columns=columns)
    path = str(tmp_path / "songs.csv")
    df.to_csv(path, index=False)
    return path


def _make_mock_model(dim=384):
    mock_model = MagicMock()
    mock_model.encode.side_effect = lambda texts, **kwargs: np.random.rand(len(texts), dim).astype(np.float32)
    return mock_model


# ---------------------------------------------------------------------------
# Column renaming
# ---------------------------------------------------------------------------

def test_precompute_renames_song_text_columns(tmp_path):
    src = _make_csv(tmp_path, [("Artist X", "My Song", "some lyrics")], columns=("artist", "song", "text"))
    out_dir = str(tmp_path / "out")
    mock_model = _make_mock_model()

    with patch("app.precompute.SentenceTransformer", return_value=mock_model):
        from app.precompute import precompute
        precompute(src, out_dir, chunk_size=100)

    data = np.load(os.path.join(out_dir, "chunk_0000.npz"), allow_pickle=True)
    assert "My Song" in data["titles"]


def test_precompute_renames_text_to_lyrics(tmp_path):
    src = _make_csv(tmp_path, [("Song A", "Artist 1", "la la la")], columns=("title", "artist", "text"))
    out_dir = str(tmp_path / "out")
    mock_model = _make_mock_model()

    with patch("app.precompute.SentenceTransformer", return_value=mock_model):
        from app.precompute import precompute
        precompute(src, out_dir, chunk_size=100)

    data = np.load(os.path.join(out_dir, "chunk_0000.npz"), allow_pickle=True)
    assert len(data["titles"]) == 1


# ---------------------------------------------------------------------------
# Missing columns
# ---------------------------------------------------------------------------

def test_precompute_raises_on_missing_required_columns(tmp_path):
    src = _make_csv(tmp_path, [("Song A", "Artist 1")], columns=("title", "artist"))
    out_dir = str(tmp_path / "out")
    mock_model = _make_mock_model()

    with patch("app.precompute.SentenceTransformer", return_value=mock_model):
        from app.precompute import precompute
        with pytest.raises(ValueError, match="CSV must contain"):
            precompute(src, out_dir, chunk_size=100)


# ---------------------------------------------------------------------------
# Limit parameter
# ---------------------------------------------------------------------------

def test_precompute_limit_restricts_rows(tmp_path):
    rows = [("Song " + str(i), "Artist", "lyrics " + str(i)) for i in range(50)]
    src = _make_csv(tmp_path, rows)
    out_dir = str(tmp_path / "out")
    mock_model = _make_mock_model()

    with patch("app.precompute.SentenceTransformer", return_value=mock_model):
        from app.precompute import precompute
        precompute(src, out_dir, chunk_size=100, limit=10)

    data = np.load(os.path.join(out_dir, "chunk_0000.npz"), allow_pickle=True)
    assert len(data["titles"]) == 10


def test_precompute_no_limit_uses_all_rows(tmp_path):
    rows = [("Song " + str(i), "Artist", "lyrics " + str(i)) for i in range(20)]
    src = _make_csv(tmp_path, rows)
    out_dir = str(tmp_path / "out")
    mock_model = _make_mock_model()

    with patch("app.precompute.SentenceTransformer", return_value=mock_model):
        from app.precompute import precompute
        precompute(src, out_dir, chunk_size=100)

    data = np.load(os.path.join(out_dir, "chunk_0000.npz"), allow_pickle=True)
    assert len(data["titles"]) == 20


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def test_precompute_creates_multiple_chunks(tmp_path):
    rows = [("Song " + str(i), "Artist", "lyrics " + str(i)) for i in range(25)]
    src = _make_csv(tmp_path, rows)
    out_dir = str(tmp_path / "out")
    mock_model = _make_mock_model()

    with patch("app.precompute.SentenceTransformer", return_value=mock_model):
        from app.precompute import precompute
        precompute(src, out_dir, chunk_size=10)

    chunks = sorted(os.listdir(out_dir))
    assert len(chunks) == 3  # ceil(25/10)
    assert chunks[0] == "chunk_0000.npz"
    assert chunks[2] == "chunk_0002.npz"


def test_precompute_npz_has_correct_arrays(tmp_path):
    rows = [("Song A", "Artist 1", "lyrics here"), ("Song B", "Artist 2", "more lyrics")]
    src = _make_csv(tmp_path, rows)
    out_dir = str(tmp_path / "out")
    mock_model = _make_mock_model()

    with patch("app.precompute.SentenceTransformer", return_value=mock_model):
        from app.precompute import precompute
        precompute(src, out_dir, chunk_size=100)

    data = np.load(os.path.join(out_dir, "chunk_0000.npz"), allow_pickle=True)
    assert set(data.files) == {"titles", "artists", "embeddings"}
    assert data["embeddings"].shape == (2, 384)
    assert data["embeddings"].dtype == np.float32
    assert list(data["titles"]) == ["Song A", "Song B"]
    assert list(data["artists"]) == ["Artist 1", "Artist 2"]


# ---------------------------------------------------------------------------
# Drops rows with missing data
# ---------------------------------------------------------------------------

def test_precompute_drops_rows_with_missing_lyrics(tmp_path):
    rows = [("Song A", "Artist 1", "good lyrics"), ("Song B", "Artist 2", None), ("Song C", "Artist 3", "")]
    src = _make_csv(tmp_path, rows)
    out_dir = str(tmp_path / "out")
    mock_model = _make_mock_model()

    with patch("app.precompute.SentenceTransformer", return_value=mock_model):
        from app.precompute import precompute
        precompute(src, out_dir, chunk_size=100)

    data = np.load(os.path.join(out_dir, "chunk_0000.npz"), allow_pickle=True)
    assert len(data["titles"]) == 1
    assert data["titles"][0] == "Song A"
