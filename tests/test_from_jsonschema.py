"""
Tests for the JSON Schema -> LinkML converter (converters/from_jsonschema.py),
which wraps schema-automator's JsonSchemaImportEngine plus a post-process pass
that recovers the constraint facets the importer drops (pattern/min/max).

The valuable assertion isn't "the importer ran" — it's that a JSON Schema, run
through convert() and then the *real* ingestion path
(parse_linkml -> build_registry_entities), produces the RegistryClasses,
RegistryProperties, and RegistryRules we expect. So these tests go all the way
to build_registry_entities(), same altitude as test_ingest_linkml.py's
build_registry_entities tests.
"""

import json
from pathlib import Path

import yaml

from ingest_linkml import parse_linkml, build_registry_entities
from neuro_ghost.converters.from_jsonschema import convert

FIXTURES = Path(__file__).parent / "fixtures"


def _convert_and_build(data, name: str, tmp_path):
    """JSON Schema (dict or file path) -> convert() -> LinkML .yml ->
    build_registry_entities()."""
    if isinstance(data, Path):
        data = json.loads(data.read_text())
    linkml_dict = convert(data, name)
    yml = tmp_path / f"{name}.yml"
    yml.write_text(yaml.safe_dump(linkml_dict, sort_keys=False))
    parsed = parse_linkml(yml)
    return linkml_dict, build_registry_entities(parsed, name, "tester")


def test_person_json_schema_maps_to_classes_properties_and_rules(tmp_path):
    """
    person.schema.json exercises the pieces that matter for the registry:
    two objects (root + a $ref'd $def), a $ref-typed property, `required`,
    a `pattern`, numeric `minimum`/`maximum`, and a named enum definition
    (RoleType) referenced by an array property (dandi's controlled-vocab
    idiom). All should survive into RegistryClass / RegistryProperty /
    RegistryRule / RegistryValueSet.
    """
    linkml_dict, built = _convert_and_build(
        FIXTURES / "person.schema.json", "person", tmp_path
    )
    properties, registry_classes, value_sets, permissible_values, rules, provenance = built

    # The two OBJECT defs become classes; the enum def (RoleType) does NOT —
    # it becomes a value set, not an empty class.
    assert set(registry_classes) == {"Person", "Address"}
    assert registry_classes["Person"].description == "An individual human being."
    assert registry_classes["Address"].description == "A postal address."

    # A top-level enum definition -> RegistryValueSet with its permissible
    # values (schema-automator would otherwise drop it as an empty class).
    assert set(value_sets) == {"RoleType"}
    role_values = {
        permissible_values[pv_id].name
        for pv_id in value_sets["RoleType"].permissible_values
    }
    assert role_values == {"author", "editor", "reviewer"}
    # The referencing property points at that value set, not a class.
    assert properties["roles"].property_range == value_sets["RoleType"].id

    # $ref property -> class-typed range (resolved to Address's real id).
    assert properties["address"].property_range == registry_classes["Address"].id

    # age is a real integer with numeric bounds; name has a pattern.
    assert properties["age"].property_range == "xsd:integer"

    # The four constraint facets each became a RegistryRule, applied to the
    # right property. pattern + min/max are the ones schema-automator's
    # importer drops and from_jsonschema.py re-applies.
    by_type = {(r.rule_type, tuple(r.applies_to)): r for r in rules.values()}
    ids = {name: p.id for name, p in properties.items()}

    def rule(rule_type, prop):
        return by_type.get((rule_type, (ids[prop],)))

    assert rule("PATTERN", "name").rule_value == "^[A-Za-z ]+$"
    assert rule("REQUIRED", "last_name").rule_value == "true"
    assert rule("MIN_VALUE", "age").rule_value == "0"
    assert rule("MAX_VALUE", "age").rule_value == "120"

    # Exactly those four — no phantom rules from unconstrained properties.
    assert {r.rule_type for r in rules.values()} == {
        "PATTERN", "REQUIRED", "MIN_VALUE", "MAX_VALUE"
    }
    assert len(rules) == 4


def test_string_length_becomes_a_length_pattern(tmp_path):
    """LinkML has no string min/maxLength facet, so from_jsonschema.py encodes
    JSON Schema minLength/maxLength as a `^[\\s\\S]{lo,hi}$` length pattern —
    but only when the field has no real pattern of its own (a real pattern is
    the more specific constraint and wins)."""
    js = {
        "title": "T", "type": "object",
        "properties": {
            "code":     {"type": "string", "minLength": 1, "maxLength": 8},
            "with_pat": {"type": "string", "minLength": 1, "maxLength": 8,
                         "pattern": "^[A-Z]+$"},
        },
    }
    d = convert(js, "t")
    assert d["slots"]["code"]["pattern"] == r"^[\s\S]{1,8}$"
    # a real pattern is respected — length does NOT clobber it.
    assert d["slots"]["with_pat"]["pattern"] == "^[A-Z]+$"

    # end-to-end: the length pattern becomes a PATTERN RegistryRule.
    yml = tmp_path / "t.yml"
    yml.write_text(yaml.safe_dump(d, sort_keys=False))
    props, classes, vs, pvs, rules, prov = build_registry_entities(
        parse_linkml(yml), "t", "tester"
    )
    code_rules = [r for r in rules.values()
                  if r.applies_to == [props["code"].id] and r.rule_type == "PATTERN"]
    assert code_rules and code_rules[0].rule_value == r"^[\s\S]{1,8}$"


def test_anyof_union_becomes_range_any_of(tmp_path):
    """An `anyOf` of $refs (dandi's polymorphic idiom, written as an array of
    `anyOf`ed refs) becomes a LinkML union via any_of, and lands on
    RegistryProperty.range_any_of resolved to the real target class ids —
    with property_range left empty (a union has no single range)."""
    js = {
        "title": "Doc", "type": "object",
        "properties": {
            "contributor": {"type": "array", "items": {"anyOf": [
                {"$ref": "#/$defs/Person"}, {"$ref": "#/$defs/Organization"},
            ]}},
            "name": {"type": "string"},   # a plain single-range control
        },
        "$defs": {
            "Person":       {"type": "object", "properties": {"name": {"type": "string"}}},
            "Organization": {"type": "object", "properties": {"legalName": {"type": "string"}}},
        },
    }
    _, built = _convert_and_build(js, "doc", tmp_path)
    properties, registry_classes, value_sets, permissible_values, rules, prov = built

    contributor = properties["contributor"]
    # union: no single range, alternatives resolved to the real class ids.
    assert not contributor.property_range
    assert set(contributor.range_any_of) == {
        registry_classes["Person"].id, registry_classes["Organization"].id,
    }
    # a non-union property keeps a single range and an empty union list.
    assert properties["name"].property_range == "xsd:string"
    assert properties["name"].range_any_of == []


def test_convert_output_is_valid_linkml_shape(tmp_path):
    """convert() returns a dict with the LinkML top-level keys the rest of the
    pipeline (and yaml.dump in schema_submission.yml) expects."""
    data = json.loads((FIXTURES / "person.schema.json").read_text())
    d = convert(data, "person")

    assert d["name"] == "person"
    assert d["id"] == "https://registry.sensein.io/schema/person"
    assert "linkml:types" in d["imports"]
    assert set(d["classes"]) == {"Person", "Address"}


def test_format_maps_to_linkml_type_or_warns(tmp_path, capsys):
    """JSON Schema string `format` maps to a LinkML semantic type where one
    exists (uri/date-time/date/time -> xsd:anyURI/dateTime/date/time). Formats
    with no LinkML type (email, uuid, ...) stay plain string and a warning is
    emitted."""
    js = {
        "title": "T", "type": "object",
        "properties": {
            "homepage": {"type": "string", "format": "uri"},
            "created":  {"type": "string", "format": "date-time"},
            "born":     {"type": "string", "format": "date"},
            "contact":  {"type": "string", "format": "email"},   # no LinkML type
        },
    }
    _, built = _convert_and_build(js, "fmt", tmp_path)
    properties = built[0]

    assert properties["homepage"].property_range == "xsd:anyURI"
    assert properties["created"].property_range == "xsd:dateTime"
    assert properties["born"].property_range == "xsd:date"
    # unmappable format falls back to string, with a warning naming it.
    assert properties["contact"].property_range == "xsd:string"
    assert "email" in capsys.readouterr().err
