"""
Vellum OS — Embeddings Tool (Optional)

Not loaded by default — only activated if user enables semantic search.
Uses BAAI/bge-small-en-v1.5 via sentence-transformers.
"""

from __future__ import annotations

from vellum.config.logging import get_logger

log = get_logger("embeddings")

_model = None


def _get_model():
    """Lazy-load the embedding model."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer

            _model = SentenceTransformer("BAAI/bge-small-en-v1.5")
            log.info("embedding_model_loaded", model="bge-small-en-v1.5")
        except ImportError:
            log.warning(
                "sentence_transformers_not_installed",
                hint="pip install vellum-os[embeddings]",
            )
            raise
    return _model


def embed_text(text: str) -> list[float]:
    """Embed a single text string."""
    model = _get_model()
    embedding = model.encode(
        f"Represent this sentence for searching relevant passages: {text}",
        normalize_embeddings=True,
    )
    return embedding.tolist()


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed multiple texts in batch."""
    model = _get_model()
    prefix = "Represent this sentence for searching relevant passages: "
    prefixed = [prefix + t for t in texts]
    embeddings = model.encode(prefixed, normalize_embeddings=True)
    return embeddings.tolist()
