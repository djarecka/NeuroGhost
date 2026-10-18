from conftest import FIXTURES
from export_json import _load_mappings
from ingest_linkml import insert_schema, parse_linkml
from mappings import Ref, RegistryIndex, load_rows, read_mapping_file

META = (
    "mapping_set_id: test_set\n"
    "mapping_date: 2026-10-18\n"
    "mapping_tool: embeddings/all-MiniLM-L6-v2\n"
    "mapping_justification: semapv:SemanticSimilarityThresholdMatching\n"
    "author_id: github-actions\n"
)
COLUMNS = "subject_id\tpredicate_id\tobject_id\tconfidence\treview_status\treviewer_id\tcomment\n"


def write(tmp_path, rows: str, meta: str | None = META):
    """A mapping table m.sssom.tsv and (unless meta is None) its metadata
    file m.sssom.yml."""
    path = tmp_path / "m.sssom.tsv"
    path.write_text(COLUMNS + rows)
    if meta is not None:
        (tmp_path / "m.sssom.yml").write_text(meta)
    return path


def test_ref_parses_class_and_property_references():
    assert Ref.parse("aind:Subject") == Ref("aind", "Subject")
    assert Ref.parse("schema.org:Thing.name") == Ref("schema.org", "Thing", "name")
    assert str(Ref.parse("bids:Columns.acq_time__scans")) == "bids:Columns.acq_time__scans"


def test_read_mapping_file_applies_header_defaults_and_reports_bad_rows(tmp_path):
    mf = read_mapping_file(write(tmp_path,
        "a:Subject\tskos:closeMatch\tb:Participant\t0.8\t\t\tlooks alike\n"
        "a:Subject.age\tskos:exactMatch\tb:Participant.age\t\tACCEPTED\tdjarecka\t\n"
        "a:Subject\tskos:sameAs\tb:Participant\t\t\t\t\n"        # unknown predicate
        "a:Subject\tskos:closeMatch\tb:Participant\t\tACCEPTED\t\t\n"  # no reviewer
        "Subject\tskos:closeMatch\tb:Participant\t\t\t\t\n"      # no source
    ))
    assert [(str(r.subject), r.review_status, r.author_id, r.mapping_tool) for r in mf.rows] == [
        ("a:Subject", "PROPOSED", "github-actions", "embeddings/all-MiniLM-L6-v2"),
        ("a:Subject.age", "ACCEPTED", "github-actions", "embeddings/all-MiniLM-L6-v2"),
    ]
    assert mf.rows[0].confidence == 0.8 and mf.rows[0].comment == "looks alike"
    assert len(mf.errors) == 3
    assert any("skos:sameAs" in e for e in mf.errors)
    assert any("needs a reviewer_id" in e for e in mf.errors)


def test_metadata_must_name_the_mapping_set_and_date(tmp_path):
    mf = read_mapping_file(write(tmp_path, "", meta="author_id: x\n"))
    assert len(mf.errors) == 2


def test_older_hash_header_still_loads_but_validate_wants_the_yml(tmp_path):
    """Metadata as `# key: value` lines at the top of the TSV (the first
    format) still reads, but validate asks for the .sssom.yml file, since
    GitHub can't show such a TSV as a table."""
    from click.testing import CliRunner
    from mappings import validate
    header = "".join(f"# {line}\n" for line in META.splitlines())
    path = tmp_path / "m.sssom.tsv"
    path.write_text(header + COLUMNS + "a:S\tskos:closeMatch\tb:T\t\t\t\t\n")
    mf = read_mapping_file(path)
    assert mf.errors == [] and not mf.has_metadata_file
    assert mf.rows[0].mapping_set_id == "test_set"

    registry = tmp_path / "registry.json"
    registry.write_text('{"classes": [{"id": "1", "name": "S", "sources": ["a"], "properties": []},'
                        ' {"id": "2", "name": "T", "sources": ["b"], "properties": []}]}')
    result = CliRunner().invoke(validate, [str(path), "--registry", str(registry)])
    assert result.exit_code == 1 and "no metadata file m.sssom.yml" in result.output


def test_load_writes_mappings_with_proposal_and_review_provenance(conn, tmp_path):
    insert_schema(conn, parse_linkml(FIXTURES / "source_a.yml"), "source_a", agent="tester")
    insert_schema(conn, parse_linkml(FIXTURES / "source_b.yml"), "source_b", agent="tester")
    mf = read_mapping_file(write(tmp_path,
        "source_a:Subject\tskos:closeMatch\tsource_b:Participant\t0.8\t\t\t\n"
        "source_a:Subject.age\tskos:exactMatch\tsource_b:Participant.age\t\tACCEPTED\tdjarecka\t\n"
        "source_a:Nope\tskos:closeMatch\tsource_b:Participant\t\t\t\t\n"
    ))
    stats = load_rows(conn, mf.rows)
    assert stats["loaded"] == 2
    assert stats["unresolved"] == [f"{mf.path}:4: source_a:Nope"]

    names = {i: n for label in ("RegistryClass", "RegistryProperty")
             for i, n in conn.execute(f"MATCH (x:{label}) RETURN x.id, x.name").get_all()}
    by_subject = _load_mappings(conn, names)
    subject_cls = conn.execute("MATCH (c:RegistryClass {name: 'Subject'}) RETURN c.id").get_next()[0]
    age = conn.execute("MATCH (p:RegistryProperty {name: 'age'}) RETURN p.id").get_next()[0]

    [cls_mapping] = by_subject[subject_cls]
    assert cls_mapping["predicate"] == "skos:closeMatch"
    assert cls_mapping["target_name"] == "Participant"
    assert cls_mapping["review_status"] == "PROPOSED"
    assert cls_mapping["proposed_by"] == "github-actions"
    assert cls_mapping["mapping_tool"] == "embeddings/all-MiniLM-L6-v2"
    assert cls_mapping["reviewed_by"] == ""

    # `age` collapses to one property shared by both sources, so this maps it
    # to itself — which is exactly what the file says.
    [prop_mapping] = by_subject[age]
    assert prop_mapping["predicate"] == "skos:exactMatch"
    assert prop_mapping["target_id"] == age
    assert prop_mapping["review_status"] == "ACCEPTED"
    assert prop_mapping["reviewed_by"] == "djarecka"
    assert prop_mapping["proposed_at"].startswith("2026-10-18")

    # Content-derived ids: loading the same rows again adds nothing.
    assert load_rows(conn, mf.rows)["loaded"] == 0
    assert cls_mapping["id"] == mf.rows[0].mapping_id


def test_registry_index_resolves_classes_and_properties():
    index = RegistryIndex({"classes": [
        {"id": "c1", "name": "Subject", "sources": ["aind"],
         "properties": [{"id": "p1", "name": "sex"}]},
    ]})
    assert index.resolve(Ref.parse("aind:Subject")) == "c1"
    assert index.resolve(Ref.parse("aind:Subject.sex")) == "p1"
    assert index.resolve(Ref.parse("bids:Subject")) is None


def test_proposed_file_round_trips_through_the_reader(tmp_path):
    """propose_mappings writes a file mappings.py reads back as PROPOSED rows
    with the generator's provenance; a property shared by several classes is
    one entity, referenced through its first class."""
    from propose_mappings import entities, write_mapping_file
    registry = {"classes": [
        {"id": "c2", "name": "Session", "sources": ["a"], "definition": "",
         "properties": [{"id": "p1", "name": "start", "definition": "Start time", "sources": ["a"]}]},
        {"id": "c1", "name": "Run", "sources": ["a"], "definition": "",
         "properties": [{"id": "p1", "name": "start", "definition": "Start time", "sources": ["a"]}]},
        {"id": "c3", "name": "Scan", "sources": ["b"], "definition": "",
         "properties": [{"id": "p2", "name": "onset", "definition": "Onset", "sources": ["b"]}]},
    ]}
    [subject] = entities(registry, "a", "properties")
    assert subject.ref == "a:Run.start"
    [obj] = entities(registry, "b", "properties")

    path = tmp_path / "x.sssom.tsv"
    write_mapping_file(path, [(subject, obj, 0.71)], mapping_set_id="set1",
                       model_name="m", author="github-actions")
    mf = read_mapping_file(path)
    assert mf.errors == []
    [row] = mf.rows
    assert (str(row.subject), row.predicate, str(row.object)) == ("a:Run.start", "skos:closeMatch", "b:Scan.onset")
    assert (row.review_status, row.confidence, row.mapping_tool, row.author_id) == \
        ("PROPOSED", 0.71, "embeddings/m", "github-actions")


def test_reviews_must_be_made_in_the_pr_authors_name(tmp_path):
    """A PR may accept/reject mappings only as its own author; reviews that
    were already in the base file (made in an earlier PR) are left alone."""
    from mappings import unattributed_reviews
    base = read_mapping_file(write(tmp_path,
        "a:S\tskos:closeMatch\tb:T\t\tACCEPTED\talice\t\n"
        "a:S.x\tskos:closeMatch\tb:T.y\t\t\t\t\n")).rows
    (tmp_path / "pr").mkdir()
    pr = read_mapping_file(write(tmp_path / "pr",
        "a:S\tskos:closeMatch\tb:T\t\tACCEPTED\talice\t\n"      # unchanged review: fine
        "a:S.x\tskos:closeMatch\tb:T.y\t\tACCEPTED\tbob\t\n"    # new review by the author: fine
        "a:S.z\tskos:closeMatch\tb:T.z\t\tREJECTED\tmallory\t\n"  # someone else's name: not
    )).rows
    problems = unattributed_reviews(pr, base, authors={"bob"})
    assert len(problems) == 1 and "mallory" in problems[0]


def test_schema_pairs_expand_all():
    from propose_mappings import schema_pairs
    reg = {"sources": [{"label": "a"}, {"label": "b"}, {"label": "c"}]}
    assert schema_pairs(reg, "a", "b") == [("a", "b")]
    assert schema_pairs(reg, "a", "all") == [("a", "b"), ("a", "c")]
    assert schema_pairs(reg, "all", "c") == [("a", "c"), ("b", "c")]
    assert schema_pairs(reg, "all", "all") == [("a", "b"), ("a", "c"), ("b", "c")]
    import pytest
    with pytest.raises(ValueError, match="unknown schema 'x'"):
        schema_pairs(reg, "x", "a")
    with pytest.raises(ValueError, match="both 'a'"):
        schema_pairs(reg, "a", "a")


def test_spaces_typed_instead_of_a_tab_still_separate_columns(tmp_path):
    """GitHub's web editor often inserts spaces for Tab: a short row whose
    last columns are separated by 2+ spaces still parses; a complete row's
    comment keeps its double spaces."""
    mf = read_mapping_file(write(tmp_path,
        "a:S\tskos:closeMatch\tb:T\t0.66\tACCEPTED  djarecka\n"
        "a:S.x\tskos:closeMatch\tb:T.y\t\tPROPOSED\t\tkeep  these  spaces\n"
    ))
    assert mf.errors == []
    assert (mf.rows[0].review_status, mf.rows[0].reviewer_id) == ("ACCEPTED", "djarecka")
    assert mf.rows[1].comment == "keep  these  spaces"
