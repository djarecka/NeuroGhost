from click.testing import CliRunner

from conftest import FIXTURES
from validate_schema import cli, validate_metamodel, validate_references


def test_class_with_slots_is_valid():
    path = str(FIXTURES / "valid_slots.yml")
    assert validate_metamodel(path) == []
    assert validate_references(path) == []


def test_class_with_attributes_is_valid():
    path = str(FIXTURES / "valid_attributes.yml")
    assert validate_metamodel(path) == []
    assert validate_references(path) == []


def test_undefined_slot_fails_reference_check():
    path = str(FIXTURES / "invalid_undefined_slot.yml")
    assert validate_metamodel(path) == []  # shape is fine — only the reference is broken
    errors = validate_references(path)
    assert errors
    assert any("nonexistent_slot" in e for e in errors)


def test_cli_accepts_valid_schema():
    result = CliRunner().invoke(cli, [str(FIXTURES / "valid_slots.yml")])
    assert result.exit_code == 0
    assert "Valid LinkML schema" in result.output


def test_cli_rejects_undefined_slot():
    result = CliRunner().invoke(cli, [str(FIXTURES / "invalid_undefined_slot.yml")])
    assert result.exit_code != 0
    assert "nonexistent_slot" in result.output


def test_cli_validates_after_fetching_external_imports(tmp_path, monkeypatch):
    """A schema importing a sibling that isn't next to it (declared via the
    imports_source annotation, e.g. BICAN's bican_core) must validate the way
    ingest sees it: with the imports fetched first. Without that, validation
    failed on the missing file and blocked such schemas from being submitted."""
    from click.testing import CliRunner
    import validate_schema

    schema = tmp_path / "submitted" / "mine.yml"
    schema.parent.mkdir()
    schema.write_text(
        "id: https://example.org/mine\nname: mine\n"
        "prefixes: {linkml: https://w3id.org/linkml/}\n"
        "imports: [linkml:types, core]\ndefault_range: string\n"
        "annotations: {imports_source: https://example.org/models}\n"
        "classes:\n  Thing:\n    is_a: Base\n")
    fetched = tmp_path / "fetched"

    def fake_resolve(path, work_dir):
        # What import_resolver does: copy the schema next to its fetched imports.
        fetched.mkdir()
        (fetched / "mine.yml").write_text(path.read_text())
        (fetched / "core.yaml").write_text(
            "id: https://example.org/core\nname: core\n"
            "prefixes: {linkml: https://w3id.org/linkml/}\nimports: [linkml:types]\n"
            "classes:\n  Base:\n    attributes: {label: {}}\n")
        return fetched / "mine.yml"

    monkeypatch.setattr(validate_schema, "resolve_external_imports", fake_resolve)
    result = CliRunner().invoke(validate_schema.cli, [str(schema)])
    assert result.exit_code == 0, result.output
    assert "Valid LinkML schema" in result.output
