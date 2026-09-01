import sys
import uuid
from pathlib import Path

import httpx
import pytest
import yaml

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


# ---------------------------------------------------------------------------
# Shared test helpers
# ---------------------------------------------------------------------------

class FakeHttpxClient:
    """Stand-in for httpx.Client used by any test that exercises code taking
    an httpx client as a dependency (e.g. the import resolver).

    `responses` maps a URL to either a raw string (returned as a 200 with
    that body) or an int (that HTTP status, empty body). An unmapped URL
    returns 404. Every call is recorded on `.calls` for assertions.
    """
    def __init__(self, responses: dict[str, str | int]):
        self.responses = responses
        self.calls: list[str] = []

    def get(self, url, timeout=None, follow_redirects=None):
        self.calls.append(url)
        r = self.responses.get(url)
        if isinstance(r, str):
            return httpx.Response(200, content=r.encode("utf-8"))
        if isinstance(r, int):
            return httpx.Response(r)
        return httpx.Response(404)

    def close(self):
        pass


@pytest.fixture
def fake_httpx_client():
    """Factory fixture: `client = fake_httpx_client({url: body_or_status})`.

    Returned as a factory rather than a pre-configured instance so each
    test can define its own URL → response map inline.
    """
    def _make(responses: dict[str, str | int]) -> FakeHttpxClient:
        return FakeHttpxClient(responses)
    return _make


@pytest.fixture
def tmp_schema(tmp_path):
    """Factory fixture: `path = tmp_schema('name', {yaml_dict})`.

    Writes a LinkML YAML file into pytest's per-test tmp_path directory
    and returns the path. Used anywhere a test needs a real LinkML file
    on disk for SchemaView / the resolver to open.
    """
    def _make(name: str, body: dict) -> Path:
        path = tmp_path / f"{name}.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(body, sort_keys=False))
        return path
    return _make
