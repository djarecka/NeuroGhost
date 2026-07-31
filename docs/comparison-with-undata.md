# NeuroGhost vs undata

Both tackle the same core problem — neuroscience data standards (BIDS, NWB,
DANDI, openMINDS, AIND, ...) each redefine the same concepts under different
names, and there's no machine-readable way to know two things are "the same".
undata (`/Users/dorota/repronim_various/undata`) is a much larger, production-
platform take on this; NeuroGhost deliberately borrows its core identity idea
and leaves the rest out. This is a quick reference for what's shared and what
isn't, and why.

## Adopted from undata

| Idea | undata | NeuroGhost |
|---|---|---|
| Content-addressed identity | `sha256` hash from semantic content, two-mode (ontology-anchored / structural fallback) | Same principle, **single mode only** — structural content hash (`name`/`description`/`range`/`units`/etc.), no ontology-anchored mode (see below) |
| Identity ≠ provenance | `ProvenanceEntry` list per entity, accumulates across sources | Same — `ProvenanceEntry` list, same idea, thinner field set (see below) |
| LinkML as intermediate representation | Every adapter emits a `SchemaDefinition`; one standard extractor classifies | Every converter emits LinkML YAML; `parse_linkml()`/`build_registry_entities()` does the extraction+hashing |
| PROV-O–grounded provenance fields | `generated_at`, `attributed_to`, `activity`, `derived_from` | Same four fields, same PROV-O predicates (`slot_uri: prov:...`) |

## Deliberately not adopted

| undata has | NeuroGhost's choice | Why |
|---|---|---|
| Two-mode hashing (ontology-anchored vs structural) | Structural only | Explicit decision: no ontology store, no ontology-anchored identity, for now |
| Align **before** Commit (alignment can inform/merge the hash) | Align **after** Commit (`align.py` runs post-ingestion) | No complex alignment exists yet — pure hash equality already handles exact duplicates; align-before-commit only matters once alignment can detect and merge *near*-duplicates |
| Knowledge service (13+ ontologies, embeddings, LLM verification, multi-precision SKOS) | `SkosMapping` model field exists but isn't wired into ingestion at all | Same reason as above — no ontology grounding in scope |
| `StorageBackend` protocol (pluggable file/Postgres backends) | One embedded LadybugDB file, no abstraction | NeuroGhost is a single-file registry driven by a GitHub Action, not a multi-user service |
| Task manager, GraphQL API, OIDC auth, curator roles, staged→curated lifecycle | None of it | All production-platform machinery for a hosted, multi-user service; out of scope |
| `ProvenanceEntry.class`/`name` (which source-schema class/slot this came from) and `source_ref` (repo/commit/file/checksum) | Considered, then dropped — see `docs/ingestion.md`'s note on `source_class`/`source_slot` | Redundant with graph structure (`HAS_PROPERTY` edges) or not yet needed |

## Where NeuroGhost has gone further

**`Rule`** (usage constraints — `required`/`multivalued`/`pattern`/min/max —
as their own content-addressed entity, referencing the `RegistryProperty` via
`applies_to`) isn't something undata's VISION.md describes as a distinct
entity type. It falls out of the same "identity ≠ usage" principle undata
established for provenance, just applied one level further: a property's
*core meaning* is separate not only from *where it came from* but also from
*how a given source happens to use it*. See `docs/ingestion.md`'s
[Rule section](ingestion.md#rule-usage-constraints-as-their-own-entity).

## Entity type mapping

| undata | NeuroGhost | Status |
|---|---|---|
| `Element` | `RegistryProperty` | Built |
| `Schema` | `RegistryClass` | Built |
| — | `Rule` | Built (NeuroGhost-specific, see above) |
| `Value` / `ValueSet` | `ValueSet` | Stub only |
| `Transform` | `Transform` | Stub only |
| `OntologyAnnotation` (multi-precision SKOS) | `SkosMapping` | Modeled, not wired into ingestion |
