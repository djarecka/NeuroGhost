import uuid
from pathlib import Path

import pytest

from ingest_linkml import parse_linkml, build_registry_entities
from schema_registry_utils import (
    RegistryProperty, RegistryClass, RegistryValueSet, PermissibleValue, RegistryRule,
    compute_content_hash_for,
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
                "is_mixin": True,
                "mixins": [],
                "slots": ["created_at"],
                "aliases": [],
            },
            "Entity": {
                "iri": "https://example.org/schema#Entity",
                "definition": "Abstract base for all registry entities.",
                "is_a": None,
                "is_abstract": True,
                "is_mixin": False,
                "mixins": [],
                "slots": ["name"],
                "aliases": [],
            },
            "Person": {
                "iri": "https://schema.org/Person",
                "definition": "A research investigator.",
                "is_a": "Entity",
                "is_abstract": False,
                "is_mixin": False,
                "mixins": ["Timestamped"],
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
                "minimum_value": None,
                "maximum_value": None,
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
                "minimum_value": None,
                "maximum_value": None,
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
                "minimum_value": None,
                "maximum_value": None,
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
                "minimum_value": None,
                "maximum_value": None,
                "aliases": [],
            },
        },
        "enums": {},
    }


def test_registry_property_does_not_retain_usage_constraints():
    """
    parse_linkml()'s dict has multivalued/required/pattern (see above) — but
    RegistryProperty deliberately doesn't model them at all: they belong on
    RegistryRule instead (see test_build_registry_entities_maps_person_
    classes_properties_and_rules), since the same property can be required
    in one source's usage and optional in another's without being a
    different concept. Assert this at the model level, not just "the dict
    I built doesn't have it" — if someone re-adds these fields to
    RegistryProperty, this fails.
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
    properties, registry_classes, value_sets, permissible_values, rules, provenance_entries = build_registry_entities(
        parsed, "comprehensive", "tester"
    )
    assert value_sets == {}  # comprehensive.yml has no enums
    assert permissible_values == {}

    assert set(properties) == {"name", "orcid", "role", "created_at"}
    assert set(registry_classes) == {"Timestamped", "Entity", "Person"}

    for entity in (*properties.values(), *registry_classes.values()):
        assert len(entity.provenance) == 1
        prov = provenance_entries[entity.provenance[0]]
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
    #     parent_class/class_mixins — the reference fields hold
    #     non-deterministic UUIDs verified separately below) are exactly
    #     the expected shape.
    class_dump = {
        name: c.model_dump(exclude={"provenance", "id", "sha256_hash",
                                    "properties", "parent_class", "class_mixins"})
        for name, c in registry_classes.items()
    }
    assert class_dump == {
        "Timestamped": {
            "name": "Timestamped",
            "description": "Mixin providing a creation timestamp.",
            "skos_mappings": [],
            "concept_uri": None,
            "is_abstract": False,
            "is_mixin": True,
            "aliases": [],
        },
        "Entity": {
            "name": "Entity",
            "description": "Abstract base for all registry entities.",
            "skos_mappings": [],
            "concept_uri": "https://example.org/schema#Entity",
            "is_abstract": True,
            "is_mixin": False,
            "aliases": [],
        },
        "Person": {
            "name": "Person",
            "description": "A research investigator.",
            "skos_mappings": [],
            "concept_uri": "https://schema.org/Person",
            "is_abstract": False,
            "is_mixin": False,
            "aliases": ["Investigator"],
        },
    }

    # 3. Cross-reference wiring: Person is_a Entity, Person mixins
    #    Timestamped, and each class's properties list matches the target
    #    property ids.
    assert registry_classes["Person"].parent_class == registry_classes["Entity"].id
    assert registry_classes["Timestamped"].parent_class is None
    assert registry_classes["Entity"].parent_class is None

    assert registry_classes["Person"].class_mixins == sorted([registry_classes["Timestamped"].id])
    assert registry_classes["Timestamped"].class_mixins == []
    assert registry_classes["Entity"].class_mixins == []

    assert registry_classes["Timestamped"].properties == sorted([properties["created_at"].id])
    assert registry_classes["Entity"].properties == sorted([properties["name"].id])
    assert registry_classes["Person"].properties == sorted([
        properties["name"].id, properties["orcid"].id,
        properties["role"].id, properties["created_at"].id,
    ])


# See the comment on EXPECTED_PROP_SHAS above re: why property sha256_hashes
# are asserted exactly but class ones aren't.
EXPECTED_BICAN_PROP_SHAS = {
    "used":             "sha256:1a7929fb43d1f9ab937f2f353ce3087a5152bd04bcd1489d7a06eebc29b8ba03",
    "was_derived_from": "sha256:161c74e7f1e64c198bc04a08549a4e1b2465ce7b97c91def323d05048ff9303e",
    "was_generated_by": "sha256:162b6a1e584c5b70d29396f9d4c94c8414b1e2893a7a736ac865ec2dad4cc017",
}


def test_build_registry_entities_maps_bican_prov_onto_the_meta_model():
    """
    Same check as test_build_registry_entities_produces_exactly_the_expected_objects,
    on bican_prov.yaml — this is the "mapping onto the meta-model" step:
    parse_linkml()'s raw LinkML dict (tested separately by
    test_parse_linkml_extracts_bican_prov_exactly) becomes real
    RegistryClass/RegistryProperty instances here.

    The interesting case this fixture exercises that comprehensive.yml
    doesn't: `used`'s range is `ProvEntity`, a class in the same schema.
    property_range must come out as ProvEntity's real id — proof that the
    "second pass" rewrite in build_registry_entities() (synthetic
    make_iri() placeholder -> real class id) already ran by the time this
    function returns, not just later at DB-write time.
    """
    parsed = parse_linkml(FIXTURES / "bican_prov.yaml")
    properties, registry_classes, value_sets, permissible_values, rules, provenance_entries = build_registry_entities(
        parsed, "bican_prov", "tester"
    )
    assert value_sets == {}
    assert permissible_values == {}

    assert set(properties) == {"used", "was_derived_from", "was_generated_by"}
    assert set(registry_classes) == {"ProvActivity", "ProvEntity"}

    for entity in (*properties.values(), *registry_classes.values()):
        assert len(entity.provenance) == 1
        prov = provenance_entries[entity.provenance[0]]
        assert prov.had_primary_source == "bican_prov"
        assert prov.was_attributed_to == "tester"
        assert prov.was_generated_by == "ingestion"
        assert prov.was_derived_from == []

    # Property sha256_hashes are exactly what's expected.
    for name, prop in properties.items():
        assert prop.sha256_hash == EXPECTED_BICAN_PROP_SHAS[name], name
        assert _is_uuid(prop.id), f"{name}.id not a UUID: {prop.id}"

    # Both source classes declare `mixin: true` — is_mixin must carry
    # through, not silently default to False.
    for name, rc in registry_classes.items():
        assert rc.is_mixin is True, name
        assert rc.is_abstract is False, name

    # property_range must be the real class id, not the synthetic
    # make_iri("ProvEntity")-style placeholder parse_linkml() starts with.
    assert properties["used"].property_range == registry_classes["ProvEntity"].id
    assert properties["was_derived_from"].property_range == registry_classes["ProvEntity"].id
    assert properties["was_generated_by"].property_range == registry_classes["ProvActivity"].id

    # Cross-reference wiring: each class's properties list matches the
    # target property's own id.
    assert registry_classes["ProvActivity"].properties == [properties["used"].id]
    assert registry_classes["ProvEntity"].properties == sorted([
        properties["was_derived_from"].id, properties["was_generated_by"].id,
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
    props1, classes1, _, _, _, _ = build_registry_entities(parsed, "comprehensive", "tester")

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
    props2, classes2, _, _, _, _ = build_registry_entities(
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
    properties, registry_classes, value_sets, permissible_values, rules, provenance_entries = build_registry_entities(
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
    assert provenance_entries[vs.provenance[0]].had_primary_source == "enum_test"

    assert set(vs.permissible_values) == set(permissible_values)
    for pv in permissible_values.values():
        assert isinstance(pv, PermissibleValue)
        assert pv.name in ("active", "deprecated")
        assert _is_uuid(pv.id)
        assert pv.sha256_hash.startswith("sha256:")
        assert len(pv.provenance) == 1
        assert provenance_entries[pv.provenance[0]].had_primary_source == "enum_test"


EXPECTED_PERSON_PROP_SHAS = {
    "name":      "sha256:0510770b2a85321802bb3d7d6616893c81d94dc69e4b78149565a93a762ab893",
    "last_name": "sha256:09f88d7393e0659562062b8750fdc683d5f4cdbd92e9de669e8d624062585bd4",
    "age":       "sha256:fedfc9376e594cee36240dac2ac47b723356c77888e14f64562de01e4ae0df7f",
}


def test_build_registry_entities_maps_person_classes_properties_and_rules():
    """
    person.yml: one class (Person), three plain-scalar properties
    (name/last_name: string, age: integer), and four declared constraints —
    a pattern on `name`, `required: true` on `last_name`, minimum_value/
    maximum_value on `age` — the first real exercise of RegistryRule
    construction in build_registry_entities(). All at the
    build_registry_entities() stage: no DB involved, this is
    "did parse_linkml()'s dict get mapped onto the meta-model correctly,"
    not "did LinkML read the file correctly" (that's parse_linkml()'s own
    tests) and not "did it get written correctly" (that's
    test_ingest_registry.py, against a real graph).
    """
    parsed = parse_linkml(FIXTURES / "person.yml")
    properties, registry_classes, value_sets, permissible_values, rules, provenance_entries = (
        build_registry_entities(parsed, "person", "tester")
    )
    assert value_sets == {}
    assert permissible_values == {}

    # Classes
    assert set(registry_classes) == {"Person"}
    person = registry_classes["Person"]
    assert person.description == "An individual human being."
    assert person.is_abstract is False
    assert person.is_mixin is False

    # Properties
    assert set(properties) == {"name", "last_name", "age"}
    for name, prop in properties.items():
        assert prop.sha256_hash == EXPECTED_PERSON_PROP_SHAS[name], name
        assert _is_uuid(prop.id), f"{name}.id not a UUID: {prop.id}"
    assert properties["name"].property_range == "xsd:string"
    assert properties["last_name"].property_range == "xsd:string"
    assert properties["age"].property_range == "xsd:integer"
    assert person.properties == sorted([
        properties["name"].id, properties["last_name"].id, properties["age"].id,
    ])

    # Rules — the actual point of this test. `name` (pattern), `last_name`
    # (required), and `age` (min + max value) each produce RegistryRule(s).
    #
    # sha256_hash isn't asserted with an exact value (same reasoning as
    # class sha256_hashes above): `applies_to` is in HashSubset and holds
    # a property's id, a freshly-minted UUID with no conn to dedup
    # against here, so it isn't deterministic across runs. Checked
    # structurally instead.
    assert set(rules) == {
        "name:PATTERN", "last_name:REQUIRED", "age:MIN_VALUE", "age:MAX_VALUE",
    }
    for key, rule in rules.items():
        assert isinstance(rule, RegistryRule)
        assert rule.sha256_hash.startswith("sha256:"), key
        assert _is_uuid(rule.id), f"{key}.id not a UUID: {rule.id}"
        assert rule.severity == "ERROR"
        assert rule.used_in_class is None
        assert rule.referenced_entities == []

    name_rule = rules["name:PATTERN"]
    assert name_rule.rule_type == "PATTERN"
    assert name_rule.rule_value == "^[A-Za-z ]+$"
    assert name_rule.applies_to == [properties["name"].id]

    last_name_rule = rules["last_name:REQUIRED"]
    assert last_name_rule.rule_type == "REQUIRED"
    assert last_name_rule.rule_value == "true"
    assert last_name_rule.applies_to == [properties["last_name"].id]

    age_min_rule = rules["age:MIN_VALUE"]
    assert age_min_rule.rule_type == "MIN_VALUE"
    assert age_min_rule.rule_value == "0"
    assert age_min_rule.applies_to == [properties["age"].id]

    age_max_rule = rules["age:MAX_VALUE"]
    assert age_max_rule.rule_type == "MAX_VALUE"
    assert age_max_rule.rule_value == "120"
    assert age_max_rule.applies_to == [properties["age"].id]

    # Provenance: every property, class, and rule gets one ProvenanceEntry
    # from this ingestion.
    for entity in (*properties.values(), person, *rules.values()):
        assert len(entity.provenance) == 1
        prov = provenance_entries[entity.provenance[0]]
        assert prov.had_primary_source == "person"
        assert prov.was_attributed_to == "tester"
