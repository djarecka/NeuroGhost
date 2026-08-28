from pathlib import Path

from db import get_connection
from ingest_linkml import insert_schema, parse_linkml

FIXTURES = Path(__file__).parent / "fixtures"


def _conn(tmp_path):
    return get_connection(str(tmp_path / "test.lbug"))


def test_identical_property_from_two_sources_collapses_to_one_entity(tmp_path):
    """
    Identity is content-derived only — no source-anchoring field is part of
    the sha256_hash — so identical content ingested from two different schemas
    collapses to one RegistryProperty node (dedup reuses its id), which accumulates one
    ProvenanceEntry per attesting source. This is how identity stays
    separate from provenance: nothing about the entity's sha256_hash depends on
    where it came from, and the shared id follows.
    """
    conn = _conn(tmp_path)

    insert_schema(conn, parse_linkml(FIXTURES / "source_a.yml"), "source_a", agent="tester")
    insert_schema(conn, parse_linkml(FIXTURES / "source_b.yml"), "source_b", agent="tester")

    rows = conn.execute("MATCH (p:RegistryProperty {name: 'age'}) RETURN p.sha256_hash").get_all()
    shas = {r[0] for r in rows}
    assert len(shas) == 1

    labels = conn.execute("""
        MATCH (p:RegistryProperty {name: 'age'})-[:HAS_PROVENANCE_P]->(:ProvenanceEntry)-[:HAD_PRIMARY_SOURCE]->(ss:SchemaSource)
        RETURN ss.label
    """).get_all()
    assert {r[0] for r in labels} == {"source_a", "source_b"}


def test_aliases_round_trip_through_the_graph(tmp_path):
    """
    aliases is a plain multivalued string field (not a UUID-reference list
    like properties), so it's written to a native list column
    (STRING[] — see db.py's _build_registry_ddl()) rather than an edge, and
    NOT JSON-encoded into a STRING column: a bound string that looks like a
    Cypher list literal gets silently reparsed and corrupted by the DB
    engine. Confirm it survives the write/read round trip through the real
    graph, not just in-memory.
    """
    conn = _conn(tmp_path)
    insert_schema(conn, parse_linkml(FIXTURES / "comprehensive.yml"), "comprehensive", agent="tester")

    prop_rows = conn.execute(
        "MATCH (p:RegistryProperty {name: 'orcid'}) RETURN p.aliases"
    ).get_all()
    assert prop_rows[0][0] == ["ORCID iD"]

    class_rows = conn.execute(
        "MATCH (c:RegistryClass {name: 'Person'}) RETURN c.aliases"
    ).get_all()
    assert class_rows[0][0] == ["Investigator"]


def test_reingesting_same_source_is_idempotent(tmp_path):
    conn = _conn(tmp_path)
    parsed = parse_linkml(FIXTURES / "source_a.yml")

    first = insert_schema(conn, parsed, "source_a", agent="tester")
    assert first["classes_new"] == 1
    assert first["properties_new"] == 1
    assert first["provenance_added"] == 2  # one class + one property

    second = insert_schema(conn, parsed, "source_a", agent="tester")
    assert second["classes_new"] == 0
    assert second["properties_new"] == 0
    assert second["provenance_added"] == 0
    assert second.get("schema_unchanged") is True


def test_inherited_slots_and_subclass_edge(tmp_path):
    conn = _conn(tmp_path)
    insert_schema(conn, parse_linkml(FIXTURES / "hierarchy.yml"), "hierarchy", agent="tester")

    props = conn.execute("""
        MATCH (c:RegistryClass {name: 'Sensor'})-[:HAS_PROPERTY]->(p:RegistryProperty)
        RETURN p.name
    """).get_all()
    assert {r[0] for r in props} == {"manufacturer", "sampling_rate"}

    parent = conn.execute("""
        MATCH (c:RegistryClass {name: 'Sensor'})-[:SUBCLASS_OF]->(p:RegistryClass)
        RETURN p.name
    """).get_all()
    assert parent == [["Device"]]


def test_required_does_not_affect_property_identity(tmp_path):
    """
    required_a.yml and required_b.yml declare the exact same "age" slot
    (same name/description/range/units) except one marks it `required: true`
    and the other doesn't. RegistryProperty doesn't model required at all
    (deferred to a future RegistryRule — see test_registry_property_does_not_retain_
    usage_constraints in test_ingest_linkml.py), so within a single source
    this must not create a second node: same sha256_hash, one node.

    Both YAMLs are ingested under the same source label, isolating the
    `required` flag as the only differing input, which is what the test
    asserts is irrelevant to identity.
    """
    conn = _conn(tmp_path)

    stats_a = insert_schema(conn, parse_linkml(FIXTURES / "required_a.yml"), "required", agent="tester")
    stats_b = insert_schema(conn, parse_linkml(FIXTURES / "required_b.yml"), "required", agent="tester")

    assert stats_a["properties_new"] == 1
    assert stats_b["properties_new"] == 0        # not a new node — same hash within one source
    assert stats_b["properties_existing"] == 1

    rows = conn.execute("MATCH (p:RegistryProperty {name: 'age'}) RETURN p.sha256_hash").get_all()
    assert len(rows) == 1                         # no duplicate node


def test_content_change_produces_different_entity(tmp_path):
    """
    Same source, edited content → new hash. Both ingests use the same
    source label ("source_a"), isolating the description edit as the sole
    driver of the hash change.

    A range edit is deliberately NOT tested here — property_range is not
    in HashSubset (see meta_model.yaml), so a range change is metadata,
    not identity. Per-usage range refinements land on RegistryRule
    (rule_type=RANGE), which does carry range in its own HashSubset.
    """
    conn = _conn(tmp_path)
    insert_schema(conn, parse_linkml(FIXTURES / "source_a.yml"), "source_a", agent="tester")

    original_sha = conn.execute(
        "MATCH (p:RegistryProperty {name: 'age'}) RETURN p.sha256_hash"
    ).get_next()[0]

    edited = parse_linkml(FIXTURES / "source_a.yml")
    edited["slots"]["age"]["definition"] = "Age of the subject in years"  # was "Age of the subject"
    insert_schema(conn, edited, "source_a", agent="tester")

    shas = {
        row[0] for row in
        conn.execute("MATCH (p:RegistryProperty {name: 'age'}) RETURN p.sha256_hash").get_all()
    }
    assert len(shas) == 2
    assert original_sha in shas


def test_bican_prov_ingests_expected_classes_and_properties(tmp_path):
    """
    bican_prov.yaml (github.com/brain-bican/models) is a small, real-world
    schema: two classes, three properties, and — notably — a slot whose
    range is another class in the same schema (used: range ProvEntity).
    Confirms build_registry_entities()'s "second pass" (see ingest_linkml.py)
    correctly rewrites that property_range from the synthetic make_iri()
    placeholder to the real RegistryClass id, not just a string that
    happens to look right.

    """
    conn = _conn(tmp_path)
    insert_schema(conn, parse_linkml(FIXTURES / "bican_prov.yaml"), "bican_prov", agent="tester")

    classes = {
        row[0]: row[1] for row in
        conn.execute("MATCH (c:RegistryClass) RETURN c.name, c.id").get_all()
    }
    assert set(classes) == {"ProvActivity", "ProvEntity"}

    props = conn.execute(
        "MATCH (p:RegistryProperty) RETURN p.name, p.property_range"
    ).get_all()
    range_by_name = {name: rng for name, rng in props}
    assert set(range_by_name) == {"used", "was_derived_from", "was_generated_by"}

    # property_range must be the real RegistryClass id, not the synthetic
    # make_iri("ProvEntity")-style placeholder _slot_to_dict() starts with.
    assert range_by_name["used"] == classes["ProvEntity"]
    assert range_by_name["was_derived_from"] == classes["ProvEntity"]
    assert range_by_name["was_generated_by"] == classes["ProvActivity"]

    has_property = conn.execute("""
        MATCH (c:RegistryClass)-[:HAS_PROPERTY]->(p:RegistryProperty)
        RETURN c.name, p.name
    """).get_all()
    assert set(map(tuple, has_property)) == {
        ("ProvActivity", "used"),
        ("ProvEntity", "was_derived_from"),
        ("ProvEntity", "was_generated_by"),
    }
