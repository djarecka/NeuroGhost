<h1 align='center'>NeuroGhost</h1>

<h3 align='center'>A shared vocabulary for neuroscience data</h3>

<p align='center'><img width="500" height="500" alt="image" src="https://github.com/user-attachments/assets/e70a2916-acea-44bf-9f23-537f290d6f92" /></p>

---

**NeuroGhost** is an open registry of neuroscience data schemas. It brings the classes and properties of many schemas together in one place, shows where they share definitions, and records reviewed **mappings** between terms that mean the same (or related) things across projects.

Registered today: **AIND, BIDS, NWB, DANDI** (asset + dandiset), **openMINDS, BBQS, BICAN** (anatomical structures), **personinfo** and a slice of **schema.org** — see the **Sources** tab on the [website](https://sensein.group/NeuroGhost/).

> **Status: 0.1.0, alpha.** The registry, its identifiers and its workflows still change as the project grows.

---

## Browse — [sensein.group/NeuroGhost](https://sensein.group/NeuroGhost/)

- **Concepts** — every class and property, filterable by schema. For a property: each class that uses it, with the **rules** in effect there (range, required, pattern, unit; class-specific ones highlighted). For any entity: its stable **id**, its content **hash**, its **mappings** (status, method, who proposed and reviewed them) and what is **mapped from** other schemas — click either end to jump to it.
- **Diff** — compare two schemas class by class. **Query** — free-text search. **Graph Schema** — classes and how they connect.
- **Transform** — map one class's fields onto another's. **Compose** — pick classes and properties to export your own LinkML schema.
- **Sources** — the registered schemas, grouped into bundles (e.g. `dandi` = asset + dandiset). **Meta-model** — the registry's own data model.

---

## Add a schema

**From the website** — the **Ingest** tab: drop a **LinkML** (`.yml`) or **JSON Schema** (`.json`) file, add the optional metadata (bundle, homepage, publisher, …) and click **Open ingestion issue**. A GitHub Action validates it, checks the registry still builds, and opens a **pull request**; once a maintainer merges it, the registry rebuilds with the new schema.

**With an AI assistant** (Claude Code, in a clone of this repo) — ask, e.g., *"add my lab's schema"*. The [`ingest-schema`](.claude/skills/ingest-schema/SKILL.md) skill:
- takes LinkML, JSON Schema, Pydantic models, or a looser description (spreadsheet, data dictionary) that it drafts into LinkML with you;
- runs the same checks as the workflow, and **previews** what the schema adds — what's already in the registry (and will be shared), what shares a name but differs, what's new, what lacks descriptions (`python neuro_ghost/preview_schema.py <schema>`);
- handles schemas that **import** others (it pins them with an `imports_source` annotation — see BICAN's in `registry_schemas/`) and the **bundle** they belong to;
- opens the PR for you, after asking. Use it for large schemas, which the website can't send.

---

## Map terms across schemas

Mappings live in [`mappings/`](mappings/README.md) as **mapping sets** — an SSSOM-style table (`<set>.sssom.tsv`, which GitHub shows as a table) plus its metadata (`<set>.sssom.yml`). Each row is one mapping, e.g. `dandiset:Dandiset  skos:closeMatch  schema.org:Dataset`, with a status: `PROPOSED`, `ACCEPTED`, `REJECTED` (kept as "not a match") or `SUPERSEDED`.

- **Free model, in CI** — Actions → **Propose Mappings** → pick a subject and an object schema (either can be *all*) and properties, classes or *all*. It opens a PR where every row is `PROPOSED`, scored by a local embedding model.
- **Your own model** — the [`propose-mappings`](.claude/skills/propose-mappings/SKILL.md) skill: your model judges candidates, **you approve each row**, and it opens a PR containing only what you approved, under your GitHub login. Its **review mode** does the same for an existing file, e.g. a *Propose Mappings* PR.
- **By hand** — edit a file and open a PR (`python neuro_ghost/mappings.py validate mappings/<file>` checks it).

To **review** proposed mappings, set a row's `review_status` to `ACCEPTED` / `REJECTED` and `reviewer_id` to your GitHub login. The **Mapping Check** on the PR verifies the file, that every reference exists, and that each new review was made by an author of the PR. Merging rebuilds the registry, and the mappings appear on the website.

---

## Upstream updates

External schemas (BIDS, NWB, AIND, openMINDS, BBQS) are **not** updated automatically. Actions → **Fetch External Schemas** downloads the latest versions and opens a PR with the changed schema files, for review ([#118](https://github.com/sensein/NeuroGhost/issues/118) tracks whether to schedule it).

---

## Use it from tools

- **Data** — the whole registry is open JSON: [`data/registry.json`](data/registry.json) (classes, properties with their per-class rules, mappings, sources, bundles), with every past version in `data/versions/` and a changelog in `data/provenance.json`.
- **MCP server** — lets an AI assistant (Claude, Cursor, …) search classes, read alignments, diff schemas and translate records: `python neuro_ghost/mcp_server.py` (stdio), or `MCP_TRANSPORT=sse` for HTTP. Configuration example in the module's docstring.

---

## How it works

- **One schema file per source** in [`registry_schemas/`](registry_schemas/), optionally with a `<name>_source.yaml` of metadata (bundle, homepage, version, …). JSON Schema is converted to LinkML; property names stay as the source wrote them.
- **Identity by content.** Every class and property gets a content **hash** (from its name, description and the hashes of what it references) and a stable **id** (a UUID kept across rebuilds). Identical content from two schemas is **one** entity, attested by both; changed content is a new entity. A property that means different things in different classes stays separate even when the name is shared.
- **Rules** (range, required, pattern, min/max, unit) are separate from identity, and scoped to a class where classes constrain a shared property differently.
- **Rebuild after merge.** Every merge that touches schemas, mappings or code triggers a rebuild that regenerates `data/` and publishes the website. Nothing downloads external schemas on its own.

More detail: [`docs/ingestion.md`](docs/ingestion.md), [`docs/model.md`](docs/model.md), [`mappings/README.md`](mappings/README.md).

---

## Running locally

```bash
git clone https://github.com/sensein/NeuroGhost.git
cd NeuroGhost
pip install -r requirements.txt
python neuro_ghost/pipeline.py --fresh --skip-converters   # rebuild the registry from registry_schemas/ (+ mappings/)
python -m http.server 8000                                 # then open http://localhost:8000
```

`pipeline.py` options: `--fresh` (start from an empty graph), `--skip-converters` (don't download external schemas), `--schemas FILE`, `--bump major|minor|patch`, `--agent TEXT`.

Inspect a single schema without rebuilding — `ingest.py` takes LinkML or JSON Schema:

```bash
python neuro_ghost/ingest.py --dry-run --verbose-readable registry_schemas/bbqs.yml
python neuro_ghost/preview_schema.py registry_schemas/bbqs.yml     # what it shares with the registry
```

Propose mappings locally (needs `pip install sentence-transformers`, which isn't in `requirements.txt`):

```bash
python neuro_ghost/propose_mappings.py aind bids --kind classes    # writes mappings/<set>.sssom.tsv + .yml
```

Tests: `pytest`.

**Stack:** [LinkML](https://linkml.io/) (schemas), [LadybugDB](https://ladybugdb.com/) (embedded graph DB used during the build), a static one-file website on GitHub Pages, GitHub Actions for submissions, rebuilds and mapping proposals, and [sentence-transformers](https://sbert.net/) (`all-MiniLM-L6-v2`) for proposing mappings.

---

## Contributing

Schemas, mappings and code all change through **reviewed pull requests**; `data/` is generated by the rebuild after each merge, never edited by hand. See **[CONTRIBUTING.md](CONTRIBUTING.md)** for how to add a schema or mappings, review mappings, and work on the code — and [open an issue](https://github.com/sensein/NeuroGhost/issues/new) to report a bug or suggest a schema.

**License:** CC0-1.0 — public domain.
