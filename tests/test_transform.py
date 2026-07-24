"""
test_transform.py
-----------------
Tests for the transform_record MCP tool using a real BBQS sample dataset
(tests/fixtures/bbqs_sample.jsonld).

The registry is patched with a minimal fixture so the tests run fully
offline without a live DB.  Alignments are hand-crafted to match the
expected cross-schema property overlaps.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from neuro_ghost.mcp_server import transform_record

FIXTURES = Path(__file__).parent / "fixtures"

# ---------------------------------------------------------------------------
# Minimal registry fixture
# ---------------------------------------------------------------------------
# Contains four schemas: bbqs, bids, nwb, dandi.
# Alignments mirror what the Proteus pipeline would produce for these classes.

_REGISTRY: dict = {
    "registry_version": "test",
    "sources": [
        {"label": "bbqs",  "version": "1.0.0", "class_count": 5},
        {"label": "bids",  "version": "1.0.0", "class_count": 3},
        {"label": "nwb",   "version": "1.0.0", "class_count": 3},
        {"label": "dandi", "version": "1.0.0", "class_count": 2},
    ],
    "classes": [
        # ------------------------------------------------------------------ #
        # BBQS source classes
        # ------------------------------------------------------------------ #
        {
            "hash_id": "sha256:bbqs_investigator",
            "name": "Investigator",
            "sources": ["bbqs"],
            "iri": "https://brain-bbqs.org/schema/Investigator",
            "definition": "A research investigator on a BBQS-funded project.",
            "properties": [
                {"name": "name",        "hash_id": "sha256:p_name"},
                {"name": "email",       "hash_id": "sha256:p_email"},
                {"name": "identifier",  "hash_id": "sha256:p_identifier"},
                {"name": "affiliation", "hash_id": "sha256:p_affiliation"},
            ],
            "alignments": [
                {
                    "target_hash_id": "sha256:bids_participant",
                    "target_name":    "Participant",
                    "distance":       0.15,
                    "method":         "proteus",
                    "skos_relation":  "closeMatch",
                },
            ],
        },
        {
            "hash_id": "sha256:bbqs_dataset",
            "name": "Dataset",
            "sources": ["bbqs"],
            "iri": "https://brain-bbqs.org/schema/Dataset",
            "definition": "A BBQS research dataset archived in DANDI/EMBER.",
            "properties": [
                {"name": "identifier", "hash_id": "sha256:p_identifier"},
                {"name": "name",       "hash_id": "sha256:p_name"},
                {"name": "species",    "hash_id": "sha256:p_species"},
                {"name": "modality",   "hash_id": "sha256:p_modality"},
            ],
            "alignments": [
                {
                    "target_hash_id": "sha256:bids_dataset",
                    "target_name":    "BIDSDataset",
                    "distance":       0.20,
                    "method":         "proteus",
                    "skos_relation":  "closeMatch",
                },
                {
                    "target_hash_id": "sha256:dandi_dandiset",
                    "target_name":    "Dandiset",
                    "distance":       0.18,
                    "method":         "proteus",
                    "skos_relation":  "closeMatch",
                },
                {
                    "target_hash_id": "sha256:nwb_nwbfile",
                    "target_name":    "NWBFile",
                    "distance":       0.35,
                    "method":         "proteus",
                    "skos_relation":  "relatedMatch",
                },
            ],
        },
        {
            "hash_id": "sha256:bbqs_device",
            "name": "Device",
            "sources": ["bbqs"],
            "iri": "https://brain-bbqs.org/schema/Device",
            "definition": "A recording device used in BBQS experiments.",
            "properties": [
                {"name": "name",     "hash_id": "sha256:p_name"},
                {"name": "modality", "hash_id": "sha256:p_modality"},
            ],
            "alignments": [
                {
                    "target_hash_id": "sha256:nwb_device",
                    "target_name":    "Device",
                    "distance":       0.10,
                    "method":         "proteus",
                    "skos_relation":  "exactMatch",
                },
            ],
        },
        {
            "hash_id": "sha256:bbqs_fundedproject",
            "name": "FundedProject",
            "sources": ["bbqs"],
            "iri": "https://brain-bbqs.org/schema/FundedProject",
            "definition": "An NIH-funded research project in the BBQS cohort.",
            "properties": [
                {"name": "identifier", "hash_id": "sha256:p_identifier"},
                {"name": "name",       "hash_id": "sha256:p_name"},
                {"name": "funding",    "hash_id": "sha256:p_funding"},
                {"name": "species",    "hash_id": "sha256:p_species"},
            ],
            "alignments": [
                {
                    "target_hash_id": "sha256:dandi_dandiset",
                    "target_name":    "Dandiset",
                    "distance":       0.40,
                    "method":         "proteus",
                    "skos_relation":  "relatedMatch",
                },
            ],
        },
        {
            "hash_id": "sha256:bbqs_software",
            "name": "Software",
            "sources": ["bbqs"],
            "iri": "https://brain-bbqs.org/schema/Software",
            "definition": "Analysis software used in BBQS data processing.",
            "properties": [
                {"name": "name",       "hash_id": "sha256:p_name"},
                {"name": "identifier", "hash_id": "sha256:p_identifier"},
            ],
            "alignments": [],  # no close match in bids/nwb/dandi yet
        },
        # ------------------------------------------------------------------ #
        # BIDS target classes
        # ------------------------------------------------------------------ #
        {
            "hash_id": "sha256:bids_participant",
            "name": "Participant",
            "sources": ["bids"],
            "iri": "https://bids.neuroimaging.io/schema/Participant",
            "definition": "A research participant in a BIDS dataset.",
            "properties": [
                {"name": "name",        "hash_id": "sha256:p_name"},
                {"name": "email",       "hash_id": "sha256:p_email"},
                {"name": "identifier",  "hash_id": "sha256:p_identifier"},
                {"name": "affiliation", "hash_id": "sha256:p_affiliation"},
            ],
            "alignments": [],
        },
        {
            "hash_id": "sha256:bids_dataset",
            "name": "BIDSDataset",
            "sources": ["bids"],
            "iri": "https://bids.neuroimaging.io/schema/BIDSDataset",
            "definition": "A BIDS-compliant dataset.",
            "properties": [
                {"name": "name",       "hash_id": "sha256:p_name"},
                {"name": "identifier", "hash_id": "sha256:p_identifier"},
                {"name": "species",    "hash_id": "sha256:p_species"},
            ],
            "alignments": [],
        },
        # ------------------------------------------------------------------ #
        # NWB target classes
        # ------------------------------------------------------------------ #
        {
            "hash_id": "sha256:nwb_device",
            "name": "Device",
            "sources": ["nwb"],
            "iri": "https://nwb-schema.readthedocs.io/en/latest/#Device",
            "definition": "A recording device described in an NWB file.",
            "properties": [
                {"name": "name",     "hash_id": "sha256:p_name"},
                {"name": "modality", "hash_id": "sha256:p_modality"},
            ],
            "alignments": [],
        },
        {
            "hash_id": "sha256:nwb_nwbfile",
            "name": "NWBFile",
            "sources": ["nwb"],
            "iri": "https://nwb-schema.readthedocs.io/en/latest/#NWBFile",
            "definition": "Root container for an NWB file.",
            "properties": [
                {"name": "identifier", "hash_id": "sha256:p_identifier"},
                {"name": "species",    "hash_id": "sha256:p_species"},
                {"name": "modality",   "hash_id": "sha256:p_modality"},
            ],
            "alignments": [],
        },
        # ------------------------------------------------------------------ #
        # DANDI target classes
        # ------------------------------------------------------------------ #
        {
            "hash_id": "sha256:dandi_dandiset",
            "name": "Dandiset",
            "sources": ["dandi"],
            "iri": "https://dandiarchive.org/schema/Dandiset",
            "definition": "A curated collection of NWB files on DANDI.",
            "properties": [
                {"name": "identifier", "hash_id": "sha256:p_identifier"},
                {"name": "name",       "hash_id": "sha256:p_name"},
                {"name": "species",    "hash_id": "sha256:p_species"},
            ],
            "alignments": [],
        },
    ],
}


@pytest.fixture(autouse=True)
def patch_registry():
    """Inject the fixture registry so every test runs fully offline."""
    with patch("neuro_ghost.mcp_server._registry", _REGISTRY):
        yield


# ---------------------------------------------------------------------------
# Helpers — extract records from the JSON-LD fixture
# ---------------------------------------------------------------------------

def _load_sample() -> list[dict]:
    return json.loads((FIXTURES / "bbqs_sample.jsonld").read_text())["@graph"]


def _entity(type_suffix: str) -> dict:
    """Return the first entity whose @type includes the given bbqs: suffix."""
    for e in _load_sample():
        types = e.get("@type", [])
        if isinstance(types, str):
            types = [types]
        if any(t.endswith(type_suffix) for t in types):
            return e
    raise KeyError(type_suffix)


def _flat(entity: dict) -> dict:
    """Strip JSON-LD @ keys and namespace prefixes for use as a plain record."""
    return {
        k.split(":")[-1]: v
        for k, v in entity.items()
        if not k.startswith("@")
    }


# ---------------------------------------------------------------------------
# Investigator → BIDS Participant
# ---------------------------------------------------------------------------

def test_investigator_to_bids_maps_core_fields():
    inv = _flat(_entity("Investigator"))
    result = transform_record("bbqs", "bids", inv)
    assert result["mapped"]["name"] == inv["name"]
    assert result["mapped"]["email"] == inv["email"]
    assert result["mapped"]["identifier"] == inv["identifier"]
    assert result["mapped"]["affiliation"] == inv["affiliation"]


def test_investigator_to_bids_reports_unmapped_bbqs_specific_fields():
    inv = _flat(_entity("Investigator"))
    result = transform_record("bbqs", "bids", inv)
    # bbqs-specific fields have no BIDS equivalent
    assert "researchAreas" in result["unmapped"] or "role" in result["unmapped"] \
        or len(result["unmapped"]) == 0  # some entities have no extras


def test_investigator_to_nwb_returns_no_property_alignments():
    inv = _flat(_entity("Investigator"))
    result = transform_record("bbqs", "nwb", inv)
    # No alignment between Investigator and any NWB class — expect a warning
    assert any("alignment" in w.lower() or "No property" in w
               for w in result["warnings"])


# ---------------------------------------------------------------------------
# Dataset → BIDS / DANDI / NWB
# ---------------------------------------------------------------------------

def test_dataset_to_bids_maps_overlapping_fields():
    ds = _flat(_entity("Dataset"))
    result = transform_record("bbqs", "bids", ds)
    assert "name" in result["mapped"]
    assert "identifier" in result["mapped"]
    assert "species" in result["mapped"]


def test_dataset_to_dandi_maps_overlapping_fields():
    ds = _flat(_entity("Dataset"))
    result = transform_record("bbqs", "dandi", ds)
    assert "name" in result["mapped"]
    assert "identifier" in result["mapped"]
    assert "species" in result["mapped"]


def test_dataset_to_nwb_maps_via_relatedmatch():
    ds = _flat(_entity("Dataset"))
    result = transform_record("bbqs", "nwb", ds)
    # distance 0.35 < 0.6 threshold — fields with shared names should map
    assert "identifier" in result["mapped"] or "species" in result["mapped"]


def test_dataset_modality_is_unmapped_when_target_lacks_it():
    """modality is a BBQS field; BIDS BIDSDataset has no modality property."""
    ds = _flat(_entity("Dataset"))
    result = transform_record("bbqs", "bids", ds)
    assert "modality" in result["unmapped"]


# ---------------------------------------------------------------------------
# Device → NWB Device
# ---------------------------------------------------------------------------

def test_device_to_nwb_maps_name_and_modality():
    dev = _flat(_entity("Device"))
    result = transform_record("bbqs", "nwb", dev)
    assert result["mapped"]["name"] == dev["name"]
    assert result["mapped"]["modality"] == dev["modality"]
    assert result["unmapped"] == [] or all(
        f in ("channels", "commonIssues") for f in result["unmapped"]
    )


def test_device_to_bids_has_no_alignments():
    dev = _flat(_entity("Device"))
    result = transform_record("bbqs", "bids", dev)
    assert any("No property alignments" in w for w in result["warnings"])


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_unknown_source_schema_returns_no_alignments():
    result = transform_record("nonexistent", "bids", {"name": "test"})
    assert result["mapped"] == {}
    assert "name" in result["unmapped"]


def test_unknown_target_schema_returns_no_alignments():
    result = transform_record("bbqs", "nonexistent", {"name": "test"})
    assert result["mapped"] == {}


def test_empty_record_returns_empty_mapped():
    result = transform_record("bbqs", "bids", {})
    assert result["mapped"] == {}
    assert result["unmapped"] == []


def test_all_schemas_reachable_from_bbqs_dataset():
    """Dataset has alignments to bids, dandi, and nwb — all should return something."""
    ds = _flat(_entity("Dataset"))
    for target in ("bids", "dandi", "nwb"):
        result = transform_record("bbqs", target, ds)
        # At minimum the call should succeed and return the result structure
        assert "mapped" in result
        assert "unmapped" in result
        assert "warnings" in result
