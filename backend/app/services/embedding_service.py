from fastembed import TextEmbedding


# ============================================================
# Lightweight embedding model
# ============================================================

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_model = None


# ============================================================
# Lazy model loading
# ============================================================

def _get_model() -> TextEmbedding:
    global _model

    if _model is None:
        _model = TextEmbedding(
            model_name=MODEL_NAME
        )

    return _model


# ============================================================
# Generate embeddings
# ============================================================

def generate_embeddings(
    texts: list[str],
) -> list[list[float]]:
    if not texts:
        return []

    model = _get_model()

    embeddings = model.embed(texts)

    return [
        embedding.tolist()
        for embedding in embeddings
    ]