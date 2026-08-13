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

## Roadmap

**MVP (Sep 29):** BBQS and DANDI aligned, transform API live, users can sign up. Full public launch with BrainKB on Oct 23.

| # | Date | Milestone | Owners | Issue |
|---|------|-----------|--------|-------|
| M1 | Aug 28 | Foundation — modules, meta-model v1, BICAN ingested, cloud deploy | @neurovium · @puja-trivedi · @djarecka · @Sulstice | [#56](https://github.com/sensein/NeuroGhost/issues/56) |
| M2 | Sep 11 | Alignment consolidated, DANDI ingested, schema strategy | @neurovium · @djarecka · @Sulstice | [#57](https://github.com/sensein/NeuroGhost/issues/57) |
| M3 | Sep 29 | **MVP soft launch** — users can sign up | @Sulstice + team | [#58](https://github.com/sensein/NeuroGhost/issues/58) |
| M4 | Oct 23 | Full public launch with BrainKB | @Sulstice + team | [#59](https://github.com/sensein/NeuroGhost/issues/59) |

---

## Website

**[sensein.group/NeuroGhost](https://sensein.group/NeuroGhost/)** — seven tabs: **Concepts**, **Diff**, **Graph Schema**, **Transform**, **Query**, **Provenance**, **Register**. Every view has download buttons.

---

## Adding a schema

1. Write a LinkML `.yml` file (copy `schemas/bbqs.yml` as a template).
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
python neuro_ghost/pipeline.py --skip-converters --schemas schemas/bbqs.yml  # one schema
```

Options: `--fresh` (wipe DB), `--skip-converters` (skip BIDS/NWB/DANDI/openMINDS/AIND fetch), `--schemas FILE`, `--bump major|minor|patch`, `--agent TEXT`.

Open `index.html` in a browser when done.

---

## Stack

- **[LadybugDB](https://ladybugdb.com/)** — embedded graph DB, no server
- **[LinkML](https://linkml.io/)** — schema format
- **[sentence-transformers](https://sbert.net/)** — `all-MiniLM-L6-v2` for semantic distance
- **Static HTML + GitHub Pages** — one-file frontend, no framework
- **GitHub Actions** — CI/CD on every schema submission

---

## Satellite Modules

NeuroGhost core is extended by independently maintained satellite modules.
Each module lives in its own repository and contributes back via pull
requests; every PR from a satellite module requires one approval from the
designated NeuroGhost approver before merging.
See [docs/GOVERNANCE.md](docs/GOVERNANCE.md) for the full spec.

### Module sync status

> **Proteus**: commits ahead of the version pinned into `neuro_ghost/align.py` (see `.proteus-pin`).
> **search_hybrid**: commits behind `sensein/NeuroGhost` main.
> Updated automatically by CI on every push to main.

<!-- MODULE_SYNC_START -->
| Module | Maintainer | Repository | Behind main | Compare |
|--------|-----------|------------|-------------|---------|
| Proteus | @neurovium (Nema) | [neurovium/Proteus](https://github.com/neurovium/Proteus) | ⚠ pin unset | [compare ↗](https://github.com/neurovium/Proteus/commits/main) |
| Dorada | @djarecka | [djarecka/NeuroGhost](https://github.com/djarecka/NeuroGhost) | 36 commits | [compare ↗](https://github.com/sensein/NeuroGhost/compare/main...djarecka:NeuroGhost:main) |
<!-- MODULE_SYNC_END -->

---

## Contributing

- Register a schema via the [Register tab](https://sensein.group/NeuroGhost/).
- [Open an issue](https://github.com/sensein/NeuroGhost/issues/new) to report bugs or suggest features.
- PRs welcome, especially around the distance function.

**License:** CC0-1.0 — public domain.
