"""Optional embedding-based semantic similarity.

Uses ``sentence-transformers`` when installed and ``use_model=True``,
otherwise falls back to a deterministic bag-of-words cosine. The fallback
is intentionally cheap so the rest of the pipeline never has a hard
dependency on a neural model.
"""

from __future__ import annotations

from typing import Sequence

from reward_hack_detector.signals.lexical import bow_cosine


class EmbeddingSignal:
    """Compute semantic similarity between two strings.

    Parameters
    ----------
    use_model:
        When ``True``, attempt to load ``sentence-transformers``. If the
        import fails, silently fall back to bag-of-words cosine.
    model_name:
        Sentence-transformers model identifier. The default is a small,
        fast model suitable for CPU.
    """

    def __init__(
        self,
        *,
        use_model: bool = False,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    ) -> None:
        self.use_model = use_model
        self.model_name = model_name
        self._model = None
        self._backend = "bow"
        if use_model:
            try:  # pragma: no cover - exercised only when extras are installed
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(model_name)
                self._backend = "sentence-transformers"
            except Exception:
                self._model = None
                self._backend = "bow"

    @property
    def backend(self) -> str:
        return self._backend

    def similarity(self, a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        if self._model is not None:  # pragma: no cover - depends on extras
            import numpy as np  # type: ignore

            embs = self._model.encode([a, b], normalize_embeddings=True)
            return float(np.dot(embs[0], embs[1]))
        return bow_cosine(a, b)

    def similarities(self, pairs: Sequence[tuple[str, str]]) -> list[float]:
        return [self.similarity(a, b) for a, b in pairs]
