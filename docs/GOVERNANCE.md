# NeuroGhost Ecosystem Governance

> **Status: Provisional** — This document tracks the satellite modules that
> feed into or extend the NeuroGhost registry. It is a living spec; entries
> are added as modules are formally onboarded.
> **The page needs updates!**

---

## Overview

NeuroGhost core (`sensein/NeuroGhost`) is the central registry and MCP server.
Around it sit independently maintained **satellite modules** — separate
repositories owned by their respective teams — that contribute schemas,
alignment pipelines, or tooling back into the core.

Each satellite module is self-governing: it sets its own release cadence,
internal review process, and roadmap. Integration into NeuroGhost core
happens exclusively through pull requests, and every such PR requires
**exactly one approval from the designated NeuroGhost approver** for that
module before merging.

```
 ┌──────────────────────────────────────────────────┐
 │                 sensein/NeuroGhost               │
 │                    (core registry)               │
 └────────────┬─────────────────────────────────────┘
              │                    │
       PR approval           PR approval
              │                    │
   ┌──────────▼──────┐   ┌────────▼────────────┐
   │    Proteus      │   │   search_hybrid      │
   │ (neurovium)     │   │  (sensein)           │
   └─────────────────┘   └──────────────────────┘
```

---

## Satellite Module Registry

| Module | Repository | Maintainer | Focus | Status | NeuroGhost Approver |
|--------|-----------|------------|-------|--------|---------------------|
| **Proteus** | [neurovium/Proteus](https://github.com/neurovium/Proteus) | @neurovium (Nema) | Cross-schema alignment pipeline | Provisional | @Sulstice |
| **search_hybrid** | [sensein/search_hybrid](https://github.com/sensein/search_hybrid) | @sensein | Hybrid search & retrieval tooling | Provisional | @Sulstice |

> **Provisional** means the module is tracked here but has no formal SLA yet.
> **Active** means the module has merged at least one PR into core and follows
> this spec. **Archived** means the module is no longer maintained.

---

## Contribution Workflow

### From a satellite module into NeuroGhost core

1. **Work happens in the satellite repo.** The module team develops, tests,
   and reviews changes internally before proposing them to core.

2. **Open a PR against `sensein/NeuroGhost` `main`.** The PR description must
   identify which satellite module it comes from and link the corresponding
   work in the satellite repo.

3. **One approval required.** The designated NeuroGhost approver for that
   module reviews and approves the PR. No other approvals are required, but
   any NeuroGhost maintainer may comment.

4. **CI must pass.** All existing tests and (where applicable) the schema
   validation workflow must be green before merging. The registry rebuild runs
   *after* merge (see [Registry data and automation](#registry-data-and-automation)),
   so PRs should not include regenerated `data/` files.

5. **Squash or merge — no rebases onto main.** The merge method is merge
   commit so the satellite module's authorship is visible in `git log`.

### Reverting satellite contributions

If a satellite PR is merged prematurely or introduces a regression, any
NeuroGhost core maintainer may open a revert PR without waiting for the
satellite module's approval. The revert is merged as soon as one core
maintainer approves it.

---

## Registry data and automation

Schemas and registry data change only through pull requests to `main`, plus
one automatic rebuild commit after each merge. Three GitHub Actions workflows
are involved, and they are kept separate on purpose:

| Workflow | Trigger | What it does | Output |
|----------|---------|--------------|--------|
| **Schema Submission** (`schema_submission.yml`) | an issue titled `schema-submission: <name>` (the website's Ingest tab, or the issue form) | validates the schema and checks that the full registry still builds with it | a PR with only `registry_schemas/<name>.yml` (+ its `_source.yaml` sidecar) |
| **Fetch External Schemas** (`fetch_external_schemas.yml`) | manual only | downloads the latest upstream schemas (BIDS, NWB, AIND, openMINDS, BBQS) with `neuro_ghost/converters/run_all.py` | a PR with the updated `registry_schemas/*.yml` |
| **Rebuild & Publish Registry** (`publish_registry.yml`) | push to `main` touching `registry_schemas/`, `meta_model.yaml`, `neuro_ghost/` or `requirements.txt`; or manual | rebuilds the registry from the schemas on `main` (`pipeline.py --fresh --skip-converters`); never downloads anything | a `chore(registry): rebuild vX.Y.Z` commit to `main` with `data/` |

Rules that follow from this:

- **Every schema change is reviewed before it lands.** That includes upstream
  updates: a fetch PR shows exactly what changed in each external schema, and a
  maintainer decides whether to merge it.
- **`data/` is generated, never edited by hand.** `data/registry.json`,
  `data/provenance.json` and `data/versions/` are written only by the rebuild
  workflow. PRs, including hand-edits to `registry_schemas/`, carry the
  schema or code change only.
- **External schemas are not fetched automatically** for now. Whether to
  schedule the fetch, and how often, is tracked in
  [#118](https://github.com/sensein/NeuroGhost/issues/118).

---

## Adding a New Satellite Module

To register a new module:

1. Open a PR that adds a row to the table above with the module name,
   repository URL, maintainer GitHub username, and a one-line focus summary.
2. Set `Status` to **Provisional**.
3. Designate a NeuroGhost approver (defaults to `@Sulstice`).
4. The PR is merged by any NeuroGhost core maintainer.

---

## Core Maintainers

| Name | GitHub | Role |
|------|--------|------|
| Suliman | @Sulstice | Lead maintainer, final approver |
| Puja Trivedi | @puja-trivedi | Core contributor; meta-model moderator |
| Dorota Jarecka | @djarecka | Meta-model moderator |

### Meta-model Moderation

Changes to `meta_model.yaml` and `schema_registry_utils/` require
approval from at least one **meta-model moderator** before merging:

| Moderator | GitHub |
|-----------|--------|
| Puja Trivedi | @puja-trivedi |
| Dorota Jarecka | @djarecka |

This covers any PR that modifies the LinkML meta-model schema, the generated
Pydantic models, the hashing logic, or the graph DDL derived from the
meta-model.

---

## Updating This Document

This document lives at `docs/GOVERNANCE.md`. Changes to the satellite module
table or approver assignments require a PR approved by `@Sulstice`.
