from sentence_transformers import SentenceTransformer

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed(text: str) -> list[float]:
    vec = get_model().encode(text[:1000], normalize_embeddings=True)
    return vec.tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    truncated = [t[:1000] for t in texts]
    vecs = get_model().encode(truncated, normalize_embeddings=True, batch_size=64, show_progress_bar=True)
    return [v.tolist() for v in vecs]
