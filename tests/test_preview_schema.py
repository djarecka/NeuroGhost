from conftest import FIXTURES
from ingest_linkml import build_registry_entities, parse_linkml
from preview_schema import preview


def test_preview_sorts_entities_into_existing_renamed_and_new(tmp_path):
    """Equal content hash = already in the registry (reused at ingest); same
    name with a different hash = worth a look; the rest is new. Missing
    descriptions are listed."""
    props, classes, *_ = build_registry_entities(parse_linkml(FIXTURES / "source_a.yml"), "a", "t")
    registry = {"classes": [{
        "name": c.name, "sha256_hash": c.sha256_hash, "sources": ["source_a"],
        "properties": [{"name": p.name, "sha256_hash": p.sha256_hash, "sources": ["source_a"]}
                       for p in props.values()],
    } for c in classes.values()]}

    new_schema = tmp_path / "mine.yml"
    new_schema.write_text(
        "id: https://example.org/mine\nname: mine\n"
        "prefixes: {linkml: https://w3id.org/linkml/}\nimports: [linkml:types]\ndefault_range: string\n"
        "classes:\n"
        "  Subject:\n"                                   # same name, different content
        "    description: Someone we measured\n"
        "    attributes:\n"
        "      age: {description: Age of the subject, range: integer}\n"   # identical to source_a
        "  Session:\n"
        "    attributes:\n"
        "      start: {}\n"                              # new, no description
    )
    report = preview(new_schema, registry, "mine")
    assert report["property"]["existing"] == [("age", ["source_a"])]
    assert report["property"]["new"] == ["start"]
    assert report["property"]["missing_description"] == ["start"]
    assert report["class"]["same_name_different_content"] == [("Subject", ["source_a"])]
    assert report["class"]["new"] == ["Session"]
    assert report["class"]["missing_description"] == ["Session"]
