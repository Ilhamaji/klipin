"""LaBSE sentence-embedding provider.

Device policy
-------------
LaBSE embeddings are served from the CPU. That is deliberate:

* The REST endpoints (/ai/search, /ai/summarize) are called by the Klipin
  backend over plain HTTP, i.e. outside any Gradio event context. A function
  wrapped in ``@spaces.GPU`` is dispatched to a ZeroGPU worker through a
  Gradio request context and a multiprocessing queue, so calling it from a
  REST request fails with "ZeroGPU worker error". Keeping the encode path on
  the CPU is what makes the API reliable.
* Encoding a single short query with LaBSE on CPU takes milliseconds, so the
  GPU buys nothing here; the expensive work (PDF extraction, LLM calls) is
  remote anyway.

ZeroGPU requirement
-------------------
A ZeroGPU Space refuses to start unless at least one ``@spaces.GPU`` function
is registered during startup. ``gpu_status`` below satisfies that check. It is
only ever called from the Gradio UI (which does provide the request context),
never from the REST API.
"""

from __future__ import annotations

import spaces
from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/LaBSE"

# LaBSE is loaded once and reused across requests.
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME, device="cpu")
    return _model


def get_embedding_model() -> SentenceTransformer:
    """Return the shared CPU LaBSE model."""
    return _get_model()


def encode_texts(texts, **kwargs):
    """Encode texts with LaBSE on the CPU.

    Kept as a free function so existing call sites keep working unchanged.
    Encoding kwargs are passed through untouched so similarity thresholds and
    cached embeddings behave exactly as before.
    """
    return _get_model().encode(texts, **kwargs)


@spaces.GPU
def gpu_status() -> str:
    """Presence marker for ZeroGPU.

    A ZeroGPU Space will not boot without at least one ``@spaces.GPU``
    function. This trivial function exists only to satisfy that check and to
    report the device the Space sees. Do not call it from REST handlers.
    """
    try:
        import torch

        if torch.cuda.is_available():
            return f"gpu available: {torch.cuda.get_device_name(0)}"
    except Exception:  # pragma: no cover - torch is always present in Spaces
        pass
    return "cpu"


class LazyEmbeddingModel:
    """Drop-in wrapper so existing ``embedding_model.encode(...)`` calls work."""

    def encode(self, *args, **kwargs):
        return encode_texts(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(_get_model(), name)


embedding_model = LazyEmbeddingModel()
