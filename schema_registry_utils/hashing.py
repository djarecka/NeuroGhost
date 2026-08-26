import hashlib
import json

from schema_registry_utils.models import RegistryClass, RegistryProperty

HASH_SUBSET = "HashSubset"


def _identity_fields(model_cls: type) -> set[str]:
    """
    The content-fingerprint fields of a RegistryEntity subclass — everything
    tagged `in_subset: [HashSubset]` in schemas/meta_model.yaml.

    The schema is the single source of truth for what counts as content, not a
    hand-maintained Python allowlist/denylist that could drift out of sync with
    it. gen-pydantic carries in_subset into each field's generated
    json_schema_extra['linkml_meta'], so this is a pure introspection of the
    already-generated model — no live SchemaView/YAML load needed here.
    """
    identity = set()
    for name, field in model_cls.model_fields.items():
        linkml_meta = (field.json_schema_extra or {}).get("linkml_meta", {})
        if HASH_SUBSET in linkml_meta.get("in_subset", []):
            identity.add(name)
    return identity


def compute_content_hash(entity: RegistryClass | RegistryProperty) -> str:
    """Compute a content sha256 from entity's HashSubset fields.

    This is the fingerprint that goes into RegistryEntity.sha256_hash — not
    the identifier (which is a UUID) but the value ingestion looks up to
    reuse an existing id for content that already appears in the registry.
    """
    identity = _identity_fields(type(entity))
    return _digest({k: v for k, v in entity.model_dump().items() if k in identity})


def compute_content_hash_for(model_cls: type, fields: dict) -> str:
    """Compute the sha256_hash for an entity that has not been constructed yet.

    Builders need the content hash to look up (and dedup against) any existing
    entity carrying the same content, before they know what `id` to construct
    with — mint a fresh UUID only if no existing entity's sha256_hash matches.
    So the hash is computed from a plain dict, before the pydantic instance
    exists.

    `fields` must carry every HashSubset slot of `model_cls`; anything else
    may be present and is ignored. Omitting an identity slot raises, because
    the alternative is a silently different fingerprint the next time the
    meta-model grows a slot — which would invalidate every stored
    sha256_hash in the registry without anything failing.
    """
    identity = _identity_fields(model_cls)
    missing = identity - set(fields)
    if missing:
        raise ValueError(
            f"{model_cls.__name__}: cannot hash — identity-defining field(s) "
            f"missing from `fields`: {sorted(missing)}"
        )
    return _digest({k: v for k, v in fields.items() if k in identity})


def _digest(content: dict) -> str:
    canonical = json.dumps(_normalize(content), sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def assign_content_hash(entity: RegistryClass | RegistryProperty) -> RegistryClass | RegistryProperty:
    """Compute entity's sha256_hash from its current content, then suffix its
    name with the first 4 hex characters of the digest (e.g. "age" -> "age_a1b2").

    Mutates entity in place and returns it. Note: since name is part of the
    hashed content, the resulting sha256_hash will no longer match a fresh
    compute_content_hash() call on the entity after this mutation.
    """
    sha = compute_content_hash(entity)
    digest = sha.split(":", 1)[1]
    entity.sha256_hash = sha
    entity.name = f"{entity.name}_{digest[:4]}"
    return entity


def _normalize(value):
    if isinstance(value, dict):
        return {key: _normalize(val) for key, val in value.items()}
    if isinstance(value, list):
        normalized = [_normalize(val) for val in value]
        if all(isinstance(val, str) for val in normalized):
            # reference lists (properties/mixins) are unordered sets
            return sorted(normalized)
        return normalized
    return value
