from pathlib import Path

import pytest

from ingest_linkml import parse_linkml, build_registry_entities
from schema_registry_utils import (
    RegistryProperty, RegistryClass, ValueSet, PermissibleValue, compute_hash_id_for,
)

FIXTURES = Path(__file__).parent / "fixtures"


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
    future Rule, since the same property can be required in one source's
    usage and optional in another's without being a different concept).
    Assert this at the model level, not just "the dict I built doesn't have
    it" — if someone re-adds these fields to RegistryProperty, this fails.
    """
    for field in ("required", "multivalued", "pattern"):
        assert field not in RegistryProperty.model_fields


def test_aliases_do_not_affect_identity():
    """
    aliases isn't tagged in_subset: HashSubset in meta_model.yaml, so
    it's excluded from hash_id — like class_uri/slot_uri, it's alternate-name
    metadata a source happens to supply, not part of what the entity *is*.
    Two otherwise-identical properties with different aliases must still
    collapse to the same hash_id (within one source: defined_in_schema is in
    the hash, so identity is source-anchored — see
    test_identical_property_from_two_sources_produces_distinct_hash_ids).
    """
    base = dict(
        name="orcid", description="ORCID identifier.", property_range="xsd:string",
        unit=None, concept_uri="https://example.org/schema#orcid",
        defined_in_schema="source_a", skos_mappings=[],
    )
    with_alias = compute_hash_id_for(RegistryProperty, dict(base, aliases=["ORCID iD"]))
    without_alias = compute_hash_id_for(RegistryProperty, dict(base, aliases=[]))
    assert with_alias == without_alias


def test_build_registry_entities_produces_exactly_the_expected_objects():
    """
    Exact-equality check of build_registry_entities()'s output — the step
    that turns parse_linkml()'s dict into content-hashed RegistryProperty/
    RegistryClass instances. hash_id is a pure content hash (no randomness),
    so these values are reproducible; if the hash computation, the set of
    fields carried into the model, or the is_a/properties resolution ever
    changes, this fails.

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

    assert {
        name: p.model_dump(exclude={"provenance"})
        for name, p in properties.items()
    } == {
        "name": {
            "hash_id": "sha256:a9d78a17053b0f3b42078d25a81cd04d0f7145db96638846e998c415bc5053ab",
            "name": "name",
            "description": "Full name.",
            "skos_mappings": [],
            "concept_uri": "https://schema.org/name",
            "source_native_id": None,
            "defined_in_schema": "comprehensive",
            "property_range": "xsd:string",
            "unit": None,
            "aliases": [],
        },
        "orcid": {
            "hash_id": "sha256:d27e546a325cc73b61c4faff2e4d95f3a4dac4ef5e609ea470f7268871edfb53",
            "name": "orcid",
            "description": "ORCID identifier.",
            "skos_mappings": [],
            "concept_uri": "https://example.org/schema#orcid",
            "source_native_id": None,
            "defined_in_schema": "comprehensive",
            "property_range": "xsd:string",
            "unit": None,
            "aliases": ["ORCID iD"],
        },
        "role": {
            "hash_id": "sha256:570586cb49eae5d55d35683580dce4a76d5665975252cab23a402e574854ea56",
            "name": "role",
            "description": "Role on the study (units: FTE)",
            "skos_mappings": [],
            "concept_uri": None,
            "source_native_id": None,
            "defined_in_schema": "comprehensive",
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
            "hash_id": "sha256:8a88c0c203de9613673c2b368e9e423b992c3896cd8f13631e2599c9a1326ab3",
            "name": "created_at",
            "description": "",
            "skos_mappings": [],
            "concept_uri": None,
            "source_native_id": None,
            "defined_in_schema": "comprehensive",
            "property_range": "xsd:dateTime",
            "unit": None,
            "aliases": [],
        },
    }

    assert {
        name: c.model_dump(exclude={"provenance"})
        for name, c in registry_classes.items()
    } == {
        "Timestamped": {
            "hash_id": "sha256:227dc9aac0a55a2ee62e6d98c7948dda9b288494823eef66a6b85612d0209b39",
            "name": "Timestamped",
            "description": "Mixin providing a creation timestamp.",
            "skos_mappings": [],
            "concept_uri": None,
            "source_native_id": None,
            "defined_in_schema": "comprehensive",
            "is_abstract": False,
            "properties": ["sha256:8a88c0c203de9613673c2b368e9e423b992c3896cd8f13631e2599c9a1326ab3"],
            "parent_class": None,
            "class_mixins": [],
            "aliases": [],
        },
        "Entity": {
            "hash_id": "sha256:b9dd5b96fe123dc7ebeb97b5bb67afec0d48c9109196f9089f6e26ee08594b1b",
            "name": "Entity",
            "description": "Abstract base for all registry entities.",
            "skos_mappings": [],
            "concept_uri": "https://example.org/schema#Entity",
            "source_native_id": None,
            "defined_in_schema": "comprehensive",
            "is_abstract": True,
            "properties": ["sha256:a9d78a17053b0f3b42078d25a81cd04d0f7145db96638846e998c415bc5053ab"],
            "parent_class": None,
            "class_mixins": [],
            "aliases": [],
        },
        "Person": {
            "hash_id": "sha256:fbb719a3ed9a446b0f4e82bacf5f0dbae6c50eadc3c8ab5c26fd6cdd2d033124",
            "name": "Person",
            "description": "A research investigator.",
            "skos_mappings": [],
            "concept_uri": "https://schema.org/Person",
            "source_native_id": None,
            "defined_in_schema": "comprehensive",
            "is_abstract": False,
            "properties": [
                "sha256:570586cb49eae5d55d35683580dce4a76d5665975252cab23a402e574854ea56",
                "sha256:8a88c0c203de9613673c2b368e9e423b992c3896cd8f13631e2599c9a1326ab3",
                "sha256:a9d78a17053b0f3b42078d25a81cd04d0f7145db96638846e998c415bc5053ab",
                "sha256:d27e546a325cc73b61c4faff2e4d95f3a4dac4ef5e609ea470f7268871edfb53",
            ],
            "parent_class": "sha256:b9dd5b96fe123dc7ebeb97b5bb67afec0d48c9109196f9089f6e26ee08594b1b",
            "class_mixins": [],
            "aliases": ["Investigator"],
        },
    }


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
    build_registry_entities()'s 3rd/4th return values are ValueSet and
    PermissibleValue dicts. PermissibleValue is a real RegistryEntity now
    (not the old hand-rolled node) — it gets a real description and
    provenance, keyed by hash_id since it's shared across enums/sources
    rather than tied to one source name.
    """
    parsed = parse_linkml(FIXTURES / "schema_with_enums.yml")
    properties, registry_classes, value_sets, permissible_values = build_registry_entities(
        parsed, "enum_test", "tester"
    )

    assert "StatusEnum" in value_sets
    vs = value_sets["StatusEnum"]
    assert isinstance(vs, ValueSet)
    assert vs.name == "StatusEnum"
    assert vs.description == "Possible statuses for an annotation."
    assert len(vs.permissible_values) == 2
    # hash_ids are deterministic — check they are sha256: prefixes
    for hid in vs.permissible_values:
        assert hid.startswith("sha256:")
    # Provenance from the ingestion
    assert len(vs.provenance) == 1
    assert vs.provenance[0].had_primary_source == "enum_test"

    assert set(vs.permissible_values) == set(permissible_values)
    for pv in permissible_values.values():
        assert isinstance(pv, PermissibleValue)
        assert pv.name in ("active", "deprecated")
        assert len(pv.provenance) == 1
        assert pv.provenance[0].had_primary_source == "enum_test"
