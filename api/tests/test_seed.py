"""Unit tests for app/seed.py"""
import io
import os
import tempfile
from unittest.mock import MagicMock, patch, call

import numpy as np
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# _insert_rows — batch commits
# ---------------------------------------------------------------------------

def test_insert_rows_commits_in_batches():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    rows = [("title", "artist", "[0.1]")] * 25_000

    with patch("app.seed.COMMIT_BATCH", 10_000), \
         patch("app.seed.execute_values"):
        from app.seed import _insert_rows
        _insert_rows(mock_conn, rows)

    # Should commit 3 times: 10K, 10K, 5K
    assert mock_conn.commit.call_count == 3


def test_insert_rows_opens_new_cursor_per_batch():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    rows = [("t", "a", "[0.1]")] * 15_000

    with patch("app.seed.COMMIT_BATCH", 10_000), \
         patch("app.seed.execute_values"):
        from app.seed import _insert_rows
        _insert_rows(mock_conn, rows)

    # cursor() should be called once per batch (2 batches)
    assert mock_conn.cursor.call_count == 2


def test_insert_rows_empty_list_does_nothing():
    mock_conn = MagicMock()

    from app.seed import _insert_rows
    _insert_rows(mock_conn, [])

    mock_conn.commit.assert_not_called()
    mock_conn.cursor.assert_not_called()


# ---------------------------------------------------------------------------
# seed — skips if table populated
# ---------------------------------------------------------------------------

def test_seed_skips_if_not_empty():
    with patch("app.seed.init_db"), \
         patch("app.seed.songs_empty", return_value=False), \
         patch("app.seed._seed_from_precomputed") as mock_pre, \
         patch("app.seed._seed_from_csv") as mock_csv:
        from app.seed import seed
        seed()

    mock_pre.assert_not_called()
    mock_csv.assert_not_called()


# ---------------------------------------------------------------------------
# seed — routes to correct data source
# ---------------------------------------------------------------------------

def test_seed_uses_precomputed_when_chunks_exist():
    with patch("app.seed.init_db"), \
         patch("app.seed.songs_empty", return_value=True), \
         patch("app.seed.glob.glob", return_value=["chunk_0000.npz"]), \
         patch("app.seed._seed_from_precomputed") as mock_pre, \
         patch("app.seed._seed_from_csv") as mock_csv:
        from app.seed import seed
        seed()

    mock_pre.assert_called_once_with(["chunk_0000.npz"])
    mock_csv.assert_not_called()


def test_seed_falls_back_to_csv_when_no_chunks():
    with patch("app.seed.init_db"), \
         patch("app.seed.songs_empty", return_value=True), \
         patch("app.seed.glob.glob", return_value=[]), \
         patch("app.seed._seed_from_precomputed") as mock_pre, \
         patch("app.seed._seed_from_csv") as mock_csv:
        from app.seed import seed
        seed()

    mock_pre.assert_not_called()
    mock_csv.assert_called_once()


# ---------------------------------------------------------------------------
# _seed_from_precomputed
# ---------------------------------------------------------------------------

def test_seed_from_precomputed_loads_npz_and_inserts(tmp_path):
    titles = np.array(["Song A", "Song B"], dtype=object)
    artists = np.array(["Artist 1", "Artist 2"], dtype=object)
    embeddings = np.random.rand(2, 384).astype(np.float32)

    npz_path = str(tmp_path / "chunk_0000.npz")
    np.savez_compressed(npz_path, titles=titles, artists=artists, embeddings=embeddings)

    mock_conn = MagicMock()
    inserted_rows = []

    def fake_insert(conn, rows):
        inserted_rows.extend(rows)

    with patch("app.seed.get_conn", return_value=mock_conn), \
         patch("app.seed.put_conn"), \
         patch("app.seed._insert_rows", side_effect=fake_insert):
        from app.seed import _seed_from_precomputed
        _seed_from_precomputed([npz_path])

    assert len(inserted_rows) == 2
    assert inserted_rows[0][0] == "Song A"
    assert inserted_rows[1][1] == "Artist 2"
    # Embedding should be formatted as a vector string
    assert inserted_rows[0][2].startswith("[")


def test_seed_from_precomputed_returns_conn_on_exception(tmp_path):
    npz_path = str(tmp_path / "chunk_0000.npz")
    # Write a valid npz so np.load doesn't fail
    np.savez_compressed(npz_path, titles=np.array([]), artists=np.array([]), embeddings=np.array([]).reshape(0, 384))

    mock_conn = MagicMock()

    with patch("app.seed.get_conn", return_value=mock_conn), \
         patch("app.seed.put_conn") as mock_put, \
         patch("app.seed._insert_rows", side_effect=Exception("insert failed")):
        from app.seed import _seed_from_precomputed
        with pytest.raises(Exception, match="insert failed"):
            _seed_from_precomputed([npz_path])

    mock_put.assert_called_once_with(mock_conn)


# ---------------------------------------------------------------------------
# _seed_from_csv
# ---------------------------------------------------------------------------

def test_seed_from_csv_reads_and_embeds(tmp_path):
    csv_content = "title,artist,lyrics\nSong A,Artist 1,some lyrics\nSong B,Artist 2,more lyrics\n"
    csv_file = tmp_path / "lyrics.csv"
    csv_file.write_text(csv_content)

    mock_conn = MagicMock()
    inserted_rows = []

    def fake_insert(conn, rows):
        inserted_rows.extend(rows)

    fake_embeddings = [[0.1] * 384, [0.2] * 384]

    with patch("app.seed.CSV_PATH", str(csv_file)), \
         patch("app.seed.get_conn", return_value=mock_conn), \
         patch("app.seed.put_conn"), \
         patch("app.seed.embed_batch", return_value=fake_embeddings), \
         patch("app.seed._insert_rows", side_effect=fake_insert):
        from app.seed import _seed_from_csv
        _seed_from_csv()

    assert len(inserted_rows) == 2
    assert inserted_rows[0][0] == "Song A"
    assert inserted_rows[1][1] == "Artist 2"


def test_seed_from_csv_raises_on_missing_columns(tmp_path):
    csv_content = "name,band\nSong A,Artist 1\n"
    csv_file = tmp_path / "bad.csv"
    csv_file.write_text(csv_content)

    with patch("app.seed.CSV_PATH", str(csv_file)), \
         patch("app.seed.embed_batch", return_value=[]):
        from app.seed import _seed_from_csv
        with pytest.raises(ValueError, match="CSV must contain"):
            _seed_from_csv()
