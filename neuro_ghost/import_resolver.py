"""
import_resolver.py — Fetch LinkML imports declared in a submitted schema
========================================================================

Why this exists
---------------
LinkML schemas can `imports:` other schemas by name (e.g. `bican_biolink`,
`bican_core`) and SchemaView resolves those names by looking in the input
schema's own directory. NeuroGhost stores each submission as a single
`registry_schemas/<name>.yml` file — no sibling schemas alongside it — so
any external import would break ingestion cold: SchemaView raises
`No such class` when a parent lookup crosses into an unresolved import,
and `parse_linkml`'s tolerant branch silently drops those `is_a` links
and their inherited slots.

To keep the "one committed schema per submission" invariant while still
supporting schemas built on shared upstream models (biolink, PROV, …),
a submitter declares where the missing siblings live and this module
fetches them into a temp directory before SchemaView sees the file.

Contract
--------
The submitter opts into external resolution by adding a LinkML
`annotations:` entry (LinkML-native, no new file format):

    id: https://example.org/my-schema
    imports:
      - linkml:types
      - bican_biolink
      - bican_core
    annotations:
      imports_source: https://raw.githubusercontent.com/brain-bican/models/main/linkml-schema

`imports_source` is treated as a directory URL: for each unresolved import
name, we try `<imports_source>/<name>.yaml` then `.yml`. CURIE-form
imports (anything with `:` before a `/`, e.g. `linkml:types`) are LinkML
built-ins and skipped.

Resolution is recursive with a seen-set — a fetched schema's own imports
are resolved the same way, inheriting the top-level `imports_source`
unless the fetched file declares its own annotation.

Nothing happens for a schema without the annotation. Existing schemas
(bbqs, bids, dandi, …) go through unchanged.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import httpx
import yaml


MAX_DEPTH = 8  # cap recursion so a pathological import graph can't hang the ingester


def _read_annotation_source(schema_yaml: dict) -> str | None:
    """Return the imports_source URL from a schema's top-level `annotations:`
    block, or None if not present. LinkML permits two annotation shapes:
    a mapping (`imports_source: <val>`) or a list of `{tag, value}` entries.
    Both are supported here."""
    ann = schema_yaml.get("annotations")
    if not ann:
        return None
    if isinstance(ann, dict):
        val = ann.get("imports_source")
        if isinstance(val, dict):
            return val.get("value")
        return val if isinstance(val, str) else None
    if isinstance(ann, list):
        for item in ann:
            if isinstance(item, dict) and item.get("tag") == "imports_source":
                v = item.get("value")
                return v if isinstance(v, str) else None
    return None


def _external_import_names(schema_yaml: dict) -> list[str]:
    """Names from `imports:` that aren't CURIE-form (e.g. `linkml:types`).
    Those CURIEs are LinkML built-ins that SchemaView resolves internally."""
    raw = schema_yaml.get("imports") or []
    out = []
    for name in raw:
        if not isinstance(name, str):
            continue
        # Skip CURIE-form built-ins ("prefix:local") — but be lenient: a
        # bare colon-less name is what we resolve.
        if ":" in name:
            continue
        out.append(name)
    return out


def _fetch_import(source_url: str, name: str, dest_dir: Path,
                  client: httpx.Client) -> Path:
    """Fetch `<source_url>/<name>.yaml` (fallback `.yml`) into dest_dir.
    Returns the local path. Raises on HTTP failure so the caller sees a
    real error rather than a silently-degraded ingest."""
    base = source_url.rstrip("/")
    for ext in ("yaml", "yml"):
        url = f"{base}/{name}.{ext}"
        r = client.get(url, timeout=30.0, follow_redirects=True)
        if r.status_code == 200:
            local = dest_dir / f"{name}.{ext}"
            local.write_bytes(r.content)
            return local
        if r.status_code != 404:
            r.raise_for_status()
    raise FileNotFoundError(
        f"Could not fetch import '{name}' from {source_url} (tried .yaml and .yml)"
    )


def _resolve_recursive(schema_path: Path, source_url: str | None,
                       dest_dir: Path, extra_search_dir: Path | None,
                       seen: set[str], depth: int,
                       client: httpx.Client) -> None:
    """Ensure every import declared by schema_path is on disk in dest_dir,
    recursing into each fetched file.

    `extra_search_dir` is the directory where the ingester-submitted
    schema originally sits. Its siblings are trusted as satisfying an
    import name, in addition to files already fetched into `dest_dir`
    and files sitting next to schema_path itself (which, for anything
    beyond the top-level call, is inside dest_dir already).
    """
    if depth > MAX_DEPTH:
        raise RecursionError(
            f"Import graph exceeded MAX_DEPTH={MAX_DEPTH} while resolving {schema_path.name}"
        )

    with schema_path.open() as f:
        schema_yaml = yaml.safe_load(f) or {}

    # A fetched file can declare its own imports_source and override the
    # parent's — otherwise inherit.
    child_source = _read_annotation_source(schema_yaml) or source_url

    search_dirs = [schema_path.parent, dest_dir]
    if extra_search_dir is not None:
        search_dirs.append(extra_search_dir)

    for name in _external_import_names(schema_yaml):
        if name in seen:
            continue
        seen.add(name)

        # Any of: sitting next to the input schema (submitter bundled it),
        # already fetched into dest_dir in an earlier pass, or (for
        # a fetched file) sitting next to that file inside dest_dir.
        already_local = any(
            (d / f"{name}.{ext}").exists()
            for d in search_dirs for ext in ("yaml", "yml")
        )
        if already_local:
            continue

        if not child_source:
            # Import can't be resolved locally and no source_url to fetch
            # from. Leaving it unresolved would produce a silent parse
            # degradation — better to fail loudly.
            raise FileNotFoundError(
                f"Schema '{schema_path.name}' imports '{name}' but no "
                f"annotations.imports_source URL is declared to fetch it from."
            )

        fetched = _fetch_import(child_source, name, dest_dir, client)
        _resolve_recursive(fetched, child_source, dest_dir,
                           extra_search_dir, seen, depth + 1, client)


def resolve_external_imports(schema_path: Path, work_dir: Path,
                             client: httpx.Client | None = None) -> Path:
    """
    Materialize `schema_path` and all its external imports into `work_dir`,
    returning the path to the copied schema. If the schema has no external
    imports (only CURIE-form built-ins) and no imports_source annotation,
    the original path is returned unchanged and no work_dir writes happen.

    `client` is optional and only used for testing — pass a pre-mocked
    httpx.Client to avoid real network access. In production the function
    creates its own client per call.
    """
    with schema_path.open() as f:
        schema_yaml = yaml.safe_load(f) or {}

    imports = _external_import_names(schema_yaml)
    source_url = _read_annotation_source(schema_yaml)

    # Zero external imports (only CURIE-form built-ins, or none at all)
    # → nothing to fetch, nothing to prepare. Return the input unchanged.
    if not imports:
        return schema_path

    work_dir.mkdir(parents=True, exist_ok=True)
    local_schema = work_dir / schema_path.name
    shutil.copy2(schema_path, local_schema)

    owns_client = client is None
    if owns_client:
        client = httpx.Client()
    try:
        # The recursive walk needs both directories to consider a name
        # already-resolved: `work_dir` for anything fetched in this run,
        # and the input schema's original directory in case the submitter
        # bundled the sibling next to it.
        _resolve_recursive(local_schema, source_url, work_dir,
                           extra_search_dir=schema_path.parent,
                           seen=set(), depth=0, client=client)
    finally:
        if owns_client:
            client.close()

    return local_schema
