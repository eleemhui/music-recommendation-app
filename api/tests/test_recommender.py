"""Unit tests for app/recommender.py"""
import urllib.parse
from unittest.mock import MagicMock, patch


def _make_mock_conn(rows):
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = rows
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return mock_conn


FAKE_ROWS = [
    ("Bohemian Rhapsody", "Queen", 0.9512),
    ("Hotel California", "Eagles", 0.8834),
    ("Stairway to Heaven", "Led Zeppelin", 0.8201),
]

FAKE_EMBEDDING = [0.1] * 384


# ---------------------------------------------------------------------------
# recommend — result structure
# ---------------------------------------------------------------------------

def test_recommend_returns_list_of_dicts():
    mock_conn = _make_mock_conn(FAKE_ROWS)
    with patch("app.recommender.get_conn", return_value=mock_conn), \
         patch("app.recommender.put_conn"), \
         patch("app.recommender.embed", return_value=FAKE_EMBEDDING):
        from app.recommender import recommend
        results = recommend("opera rock", 3)

    assert isinstance(results, list)
    assert len(results) == 3


def test_recommend_result_fields():
    mock_conn = _make_mock_conn(FAKE_ROWS)
    with patch("app.recommender.get_conn", return_value=mock_conn), \
         patch("app.recommender.put_conn"), \
         patch("app.recommender.embed", return_value=FAKE_EMBEDDING):
        from app.recommender import recommend
        result = recommend("rock anthem", 3)[0]

    assert set(result.keys()) == {"title", "artist", "score", "spotify_url"}
    assert result["title"] == "Bohemian Rhapsody"
    assert result["artist"] == "Queen"
    assert result["score"] == round(0.9512, 4)


# ---------------------------------------------------------------------------
# recommend — spotify URL
# ---------------------------------------------------------------------------

def test_recommend_builds_spotify_search_url():
    mock_conn = _make_mock_conn([("My Song", "My Artist", 0.9)])
    with patch("app.recommender.get_conn", return_value=mock_conn), \
         patch("app.recommender.put_conn"), \
         patch("app.recommender.embed", return_value=FAKE_EMBEDDING):
        from app.recommender import recommend
        result = recommend("test", 3)[0]

    expected_query = urllib.parse.quote("My Song My Artist")
    assert result["spotify_url"] == f"https://open.spotify.com/search/{expected_query}"


def test_recommend_url_encodes_special_chars():
    mock_conn = _make_mock_conn([("Don't Stop Me Now", "Queen & Friends", 0.9)])
    with patch("app.recommender.get_conn", return_value=mock_conn), \
         patch("app.recommender.put_conn"), \
         patch("app.recommender.embed", return_value=FAKE_EMBEDDING):
        from app.recommender import recommend
        result = recommend("test", 3)[0]

    assert " " not in result["spotify_url"].split("/search/")[1]


# ---------------------------------------------------------------------------
# recommend — n clamping
# ---------------------------------------------------------------------------

def test_recommend_clamps_n_below_3():
    mock_conn = _make_mock_conn(FAKE_ROWS)
    mock_cursor = mock_conn.cursor.return_value.__enter__.return_value
    with patch("app.recommender.get_conn", return_value=mock_conn), \
         patch("app.recommender.put_conn"), \
         patch("app.recommender.embed", return_value=FAKE_EMBEDDING):
        from app.recommender import recommend
        recommend("test", 1)

    sql_args = mock_cursor.execute.call_args[0][1]
    assert sql_args[2] == 3


def test_recommend_clamps_n_above_5():
    mock_conn = _make_mock_conn(FAKE_ROWS)
    mock_cursor = mock_conn.cursor.return_value.__enter__.return_value
    with patch("app.recommender.get_conn", return_value=mock_conn), \
         patch("app.recommender.put_conn"), \
         patch("app.recommender.embed", return_value=FAKE_EMBEDDING):
        from app.recommender import recommend
        recommend("test", 10)

    sql_args = mock_cursor.execute.call_args[0][1]
    assert sql_args[2] == 5


def test_recommend_accepts_n_in_range():
    mock_conn = _make_mock_conn(FAKE_ROWS)
    mock_cursor = mock_conn.cursor.return_value.__enter__.return_value
    with patch("app.recommender.get_conn", return_value=mock_conn), \
         patch("app.recommender.put_conn"), \
         patch("app.recommender.embed", return_value=FAKE_EMBEDDING):
        from app.recommender import recommend
        recommend("test", 4)

    sql_args = mock_cursor.execute.call_args[0][1]
    assert sql_args[2] == 4


# ---------------------------------------------------------------------------
# recommend — connection lifecycle
# ---------------------------------------------------------------------------

def test_recommend_returns_conn_on_exception():
    mock_conn = _make_mock_conn([])
    mock_cursor = mock_conn.cursor.return_value.__enter__.return_value
    mock_cursor.execute.side_effect = Exception("DB error")

    with patch("app.recommender.get_conn", return_value=mock_conn), \
         patch("app.recommender.put_conn") as mock_put, \
         patch("app.recommender.embed", return_value=FAKE_EMBEDDING):
        from app.recommender import recommend
        try:
            recommend("test", 3)
        except Exception:
            pass

    mock_put.assert_called_once_with(mock_conn)
