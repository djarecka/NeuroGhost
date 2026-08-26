import uuid
from pathlib import Path

import pytest

from ingest_linkml import parse_linkml, build_registry_entities
from schema_registry_utils import (
    RegistryProperty, RegistryClass, RegistryValueSet, PermissibleValue, compute_content_hash_for,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _is_uuid(s):
    """Every entity id is a uuid4 string. Assert it parses."""
    try:
        uuid.UUID(s)
        return True
    except (ValueError, TypeError):
        return False


def test_class_with_slots():
    parsed = parse_linkml(FIXTURES / "valid_slots.yml")

    assert set(parsed["classes"]) == {"Person"}
    person = parsed["classes"]["Person"]
    assert person["iri"] == "https://example.org/schema#Person"
    assert set(person["slots"]) == {"name", "orcid"}

    assert set(parsed["slots"]) == {"name", "orcid"}
    assert parsed["slots"]["name"]["value_range"] == "xsd:string"
    assert parsed["slots"]["orcid"]["pattern"]


def test_class_with_attributes():
    parsed = parse_linkml(FIXTURES / "valid_attributes.yml")

    assert set(parsed["classes"]) == {"Device"}
    device = parsed["classes"]["Device"]
    assert set(device["slots"]) == {"manufacturer", "sampling_rate"}

    # attributes declared inline on a class must show up in the global
    # slots dict too — this is exactly what the old hand-rolled parser missed
    assert set(parsed["slots"]) == {"manufacturer", "sampling_rate"}
    assert parsed["slots"]["sampling_rate"]["required"] is True
    assert parsed["slots"]["sampling_rate"]["units"] == "Hz"


def test_undefined_slot_raises():
    with pytest.raises(ValueError, match="nonexistent_slot"):
        parse_linkml(FIXTURES / "invalid_undefined_slot.yml")


def test_parse_linkml_extracts_exactly_the_expected_dict():
    """
    Exact-equality check (not spot-checks) of parse_linkml()'s raw LinkML
    extraction — this is the intermediate dict, before build_registry_entities()
    converts it into RegistryProperty/RegistryClass. It legitimately includes
    multivalued/required/pattern, since those are genuinely part of a LinkML
    slot declaration — whether the *registry* keeps them is a separate
    question, covered by test_build_registry_entities_* below.

    Exercises every element parse_linkml must handle at once: a mixin, an
    abstract base, is_a inheritance, a top-level `slots:` reference, an
    inline `attributes:` declaration, class_uri/slot_uri resolved both from
    the schema's own `prefixes:` (ex:) and from the KNOWN_PREFIXES fallback
    (schema:), a slot with no class_uri/slot_uri at all, multivalued/
    required/pattern, and a units-in-description extraction. If parse_linkml
    starts silently dropping or adding fields, this fails — a spot-check on
    a couple of keys wouldn't.
    """
    parsed = parse_linkml(FIXTURES / "comprehensive.yml")

    assert parsed == {
        "meta": {
            "id": "https://example.org/comprehensive",
            "name": "comprehensive",
            "version": "1.0.0",
            "description": "A schema exercising every element parse_linkml must extract.",
        },
        "prefixes": {
            "linkml": "https://w3id.org/linkml/",
            "ex": "https://example.org/schema#",
        },
        "classes": {
            "Timestamped": {
                "iri": "",
                "definition": "Mixin providing a creation timestamp.",
                "is_a": None,
                "is_abstract": False,
                "slots": ["created_at"],
                "aliases": [],
            },
            "Entity": {
                "iri": "https://example.org/schema#Entity",
                "definition": "Abstract base for all registry entities.",
                "is_a": None,
                "is_abstract": True,
                "slots": ["name"],
                "aliases": [],
            },
            "Person": {
                "iri": "https://schema.org/Person",
                "definition": "A research investigator.",
                "is_a": "Entity",
                "is_abstract": False,
                "slots": ["orcid", "role", "created_at", "name"],
                "aliases": ["Investigator"],
            },
        },
        "slots": {
            "created_at": {
                "iri": "",
                "definition": "",
                "value_range": "xsd:dateTime",
                "units": "",
                "multivalued": False,
                "required": False,
                "pattern": "",
                "aliases": [],
            },
            "name": {
                "iri": "https://schema.org/name",
                "definition": "Full name.",
                "value_range": "xsd:string",
                "units": "",
                "multivalued": False,
                "required": False,
                "pattern": "",
                "aliases": [],
            },
            "orcid": {
                "iri": "https://example.org/schema#orcid",
                "definition": "ORCID identifier.",
                "value_range": "xsd:string",
                "units": "",
                "multivalued": False,
                "required": False,
                "pattern": r"^\d{4}-\d{4}-\d{4}-\d{3}[0-9X]$",
                "aliases": ["ORCID iD"],
            },
            "role": {
                "iri": "",
                "definition": "Role on the study (units: FTE)",
                "value_range": "xsd:string",
                "units": "FTE",
                "multivalued": True,
                "required": True,
                "pattern": "^[A-Za-z ]+$",
                "aliases": [],
            },
        },
        "enums": {},
    }


def test_registry_property_does_not_retain_usage_constraints():
    """
    parse_linkml()'s dict has multivalued/required/pattern (see above) — but
    RegistryProperty deliberately doesn't model them at all (deferred to a
    future RegistryRule, since the same property can be required in one source's
    usage and optional in another's without being a different concept).
    Assert this at the model level, not just "the dict I built doesn't have
    it" — if someone re-adds these fields to RegistryProperty, this fails.
    """
    for field in ("required", "multivalued", "pattern"):
        assert field not in RegistryProperty.model_fields


def test_aliases_do_not_affect_identity():
    """
    aliases isn't tagged in_subset: HashSubset in meta_model.yaml, so
    it's excluded from sha256_hash — like class_uri/slot_uri, it's alternate-name
    metadata a source happens to supply, not part of what the entity *is*.
    Two otherwise-identical properties with different aliases must still
    collapse to the same sha256_hash (and therefore share an id via dedup).
    """
    base = dict(
        name="orcid", description="ORCID identifier.", property_range="xsd:string",
        unit=None, concept_uri="https://example.org/schema#orcid",
        skos_mappings=[],
    )
    with_alias = compute_content_hash_for(RegistryProperty, dict(base, aliases=["ORCID iD"]))
    without_alias = compute_content_hash_for(RegistryProperty, dict(base, aliases=[]))
    assert with_alias == without_alias


def test_property_range_does_not_affect_identity():
    """
    property_range isn't in HashSubset — it's a graph reference (a class id,
    an enum id, or an XSD CURIE), resolved by build_registry_entities()'s
    post-hash pass, and per-usage range refinements live on RegistryRule
    (rule_type=RANGE). Making it identity-defining would force a mutual
    dependency between class hashes and property hashes that self-referential
    slots can't satisfy.

    Two properties differing only by property_range must therefore
    collapse to the same sha256_hash.
    """
    base = dict(
        name="target", description="An arbitrary reference.",
        unit=None, concept_uri=None, skos_mappings=[], aliases=[],
    )
    as_string = compute_content_hash_for(RegistryProperty, dict(base, property_range="xsd:string"))
    as_class_ref = compute_content_hash_for(
        RegistryProperty, dict(base, property_range="606a7c1d-0f96-4599-8070-aad647f433f8"),
    )
    assert as_string == as_class_ref


# Deterministic sha256 fingerprints for the entities that come out of
# comprehensive.yml. Kept explicit so a silent shift in what feeds the hash
# (e.g. a HashSubset slot added/removed, or _digest's canonicalization
# changing) fails loudly here. UUIDs are non-deterministic (uuid4) so the
# `id` field is asserted structurally, and cross-refs are checked by matching
# them against the target entity's own id — see the test body.
EXPECTED_PROP_SHAS = {
    "name":       "sha256:049ca9da4b9dc3a3c7510ddb041f1e67af456b2f545c7c5cb3eec102c1ce4e7f",
    "orcid":      "sha256:9b314737103a14dd66fca3b5d52dd6ae956d86307976a3e5e1d68f728c81ee1b",
    "role":       "sha256:f8c9caa50578d700e2985a2c1c39701619722cc6477bca780b574780b031279c",
    "created_at": "sha256:f5035dbf9b5ee2cdecb9ed9427df4deee27fcd8aad716d3e7fd6ec7e14a32f26",
}
# Class sha256_hashes are deliberately NOT asserted with exact values: a
# class's content includes its properties' UUID ids (see meta_model's
# HashSubset on RegistryClass.properties), so the class hash is only
# deterministic if the property UUIDs are — which in production happens
# via dedup lookup on subsequent ingests, and in tests via the FakeConn
# helper below. See test_class_hash_dedup_makes_a_re_ingest_deterministic
# for the invariant that actually matters (second ingest with dedup
# produces the same ids as the first).


def test_build_registry_entities_produces_exactly_the_expected_objects():
    """
    Two-part check on build_registry_entities()'s output — the step that
    turns parse_linkml()'s dict into RegistryProperty/RegistryClass
    instances.

    1. sha256_hash is a pure content fingerprint, deterministic across runs,
       so it's asserted with exact expected values. If the hash computation,
       the set of fields carried into the model, or the is_a/properties
       resolution ever changes, this fails.
    2. id is a uuid4 (non-deterministic per run) — asserted structurally
       (parses as a UUID) and by cross-reference consistency: each class's
       parent_class and properties list must match the target entity's own
       id, so property/class UUIDs and their references stay wired up
       correctly regardless of what specific UUIDs get minted this run.

    provenance is checked separately (excluded from the equality dump) since
    ProvenanceEntry.id/generated_at_time are non-deterministic per run.
    """
    parsed = parse_linkml(FIXTURES / "comprehensive.yml")
    properties, registry_classes, value_sets, permissible_values = build_registry_entities(
        parsed, "comprehensive", "tester"
    )
    assert value_sets == {}  # comprehensive.yml has no enums
    assert permissible_values == {}

    assert set(properties) == {"name", "orcid", "role", "created_at"}
    assert set(registry_classes) == {"Timestamped", "Entity", "Person"}

    for entity in (*properties.values(), *registry_classes.values()):
        assert len(entity.provenance) == 1
        prov = entity.provenance[0]
        assert prov.had_primary_source == "comprehensive"
        assert prov.was_attributed_to == "tester"
        assert prov.was_generated_by == "ingestion"
        assert prov.was_derived_from == []

    # 1a. Property sha256_hashes are exactly what's expected.
    for name, prop in properties.items():
        assert prop.sha256_hash == EXPECTED_PROP_SHAS[name], name
        assert _is_uuid(prop.id), f"{name}.id not a UUID: {prop.id}"

    # 1b. Property content dumps (excluding id/sha256_hash/provenance which
    #     are checked separately) are exactly the expected shape.
    non_identity_dump = {
        name: p.model_dump(exclude={"provenance", "id", "sha256_hash"})
        for name, p in properties.items()
    }
    assert non_identity_dump == {
        "name": {
            "name": "name",
            "description": "Full name.",
            "skos_mappings": [],
            "concept_uri": "https://schema.org/name",
            "property_range": "xsd:string",
            "unit": None,
            "aliases": [],
        },
        "orcid": {
            "name": "orcid",
            "description": "ORCID identifier.",
            "skos_mappings": [],
            "concept_uri": "https://example.org/schema#orcid",
            "property_range": "xsd:string",
            "unit": None,
            "aliases": ["ORCID iD"],
        },
        "role": {
            "name": "role",
            "description": "Role on the study (units: FTE)",
            "skos_mappings": [],
            "concept_uri": None,
            "property_range": "xsd:string",
            "unit": {
                "ucum_code": "FTE",
                "has_quantity_kind": None,
                "symbol": None,
                "abbreviation": None,
                "descriptive_name": None,
            },
            "aliases": [],
        },
        "created_at": {
            "name": "created_at",
            "description": "",
            "skos_mappings": [],
            "concept_uri": None,
            "property_range": "xsd:dateTime",
            "unit": None,
            "aliases": [],
        },
    }

    # 2a. Every class carries a sha256_hash of the right shape and a valid
    #     UUID id. Exact class sha256 values aren't asserted — see the
    #     comment on EXPECTED_CLASS_SHAS above.
    for name, rc in registry_classes.items():
        assert rc.sha256_hash.startswith("sha256:"), name
        assert _is_uuid(rc.id), f"{name}.id not a UUID: {rc.id}"

    # 2b. Class content dumps (excluding id/sha256_hash/provenance/properties/
    #     parent_class — the reference fields hold non-deterministic UUIDs
    #     verified separately below) are exactly the expected shape.
    class_dump = {
        name: c.model_dump(exclude={"provenance", "id", "sha256_hash",
                                    "properties", "parent_class"})
        for name, c in registry_classes.items()
    }
    assert class_dump == {
        "Timestamped": {
            "name": "Timestamped",
            "description": "Mixin providing a creation timestamp.",
            "skos_mappings": [],
            "concept_uri": None,
            "is_abstract": False,
            "is_mixin": False,
            "class_mixins": [],
            "aliases": [],
        },
        "Entity": {
            "name": "Entity",
            "description": "Abstract base for all registry entities.",
            "skos_mappings": [],
            "concept_uri": "https://example.org/schema#Entity",
            "is_abstract": True,
            "is_mixin": False,
            "class_mixins": [],
            "aliases": [],
        },
        "Person": {
            "name": "Person",
            "description": "A research investigator.",
            "skos_mappings": [],
            "concept_uri": "https://schema.org/Person",
            "is_abstract": False,
            "is_mixin": False,
            "class_mixins": [],
            "aliases": ["Investigator"],
        },
    }

    # 3. Cross-reference wiring: Person is_a Entity, and each class's
    #    properties list matches the target property ids.
    assert registry_classes["Person"].parent_class == registry_classes["Entity"].id
    assert registry_classes["Timestamped"].parent_class is None
    assert registry_classes["Entity"].parent_class is None

    assert registry_classes["Timestamped"].properties == sorted([properties["created_at"].id])
    assert registry_classes["Entity"].properties == sorted([properties["name"].id])
    assert registry_classes["Person"].properties == sorted([
        properties["name"].id, properties["orcid"].id,
        properties["role"].id, properties["created_at"].id,
    ])


class _FakeConn:
    """Minimal stand-in for the LadybugDB connection that just remembers
    which sha256_hash → id pairs it has seen. Used to demonstrate that
    build_registry_entities() reuses ids via find_id_by_sha256 the same way
    the real ingestion path does — without spinning up a real DB."""
    def __init__(self):
        self._by_sha: dict[tuple[str, str], str] = {}

    def see(self, label: str, sha: str, node_id: str) -> None:
        self._by_sha[(label, sha)] = node_id

    # find_id_by_sha256 uses Cypher against a real conn; the ingestion code
    # goes through db.find_id_by_sha256(conn, label, sha) — so patch that
    # function in the fake-conn test rather than duck-typing execute().


def test_class_hash_dedup_makes_a_re_ingest_deterministic(monkeypatch):
    """
    On a first ingest with an empty graph, every entity gets a fresh uuid4
    id — RegistryProperty ids are random, so any RegistryClass sha256 that
    includes those property ids is also non-deterministic across separate
    empty-graph runs.

    In production this is not a problem: the second ingest of the same
    schema (or any other schema that shares content) finds each entity by
    sha256_hash and reuses the existing id, so class content stabilizes and
    dedup collapses the class too. This test simulates that with a fake
    conn: after the first ingest, feed the entities' sha256 → id map back
    in as `find_id_by_sha256` results, run the second ingest, and assert
    every id round-trips.
    """
    import ingest_linkml as ingest_mod
    from ingest_linkml import build_registry_entities, parse_linkml

    parsed = parse_linkml(FIXTURES / "comprehensive.yml")
    props1, classes1, _, _ = build_registry_entities(parsed, "comprehensive", "tester")

    # After first ingest: build the (label, sha256) -> id map that a
    # populated registry would return from find_id_by_sha256.
    seen: dict[tuple[str, str], str] = {}
    for p in props1.values():
        seen[("RegistryProperty", p.sha256_hash)] = p.id
    for c in classes1.values():
        seen[("RegistryClass", c.sha256_hash)] = c.id

    def fake_lookup(conn, label, sha):
        return seen.get((label, sha))

    monkeypatch.setattr(ingest_mod, "find_id_by_sha256", fake_lookup)

    # Second ingest, this time with `conn` set to any non-None sentinel — the
    # patched find_id_by_sha256 doesn't touch it. Every id must match.
    props2, classes2, _, _ = build_registry_entities(
        parsed, "comprehensive", "tester", conn=object(),
    )
    for name, p1 in props1.items():
        assert props2[name].id == p1.id, name
        assert props2[name].sha256_hash == p1.sha256_hash, name
    for name, c1 in classes1.items():
        assert classes2[name].id == c1.id, name
        assert classes2[name].sha256_hash == c1.sha256_hash, name


def test_parse_linkml_extracts_enums():
    """parse_linkml() returns an 'enums' dict with parsed enum definitions."""
    parsed = parse_linkml(FIXTURES / "schema_with_enums.yml")

    assert "enums" in parsed
    assert "StatusEnum" in parsed["enums"]

    status_enum = parsed["enums"]["StatusEnum"]
    assert status_enum["definition"] == "Possible statuses for an annotation."
    assert set(status_enum["permissible_values"]) == {"active", "deprecated"}
    assert status_enum["permissible_values"]["active"]["meaning"] == (
        "http://www.w3.org/2004/02/skos/core#Concept"
    )
    assert status_enum["permissible_values"]["deprecated"]["meaning"] == ""


def test_build_registry_entities_produces_value_sets():
    """
    build_registry_entities()'s 3rd/4th return values are RegistryValueSet and
    PermissibleValue dicts. PermissibleValue is a real RegistryEntity now
    (not the old hand-rolled node) — it gets a real description and
    provenance, keyed by id since it's shared across enums/sources
    rather than tied to one source name.
    """
    parsed = parse_linkml(FIXTURES / "schema_with_enums.yml")
    properties, registry_classes, value_sets, permissible_values = build_registry_entities(
        parsed, "enum_test", "tester"
    )

    assert "StatusEnum" in value_sets
    vs = value_sets["StatusEnum"]
    assert isinstance(vs, RegistryValueSet)
    assert vs.name == "StatusEnum"
    assert vs.description == "Possible statuses for an annotation."
    assert len(vs.permissible_values) == 2
    # PermissibleValue references are UUIDs (the target's id).
    for pv_id in vs.permissible_values:
        assert _is_uuid(pv_id)
    # sha256_hash on the value set itself starts with the sha256: prefix.
    assert vs.sha256_hash.startswith("sha256:")
    # Provenance from the ingestion
    assert len(vs.provenance) == 1
    assert vs.provenance[0].had_primary_source == "enum_test"

    assert set(vs.permissible_values) == set(permissible_values)
    for pv in permissible_values.values():
        assert isinstance(pv, PermissibleValue)
        assert pv.name in ("active", "deprecated")
        assert _is_uuid(pv.id)
        assert pv.sha256_hash.startswith("sha256:")
        assert len(pv.provenance) == 1
        assert pv.provenance[0].had_primary_source == "enum_test"
