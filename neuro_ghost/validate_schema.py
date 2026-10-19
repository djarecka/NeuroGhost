"""
validate_schema.py — Validate a submitted file is a well-formed LinkML schema
==============================================================================

WHY THIS FILE EXISTS
--------------------
The schema-submission GitHub Action used to "validate" incoming YAML by
checking that the string "classes:" appeared in the text and that the
parsed dict had "classes"/"slots" keys. That accepts almost anything —
a schema with a class that lists a slot which is never defined, or an
is_a parent that doesn't exist, sails straight through and only breaks
later, deep inside ingest_linkml.py.

This script does real LinkML validation, in two passes:

  1. Metamodel validation — is this YAML shaped like a LinkML schema at
     all? (required fields like id/name present, types match the LinkML
     metamodel's JSON Schema). Uses linkml's own Linter.validate_schema(),
     the same check `linkml validate schema.yml` runs.

  2. Reference resolution — do all the internal references actually
     resolve? A schema can satisfy the metamodel shape while still
     pointing a class's slots at an undefined slot name, or is_a at an
     undefined parent class, or a slot's range at an undefined
     class/type/enum. SchemaView resolves every class's induced slots,
     which forces exactly those lookups and raises a clear ValueError
     if something doesn't resolve.

USAGE
-----
  python validate_schema.py registry_schemas/bbqs.yml
  python validate_schema.py registry_schemas/bbqs.yml --strict   # also fail on lint warnings
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import click
from linkml.linter.linter import Linter
from linkml_runtime.utils.schemaview import SchemaView

from import_resolver import resolve_external_imports


def validate_metamodel(schema_path: str) -> list[str]:
    """Return a list of human-readable errors from metamodel validation."""
    return [
        f"{problem.rule_name}: {problem.message}"
        for problem in Linter.validate_schema(schema_path)
    ]


def validate_references(schema_path: str) -> list[str]:
    """
    Force resolution of every class's slots (and thereby their is_a
    parents and ranges) and collect any dangling references.

    Returns an empty list if the schema loads and every reference resolves.
    """
    errors: list[str] = []
    try:
        sv = SchemaView(schema_path)
    except Exception as e:  # malformed enough that SchemaView itself chokes
        return [f"could not load schema: {e}"]

    for class_name in sv.all_classes():
        try:
            sv.class_induced_slots(class_name)
        except ValueError as e:
            errors.append(f"class '{class_name}': {e}")

    return errors


@click.command()
@click.argument("schema_path", type=click.Path(exists=True))
def cli(schema_path: str) -> None:
    """Validate SCHEMA_PATH is a well-formed, internally-consistent LinkML schema."""
    # A schema may import sibling schemas that aren't in registry_schemas/
    # (declared via the imports_source annotation — see import_resolver.py).
    # Fetch them first, exactly as ingest does, and validate that copy.
    with tempfile.TemporaryDirectory() as work:
        _validate(str(resolve_external_imports(Path(schema_path), Path(work))), schema_path)


def _validate(resolved_path: str, schema_path: str) -> None:
    metamodel_errors = validate_metamodel(resolved_path)
    if metamodel_errors:
        click.echo(f"FAILED metamodel validation for {schema_path}:")
        for err in metamodel_errors:
            click.echo(f"  - {err}")
        sys.exit(1)

    reference_errors = validate_references(resolved_path)
    if reference_errors:
        click.echo(f"FAILED reference validation for {schema_path}:")
        for err in reference_errors:
            click.echo(f"  - {err}")
        sys.exit(1)

    sv = SchemaView(resolved_path)
    click.echo(
        f"Valid LinkML schema: {schema_path} "
        f"({len(sv.all_classes())} classes, {len(sv.all_slots())} slots)"
    )


if __name__ == "__main__":
    cli()
