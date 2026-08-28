"""
base_align.py — Simple embedding-based alignment (no Proteus dependency)
=========================================================================

Takes two MatchingProfile dicts (same schema as align.py) and returns a
confidence score using cosine similarity on sentence embeddings, with token
Jaccard as a fallback when the embedding model is unavailable.

This is intentionally kept simple — no unit veto, no structural repair,
no IRI anchoring. Those are Proteus concerns. Use this when you want a
fast baseline or when the Proteus module is not installed.

Interface
---------
  score(a, b) -> float          # 0.0 (unrelated) – 1.0 (identical)
  align(a, b) -> AlignResult    # score + method label
  align_many(pairs) -> list[AlignResult]
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from typing import Sequence

# ---------------------------------------------------------------------------
# Lazy embedding model
# ---------------------------------------------------------------------------

_model = None
_model_name = "all-MiniLM-L6-v2"


def _get_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(_model_name)
        except Exception:
            _model = "unavailable"
    return _model


def _embed(text: str) -> list[float] | None:
    if not text or not text.strip():
        return None
    m = _get_model()
    if m == "unavailable":
        return None
    return m.encode([text], normalize_embeddings=True)[0].tolist()


def _cosine(a: list[float], b: list[float]) -> float:
    import numpy as np
    return float(np.dot(a, b))


# ---------------------------------------------------------------------------
# Lexical fallback
# ---------------------------------------------------------------------------

def _tokens(name: str) -> set[str]:
    s = re.sub(r"([a-z])([A-Z])", r"\1_\2", name)
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", s)
    return set(re.split(r"[\s_\-/]+", s.lower())) - {""}


def _jaccard(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    union = ta | tb
    return len(ta & tb) / len(union) if union else 0.0


def _string_sim(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

@dataclass
class AlignResult:
    a_name:     str
    b_name:     str
    confidence: float   # 0.0–1.0
    distance:   float   # 1.0 - confidence
    method:     str     # "embedding-cosine" | "lexical-jaccard" | "lexical-string"


# ---------------------------------------------------------------------------
# Core scoring
# ---------------------------------------------------------------------------

def score(a: dict, b: dict) -> tuple[float, str]:
    """
    Return (confidence, method) for a pair of MatchingProfile dicts.
    Uses embedding cosine on (name + definition) when model is available,
    falls back to max(jaccard, string_sim) on names.
    """
    a_text = " ".join(filter(None, [a.get("name", ""), a.get("definition", "")])).strip()
    b_text = " ".join(filter(None, [b.get("name", ""), b.get("definition", "")])).strip()

    ea = _embed(a_text)
    eb = _embed(b_text)

    if ea is not None and eb is not None:
        return _cosine(ea, eb), "embedding-cosine"

    # Lexical fallback
    name_a, name_b = a.get("name", ""), b.get("name", "")
    jac = _jaccard(name_a, name_b)
    sim = _string_sim(name_a, name_b)
    if jac >= sim:
        return jac, "lexical-jaccard"
    return sim, "lexical-string"


def align(a: dict, b: dict) -> AlignResult:
    conf, method = score(a, b)
    return AlignResult(
        a_name=a.get("name", ""),
        b_name=b.get("name", ""),
        confidence=round(conf, 6),
        distance=round(1.0 - conf, 6),
        method=method,
    )


def align_many(pairs: Sequence[tuple[dict, dict]]) -> list[AlignResult]:
    return [align(a, b) for a, b in pairs]
