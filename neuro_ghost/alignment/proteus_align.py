"""
proteus_align.py — Proteus alignment module caller
====================================================

Tries to import the external `proteus` package (neurovium/Proteus).
When it is installed, delegates to it directly.
When it is not, falls back to the inline Proteus implementation in align.py
so the pipeline always works regardless of whether the satellite module
has been installed.

Usage
-----
  from neuro_ghost.alignment.proteus_align import compute_alignment, BACKEND

  result = compute_alignment(class_a, class_b)
  # result is a _Pending-like object with .confidence, .predicate, .method
  print(BACKEND)  # "proteus-package" or "proteus-inline"
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Attempt to import the external Proteus package
# ---------------------------------------------------------------------------

BACKEND: str

try:
    # neurovium/Proteus exposes its pipeline under `proteus.align`
    from proteus.align import compute_alignment as _proteus_compute  # type: ignore
    from proteus.align import repair_structural, write_alignment      # type: ignore

    def compute_alignment(a: dict, b: dict):
        return _proteus_compute(a, b)

    BACKEND = "proteus-package"

except ImportError:
    # Fall back to the inline implementation that lives in align.py
    import sys
    from pathlib import Path

    # Ensure neuro_ghost/ is on sys.path so `align` can be imported as a module
    _pkg_dir = Path(__file__).resolve().parents[1]
    if str(_pkg_dir) not in sys.path:
        sys.path.insert(0, str(_pkg_dir))

    from align import (  # type: ignore
        compute_alignment,
        repair_structural,
        write_alignment,
    )

    BACKEND = "proteus-inline"


# ---------------------------------------------------------------------------
# Re-export the full pipeline surface so callers only need this module
# ---------------------------------------------------------------------------

__all__ = [
    "compute_alignment",
    "repair_structural",
    "write_alignment",
    "BACKEND",
]
