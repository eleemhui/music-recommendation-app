"""Unit tests for app/main.py (FastAPI endpoints)"""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


MOCK_SONGS = [
    {"title": "Song A", "artist": "Artist 1", "score": 0.95, "spotify_url": "https://open.spotify.com/search/Song%20A%20Artist%201"},
    {"title": "Song B", "artist": "Artist 2", "score": 0.88, "spotify_url": "https://open.spotify.com/search/Song%20B%20Artist%202"},
    {"title": "Song C", "artist": "Artist 3", "score": 0.81, "spotify_url": "https://open.spotify.com/search/Song%20C%20Artist%203"},
]


@pytest.fixture
def client():
    with patch("app.recommender.recommend", return_value=MOCK_SONGS):
        from app.main import app
        with TestClient(app) as c:
            yield c


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /recommend — valid requests
# ---------------------------------------------------------------------------

def test_recommend_valid_phrase_returns_songs(client):
    with patch("app.recommender.recommend", return_value=MOCK_SONGS):
        response = client.post("/recommend", json={"phrase": "heartbreak and rain"})

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["title"] == "Song A"
    assert data[0]["spotify_url"].startswith("https://open.spotify.com/search/")


def test_recommend_returns_correct_fields(client):
    with patch("app.recommender.recommend", return_value=MOCK_SONGS):
        response = client.post("/recommend", json={"phrase": "summer vibes"})

    assert response.status_code == 200
    for song in response.json():
        assert set(song.keys()) == {"title", "artist", "score", "spotify_url"}


def test_recommend_default_n_is_5(client):
    with patch("app.main.recommend", return_value=MOCK_SONGS) as mock_rec:
        client.post("/recommend", json={"phrase": "test"})
    mock_rec.assert_called_once_with("test", 5)


def test_recommend_custom_n(client):
    with patch("app.main.recommend", return_value=MOCK_SONGS) as mock_rec:
        client.post("/recommend", json={"phrase": "test", "n": 3})
    mock_rec.assert_called_once_with("test", 3)


def test_recommend_strips_whitespace_from_phrase(client):
    with patch("app.main.recommend", return_value=MOCK_SONGS) as mock_rec:
        client.post("/recommend", json={"phrase": "  summer vibes  "})
    mock_rec.assert_called_once_with("summer vibes", 5)


# ---------------------------------------------------------------------------
# POST /recommend — invalid requests
# ---------------------------------------------------------------------------

def test_recommend_blank_phrase_returns_400(client):
    with patch("app.recommender.recommend", return_value=MOCK_SONGS):
        response = client.post("/recommend", json={"phrase": "   "})
    assert response.status_code == 400


def test_recommend_empty_phrase_returns_422(client):
    response = client.post("/recommend", json={"phrase": ""})
    assert response.status_code == 422


def test_recommend_phrase_too_long_returns_422(client):
    response = client.post("/recommend", json={"phrase": "x" * 501})
    assert response.status_code == 422


def test_recommend_n_too_small_returns_422(client):
    response = client.post("/recommend", json={"phrase": "test", "n": 2})
    assert response.status_code == 422


def test_recommend_n_too_large_returns_422(client):
    response = client.post("/recommend", json={"phrase": "test", "n": 6})
    assert response.status_code == 422


def test_recommend_missing_phrase_returns_422(client):
    response = client.post("/recommend", json={})
    assert response.status_code == 422
