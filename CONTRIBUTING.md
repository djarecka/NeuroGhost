# Contributing to NeuroGhost

Thanks for helping! Everything in NeuroGhost — schemas, mappings, code —
changes through **pull requests** to `main`. A merge triggers a rebuild that
regenerates the registry data and publishes the website.

## Ground rules

- **Schemas and mappings are reviewed before they land.** That includes
  upstream updates (*Fetch External Schemas* opens a PR, never commits) and
  AI-proposed mappings (a person approves each row; `mapping_tool` records the
  model).
- **`data/` is generated, never edited by hand.** The rebuild after each merge
  writes `data/registry.json`, `data/versions/` and `data/provenance.json`.
  PRs carry only schema, mapping or code changes.
- **Mapping reviews are made in your own name.** The *Mapping Check* rejects an
  `ACCEPTED`/`REJECTED` row whose `reviewer_id` isn't an author of the PR.
- **The meta-model needs a moderator.** Changes to `meta_model.yaml` (and the
  generated `schema_registry_utils/models.py`) define identity and hashing for
  the whole registry, so they need approval from a meta-model moderator:
  @puja-trivedi or @djarecka.

## Add a schema

- **Website:** the *Ingest* tab of [sensein.group/NeuroGhost](https://sensein.group/NeuroGhost/)
  — LinkML or JSON Schema, plus optional metadata. It opens an issue; a
  workflow validates the schema and opens the PR.
- **Claude Code:** the [`ingest-schema`](.claude/skills/ingest-schema/SKILL.md)
  skill — also for Pydantic models, spreadsheets/data dictionaries, large
  schemas, and schemas that import others.
- **By hand:** add `registry_schemas/<name>.yml` (LinkML) and, optionally,
  `registry_schemas/<name>_source.yaml` with its metadata (see
  `neuro_ghost/source_metadata.py`), then open a PR. Check it first:
  ```bash
  python neuro_ghost/validate_schema.py registry_schemas/<name>.yml
  python scripts/check_duplicate_schema.py registry_schemas/<name>.yml
  python neuro_ghost/preview_schema.py registry_schemas/<name>.yml
  ```

The registry label is the schema's LinkML `name:`. Add it to the schema
dropdowns in `.github/workflows/propose_mappings.yml` so it can be mapped.

## Add or review mappings

See [`mappings/README.md`](mappings/README.md). In short: the *Propose
Mappings* workflow (free embedding model, all rows `PROPOSED`), the
[`propose-mappings`](.claude/skills/propose-mappings/SKILL.md) skill (your own
model, you approve each row; also reviews existing files), or edit a mapping
set by hand. To review, set `review_status` and your login as `reviewer_id`.

## Change the code or the website

```bash
pip install -r requirements.txt
pytest                                                    # tests
python neuro_ghost/pipeline.py --fresh --skip-converters  # full local rebuild (~5 min)
python -m http.server 8000                                # website at http://localhost:8000
```

- **Website:** `index.html` is the whole site (one file). Test it served
  locally with real data, and click through the tabs you touched.
- **Meta-model:** after editing `meta_model.yaml`, regenerate and commit
  `./scripts/gen_models.sh` (and `python scripts/gen_metamodel_json.py`); CI
  checks both are in sync.
- **Workflows:** check `.github/workflows/*.yml` with
  [actionlint](https://github.com/rhysd/actionlint).
- **Don't commit `data/`** from a local rebuild — it's regenerated after merge.

## Report a problem or suggest a schema

[Open an issue](https://github.com/sensein/NeuroGhost/issues/new).
