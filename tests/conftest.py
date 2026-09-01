import sys
import uuid
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
NEURO_GHOST_DIR = REPO_ROOT / "neuro_ghost"

# neuro_ghost/*.py use flat imports (e.g. `from db import ...`), the same way
# they resolve when run directly as `python neuro_ghost/ingest_linkml.py` —
# so neuro_ghost/ itself, not just the repo root, must be on sys.path.
for p in (str(REPO_ROOT), str(NEURO_GHOST_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

FIXTURES = Path(__file__).parent / "fixtures"


def is_uuid(s) -> bool:
    """Every entity id is a uuid4 string. Assert it parses."""
    try:
        uuid.UUID(s)
        return True
    except (ValueError, TypeError):
        return False


@pytest.fixture
def conn(tmp_path):
    """A fresh, empty LadybugDB in pytest's per-test temp dir."""
    from db import get_connection
    return get_connection(str(tmp_path / "test.lbug"))
