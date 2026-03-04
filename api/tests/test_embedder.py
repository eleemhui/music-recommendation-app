"""Unit tests for app/embedder.py"""
import numpy as np
from unittest.mock import MagicMock, patch


def _make_mock_model(output_dim=384):
    mock_model = MagicMock()
    mock_model.encode.side_effect = lambda texts, **kwargs: (
        np.random.rand(output_dim).astype(np.float32)
        if isinstance(texts, str)
        else np.random.rand(len(texts), output_dim).astype(np.float32)
    )
    return mock_model


# ---------------------------------------------------------------------------
# get_model
# ---------------------------------------------------------------------------

def test_get_model_creates_singleton():
    import app.embedder as emb_module
    emb_module._model = None

    mock_model = MagicMock()
    with patch("app.embedder.SentenceTransformer", return_value=mock_model) as mock_cls:
        from app.embedder import get_model
        m1 = get_model()
        m2 = get_model()

    mock_cls.assert_called_once_with("all-MiniLM-L6-v2")
    assert m1 is m2

    emb_module._model = None


# ---------------------------------------------------------------------------
# embed
# ---------------------------------------------------------------------------

def test_embed_returns_list_of_floats():
    import app.embedder as emb_module
    emb_module._model = None

    mock_model = _make_mock_model()
    with patch("app.embedder.SentenceTransformer", return_value=mock_model):
        from app.embedder import embed
        result = embed("love and heartbreak")

    assert isinstance(result, list)
    assert len(result) == 384
    assert all(isinstance(v, float) for v in result)

    emb_module._model = None


def test_embed_truncates_to_1000_chars():
    import app.embedder as emb_module
    emb_module._model = None

    long_text = "x" * 2000
    mock_model = _make_mock_model()

    with patch("app.embedder.SentenceTransformer", return_value=mock_model):
        from app.embedder import embed
        embed(long_text)

    encoded_text = mock_model.encode.call_args[0][0]
    assert len(encoded_text) == 1000

    emb_module._model = None


def test_embed_uses_normalize_embeddings():
    import app.embedder as emb_module
    emb_module._model = None

    mock_model = _make_mock_model()
    with patch("app.embedder.SentenceTransformer", return_value=mock_model):
        from app.embedder import embed
        embed("test")

    kwargs = mock_model.encode.call_args[1]
    assert kwargs.get("normalize_embeddings") is True

    emb_module._model = None


# ---------------------------------------------------------------------------
# embed_batch
# ---------------------------------------------------------------------------

def test_embed_batch_returns_list_of_lists():
    import app.embedder as emb_module
    emb_module._model = None

    mock_model = _make_mock_model()
    with patch("app.embedder.SentenceTransformer", return_value=mock_model):
        from app.embedder import embed_batch
        result = embed_batch(["song one", "song two", "song three"])

    assert isinstance(result, list)
    assert len(result) == 3
    assert all(isinstance(row, list) and len(row) == 384 for row in result)

    emb_module._model = None


def test_embed_batch_truncates_each_text():
    import app.embedder as emb_module
    emb_module._model = None

    texts = ["a" * 2000, "b" * 500, "c" * 1500]
    mock_model = _make_mock_model()

    with patch("app.embedder.SentenceTransformer", return_value=mock_model):
        from app.embedder import embed_batch
        embed_batch(texts)

    truncated = mock_model.encode.call_args[0][0]
    assert all(len(t) <= 1000 for t in truncated)

    emb_module._model = None
