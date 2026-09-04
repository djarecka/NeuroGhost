<h1 align='center'>NeuroGhost</p>

<h3 align='center'>A shared vocabulary for neuroscience data</h3>

<p align='center'><img width="500" height="500" alt="image" src="https://github.com/user-attachments/assets/e70a2916-acea-44bf-9f23-537f290d6f92" /></p>

---

**NeuroGhost** is a public catalog of neuroscience vocabularies. Labs publish their [LinkML](https://linkml.io/) schema; the registry compares it to every other schema and surfaces which terms mean the same thing across projects.

**Distance score** — 0.0 = identical, 1.0 = unrelated. Computed via the Proteus pipeline: name similarity, token Jaccard, alias overlap, definition embeddings, IRI anchor, and unit dimensional veto. Adjustable live on the Concepts page.

---

## By the Numbers

| Stat | Value |
|------|-------|
| Schemas registered | **7** — aind · bids · nwb · bbqs · dandi · openminds · personinfo |
| Classes catalogued | **671** across all schemas |
| Properties indexed | **~3,800** content-addressed nodes |
| Alignment edges | **56** across 28 classes · mean distance **0.17** |
| Alignment methods | IRI anchor 77% · semantic-name 14% · composite 9% |
| Confidence floor | **0.45** — pairs below this threshold are dropped |
| `skos:exactMatch` threshold | **0.95** — IRI anchor + unit compatibility required |

---

## Adding a schema

1. Write a LinkML `.yml` file (copy `registry_schemas/bbqs.yml` as a template).
2. Go to the [Register tab](https://sensein.group/NeuroGhost/), paste your YAML, click **Open GitHub Issue**.
3. A GitHub Action validates, ingests, aligns, and archives it within minutes.

No installation, no pull request, no reviewers required.

---

## Running locally

```bash
git clone https://github.com/sensein/NeuroGhost.git
cd NeuroGhost
pip install -r requirements.txt
```

```bash
python neuro_ghost/pipeline.py --fresh                              # full rebuild
python neuro_ghost/pipeline.py --fresh --skip-converters            # local schemas only
python neuro_ghost/pipeline.py --skip-converters --schemas registry_schemas/bbqs.yml  # one schema
```

Options: `--fresh` (wipe DB), `--skip-converters` (skip BIDS/NWB/DANDI/openMINDS/AIND fetch), `--schemas FILE`, `--bump major|minor|patch`, `--agent TEXT`.

Open `index.html` in a browser when done.

To inspect or ingest a single schema without running the full pipeline, use `ingest.py` — it accepts **LinkML (`.yml`)** or **JSON Schema (`.json`)** (JSON is converted to LinkML first):

```bash
python neuro_ghost/ingest.py --dry-run --verbose registry_schemas/bbqs.yml
python neuro_ghost/ingest.py --dry-run --verbose dandiset.json   # JSON Schema
```

`--dry-run` parses and reports counts without writing to the DB; `--verbose` additionally prints every `RegistryClass`/`RegistryProperty`/`RegistryValueSet`/`RegistryRule`/`ProvenanceEntry` that would be created, exactly as stored (id references shown as raw UUIDs). `--verbose-readable` is the same but resolves those id references to names for easier reading. Format is chosen by extension; override a misnamed file with `--format linkml|json`.

(`ingest_linkml.py` is the LinkML-only ingester underneath; `ingest.py` is the format-aware wrapper.)

---

## Stack

- **[LadybugDB](https://ladybugdb.com/)** — embedded graph DB, no server
- **[LinkML](https://linkml.io/)** — schema format
- **[sentence-transformers](https://sbert.net/)** — `all-MiniLM-L6-v2` for semantic distance
- **Static HTML + GitHub Pages** — one-file frontend, no framework
- **GitHub Actions** — CI/CD on every schema submission

---


## Contributing

- Register a schema via the [Register tab](https://sensein.group/NeuroGhost/).
- [Open an issue](https://github.com/sensein/NeuroGhost/issues/new) to report bugs or suggest features.
- PRs welcome, especially around the distance function.

**License:** CC0-1.0 — public domain.
