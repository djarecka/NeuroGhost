"""Unit tests for neuro_ghost.import_resolver.

Covers:
  - No-op when a schema declares no external imports or no imports_source
  - CURIE-style imports (linkml:types) are always skipped
  - A one-level external import is fetched into the work_dir
  - Recursive resolution (fetched files' own imports are fetched too)
  - A missing import + missing imports_source raises loudly
  - Cycle protection via the seen-set and MAX_DEPTH
  - Mapping-form annotations, list-form annotations, and dict-value forms
    all get read the same way
"""
from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import yaml

from import_resolver import (
    MAX_DEPTH,
    _external_import_names,
    _read_annotation_source,
    resolve_external_imports,
)


# ---------------------------------------------------------------------------
# Tiny mock httpx.Client — dispatches by URL from a dict.
# ---------------------------------------------------------------------------

class FakeClient:
    """Stand-in for httpx.Client. `responses` maps a URL to either a raw
    string (200 OK with that body) or an int (that HTTP status, empty body)."""
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _write(path: Path, obj: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj, sort_keys=False))
    return path


@pytest.fixture
def tmp_schema(tmp_path):
    """Factory for temporary LinkML schemas in an isolated dir."""
    def _make(name: str, body: dict) -> Path:
        return _write(tmp_path / f"{name}.yaml", body)
    return _make


# ---------------------------------------------------------------------------
# Annotation reader
# ---------------------------------------------------------------------------

def test_read_annotation_source_mapping_form():
    assert _read_annotation_source({
        "annotations": {"imports_source": "https://example.com/x"}
    }) == "https://example.com/x"


def test_read_annotation_source_dict_value_form():
    # LinkML's `annotations:` can hold {tag: {value: ...}} shapes when
    # additional metadata is attached to the annotation.
    assert _read_annotation_source({
        "annotations": {"imports_source": {"value": "https://example.com/x"}}
    }) == "https://example.com/x"


def test_read_annotation_source_list_form():
    assert _read_annotation_source({
        "annotations": [
            {"tag": "unrelated", "value": "ignore me"},
            {"tag": "imports_source", "value": "https://example.com/x"},
        ]
    }) == "https://example.com/x"


def test_read_annotation_source_missing():
    assert _read_annotation_source({}) is None
    assert _read_annotation_source({"annotations": {"other": "v"}}) is None


# ---------------------------------------------------------------------------
# External-import filter
# ---------------------------------------------------------------------------

def test_external_import_names_skips_curies():
    yml = {"imports": ["linkml:types", "biolink:core", "bican_biolink", "bican_core"]}
    assert _external_import_names(yml) == ["bican_biolink", "bican_core"]


def test_external_import_names_empty():
    assert _external_import_names({}) == []
    assert _external_import_names({"imports": []}) == []


# ---------------------------------------------------------------------------
# resolve_external_imports — the real thing
# ---------------------------------------------------------------------------

def test_no_annotation_is_a_noop(tmp_schema, tmp_path):
    """A schema without imports_source returns unchanged and writes nothing
    to work_dir — matches pre-existing bbqs/bids/… behavior."""
    schema = tmp_schema("plain", {
        "id": "https://example.org/plain",
        "name": "plain",
        "imports": ["linkml:types"],
    })
    work_dir = tmp_path / "work"

    client = FakeClient({})
    result = resolve_external_imports(schema, work_dir, client=client)

    assert result == schema
    assert client.calls == []
    assert not work_dir.exists() or not any(work_dir.iterdir())


def test_only_curie_imports_is_a_noop_even_with_source(tmp_schema, tmp_path):
    """imports_source set but every import is a built-in CURIE — nothing
    to fetch, no work_dir writes."""
    schema = tmp_schema("plain", {
        "id": "https://example.org/plain",
        "imports": ["linkml:types"],
        "annotations": {"imports_source": "https://example.com/base"},
    })
    work_dir = tmp_path / "work"

    client = FakeClient({})
    result = resolve_external_imports(schema, work_dir, client=client)

    # No external imports → returns original path, does no work.
    assert result == schema
    assert client.calls == []


def test_single_external_import_fetched(tmp_schema, tmp_path):
    """One external import is fetched and materialized in work_dir alongside
    a copy of the original schema."""
    schema = tmp_schema("root", {
        "id": "https://example.org/root",
        "imports": ["linkml:types", "sib"],
        "annotations": {"imports_source": "https://example.com/base"},
    })
    work_dir = tmp_path / "work"

    sib_body = yaml.safe_dump({
        "id": "https://example.org/sib",
        "name": "sib",
        "classes": {"Thing": {"description": "a thing"}},
    })
    client = FakeClient({"https://example.com/base/sib.yaml": sib_body})

    result = resolve_external_imports(schema, work_dir, client=client)

    assert result == work_dir / "root.yaml"
    assert (work_dir / "sib.yaml").exists()
    assert yaml.safe_load((work_dir / "sib.yaml").read_text())["name"] == "sib"
    assert client.calls == ["https://example.com/base/sib.yaml"]


def test_yml_fallback_after_yaml_404(tmp_schema, tmp_path):
    """If the .yaml URL 404s, the resolver falls back to .yml."""
    schema = tmp_schema("root", {
        "imports": ["sib"],
        "annotations": {"imports_source": "https://example.com/base"},
    })
    work_dir = tmp_path / "work"

    sib_body = yaml.safe_dump({"name": "sib"})
    client = FakeClient({
        "https://example.com/base/sib.yaml": 404,
        "https://example.com/base/sib.yml":  sib_body,
    })

    resolve_external_imports(schema, work_dir, client=client)

    assert (work_dir / "sib.yml").exists()
    assert client.calls == [
        "https://example.com/base/sib.yaml",
        "https://example.com/base/sib.yml",
    ]


def test_recursive_imports_fetched(tmp_schema, tmp_path):
    """A fetched sibling declaring its own `imports:` triggers another
    round of fetches, inheriting the source URL."""
    schema = tmp_schema("root", {
        "imports": ["sib_a"],
        "annotations": {"imports_source": "https://example.com/base"},
    })
    work_dir = tmp_path / "work"

    sib_a_body = yaml.safe_dump({
        "name": "sib_a",
        "imports": ["linkml:types", "sib_b"],
    })
    sib_b_body = yaml.safe_dump({"name": "sib_b"})
    client = FakeClient({
        "https://example.com/base/sib_a.yaml": sib_a_body,
        "https://example.com/base/sib_b.yaml": sib_b_body,
    })

    resolve_external_imports(schema, work_dir, client=client)

    assert (work_dir / "sib_a.yaml").exists()
    assert (work_dir / "sib_b.yaml").exists()
    assert set(client.calls) == {
        "https://example.com/base/sib_a.yaml",
        "https://example.com/base/sib_b.yaml",
    }


def test_cycle_is_broken_by_seen_set(tmp_schema, tmp_path):
    """sib_a imports sib_b, sib_b imports sib_a — resolution must terminate
    without re-fetching."""
    schema = tmp_schema("root", {
        "imports": ["sib_a"],
        "annotations": {"imports_source": "https://example.com/base"},
    })
    work_dir = tmp_path / "work"

    sib_a_body = yaml.safe_dump({"name": "sib_a", "imports": ["sib_b"]})
    sib_b_body = yaml.safe_dump({"name": "sib_b", "imports": ["sib_a"]})
    client = FakeClient({
        "https://example.com/base/sib_a.yaml": sib_a_body,
        "https://example.com/base/sib_b.yaml": sib_b_body,
    })

    resolve_external_imports(schema, work_dir, client=client)

    # Each sibling fetched exactly once, cycle didn't hang the loop.
    assert sorted(client.calls) == [
        "https://example.com/base/sib_a.yaml",
        "https://example.com/base/sib_b.yaml",
    ]


def test_missing_import_without_source_raises(tmp_schema, tmp_path):
    """An external import name with no imports_source is a loud error, not
    a silent parse degradation."""
    schema = tmp_schema("root", {"imports": ["sib"]})
    work_dir = tmp_path / "work"

    client = FakeClient({})
    with pytest.raises(FileNotFoundError, match="no annotations.imports_source"):
        resolve_external_imports(schema, work_dir, client=client)


def test_unreachable_import_raises(tmp_schema, tmp_path):
    """Both .yaml and .yml return 404 — resolver surfaces the failure."""
    schema = tmp_schema("root", {
        "imports": ["ghost"],
        "annotations": {"imports_source": "https://example.com/base"},
    })
    work_dir = tmp_path / "work"

    client = FakeClient({
        "https://example.com/base/ghost.yaml": 404,
        "https://example.com/base/ghost.yml":  404,
    })
    with pytest.raises(FileNotFoundError, match="Could not fetch import 'ghost'"):
        resolve_external_imports(schema, work_dir, client=client)


def test_child_imports_source_overrides_parent(tmp_schema, tmp_path):
    """A fetched sibling can declare its own imports_source; its transitive
    imports come from that URL rather than the root's."""
    schema = tmp_schema("root", {
        "imports": ["sib_a"],
        "annotations": {"imports_source": "https://one.example.com"},
    })
    work_dir = tmp_path / "work"

    sib_a_body = yaml.safe_dump({
        "name": "sib_a",
        "imports": ["sib_b"],
        "annotations": {"imports_source": "https://two.example.com"},
    })
    sib_b_body = yaml.safe_dump({"name": "sib_b"})
    client = FakeClient({
        "https://one.example.com/sib_a.yaml": sib_a_body,
        "https://two.example.com/sib_b.yaml": sib_b_body,
    })

    resolve_external_imports(schema, work_dir, client=client)

    assert (work_dir / "sib_a.yaml").exists()
    assert (work_dir / "sib_b.yaml").exists()
    # sib_b came from the child's URL, NOT the root's.
    assert "https://two.example.com/sib_b.yaml" in client.calls
    assert "https://one.example.com/sib_b.yaml" not in client.calls


def test_local_sibling_shortcircuits_fetch(tmp_schema, tmp_path):
    """An import whose file already sits next to the input schema is
    trusted — no fetch attempt is made."""
    schema = tmp_schema("root", {
        "imports": ["local_sib"],
        "annotations": {"imports_source": "https://example.com/base"},
    })
    # Drop the sibling next to root.yaml.
    (schema.parent / "local_sib.yaml").write_text(yaml.safe_dump({"name": "local_sib"}))

    work_dir = tmp_path / "work"
    client = FakeClient({})  # empty — any fetch would return 404 and fail

    result = resolve_external_imports(schema, work_dir, client=client)

    # A copy of the root schema still lands in work_dir (SchemaView will
    # be pointed at that copy), but no fetch was issued.
    assert result == work_dir / "root.yaml"
    assert client.calls == []


def test_max_depth_guard(tmp_schema, tmp_path):
    """A chain longer than MAX_DEPTH raises RecursionError."""
    schema = tmp_schema("root", {
        "imports": ["sib_0"],
        "annotations": {"imports_source": "https://example.com/base"},
    })
    work_dir = tmp_path / "work"

    # Chain sib_0 → sib_1 → … → sib_{MAX_DEPTH+1}
    responses: dict[str, str | int] = {}
    for i in range(MAX_DEPTH + 2):
        body = {"name": f"sib_{i}", "imports": [f"sib_{i+1}"]}
        responses[f"https://example.com/base/sib_{i}.yaml"] = yaml.safe_dump(body)
    client = FakeClient(responses)

    with pytest.raises(RecursionError, match="MAX_DEPTH"):
        resolve_external_imports(schema, work_dir, client=client)
