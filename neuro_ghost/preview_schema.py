"""
preview_schema.py — What a schema would add to the registry, before submitting it
================================================================================
Builds the schema's registry entities locally (no graph, nothing written) and
compares their content hashes with the current export (data/registry.json).
Hashes are content-only, so an equal hash means the registry already has that
exact class or property and ingest will reuse it. Reports, for classes and
properties:

  * already in the registry (same content) — and from which schemas;
  * same name as a registry entity but different content — worth a look:
    a deliberate difference, or a near-copy that could reuse the existing one;
  * new;
  * missing descriptions (they make reuse and mapping much harder).

Usage:
    python neuro_ghost/preview_schema.py registry_schemas/<name>.yml
    python neuro_ghost/preview_schema.py my_schema.json        # JSON Schema: converted first
"""
from __future__ import annotations

import json
import logging
import tempfile
from collections import defaultdict
from pathlib import Path

import click
import yaml

from ingest_linkml import build_registry_entities, parse_linkml


def _registry_index(registry: dict) -> tuple[dict, dict]:
    """(sha256 -> {name, sources}, name -> [sha256]) for classes and for properties."""
    by_hash = {"class": {}, "property": {}}
    by_name = {"class": defaultdict(set), "property": defaultdict(set)}

    def add(kind, entity):
        h = entity.get("sha256_hash")
        if not h:
            return
        e = by_hash[kind].setdefault(h, {"name": entity["name"], "sources": set()})
        e["sources"].update(entity.get("sources", []))
        by_name[kind][entity["name"]].add(h)

    for c in registry.get("classes", []):
        add("class", c)
        for p in c.get("properties", []):
            add("property", p)
    return by_hash, by_name


def preview(schema: Path, registry: dict, label: str) -> dict:
    """Compare the schema's classes and properties with the registry."""
    properties, classes, *_ = build_registry_entities(parse_linkml(schema), label, "preview")
    by_hash, by_name = _registry_index(registry)
    report = {}
    for kind, entities in (("class", classes.values()), ("property", properties.values())):
        existing, renamed, new, undescribed = [], [], [], []
        for e in sorted(entities, key=lambda e: e.name):
            if not (e.description or "").strip():
                undescribed.append(e.name)
            hit = by_hash[kind].get(e.sha256_hash)
            if hit:
                existing.append((e.name, sorted(hit["sources"])))
            elif by_name[kind].get(e.name):
                renamed.append((e.name, sorted({s for h in by_name[kind][e.name]
                                               for s in by_hash[kind][h]["sources"]})))
            else:
                new.append(e.name)
        report[kind] = {"total": len(existing) + len(renamed) + len(new), "existing": existing,
                        "same_name_different_content": renamed, "new": new,
                        "missing_description": undescribed}
    return report


def _show(report: dict, limit: int) -> None:
    def names(items, with_sources=False):
        shown = [f"{n} ({', '.join(s)})" if with_sources else n for n, s in items] \
            if with_sources else list(items)
        more = f" … +{len(shown) - limit} more" if len(shown) > limit else ""
        return ", ".join(shown[:limit]) + more if shown else "—"

    for kind, label in (("class", "Classes"), ("property", "Properties")):
        r = report[kind]
        click.echo(f"\n{label}: {r['total']}")
        click.echo(f"  already in the registry (reused): {len(r['existing'])}  {names(r['existing'], True)}")
        click.echo(f"  same name, different content:     {len(r['same_name_different_content'])}  "
                   f"{names(r['same_name_different_content'], True)}")
        click.echo(f"  new:                              {len(r['new'])}  {names(r['new'])}")
        click.echo(f"  missing a description:            {len(r['missing_description'])}  "
                   f"{names(r['missing_description'])}")


@click.command()
@click.argument("schema", type=click.Path(exists=True, path_type=Path))
@click.option("--registry", default="data/registry.json", show_default=True,
              type=click.Path(exists=True, path_type=Path))
@click.option("--label", default=None, help="Source label to preview under (default: file name).")
@click.option("--limit", default=12, show_default=True, help="Names listed per line.")
@click.option("--json", "as_json", is_flag=True, help="Print the full report as JSON.")
def cli(schema: Path, registry: Path, label: str | None, limit: int, as_json: bool) -> None:
    """Preview what SCHEMA (LinkML .yml, or JSON Schema .json) would add to the registry."""
    logging.disable(logging.WARNING)
    label = label or schema.name.split(".")[0]
    if schema.suffix == ".json":
        from converters.from_jsonschema import convert
        converted = Path(tempfile.mkdtemp()) / f"{label}.yml"
        converted.write_text(yaml.safe_dump(convert(json.loads(schema.read_text()), label),
                                            sort_keys=False))
        schema = converted
    report = preview(schema, json.loads(registry.read_text()), label)
    if as_json:
        click.echo(json.dumps(report, indent=2))
    else:
        _show(report, limit)


if __name__ == "__main__":
    cli()
