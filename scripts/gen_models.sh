#!/usr/bin/env bash
#
# Regenerate schema_registry_utils/models.py from meta_model.yaml.
#
# Used by both developers and .github/workflows/gen_models.yml, so that a local
# run and a CI run produce byte-identical output — otherwise the workflow would
# commit a spurious diff on every push.
#
# Two things make the output environment-dependent, so do not "simplify" them
# away:
#   * gen-pydantic embeds its argument verbatim as `source_file` in the
#     linkml_meta block. Passing an absolute path bakes in the checkout
#     directory, so we cd to the repo root and pass a relative path.
#   * `metamodel_version` in the output is the installed LinkML version, so CI
#     pins linkml to the same version this script is developed against.
#
# Usage:
#   ./scripts/gen_models.sh           # rewrite models.py in place
#   ./scripts/gen_models.sh --check   # exit 1 if models.py is out of date
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

SCHEMA="meta_model.yaml"
TARGET="schema_registry_utils/models.py"

# Prefer the repo venv's gen-pydantic; fall back to PATH (CI installs it there).
if [ -x .venv/bin/gen-pydantic ]; then
    GEN=.venv/bin/gen-pydantic
else
    GEN=gen-pydantic
fi

TMP="$(mktemp)"
BODY="$(mktemp)"
trap 'rm -f "$TMP" "$BODY"' EXIT

"$GEN" "$SCHEMA" > "$BODY"

{
    echo "# ---------------------------------------------------------------------------"
    echo "# GENERATED FILE — DO NOT EDIT BY HAND."
    echo "#"
    echo "# Produced by ./scripts/gen_models.sh from $SCHEMA."
    echo "# Edit the schema and regenerate; hand edits are overwritten by"
    echo "# .github/workflows/gen_models.yml on the next schema change."
    echo "# ---------------------------------------------------------------------------"
    cat "$BODY"
} > "$TMP"

if [ "${1:-}" = "--check" ]; then
    if diff -u "$TARGET" "$TMP"; then
        echo "$TARGET is up to date with $SCHEMA."
    else
        echo ""
        echo "ERROR: $TARGET is out of date with $SCHEMA."
        echo "Run ./scripts/gen_models.sh and commit the result."
        exit 1
    fi
else
    cp "$TMP" "$TARGET"
    echo "Wrote $TARGET from $SCHEMA."
fi
