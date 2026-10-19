---
name: ingest-schema
description: Add a new schema to the NeuroGhost registry — from LinkML, JSON Schema, Pydantic models, or a looser description (spreadsheet, data dictionary, docs) — check it locally the way the submission workflow would, preview what it adds and what already exists, and open a PR with the schema and its source metadata. Use when the user wants to submit/add/register/ingest a schema ("add my lab's schema", "ingest this JSON schema", "register these Pydantic models").
---

# Ingest a schema

Get a schema into `registry_schemas/` as LinkML, check it exactly as the
submission workflow does, show the user what it adds to the registry, and open
a PR with it. Merging the PR triggers the registry rebuild, which ingests it.

This replaces the website's Ingest tab when the schema is large (the tab's
issue-URL prefill is limited to ~8 KB) or the user can't use it (SSO).

Keep the user in control: never change the meaning of their schema without
asking, and ask before committing, pushing, or opening the PR.

## 1. Set up

- Repository root, branch off an up-to-date `main`:
  `git fetch upstream && git switch -c schema/<name> upstream/main`
  (or `origin` if they work directly on sensein/NeuroGhost).
- `gh auth status` must show a logged-in account (for the PR).
- Python with `requirements.txt` installed.

## 2. Get the schema and its name

Ask for the schema (a path, a URL, or pasted text) and a short file **name**:
lowercase letters, digits and hyphens (the workflow's rule:
`re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')`), for
`registry_schemas/<name>.yml`. Check that file doesn't already exist.

The **label** the registry shows (and that mapping files and the Propose
Mappings dropdown use) is the schema's own LinkML `name:`, not the file name.
Check that it isn't already a label in `data/registry.json` → `sources`. If
it's too generic for a shared registry, tell the user; changing `name:` is
their call (it edits their schema), the `id` stays as is either way.

Download a URL into its own new, empty directory. For a file in a repository,
**pin it to a commit**: record the commit (e.g.
`gh api "repos/<org>/<repo>/commits?path=<path>&per_page=1" --jq '.[0].sha'`)
for `source_id` and for imports below.

Then, by format:

- **LinkML** (`.yml`/`.yaml` with `classes:` / `slots:`): copy it to
  `registry_schemas/<name>.yml` unchanged — except for **imports**: if its
  `imports:` names sibling schemas (anything other than CURIEs like
  `linkml:types`), they won't be next to it in `registry_schemas/`. Add one
  annotation pointing at the directory they live in, pinned to the commit
  (see `neuro_ghost/import_resolver.py`), and tell the user it's the only
  change:
  ```yaml
  annotations:
    imports_source: https://raw.githubusercontent.com/<org>/<repo>/<commit>/<dir>
  ```
  Classes from imported schemas are registered as part of this schema (and
  shared with any later schema that imports the same ones) — mention it.
- **JSON Schema** (`.json`, or YAML with `properties` / `$defs`): convert with
  the same converter the workflow uses —
  ```bash
  python -c "import json,sys,yaml; sys.path.insert(0,'.'); \
  from neuro_ghost.converters.from_jsonschema import convert; \
  d=convert(json.load(open('<input.json>')), '<name>'); \
  open('registry_schemas/<name>.yml','w').write(yaml.dump(d, default_flow_style=False, allow_unicode=True, sort_keys=False))"
  ```
- **Pydantic models**: import the top-level model(s) and use
  `Model.model_json_schema()`, then convert as JSON Schema. Several models:
  convert each and merge their `classes` / `slots` / `enums` (first definition
  wins, as `neuro_ghost/converters/aind.py` does).
- **Anything else** (spreadsheet, data dictionary, paper, prose): draft LinkML
  with the user — one class per record type, one attribute per field, with the
  field's description, `range`, `required`, `pattern`, units — and confirm the
  draft with them before going on. Keep their names; don't invent fields.

## 3. Check it like the workflow

```bash
python neuro_ghost/validate_schema.py registry_schemas/<name>.yml
python scripts/check_duplicate_schema.py registry_schemas/<name>.yml
python neuro_ghost/ingest.py --dry-run --verbose-readable registry_schemas/<name>.yml
```

Fix validation errors (undefined slots or ranges, a dangling `is_a`) — explain
each fix and get the user's OK if it changes meaning. If the duplicate check
fails, the identical schema is already registered under another name: stop
and tell the user.

## 4. Preview what it adds

```bash
python neuro_ghost/preview_schema.py registry_schemas/<name>.yml
```

Summarize for the user, in plain words:

- **Already in the registry** — identical classes/properties another schema
  has; they'll be shared, which is good.
- **Same name, different content** — look at each with the user: a real
  difference, or a near-copy (e.g. only the description differs) where
  reusing the existing definition would let the two schemas share it.
- **New** — what this schema contributes.
- **Missing descriptions** — offer to draft them (one sentence each) for the
  user to approve; descriptions are what make reuse and mapping work. For a
  schema converted from an upstream source, suggest fixing it upstream instead
  of editing only the registry copy.

Re-run the preview after any change.

## 5. Source metadata

Ask whether the schema belongs under an umbrella (**bundle**) — several files
of one project, like `dandi` (asset + dandiset) or `bican`; reuse an existing
`bundle_label` from `data/registry.json` → `bundles` when it fits. Pre-fill
what you can from the source (repository description, homepage, license,
the schema's own `license:`), ask for the rest, and write
`registry_schemas/<name>_source.yaml` (see `neuro_ghost/source_metadata.py`);
skip what nobody knows:

```yaml
bundle_label: <umbrella name if this is one file of a multi-file schema, e.g. dandi>
bundle_title: <human-readable title>
bundle_homepage: <project URL>
bundle_publisher: <organization>
bundle_contact: <email or URL>
bundle_license: <e.g. CC-BY-4.0>
source_id: <where this file comes from, e.g. a repository URL>
source_version: <the schema's own version>
```

## 6. Open the PR — ask first

Show a short summary (name, format, counts from the preview, metadata) and
**ask before** committing, pushing, or opening the PR:

```bash
git add registry_schemas/<name>.yml registry_schemas/<name>_source.yaml .github/workflows/propose_mappings.yml
git commit -m "Add schema: <name>"
git push -u origin schema/<name>
gh pr create --base main --title "Add schema: <name>" --body "<summary: source, format, what the preview found>"
```

(From a fork: `--repo sensein/NeuroGhost --head <login>:schema/<name>`.)

Before the PR, add the schema's **label** to the two schema dropdowns in
`.github/workflows/propose_mappings.yml` (they're a fixed list), in the same
commit, so it can be mapped right after merging.

Optionally, before the PR, run a full rebuild in a scratch copy of the repo
(`python neuro_ghost/pipeline.py --fresh --skip-converters`, ~5 min) and check
`data/registry.json` there: the new label in `sources`, in the right bundle.

After it's merged, the rebuild ingests it; mapping comes next — suggest the
`propose-mappings` skill (or the *Propose Mappings* workflow) with the label.
