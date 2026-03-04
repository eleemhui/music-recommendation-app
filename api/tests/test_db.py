"""Unit tests for app/db.py"""
import os
from unittest.mock import MagicMock, patch, call

import pytest


# ---------------------------------------------------------------------------
# get_pool
# ---------------------------------------------------------------------------

def test_get_pool_creates_pool_with_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/test")

    mock_pool = MagicMock()
    with patch("app.db._pool", None), \
         patch("app.db.SimpleConnectionPool", return_value=mock_pool) as mock_cls:
        from app.db import get_pool
        # Reset module-level singleton
        import app.db as db_module
        db_module._pool = None

        result = get_pool()

        mock_cls.assert_called_once_with(1, 10, dsn="postgresql://user:pass@localhost/test")
        assert result is mock_pool


def test_get_pool_returns_existing_pool():
    mock_pool = MagicMock()
    import app.db as db_module
    db_module._pool = mock_pool

    with patch("app.db.SimpleConnectionPool") as mock_cls:
        from app.db import get_pool
        result = get_pool()
        mock_cls.assert_not_called()
        assert result is mock_pool

    db_module._pool = None


# ---------------------------------------------------------------------------
# get_conn / put_conn
# ---------------------------------------------------------------------------

def test_get_conn_calls_pool_getconn():
    mock_conn = MagicMock()
    mock_pool = MagicMock()
    mock_pool.getconn.return_value = mock_conn

    with patch("app.db.get_pool", return_value=mock_pool):
        from app.db import get_conn
        result = get_conn()

    mock_pool.getconn.assert_called_once()
    assert result is mock_conn


def test_put_conn_calls_pool_putconn():
    mock_conn = MagicMock()
    mock_pool = MagicMock()

    with patch("app.db.get_pool", return_value=mock_pool):
        from app.db import put_conn
        put_conn(mock_conn)

    mock_pool.putconn.assert_called_once_with(mock_conn)


# ---------------------------------------------------------------------------
# init_db
# ---------------------------------------------------------------------------

def test_init_db_creates_extension_table_and_index():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with patch("app.db.get_conn", return_value=mock_conn), \
         patch("app.db.put_conn") as mock_put:
        from app.db import init_db
        init_db()

    executed_sql = [c.args[0].strip() for c in mock_cursor.execute.call_args_list]
    assert any("CREATE EXTENSION" in sql and "vector" in sql for sql in executed_sql)
    assert any("CREATE TABLE" in sql and "songs" in sql for sql in executed_sql)
    assert any("CREATE INDEX" in sql and "hnsw" in sql for sql in executed_sql)
    mock_conn.commit.assert_called_once()
    mock_put.assert_called_once_with(mock_conn)


def test_init_db_returns_conn_on_exception():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.execute.side_effect = Exception("DB error")
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with patch("app.db.get_conn", return_value=mock_conn), \
         patch("app.db.put_conn") as mock_put:
        from app.db import init_db
        with pytest.raises(Exception, match="DB error"):
            init_db()

    mock_put.assert_called_once_with(mock_conn)


# ---------------------------------------------------------------------------
# songs_empty
# ---------------------------------------------------------------------------

def test_songs_empty_returns_true_when_count_is_zero():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (0,)
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with patch("app.db.get_conn", return_value=mock_conn), \
         patch("app.db.put_conn"):
        from app.db import songs_empty
        assert songs_empty() is True


def test_songs_empty_returns_false_when_count_is_nonzero():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (42,)
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with patch("app.db.get_conn", return_value=mock_conn), \
         patch("app.db.put_conn"):
        from app.db import songs_empty
        assert songs_empty() is False
