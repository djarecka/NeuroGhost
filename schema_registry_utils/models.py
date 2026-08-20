# ---------------------------------------------------------------------------
# GENERATED FILE — DO NOT EDIT BY HAND.
#
# Produced by ./scripts/gen_models.sh from schemas/meta_model.yaml.
# Edit the schema and regenerate; hand edits are overwritten by
# .github/workflows/gen_models.yml on the next schema change.
# ---------------------------------------------------------------------------
from __future__ import annotations

import re
import sys
from datetime import (
    date,
    datetime,
    time
)
from decimal import Decimal
from enum import Enum
from typing import (
    Any,
    ClassVar,
    Literal,
    Optional,
    Union
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer
)


metamodel_version = "1.11.0"
version = "None"


class ConfiguredBaseModel(BaseModel):
    model_config = ConfigDict(
        serialize_by_alias = True,
        validate_by_name = True,
        validate_assignment = True,
        validate_default = True,
        extra = "forbid",
        arbitrary_types_allowed = True,
        use_enum_values = True,
        strict = False,
    )





class LinkMLMeta(RootModel):
    root: dict[str, Any] = {}
    model_config = ConfigDict(frozen=True)

    def __getattr__(self, key:str):
        return getattr(self.root, key)

    def __getitem__(self, key:str):
        return self.root[key]

    def __setitem__(self, key:str, value):
        self.root[key] = value

    def __contains__(self, key:str) -> bool:
        return key in self.root


linkml_meta = LinkMLMeta({'default_prefix': 'screg',
     'default_range': 'string',
     'description': 'Meta-model for the schema registry: defines the registered '
                    'object types (RegistryClass, RegistryProperty, and related '
                    'support classes) used to describe classes and data elements '
                    'that can be registered, versioned, related to each other, and '
                    'compared for similarity. NOTE: `id` above is a placeholder '
                    'namespace — replace before publishing.',
     'id': 'https://example.org/schema-registry-utils/meta-model',
     'imports': ['linkml:types'],
     'name': 'schema_registry_meta_model',
     'prefixes': {'linkml': {'prefix_prefix': 'linkml',
                             'prefix_reference': 'https://w3id.org/linkml/'},
                  'owl': {'prefix_prefix': 'owl',
                          'prefix_reference': 'http://www.w3.org/2002/07/owl#'},
                  'prov': {'prefix_prefix': 'prov',
                           'prefix_reference': 'http://www.w3.org/ns/prov#'},
                  'qudt': {'prefix_prefix': 'qudt',
                           'prefix_reference': 'http://qudt.org/schema/qudt/'},
                  'rdfs': {'prefix_prefix': 'rdfs',
                           'prefix_reference': 'http://www.w3.org/2000/01/rdf-schema#'},
                  'screg': {'prefix_prefix': 'screg',
                            'prefix_reference': 'https://example.org/schema-registry-utils/'},
                  'skos': {'prefix_prefix': 'skos',
                           'prefix_reference': 'http://www.w3.org/2004/02/skos/core#'}},
     'source_file': 'schemas/meta_model.yaml',
     'subsets': {'HashSubset': {'description': 'Slots that are part of a '
                                               "RegistryEntity subclass's content "
                                               'hash (hash_id). '
                                               'schema_registry_utils/hashing.py '
                                               'derives the identity field set '
                                               "from each field's in_subset "
                                               'metadata.',
                                'from_schema': 'https://example.org/schema-registry-utils/meta-model',
                                'name': 'HashSubset'}}} )

class SkosMappingTypeEnum(str, Enum):
    """
    The kind of SKOS mapping relation between a registry entity and an external concept.
    """
    EXACT_MATCH = "EXACT_MATCH"
    """
    The registry entity is equivalent to the external concept.
    """
    CLOSE_MATCH = "CLOSE_MATCH"
    """
    The registry entity is sufficiently similar to the external concept.
    """
    BROAD_MATCH = "BROAD_MATCH"
    """
    The external concept is broader than the registry entity.
    """
    NARROW_MATCH = "NARROW_MATCH"
    """
    The external concept is narrower than the registry entity.
    """
    RELATED_MATCH = "RELATED_MATCH"
    """
    The registry entity is related to the external concept.
    """
    EQUIVALENT_CLASS = "EQUIVALENT_CLASS"
    """
    Strict logical equivalence. Exclusively human-issued and used sparingly: it is the one predicate the alignment pipeline's reasoner-based repair pass may treat as OWL equivalence, so it must never be machine-assigned.
    """


class ReviewStatusEnum(str, Enum):
    """
    Curation lifecycle of a Mapping.
    """
    PROPOSED = "PROPOSED"
    """
    Machine- or human-proposed; not yet reviewed.
    """
    ACCEPTED = "ACCEPTED"
    """
    Validated by a reviewer; safe for high-rigor queries.
    """
    REJECTED = "REJECTED"
    """
    Reviewed and refuted; retained as negative evidence.
    """
    SUPERSEDED = "SUPERSEDED"
    """
    Replaced by a newer mapping.
    """


class RuleTypeEnum(str, Enum):
    """
    The kind of constraint a Rule expresses. Each value indicates which of Rule's typed parameter slots should be populated (see Rule and rule_type for the mapping). The declarative types (PATTERN through ENUM_MEMBERSHIP) cover the field-level constraints source schemas state directly (dandi-schema `Field(...)` args, LinkML slot facets, JSON Schema keywords); EXPRESSION is the escape hatch for class-level or imperative rules preserved verbatim (dandi-schema `@model_validator`, JSON Schema `if/then/else`, SHACL shapes).
    """
    PATTERN = "PATTERN"
    """
    Value must match a regex (`pattern` slot). dandi-schema's `Field(pattern=NAME_PATTERN)`, LinkML's `pattern:` facet.
    """
    VALUE_RANGE = "VALUE_RANGE"
    """
    Numeric value must lie within [min_value, max_value], with exclusive_minimum/exclusive_maximum flags controlling inclusivity. Populates min_value/max_value and, when set, the exclusive_* flags.
    """
    LENGTH_RANGE = "LENGTH_RANGE"
    """
    String length must lie within [min_length, max_length]. dandi-schema's `Field(max_length=10000)` on `description`.
    """
    CARDINALITY = "CARDINALITY"
    """
    Multivalued property's item count must lie within [min_cardinality, max_cardinality]. Distinct from LENGTH_RANGE so a Rule bounding a list's size and a Rule bounding a string field's characters never accidentally hash the same.
    """
    REQUIRED = "REQUIRED"
    """
    Property must be present. is_required carries the boolean (true asserts required; false explicitly asserts optional, which some sources state).
    """
    MULTIVALUED = "MULTIVALUED"
    """
    Property may (is_multivalued=true) or may not (is_multivalued=false) carry multiple values.
    """
    ENUM_MEMBERSHIP = "ENUM_MEMBERSHIP"
    """
    Value must be drawn from a ValueSet (`allowed_value_set`). Distinct from setting property_range to a ValueSet — that is a type declaration; this is the enforceable check.
    """
    EXPRESSION = "EXPRESSION"
    """
    Constraint expressed as free-form text in a specified language (`expression` + `expression_language`) — used for rules the registry ingested but cannot decompose into the typed parameter slots above (imperative validators, conditional cross-field logic, SHACL/ShEx shapes).
    """


class RuleSeverityEnum(str, Enum):
    """
    How a Rule failure is to be reported by a downstream validator. Mirrors SHACL's sh:severity levels; a source schema that does not state a severity ingests as ERROR (see Rule.severity ifabsent).
    """
    ERROR = "ERROR"
    """
    Failure is a hard violation.
    """
    WARNING = "WARNING"
    """
    Failure is a recommendation the source encodes but does not hard-fail on.
    """
    INFO = "INFO"
    """
    Failure is advisory only — a hint, not a defect.
    """


class RuleExpressionLanguageEnum(str, Enum):
    """
    Formalism used by a Rule's `expression` string. Named so a downstream tool can dispatch on the value (or refuse to execute what it does not understand); two rules with identical expression text but different languages are different Rules.
    """
    SHACL = "SHACL"
    """
    W3C SHACL shape (Turtle or JSON-LD).
    """
    SHEX = "SHEX"
    """
    ShEx shape expression.
    """
    JSON_SCHEMA = "JSON_SCHEMA"
    """
    JSON Schema fragment — typically the `if/then/else` or `allOf`/`anyOf`/`oneOf` composition that could not be expressed as a declarative rule_type.
    """
    SPARQL_ASK = "SPARQL_ASK"
    """
    SPARQL ASK query — the constraint holds iff the query returns true.
    """
    PYTHON = "PYTHON"
    """
    Python source (dandi-schema's `@model_validator` bodies, Pydantic `@field_validator` bodies). Preserved for record only — the registry does not execute these.
    """
    LINKML_RULES = "LINKML_RULES"
    """
    A LinkML `rules:` block (preconditions/postconditions expressed in LinkML's own rule language).
    """
    PLAIN_TEXT = "PLAIN_TEXT"
    """
    Natural-language description — the source stated a constraint prose-only, with no machine-checkable form.
    """



class RegistryEntity(ConfiguredBaseModel):
    """
    Common base for content-addressed, provenance-tracked objects registered in the schema registry. Identity (hash_id) is derived from content, so there is no separate version slot: a change produces a new hash_id, with lineage tracked via derived_from on each ProvenanceEntry.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'abstract': True,
         'from_schema': 'https://example.org/schema-registry-utils/meta-model'})

    hash_id: str = Field(default=..., description="""Content-hash-derived identifier (format sha256:<hex>). A change in any identity-defining field produces a new hash_id; lineage is preserved via derived_from.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity', 'Transform']} })
    name: str = Field(default=..., description="""Human-readable label for this entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity', 'Transform'], 'in_subset': ['HashSubset']} })
    description: str = Field(default=..., description="""Human-readable description of this entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity', 'Transform'],
         'in_subset': ['HashSubset'],
         'slot_uri': 'skos:definition'} })
    provenance: list[ProvenanceEntry] = Field(default=..., description="""One ProvenanceEntry per source attesting to this entity. Accumulates as more sources are ingested — never affects hash_id.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity', 'Mapping']} })
    skos_mappings: Optional[list[Mapping]] = Field(default=None, description="""Semantic mappings to external vocabulary concepts, or to other registry entities (align.py's computed correspondences). Storage is embedded (the owning entity is the implicit subject); SSSOM export materializes subject_id from the owning entity's hash_id, so exported mapping sets are standalone, standards-conformant records.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity']} })
    aliases: Optional[list[str]] = Field(default=None, description="""Alternate names/synonyms/abbreviations for this entity (e.g. \"lfp\" for \"local field potential\"), preserved from the source schema. Used as alignment evidence (align.py's alias_overlap signal) — not part of the schema's own semantics.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity'], 'slot_uri': 'skos:altLabel'} })
    concept_uri: Optional[str] = Field(default=None, description="""Ontology IRI for this entity (class or property), preserved from the source schema on ingestion. Not part of the content hash; used for alignment and cross-source lookup.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity']} })
    source_native_id: Optional[str] = Field(default=None, description="""The verbatim identifier of this element in its source schema (the raw column/field/key name, e.g. \"z_spec\", \"sub-01\"), preserved exactly as written. Alignment's lexical channel matches on this — `name` alone loses the source's own spelling, abbreviations and casing, which is often the strongest cheap signal. Optional; not part of the content hash.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity']} })


class RegistryClass(RegistryEntity):
    """
    A registered class (object class) representing a concept or entity type in the registry, e.g. \"Patient\".
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://example.org/schema-registry-utils/meta-model'})

    defined_in_schema: str = Field(default=..., description="""The SchemaSource this class/property belongs to (stored as id FK, like had_primary_source). IN the hash — this is the mechanical form of \"users add a new class, and the mapping between them is added\": identical content in two schemas is two entities, and their correspondence is always an explicit Mapping record that can be proposed, reviewed, rejected, and exported. Nothing is ever implicitly identified across sources, so nothing disappears from the alignment problem without a record. Deliberately the schema, not a version: content unchanged across versions of one schema keeps its hash_id, so existing mappings survive re-ingestion. Attached to RegistryClass and RegistryProperty only — the entities alignment compares; PermissibleValue keeps its cross-source sharing semantics unchanged.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryClass', 'RegistryProperty', 'Rule'],
         'in_subset': ['HashSubset']} })
    properties: Optional[list[str]] = Field(default=None, description="""The set of properties that belong to this class.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryClass'], 'in_subset': ['HashSubset']} })
    parent_class: Optional[str] = Field(default=None, description="""The class this class inherits from (stored as hash_id FK).""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryClass'],
         'in_subset': ['HashSubset'],
         'slot_uri': 'linkml:is_a'} })
    class_mixins: Optional[list[str]] = Field(default=None, description="""Additional classes mixed into this class.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryClass'], 'in_subset': ['HashSubset']} })
    is_abstract: Optional[bool] = Field(default=False, description="""Whether this registered class is itself declared abstract.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryClass'],
         'ifabsent': 'false',
         'in_subset': ['HashSubset'],
         'slot_uri': 'linkml:abstract'} })
    hash_id: str = Field(default=..., description="""Content-hash-derived identifier (format sha256:<hex>). A change in any identity-defining field produces a new hash_id; lineage is preserved via derived_from.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity', 'Transform']} })
    name: str = Field(default=..., description="""Human-readable label for this entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity', 'Transform'], 'in_subset': ['HashSubset']} })
    description: str = Field(default=..., description="""Human-readable description of this entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity', 'Transform'],
         'in_subset': ['HashSubset'],
         'slot_uri': 'skos:definition'} })
    provenance: list[ProvenanceEntry] = Field(default=..., description="""One ProvenanceEntry per source attesting to this entity. Accumulates as more sources are ingested — never affects hash_id.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity', 'Mapping']} })
    skos_mappings: Optional[list[Mapping]] = Field(default=None, description="""Semantic mappings to external vocabulary concepts, or to other registry entities (align.py's computed correspondences). Storage is embedded (the owning entity is the implicit subject); SSSOM export materializes subject_id from the owning entity's hash_id, so exported mapping sets are standalone, standards-conformant records.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity']} })
    aliases: Optional[list[str]] = Field(default=None, description="""Alternate names/synonyms/abbreviations for this entity (e.g. \"lfp\" for \"local field potential\"), preserved from the source schema. Used as alignment evidence (align.py's alias_overlap signal) — not part of the schema's own semantics.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity'], 'slot_uri': 'skos:altLabel'} })
    concept_uri: Optional[str] = Field(default=None, description="""Ontology IRI for this entity (class or property), preserved from the source schema on ingestion. Not part of the content hash; used for alignment and cross-source lookup.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity']} })
    source_native_id: Optional[str] = Field(default=None, description="""The verbatim identifier of this element in its source schema (the raw column/field/key name, e.g. \"z_spec\", \"sub-01\"), preserved exactly as written. Alignment's lexical channel matches on this — `name` alone loses the source's own spelling, abbreviations and casing, which is often the strongest cheap signal. Optional; not part of the content hash.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity']} })


class RegistryProperty(RegistryEntity):
    """
    A registered property (data element) representing a characteristic or attribute that can be attached to a RegistryClass, e.g. \"age\". Usage constraints (required, multivalued, min/max, pattern) are deliberately not here — they belong on Rule, since the same property can be required in one source's usage and optional in another's without being a different concept.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://example.org/schema-registry-utils/meta-model'})

    defined_in_schema: str = Field(default=..., description="""The SchemaSource this class/property belongs to (stored as id FK, like had_primary_source). IN the hash — this is the mechanical form of \"users add a new class, and the mapping between them is added\": identical content in two schemas is two entities, and their correspondence is always an explicit Mapping record that can be proposed, reviewed, rejected, and exported. Nothing is ever implicitly identified across sources, so nothing disappears from the alignment problem without a record. Deliberately the schema, not a version: content unchanged across versions of one schema keeps its hash_id, so existing mappings survive re-ingestion. Attached to RegistryClass and RegistryProperty only — the entities alignment compares; PermissibleValue keeps its cross-source sharing semantics unchanged.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryClass', 'RegistryProperty', 'Rule'],
         'in_subset': ['HashSubset']} })
    property_range: str = Field(default=..., description="""The data type or value range for this property: a canonical XSD CURIE for primitives (e.g. \"xsd:string\", \"xsd:integer\"), or the hash_id of a ValueSet for enumerated values. Bare primitive names (\"string\", \"float\") are deprecated: datatype compatibility is an alignment signal and an incompatibility veto, so \"float\", \"xsd:float\" and \"double\" must not read as three unrelated types. Ingestion normalizes source-native type names to XSD CURIEs; the declared range stays string until that lands.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryProperty'],
         'in_subset': ['HashSubset'],
         'slot_uri': 'linkml:range'} })
    unit: Optional[UnitOfMeasure] = Field(default=None, description="""Structured unit of measure for this property's values, if applicable. ucum_code is the primary field for programmatic unit-compatibility checks (align.py's unit veto); the others are supplementary.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryProperty'],
         'in_subset': ['HashSubset'],
         'slot_uri': 'qudt:unit'} })
    hash_id: str = Field(default=..., description="""Content-hash-derived identifier (format sha256:<hex>). A change in any identity-defining field produces a new hash_id; lineage is preserved via derived_from.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity', 'Transform']} })
    name: str = Field(default=..., description="""Human-readable label for this entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity', 'Transform'], 'in_subset': ['HashSubset']} })
    description: str = Field(default=..., description="""Human-readable description of this entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity', 'Transform'],
         'in_subset': ['HashSubset'],
         'slot_uri': 'skos:definition'} })
    provenance: list[ProvenanceEntry] = Field(default=..., description="""One ProvenanceEntry per source attesting to this entity. Accumulates as more sources are ingested — never affects hash_id.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity', 'Mapping']} })
    skos_mappings: Optional[list[Mapping]] = Field(default=None, description="""Semantic mappings to external vocabulary concepts, or to other registry entities (align.py's computed correspondences). Storage is embedded (the owning entity is the implicit subject); SSSOM export materializes subject_id from the owning entity's hash_id, so exported mapping sets are standalone, standards-conformant records.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity']} })
    aliases: Optional[list[str]] = Field(default=None, description="""Alternate names/synonyms/abbreviations for this entity (e.g. \"lfp\" for \"local field potential\"), preserved from the source schema. Used as alignment evidence (align.py's alias_overlap signal) — not part of the schema's own semantics.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity'], 'slot_uri': 'skos:altLabel'} })
    concept_uri: Optional[str] = Field(default=None, description="""Ontology IRI for this entity (class or property), preserved from the source schema on ingestion. Not part of the content hash; used for alignment and cross-source lookup.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity']} })
    source_native_id: Optional[str] = Field(default=None, description="""The verbatim identifier of this element in its source schema (the raw column/field/key name, e.g. \"z_spec\", \"sub-01\"), preserved exactly as written. Alignment's lexical channel matches on this — `name` alone loses the source's own spelling, abbreviations and casing, which is often the strongest cheap signal. Optional; not part of the content hash.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity']} })


class ProvenanceEntry(ConfiguredBaseModel):
    """
    One source's attestation of a registry entity — where it came from and how/when this record was generated (W3C PROV-O fields). An entity accumulates one ProvenanceEntry per source that attests to it; identity (hash_id) never depends on provenance, so the same entity can carry many. Stored as its own node, linked via HAS_PROVENANCE / HAS_PROVENANCE_P edges (multivalued — cannot be inlined into the parent's node table). Identified by id, not hash_id — a ProvenanceEntry is a per-attestation record, not a deduplicated, content-addressed registry entity.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://example.org/schema-registry-utils/meta-model'})

    id: str = Field(default=..., description="""Plain unique identifier, used by every class that isn't part of the content-addressed RegistryEntity family (ProvenanceEntry, SchemaSource, SchemaVersionSnapshot, Mapping) — LinkML's own conventional name for a non-content-derived identifier. hash_id is reserved for RegistryEntity subclasses.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProvenanceEntry',
                       'Mapping',
                       'SchemaSource',
                       'SchemaVersionSnapshot']} })
    had_primary_source: str = Field(default=..., description="""The SchemaSource this attestation came from (stored as id FK, like is_a). A real Entity->Entity link, not a denormalized label copy — PROV-O's own hadPrimarySource is a relationship between entities.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProvenanceEntry'], 'slot_uri': 'prov:hadPrimarySource'} })
    source_version: Optional[str] = Field(default=None, description="""Version of the source schema as declared by the source itself, never invented or bumped by the registry. On SchemaSource: the version at first ingestion (known frozen-value limitation). On ProvenanceEntry: the source's version at the time of this attestation — this is what lets a query scope entities and mappings to \"BIDS 1.9 specifically\", lets re-ingestion diff by version, and makes an alignment run's inputs statable, without needing SchemaVersionSnapshot.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProvenanceEntry', 'SchemaSource', 'SchemaVersionSnapshot']} })
    registry_version: Optional[str] = Field(default=None, description="""Registry snapshot version in effect when this ProvenanceEntry was generated. Not on RegistryClass/RegistryProperty directly — the same entity can be attested by different sources at different times, each under a different registry version, so it belongs on the per-source attestation, not the entity itself. No PROV-O term — purely our own versioning concept.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProvenanceEntry', 'SchemaSource', 'SchemaVersionSnapshot']} })
    generated_at_time: datetime  = Field(default=..., description="""ISO-8601 timestamp this ProvenanceEntry was generated.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProvenanceEntry'], 'slot_uri': 'prov:generatedAtTime'} })
    was_attributed_to: str = Field(default=..., description="""Agent (user or system) that generated this ProvenanceEntry.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProvenanceEntry'], 'slot_uri': 'prov:wasAttributedTo'} })
    was_generated_by: Optional[str] = Field(default=None, description="""The activity that produced this ProvenanceEntry, e.g. \"ingestion\", \"manual\", \"alignment\".""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProvenanceEntry'], 'slot_uri': 'prov:wasGeneratedBy'} })
    was_derived_from: Optional[list[str]] = Field(default=None, description="""hash_ids of entities this entity was derived from, if any. Stored as a native list column in the graph database.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProvenanceEntry'], 'slot_uri': 'prov:wasDerivedFrom'} })


class MappingProvenanceEntry(ProvenanceEntry):
    """
    ProvenanceEntry, but had_primary_source isn't required — a Mapping is often cross-schema (comparing content from two sources) or produced by a pure algorithmic process with no single schema to attribute to, unlike a RegistryClass/RegistryProperty attestation which always traces back to exactly one SchemaSource. Also carries the fields that describe *how* the mapping was produced (justification, evidence, tool) — those belong here rather than on Mapping itself, alongside was_generated_by/generated_at_time.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://example.org/schema-registry-utils/meta-model',
         'slot_usage': {'had_primary_source': {'name': 'had_primary_source',
                                               'required': False}}})

    mapping_justification: Optional[str] = Field(default=None, description="""How this mapping came to be. Values SHOULD be semapv CURIEs (https://w3id.org/semapv/vocab/): semapv:ManualMappingCuration for source-declared or human-curated mappings, semapv:LexicalMatching, semapv:SemanticSimilarityThresholdMatching, semapv:StructuralMatching, semapv:LogicalReasoning, semapv:CompositeMatching for computed ones. The range stays string (no enum migration forced), but free-form values (\"manual\", \"exact_class_uri\") are deprecated: the alignment pipeline keys review, predicate policy, and per-method evaluation off these terms, and SSSOM requires them — a free string collapses the distinction between statistical evidence and declared semantics.""", json_schema_extra = { "linkml_meta": {'domain_of': ['MappingProvenanceEntry']} })
    match_string: Optional[list[str]] = Field(default=None, description="""The strings/evidence the match was made on, if any.""", json_schema_extra = { "linkml_meta": {'domain_of': ['MappingProvenanceEntry']} })
    mapping_tool: Optional[str] = Field(default=None, description="""Name of the tool/process that produced this mapping, e.g. \"align.py\".""", json_schema_extra = { "linkml_meta": {'domain_of': ['MappingProvenanceEntry']} })
    id: str = Field(default=..., description="""Plain unique identifier, used by every class that isn't part of the content-addressed RegistryEntity family (ProvenanceEntry, SchemaSource, SchemaVersionSnapshot, Mapping) — LinkML's own conventional name for a non-content-derived identifier. hash_id is reserved for RegistryEntity subclasses.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProvenanceEntry',
                       'Mapping',
                       'SchemaSource',
                       'SchemaVersionSnapshot']} })
    had_primary_source: Optional[str] = Field(default=None, description="""The SchemaSource this attestation came from (stored as id FK, like is_a). A real Entity->Entity link, not a denormalized label copy — PROV-O's own hadPrimarySource is a relationship between entities.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProvenanceEntry'], 'slot_uri': 'prov:hadPrimarySource'} })
    source_version: Optional[str] = Field(default=None, description="""Version of the source schema as declared by the source itself, never invented or bumped by the registry. On SchemaSource: the version at first ingestion (known frozen-value limitation). On ProvenanceEntry: the source's version at the time of this attestation — this is what lets a query scope entities and mappings to \"BIDS 1.9 specifically\", lets re-ingestion diff by version, and makes an alignment run's inputs statable, without needing SchemaVersionSnapshot.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProvenanceEntry', 'SchemaSource', 'SchemaVersionSnapshot']} })
    registry_version: Optional[str] = Field(default=None, description="""Registry snapshot version in effect when this ProvenanceEntry was generated. Not on RegistryClass/RegistryProperty directly — the same entity can be attested by different sources at different times, each under a different registry version, so it belongs on the per-source attestation, not the entity itself. No PROV-O term — purely our own versioning concept.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProvenanceEntry', 'SchemaSource', 'SchemaVersionSnapshot']} })
    generated_at_time: datetime  = Field(default=..., description="""ISO-8601 timestamp this ProvenanceEntry was generated.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProvenanceEntry'], 'slot_uri': 'prov:generatedAtTime'} })
    was_attributed_to: str = Field(default=..., description="""Agent (user or system) that generated this ProvenanceEntry.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProvenanceEntry'], 'slot_uri': 'prov:wasAttributedTo'} })
    was_generated_by: Optional[str] = Field(default=None, description="""The activity that produced this ProvenanceEntry, e.g. \"ingestion\", \"manual\", \"alignment\".""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProvenanceEntry'], 'slot_uri': 'prov:wasGeneratedBy'} })
    was_derived_from: Optional[list[str]] = Field(default=None, description="""hash_ids of entities this entity was derived from, if any. Stored as a native list column in the graph database.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProvenanceEntry'], 'slot_uri': 'prov:wasDerivedFrom'} })


class Mapping(ConfiguredBaseModel):
    """
    A semantic mapping from a registry entity to a target — another registry entity (by hash_id) or an external vocabulary concept (by IRI). Covers both a source-declared mapping and one align.py computes, distinguished by provenance.mapping_justification, not by class. Identified by id, not hash_id — not is_a RegistryEntity.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://example.org/schema-registry-utils/meta-model',
         'slot_usage': {'provenance': {'name': 'provenance',
                                       'range': 'MappingProvenanceEntry'}}})

    id: str = Field(default=..., description="""Plain unique identifier, used by every class that isn't part of the content-addressed RegistryEntity family (ProvenanceEntry, SchemaSource, SchemaVersionSnapshot, Mapping) — LinkML's own conventional name for a non-content-derived identifier. hash_id is reserved for RegistryEntity subclasses.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProvenanceEntry',
                       'Mapping',
                       'SchemaSource',
                       'SchemaVersionSnapshot']} })
    mapping_type: Optional[SkosMappingTypeEnum] = Field(default=None, description="""The kind of SKOS mapping relation this represents.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Mapping']} })
    target: Optional[str] = Field(default=None, description="""What this mapping points to — an external ontology concept (IRI), or another registry entity's hash_id for align.py's computed cross-schema correspondences.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Mapping']} })
    confidence: Optional[float] = Field(default=None, description="""Score in [0,1] assigned by whatever process produced this mapping. Not required — a manually-declared mapping may have no numeric score.""", ge=0.0, le=1.0, json_schema_extra = { "linkml_meta": {'domain_of': ['Mapping']} })
    review_status: Optional[ReviewStatusEnum] = Field(default=None, description="""Curation lifecycle state. Always PROPOSED for now — nothing in this registry curates mappings yet, so this field exists to be standards-conformant (SSSOM/Proteus), not because anything sets it to ACCEPTED/REJECTED today.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Mapping']} })
    mapping_set_id: Optional[str] = Field(default=None, description="""Identifier of the mapping set (one matcher run, one curation campaign, one source-declaration ingestion) this mapping belongs to. Optional. This is the unit of run-level provenance and wholesale supersession: a miscalibrated run is superseded by set, not mapping-by-mapping, and one run exports as one SSSOM TSV.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Mapping']} })
    provenance: list[MappingProvenanceEntry] = Field(default=..., description="""One ProvenanceEntry per source attesting to this entity. Accumulates as more sources are ingested — never affects hash_id.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity', 'Mapping']} })


class Rule(RegistryEntity):
    """
    A validation or business rule that constrains one or more registry entities. Covers both the declarative property-level constraints a source schema states directly (regex pattern, min/max value, length/cardinality bounds, required, multivalued, enum membership — dandi-schema's `Field(pattern=..., min_length=..., max_length=...)`, LinkML's slot facets, JSON Schema's keyword set) and the class-level cross-field constraints those schemas express as model validators (dandi-schema's `@model_validator` — e.g. \"ContactPerson requires email\", \"datePublished implies publishedBy and doi\", \"identifier or url must be present\"). Both surface in the same registry so alignment can compare them: two schemas that state \"identifier matches ORCID\" about the same-hash property should recognize the equivalence.
    A single Rule instance carries only the slots relevant to its `rule_type` — the constraint-parameter slots (pattern, min_value, min_length, allowed_value_set, expression, etc.) are all optional and populated by rule_type. Rules that a source states declaratively populate the typed slots; imperative validators the registry cannot decompose (dandi-schema's Python `@model_validator` bodies, JSON Schema `if/then/else`) are captured via `expression` + `expression_language`, preserving the source form without pretending to have parsed it.
    Identity is content-addressed like any RegistryEntity: same rule_type + same parameters + same targets + same defined_in_schema + same defined_in_class hash to the same Rule; a schema that changes only the human-readable `error_message` keeps its hash_id (see the HashSubset membership on each slot). Rules are attached to RegistryClass/RegistryProperty through the `applies_to` slot — not inlined on the entity itself, because the same property can carry different constraints in different sources' usage (a stance already made explicit in RegistryProperty's own description).
    LinkML slot_usage (and equivalent per-class refinements in other schema languages) is modeled through the optional `defined_in_class` slot rather than a separate override entity or an inheritance chain. A Rule with `defined_in_class` unset is a schema-level default — effective wherever its `applies_to` property is used, unless a more specific Rule takes precedence. A Rule with `defined_in_class = ClassB` is a class-level refinement — effective only when the property is used inside ClassB, and it overrides the schema-level Rule of the *same rule_type* on the *same applies_to* property (rule_type-by-rule_type, matching LinkML's slot_usage semantics: overriding `pattern` in one class does not also drop the schema-level `required`). Class-level rules that aren't slot refinements at all — dandi-schema's cross-field `@model_validator` for \"identifier or url must be present\" — use the same mechanism: `defined_in_class = ContactCard`, `applies_to = [identifier_property, url_property]`, `rule_type = EXPRESSION`; no special-casing.
    Effective-rule resolution for property P used inside class C is therefore: for each rule_type, prefer the Rule with `defined_in_class = C and applies_to contains P` if one exists; otherwise fall back to the Rule with `defined_in_class` unset. The registry does not currently execute this resolution — it stores both the schema-level and class-level Rules as data — but the model is shaped so a downstream validator (or an alignment pass that wants to compare \"the effective pattern on this slot in this class\") can do so with a single graph walk.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://example.org/schema-registry-utils/meta-model'})

    defined_in_schema: str = Field(default=..., description="""The SchemaSource this class/property belongs to (stored as id FK, like had_primary_source). IN the hash — this is the mechanical form of \"users add a new class, and the mapping between them is added\": identical content in two schemas is two entities, and their correspondence is always an explicit Mapping record that can be proposed, reviewed, rejected, and exported. Nothing is ever implicitly identified across sources, so nothing disappears from the alignment problem without a record. Deliberately the schema, not a version: content unchanged across versions of one schema keeps its hash_id, so existing mappings survive re-ingestion. Attached to RegistryClass and RegistryProperty only — the entities alignment compares; PermissibleValue keeps its cross-source sharing semantics unchanged.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryClass', 'RegistryProperty', 'Rule'],
         'in_subset': ['HashSubset']} })
    defined_in_class: Optional[str] = Field(default=None, description="""The RegistryClass this rule is scoped to, if any — populated for class-level refinements that ingest from LinkML `slot_usage` blocks (or equivalent per-class overrides in other schema languages), and for standalone class-level constraints (cross-field validators, class invariants) that aren't slot refinements at all. Unset means the rule is a schema-level default: effective wherever `applies_to` matches. Set means the rule is effective *only* when the target property is used inside this class, and it overrides the schema-level rule of the same rule_type on the same applies_to property (rule_type-by-rule_type override, matching LinkML's slot_usage: refining `pattern` for a class does not drop the schema-level `required`). Range is RegistryClass rather than RegistryEntity because a class-scope override is meaningful only against a class — a property doesn't have a \"slot_usage\" of its own.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Rule'], 'in_subset': ['HashSubset']} })
    rule_type: RuleTypeEnum = Field(default=..., description="""What kind of constraint this Rule expresses. Determines which of the typed parameter slots below are populated: PATTERN populates `pattern`, VALUE_RANGE populates min_value/max_value (and optionally the exclusive_* flags), LENGTH_RANGE populates min_length/max_length, CARDINALITY populates min_cardinality/max_cardinality, REQUIRED populates is_required, MULTIVALUED populates is_multivalued, ENUM_MEMBERSHIP populates allowed_value_set, and EXPRESSION populates `expression` + `expression_language` for imperative rules the registry ingested but does not decompose (dandi-schema's `@model_validator` bodies, JSON Schema `if/then/else`, SHACL/ShEx snippets). Identity-defining — a rule of type PATTERN with pattern \"^\\d+$\" is a different Rule from a rule of type EXPRESSION whose expression happens to embed the same regex.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Rule'], 'in_subset': ['HashSubset']} })
    applies_to: list[str] = Field(default=..., description="""The registry entities this rule constrains — typically one RegistryProperty for a property-level constraint (a pattern on `identifier`, a min_length on `description`), or several RegistryProperty entities for a cross-field validator (dandi-schema's `@model_validator` for \"identifier or url must be present\" names both properties here). The class this rule is scoped to, if any, goes on `defined_in_class`, not here — so applies_to stays purely about the constrained targets. Range is RegistryEntity for flexibility; ingestion should only ever populate this with RegistryClass or RegistryProperty targets (PermissibleValue, ValueSet, Rule itself are not valid targets).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Rule'], 'in_subset': ['HashSubset']} })
    severity: Optional[RuleSeverityEnum] = Field(default=RuleSeverityEnum.ERROR, description="""How a failure of this rule should be reported. Defaults to ERROR (the source-schema default: dandi-schema's Pydantic constraints and `@model_validator` bodies all raise). WARNING is for recommendation-style rules a source encodes but does not want to hard-fail on; INFO is for advisory/metadata rules used only to surface hints.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Rule'], 'ifabsent': 'ERROR', 'in_subset': ['HashSubset']} })
    error_message: Optional[str] = Field(default=None, description="""Human-readable message describing what the rule requires, shown when it fails. Preserved verbatim from the source schema where one is supplied (dandi-schema's `ValueError` strings inside `@model_validator`, LinkML's `constraint_message`); otherwise populated by ingestion with a canned message derived from rule_type + parameters.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Rule']} })
    pattern: Optional[str] = Field(default=None, description="""Regex the constrained value must match, populated for rule_type=PATTERN. ECMA-262 syntax (JSON Schema / Pydantic / LinkML share this), preserved verbatim from the source; no dialect translation on ingest, because a \"same regex\" recognition across sources is exactly what alignment needs to see.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Rule'], 'in_subset': ['HashSubset']} })
    min_value: Optional[float] = Field(default=None, description="""Lower bound for the constrained value, populated for rule_type=VALUE_RANGE. Inclusive unless exclusive_minimum is true.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Rule'], 'in_subset': ['HashSubset']} })
    max_value: Optional[float] = Field(default=None, description="""Upper bound for the constrained value, populated for rule_type=VALUE_RANGE. Inclusive unless exclusive_maximum is true.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Rule'], 'in_subset': ['HashSubset']} })
    exclusive_minimum: Optional[bool] = Field(default=False, description="""If true, min_value is a strict lower bound (value > min_value rather than value >= min_value). Follows JSON Schema draft-07+ semantics (a boolean flag on the numeric bound, not a separate numeric field as in draft-04).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Rule'], 'ifabsent': 'false', 'in_subset': ['HashSubset']} })
    exclusive_maximum: Optional[bool] = Field(default=False, description="""If true, max_value is a strict upper bound (value < max_value rather than value <= max_value).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Rule'], 'ifabsent': 'false', 'in_subset': ['HashSubset']} })
    min_length: Optional[int] = Field(default=None, description="""Minimum string length, populated for rule_type=LENGTH_RANGE (dandi-schema's `Field(max_length=...)` on `description`, ORCID identifier length constraints).""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['Rule'], 'in_subset': ['HashSubset']} })
    max_length: Optional[int] = Field(default=None, description="""Maximum string length, populated for rule_type=LENGTH_RANGE.""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['Rule'], 'in_subset': ['HashSubset']} })
    min_cardinality: Optional[int] = Field(default=None, description="""Minimum number of items for a multivalued property, populated for rule_type=CARDINALITY (dandi-schema's `List[LicenseType] = Field(min_length=1)` — same keyword `min_length`, but on a list, not a string; kept as a separate slot so string-length and list-cardinality constraints don't collide on the hash).""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['Rule'], 'in_subset': ['HashSubset']} })
    max_cardinality: Optional[int] = Field(default=None, description="""Maximum number of items for a multivalued property, populated for rule_type=CARDINALITY (dandi-schema's `List[AccessRequirements] = Field(max_length=1)`, exact-one enforced as min_cardinality=max_cardinality=1).""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['Rule'], 'in_subset': ['HashSubset']} })
    is_required: Optional[bool] = Field(default=None, description="""Whether the constrained property must be present, populated for rule_type=REQUIRED. Left nullable rather than ifabsent-false: a Rule of another rule_type does not implicitly assert \"not required\", and the boolean-required convention (RegistryProperty is not itself required-by-default) is a Rule-level concern.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Rule'], 'in_subset': ['HashSubset']} })
    is_multivalued: Optional[bool] = Field(default=None, description="""Whether the constrained property may carry multiple values, populated for rule_type=MULTIVALUED. Also left nullable — a Rule of type PATTERN says nothing about multivaluedness.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Rule'], 'in_subset': ['HashSubset']} })
    allowed_value_set: Optional[str] = Field(default=None, description="""ValueSet the constrained value must be drawn from, populated for rule_type=ENUM_MEMBERSHIP. Stored as a ValueSet hash_id FK so the permissible values live once, shared across every rule that restricts to them; the range-level ValueSet on RegistryProperty (via property_range) is the type declaration, while this Rule is the enforceable constraint — a property whose range is a ValueSet typically also has a Rule of type ENUM_MEMBERSHIP pointing at the same ValueSet.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Rule'], 'in_subset': ['HashSubset']} })
    referenced_entities: Optional[list[str]] = Field(default=None, description="""Additional entities an EXPRESSION-type rule mentions but does not apply to as its direct target — e.g. a dandi-schema `@model_validator` that reads `roleName` and `email` on Contributor would list Contributor in `applies_to` and both RegistryProperties here. Lets alignment find rules that touch a given property without conflating direct constraints with incidental references. Empty/omitted for the declarative rule_types.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Rule'], 'in_subset': ['HashSubset']} })
    expression: Optional[str] = Field(default=None, description="""Free-form constraint text, populated for rule_type=EXPRESSION when the source's rule cannot be decomposed into the typed parameter slots above — dandi-schema's `@model_validator` bodies (\"if RoleType.ContactPerson in self.roleName and self.email is None: raise ValueError(...)\"), JSON Schema `if/then/else` blocks, SHACL/ShEx shapes, SPARQL ASK queries. Stored verbatim; the registry does not currently execute these, but preserving the source form keeps the door open (a Proteus validator, an external SHACL engine) and makes alignment able to spot near-duplicates across schemas.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Rule'], 'in_subset': ['HashSubset']} })
    expression_language: Optional[RuleExpressionLanguageEnum] = Field(default=None, description="""Which formalism the `expression` string is written in — required when `expression` is set, so a downstream tool that consumes rules knows how (or whether) it can execute them. Two rules with the same expression text but different declared languages are different Rules (SHACL vs. ShEx text can look alike but mean different things).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Rule'], 'in_subset': ['HashSubset']} })
    hash_id: str = Field(default=..., description="""Content-hash-derived identifier (format sha256:<hex>). A change in any identity-defining field produces a new hash_id; lineage is preserved via derived_from.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity', 'Transform']} })
    name: str = Field(default=..., description="""Human-readable label for this entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity', 'Transform'], 'in_subset': ['HashSubset']} })
    description: str = Field(default=..., description="""Human-readable description of this entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity', 'Transform'],
         'in_subset': ['HashSubset'],
         'slot_uri': 'skos:definition'} })
    provenance: list[ProvenanceEntry] = Field(default=..., description="""One ProvenanceEntry per source attesting to this entity. Accumulates as more sources are ingested — never affects hash_id.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity', 'Mapping']} })
    skos_mappings: Optional[list[Mapping]] = Field(default=None, description="""Semantic mappings to external vocabulary concepts, or to other registry entities (align.py's computed correspondences). Storage is embedded (the owning entity is the implicit subject); SSSOM export materializes subject_id from the owning entity's hash_id, so exported mapping sets are standalone, standards-conformant records.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity']} })
    aliases: Optional[list[str]] = Field(default=None, description="""Alternate names/synonyms/abbreviations for this entity (e.g. \"lfp\" for \"local field potential\"), preserved from the source schema. Used as alignment evidence (align.py's alias_overlap signal) — not part of the schema's own semantics.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity'], 'slot_uri': 'skos:altLabel'} })
    concept_uri: Optional[str] = Field(default=None, description="""Ontology IRI for this entity (class or property), preserved from the source schema on ingestion. Not part of the content hash; used for alignment and cross-source lookup.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity']} })
    source_native_id: Optional[str] = Field(default=None, description="""The verbatim identifier of this element in its source schema (the raw column/field/key name, e.g. \"z_spec\", \"sub-01\"), preserved exactly as written. Alignment's lexical channel matches on this — `name` alone loses the source's own spelling, abbreviations and casing, which is often the strongest cheap signal. Optional; not part of the content hash.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity']} })


class Transform(ConfiguredBaseModel):
    """
    STUB — a transformation between two RegistryClass definitions. Slots intentionally minimal; scope TBD.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://example.org/schema-registry-utils/meta-model'})

    hash_id: str = Field(default=..., description="""Content-hash-derived identifier (format sha256:<hex>). A change in any identity-defining field produces a new hash_id; lineage is preserved via derived_from.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity', 'Transform']} })
    name: str = Field(default=..., description="""Human-readable label for this entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity', 'Transform'], 'in_subset': ['HashSubset']} })
    description: str = Field(default=..., description="""Human-readable description of this entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity', 'Transform'],
         'in_subset': ['HashSubset'],
         'slot_uri': 'skos:definition'} })


class PermissibleValue(RegistryEntity):
    """
    A single permissible value within a ValueSet enumeration. The `name` field holds the value text (e.g. \"EXACT_MATCH\"); `meaning` optionally maps it to an external ontology IRI. Identity is content-addressed on (name, description, meaning) — identical values across sources share one node, with provenance accumulating like any other RegistryEntity.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://example.org/schema-registry-utils/meta-model'})

    meaning: Optional[str] = Field(default=None, description="""Ontology IRI this permissible value maps to (e.g. skos:exactMatch for the EXACT_MATCH value in SkosMappingTypeEnum).""", json_schema_extra = { "linkml_meta": {'domain_of': ['PermissibleValue'], 'in_subset': ['HashSubset']} })
    hash_id: str = Field(default=..., description="""Content-hash-derived identifier (format sha256:<hex>). A change in any identity-defining field produces a new hash_id; lineage is preserved via derived_from.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity', 'Transform']} })
    name: str = Field(default=..., description="""Human-readable label for this entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity', 'Transform'], 'in_subset': ['HashSubset']} })
    description: str = Field(default=..., description="""Human-readable description of this entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity', 'Transform'],
         'in_subset': ['HashSubset'],
         'slot_uri': 'skos:definition'} })
    provenance: list[ProvenanceEntry] = Field(default=..., description="""One ProvenanceEntry per source attesting to this entity. Accumulates as more sources are ingested — never affects hash_id.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity', 'Mapping']} })
    skos_mappings: Optional[list[Mapping]] = Field(default=None, description="""Semantic mappings to external vocabulary concepts, or to other registry entities (align.py's computed correspondences). Storage is embedded (the owning entity is the implicit subject); SSSOM export materializes subject_id from the owning entity's hash_id, so exported mapping sets are standalone, standards-conformant records.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity']} })
    aliases: Optional[list[str]] = Field(default=None, description="""Alternate names/synonyms/abbreviations for this entity (e.g. \"lfp\" for \"local field potential\"), preserved from the source schema. Used as alignment evidence (align.py's alias_overlap signal) — not part of the schema's own semantics.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity'], 'slot_uri': 'skos:altLabel'} })
    concept_uri: Optional[str] = Field(default=None, description="""Ontology IRI for this entity (class or property), preserved from the source schema on ingestion. Not part of the content hash; used for alignment and cross-source lookup.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity']} })
    source_native_id: Optional[str] = Field(default=None, description="""The verbatim identifier of this element in its source schema (the raw column/field/key name, e.g. \"z_spec\", \"sub-01\"), preserved exactly as written. Alignment's lexical channel matches on this — `name` alone loses the source's own spelling, abbreviations and casing, which is often the strongest cheap signal. Optional; not part of the content hash.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity']} })


class ValueSet(RegistryEntity):
    """
    A controlled set of permissible values, usable as a RegistryProperty range. LinkML enums ingest as ValueSet nodes; each permissible value becomes a separate PermissibleValue node linked via HAS_PERMISSIBLE_VALUE edges.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://example.org/schema-registry-utils/meta-model'})

    permissible_values: Optional[list[str]] = Field(default=None, description="""The set of permissible values for this ValueSet. Stored as hash_id references; HAS_PERMISSIBLE_VALUE edges are the graph traversal.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ValueSet'], 'in_subset': ['HashSubset']} })
    hash_id: str = Field(default=..., description="""Content-hash-derived identifier (format sha256:<hex>). A change in any identity-defining field produces a new hash_id; lineage is preserved via derived_from.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity', 'Transform']} })
    name: str = Field(default=..., description="""Human-readable label for this entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity', 'Transform'], 'in_subset': ['HashSubset']} })
    description: str = Field(default=..., description="""Human-readable description of this entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity', 'Transform'],
         'in_subset': ['HashSubset'],
         'slot_uri': 'skos:definition'} })
    provenance: list[ProvenanceEntry] = Field(default=..., description="""One ProvenanceEntry per source attesting to this entity. Accumulates as more sources are ingested — never affects hash_id.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity', 'Mapping']} })
    skos_mappings: Optional[list[Mapping]] = Field(default=None, description="""Semantic mappings to external vocabulary concepts, or to other registry entities (align.py's computed correspondences). Storage is embedded (the owning entity is the implicit subject); SSSOM export materializes subject_id from the owning entity's hash_id, so exported mapping sets are standalone, standards-conformant records.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity']} })
    aliases: Optional[list[str]] = Field(default=None, description="""Alternate names/synonyms/abbreviations for this entity (e.g. \"lfp\" for \"local field potential\"), preserved from the source schema. Used as alignment evidence (align.py's alias_overlap signal) — not part of the schema's own semantics.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity'], 'slot_uri': 'skos:altLabel'} })
    concept_uri: Optional[str] = Field(default=None, description="""Ontology IRI for this entity (class or property), preserved from the source schema on ingestion. Not part of the content hash; used for alignment and cross-source lookup.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity']} })
    source_native_id: Optional[str] = Field(default=None, description="""The verbatim identifier of this element in its source schema (the raw column/field/key name, e.g. \"z_spec\", \"sub-01\"), preserved exactly as written. Alignment's lexical channel matches on this — `name` alone loses the source's own spelling, abbreviations and casing, which is often the strongest cheap signal. Optional; not part of the content hash.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RegistryEntity']} })


class UnitOfMeasure(ConfiguredBaseModel):
    """
    A structured unit of measure for a RegistryProperty, inlined (not its own content-addressed entity). Field names/slot_uri follow LinkML's own linkml:units module — defined locally rather than imported, since db.py's DDL generator reads meta_model.yaml's own classes directly and doesn't resolve LinkML imports (see git history for the import-vs- repeat discussion). LinkML's own alignment for units *is* QUDT/rdfs — there's no separate \"linkml:\" URI for these concepts to also target.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'annotations': {'db_inline': {'tag': 'db_inline', 'value': True}},
         'class_uri': 'qudt:Unit',
         'from_schema': 'https://example.org/schema-registry-utils/meta-model'})

    ucum_code: Optional[str] = Field(default=None, description="""UCUM (Unified Code for Units of Measure) code, e.g. \"mV\", \"deg\", \"Hz\". Compact and machine-parseable — the primary field for programmatic unit-compatibility checks (align.py's unit veto).""", json_schema_extra = { "linkml_meta": {'domain_of': ['UnitOfMeasure'], 'slot_uri': 'qudt:ucumCode'} })
    has_quantity_kind: Optional[str] = Field(default=None, description="""IRI naming the dimension/kind of quantity being measured, e.g. a QUDT quantity-kind IRI for \"ElectricPotential\" or \"PlaneAngle\". Lets incommensurable units (different quantity kinds) be vetoed outright, independent of whether a conversion factor is known.""", json_schema_extra = { "linkml_meta": {'domain_of': ['UnitOfMeasure'], 'slot_uri': 'qudt:hasQuantityKind'} })
    symbol: Optional[str] = Field(default=None, description="""Name of the unit encoded as a symbol (e.g. \"Ω\", \"°\").""", json_schema_extra = { "linkml_meta": {'domain_of': ['UnitOfMeasure'], 'slot_uri': 'qudt:symbol'} })
    abbreviation: Optional[str] = Field(default=None, description="""Short ASCII abbreviation for the unit, for contexts where non-ASCII symbols would be problematic.""", json_schema_extra = { "linkml_meta": {'domain_of': ['UnitOfMeasure'], 'slot_uri': 'qudt:abbreviation'} })
    descriptive_name: Optional[str] = Field(default=None, description="""The spelled-out name of the unit, e.g. \"millivolt\".""", json_schema_extra = { "linkml_meta": {'domain_of': ['UnitOfMeasure'], 'slot_uri': 'rdfs:label'} })


class SchemaSource(ConfiguredBaseModel):
    """
    Registry record for a schema source (one node per ingested schema label). Tracks the source's IRI, MIME type, and the registry version it was first added under. Identity uses id (not hash_id) because this is a mutable administrative record, not a content-addressed entity.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://example.org/schema-registry-utils/meta-model'})

    id: str = Field(default=..., description="""Plain unique identifier, used by every class that isn't part of the content-addressed RegistryEntity family (ProvenanceEntry, SchemaSource, SchemaVersionSnapshot, Mapping) — LinkML's own conventional name for a non-content-derived identifier. hash_id is reserved for RegistryEntity subclasses.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProvenanceEntry',
                       'Mapping',
                       'SchemaSource',
                       'SchemaVersionSnapshot']} })
    label: str = Field(default=..., description="""Short identifier label for this schema source (e.g. \"bids\", \"nwb\").""", json_schema_extra = { "linkml_meta": {'domain_of': ['SchemaSource']} })
    title: Optional[str] = Field(default=None, description="""Human-readable full name of the schema (e.g. \"Brain Imaging Data Structure\"), distinct from the short `label` used as its identifier.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SchemaSource']} })
    publisher: Optional[str] = Field(default=None, description="""Organization or group that maintains this schema.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SchemaSource']} })
    contact: Optional[str] = Field(default=None, description="""Contact point for this schema (person, mailing list, or URL).""", json_schema_extra = { "linkml_meta": {'domain_of': ['SchemaSource']} })
    homepage: Optional[str] = Field(default=None, description="""Documentation or landing page for this schema.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SchemaSource']} })
    is_hub: Optional[bool] = Field(default=False, description="""True if this schema is (part of) the registry's core/bridge vocabulary that other schemas are matched against, rather than matching every schema pairwise. Not auto-derived — set deliberately, since which schema serves as the hub is a curatorial decision.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SchemaSource'], 'ifabsent': 'false'} })
    source_iri: Optional[str] = Field(default=None, description="""Canonical IRI for this schema source.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SchemaSource']} })
    source_version: Optional[str] = Field(default=None, description="""Version of the source schema as declared by the source itself, never invented or bumped by the registry. On SchemaSource: the version at first ingestion (known frozen-value limitation). On ProvenanceEntry: the source's version at the time of this attestation — this is what lets a query scope entities and mappings to \"BIDS 1.9 specifically\", lets re-ingestion diff by version, and makes an alignment run's inputs statable, without needing SchemaVersionSnapshot.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProvenanceEntry', 'SchemaSource', 'SchemaVersionSnapshot']} })
    mime_type: Optional[str] = Field(default=None, description="""MIME type of the schema file (e.g. \"application/yaml\").""", json_schema_extra = { "linkml_meta": {'domain_of': ['SchemaSource']} })
    created_at: Optional[datetime ] = Field(default=None, description="""ISO-8601 timestamp when this record was created.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SchemaSource', 'SchemaVersionSnapshot']} })
    registry_version: Optional[str] = Field(default=None, description="""Registry snapshot version in effect when this ProvenanceEntry was generated. Not on RegistryClass/RegistryProperty directly — the same entity can be attested by different sources at different times, each under a different registry version, so it belongs on the per-source attestation, not the entity itself. No PROV-O term — purely our own versioning concept.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProvenanceEntry', 'SchemaSource', 'SchemaVersionSnapshot']} })


class SchemaVersionSnapshot(ConfiguredBaseModel):
    """
    An immutable snapshot of a schema at a specific version, created each time a schema ingestion produces new or changed content. Records the class and property counts and a human-readable summary of changes.
    QUESTIONABLE (as of 2026-08-04): likely unnecessary. It's write-only — nothing outside ingest_linkml.py's own _prev_schema_version() ever reads it back (not export_json.py, not mcp_server.py, not any CI workflow). Its source_version is a self-invented semver bump (_bump_semver()) that, after the first ingestion, ignores the source file's real declared meta[\"version\"] entirely — and it duplicates SchemaSource.source_version, which has its own bug (frozen at first-ingestion value, never updated). The one thing it enables (the \"schema unchanged, skip\" short-circuit) doesn't need stored history: write_registry_entities() is already idempotent, so stats (classes_new/properties_new/provenance_added) tell you the same thing fresh on every run. Added incidentally in a1dba23 (\"Auto-sync graph schema from meta_model.yaml via CI\"), not from a deliberate versioning design. Candidate for removal — same category as the Relation class (removed in c599c2b): present in the schema, never actually needed.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://example.org/schema-registry-utils/meta-model'})

    id: str = Field(default=..., description="""Plain unique identifier, used by every class that isn't part of the content-addressed RegistryEntity family (ProvenanceEntry, SchemaSource, SchemaVersionSnapshot, Mapping) — LinkML's own conventional name for a non-content-derived identifier. hash_id is reserved for RegistryEntity subclasses.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProvenanceEntry',
                       'Mapping',
                       'SchemaSource',
                       'SchemaVersionSnapshot']} })
    schema_label: str = Field(default=..., description="""Label of the schema this snapshot belongs to (FK to SchemaSource.label).""", json_schema_extra = { "linkml_meta": {'domain_of': ['SchemaVersionSnapshot']} })
    source_version: Optional[str] = Field(default=None, description="""Version of the source schema as declared by the source itself, never invented or bumped by the registry. On SchemaSource: the version at first ingestion (known frozen-value limitation). On ProvenanceEntry: the source's version at the time of this attestation — this is what lets a query scope entities and mappings to \"BIDS 1.9 specifically\", lets re-ingestion diff by version, and makes an alignment run's inputs statable, without needing SchemaVersionSnapshot.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProvenanceEntry', 'SchemaSource', 'SchemaVersionSnapshot']} })
    yml_path: Optional[str] = Field(default=None, description="""Relative path to the schema YAML file at snapshot time.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SchemaVersionSnapshot']} })
    class_count: Optional[int] = Field(default=None, description="""Number of classes in the schema at this version.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SchemaVersionSnapshot']} })
    property_count: Optional[int] = Field(default=None, description="""Number of properties in the schema at this version.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SchemaVersionSnapshot']} })
    changes_summary: Optional[str] = Field(default=None, description="""Human-readable summary of what changed in this version.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SchemaVersionSnapshot']} })
    created_at: Optional[datetime ] = Field(default=None, description="""ISO-8601 timestamp when this record was created.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SchemaSource', 'SchemaVersionSnapshot']} })
    registry_version: Optional[str] = Field(default=None, description="""Registry snapshot version in effect when this ProvenanceEntry was generated. Not on RegistryClass/RegistryProperty directly — the same entity can be attested by different sources at different times, each under a different registry version, so it belongs on the per-source attestation, not the entity itself. No PROV-O term — purely our own versioning concept.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProvenanceEntry', 'SchemaSource', 'SchemaVersionSnapshot']} })


# Model rebuild
# see https://pydantic-docs.helpmanual.io/usage/models/#rebuilding-a-model
RegistryEntity.model_rebuild()
RegistryClass.model_rebuild()
RegistryProperty.model_rebuild()
ProvenanceEntry.model_rebuild()
MappingProvenanceEntry.model_rebuild()
Mapping.model_rebuild()
Rule.model_rebuild()
Transform.model_rebuild()
PermissibleValue.model_rebuild()
ValueSet.model_rebuild()
UnitOfMeasure.model_rebuild()
SchemaSource.model_rebuild()
SchemaVersionSnapshot.model_rebuild()
