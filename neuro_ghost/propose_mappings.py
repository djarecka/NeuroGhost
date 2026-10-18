"""
propose_mappings.py — Candidate mappings between two schemas, from embeddings
=============================================================================
Embeds every class or property of a subject schema and an object schema
("name: definition", free local sentence-transformers model) and writes each
subject entity's best object matches as a PROPOSED mapping file
(mappings/*.sssom.tsv, see mappings.py). Nothing here decides what's right —
scores are evidence for a reviewer, a person, or a stronger model (the
propose-mappings skill reads this file and asks the user to approve rows).

Reads the registry.json export, not the graph, so it runs without a rebuild.

Either side can be `all` (every other registered schema; `all all` = every
pair once), and `--kind all` does classes and properties — all into one file.

Usage:
    python neuro_ghost/propose_mappings.py aind bids --kind properties
    python neuro_ghost/propose_mappings.py asset bbqs --kind classes --top-k 2 --min-score 0.7
    python neuro_ghost/propose_mappings.py aind all --kind all
"""
from __future__ import annotations

import datetime
import json
from dataclasses import dataclass
from pathlib import Path

import click

DEFAULT_MODEL = "all-MiniLM-L6-v2"


@dataclass
class Entity:
    id: str
    ref: str          # source:Class or source:Class.prop
    name: str
    definition: str

    @property
    def text(self) -> str:
        return f"{self.name}: {self.definition[:300]}" if self.definition else self.name


def entities(registry: dict, source: str, kind: str) -> list[Entity]:
    """A source's classes or properties. A property used by several classes
    is one entity, referenced through the first of those classes by name."""
    found: dict[str, Entity] = {}
    for c in sorted(registry.get("classes", []), key=lambda c: c["name"]):
        if source not in c.get("sources", []):
            continue
        if kind == "classes":
            found.setdefault(c["id"], Entity(c["id"], f"{source}:{c['name']}",
                                             c["name"], c.get("definition") or ""))
            continue
        for p in c.get("properties", []):
            if source in p.get("sources", []):
                found.setdefault(p["id"], Entity(p["id"], f"{source}:{c['name']}.{p['name']}",
                                                 p["name"], p.get("definition") or ""))
    return list(found.values())


def schema_pairs(registry: dict, subject: str, obj: str) -> list[tuple[str, str]]:
    """The (subject, object) schema pairs to map; either side may be "all".
    `all all` is every pair of registered schemas, once."""
    labels = [s["label"] for s in registry.get("sources", [])]
    for name in (subject, obj):
        if name != "all" and name not in labels:
            raise ValueError(f"unknown schema {name!r}; registered: {', '.join(labels)}")
    if subject == obj != "all":
        raise ValueError(f"subject and object are both {subject!r}")
    if subject == "all" and obj == "all":
        return [(a, b) for i, a in enumerate(labels) for b in labels[i + 1:]]
    if subject == "all":
        return [(a, obj) for a in labels if a != obj]
    if obj == "all":
        return [(subject, b) for b in labels if b != subject]
    return [(subject, obj)]


def load_model(model_name: str):
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(model_name)


def propose(subjects: list[Entity], objects: list[Entity], top_k: int,
            min_score: float, model) -> list[tuple[Entity, Entity, float]]:
    """(subject, object, cosine score) for each subject's top_k objects at or
    above min_score, best first. An entity shared by both schemas (same id)
    is already one entity, so it isn't proposed as a mapping to itself."""
    if not subjects or not objects:
        return []
    encode = lambda es: model.encode([e.text for e in es], normalize_embeddings=True,
                                     show_progress_bar=False, batch_size=64)
    scores = encode(subjects) @ encode(objects).T
    out = []
    for i, s in enumerate(subjects):
        ranked = [j for j in scores[i].argsort()[::-1] if objects[j].id != s.id]
        for j in ranked[:top_k]:
            if scores[i, j] >= min_score:
                out.append((s, objects[j], float(scores[i, j])))
    return sorted(out, key=lambda t: -t[2])


def write_mapping_file(path: Path, rows: list[tuple[Entity, Entity, float]], *,
                       mapping_set_id: str, model_name: str, author: str) -> None:
    header = {
        "mapping_set_id": mapping_set_id,
        "mapping_date": datetime.date.today().isoformat(),
        "mapping_tool": f"embeddings/{model_name}",
        "mapping_justification": "semapv:SemanticSimilarityThresholdMatching",
        "author_id": author,
    }
    lines = [f"# {k}: {v}" for k, v in header.items()]
    lines.append("\t".join(["subject_id", "predicate_id", "object_id", "confidence",
                            "review_status", "reviewer_id", "comment"]))
    for s, o, score in rows:
        lines.append("\t".join([s.ref, "skos:closeMatch", o.ref, f"{score:.3f}",
                                "PROPOSED", "", ""]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@click.command()
@click.argument("subject_source")
@click.argument("object_source")
@click.option("--kind", type=click.Choice(["properties", "classes", "all"]), default="properties", show_default=True)
@click.option("--top-k", default=1, show_default=True, help="Matches kept per subject entity.")
@click.option("--min-score", default=0.6, show_default=True,
              help="Cosine cut-off (model-specific: bge models score higher overall).")
@click.option("--model", "model_name", default=DEFAULT_MODEL, show_default=True)
@click.option("--registry", default="data/registry.json", show_default=True,
              type=click.Path(exists=True, path_type=Path))
@click.option("--author", default="github-actions", show_default=True,
              help="author_id recorded for the proposals.")
@click.option("--out", type=click.Path(path_type=Path), default=None,
              help="Output file. Default: mappings/<date>_embeddings_<subject>__<object>_<kind>.sssom.tsv")
def cli(subject_source, object_source, kind, top_k, min_score, model_name, registry, author, out) -> None:
    """Propose mappings from SUBJECT_SOURCE to OBJECT_SOURCE (source labels,
    e.g. aind bids; either may be `all`)."""
    reg = json.loads(registry.read_text())
    try:
        pairs = schema_pairs(reg, subject_source, object_source)
    except ValueError as e:
        raise click.UsageError(str(e))
    kinds = ["classes", "properties"] if kind == "all" else [kind]
    model = load_model(model_name)
    rows: list = []
    for subj, obj in pairs:
        for k in kinds:
            found = propose(entities(reg, subj, k), entities(reg, obj, k), top_k, min_score, model)
            click.echo(f"  {subj} → {obj} ({k}): {len(found)}")
            rows += found
    set_id = f"{datetime.date.today().isoformat()}_embeddings_{subject_source}__{object_source}_{kind}"
    out = out or Path("mappings") / f"{set_id}.sssom.tsv"
    write_mapping_file(out, rows, mapping_set_id=set_id, model_name=model_name, author=author)
    click.echo(f"{len(rows)} proposed mapping(s) from {len(pairs)} schema pair(s) -> {out}")


if __name__ == "__main__":
    cli()
