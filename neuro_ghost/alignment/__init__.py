"""
neuro_ghost.alignment
=====================

Two alignment backends, same interface:

  base_align    — cosine similarity on sentence embeddings; no external deps
  proteus_align — Proteus pipeline (external package or inline fallback)

Quick start::

    from neuro_ghost.alignment.base_align import align
    from neuro_ghost.alignment.proteus_align import compute_alignment, BACKEND
"""

from .base_align import align, align_many, AlignResult
from .proteus_align import compute_alignment, BACKEND

__all__ = ["align", "align_many", "AlignResult", "compute_alignment", "BACKEND"]
