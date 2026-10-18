"""
converters/openminds.py — Fetch openMINDS schema and convert to LinkML
----------------------------------------------------------------------
openMINDS moved from HBP-MINDS to openMetadataInitiative.
JSON Schema version lives at:
  https://github.com/openMetadataInitiative/openMINDS_json-schema
  branch: main, path: schemas/{version}/

The core schemas we want are in the "core" module subfolder.
"""

from __future__ import annotations
import httpx, yaml, json, re
from pathlib import Path

# Correct org: openMetadataInitiative, not HBP-MINDS
GITHUB_API = "https://api.github.com/repos/openMetadataInitiative/openMINDS_json-schema/contents/schemas"
GITHUB_RAW = "https://raw.githubusercontent.com/openMetadataInitiative/openMINDS_json-schema/main/schemas"
OUT_PATH   = Path("registry_schemas/openminds.yml")

OPENMINDS_TYPE_MAP = {
    "string":  "xsd:string",
    "integer": "xsd:integer",
    "number":  "xsd:float",
    "boolean": "xsd:boolean",
    "array":   "xsd:string",
    "null":    "xsd:string",
}


def fetch_json(url: str) -> dict | list:
    resp = httpx.get(url, timeout=30, follow_redirects=True,
                     headers={"Accept": "application/vnd.github+json"})
    resp.raise_for_status()
    return resp.json()


def clean_name(s: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_]', '_', s)


def convert() -> dict:
    print("[openminds] Fetching openMINDS JSON Schema listing…")
    all_classes: dict = {}
    all_slots:   dict = {}

    try:
        # List available versions
        top = fetch_json(GITHUB_API)
        if not isinstance(top, list):
            raise ValueError("Unexpected response from API")

        # Take the most recent version folder
        version_dirs = [item for item in top if item.get("type") == "dir"]
        if not version_dirs:
            raise ValueError("No version directories found")

        # Sort by name to get latest (e.g. "v3.0.0" > "v2.0.0")
        version_dirs.sort(key=lambda x: x["name"], reverse=True)
        latest = version_dirs[0]
        print(f"[openminds]   Using version: {latest['name']}")

        # List subdirectories (modules)
        modules = fetch_json(latest["url"])
        if not isinstance(modules, list):
            raise ValueError("Unexpected module listing")

        schema_files_fetched = 0
        for module in modules[:5]:  # core, SANDS, controlledTerms, etc.
            if module.get("type") != "dir":
                continue
            try:
                files = fetch_json(module["url"])
                if not isinstance(files, list):
                    continue
                json_files = [f for f in files if isinstance(f, dict) and
                              (f.get("name", "").endswith(".json") or
                               f.get("name", "").endswith(".schema.json"))]
                for sf in json_files[:8]:
                    try:
                        schema = fetch_json(sf["download_url"])
                        if not isinstance(schema, dict):
                            continue
                        raw_name = sf["name"].replace(".schema.json","").replace(".json","")
                        cls_name = clean_name(raw_name)
                        required = set(schema.get("required") or [])
                        # Class-local attributes with bare names: the same
                        # name can mean different things in different classes,
                        # which ingest keeps apart (ingest_linkml._slot_key).
                        attributes: dict = {}
                        for prop, pbody in (schema.get("properties") or {}).items():
                            if prop.startswith("@") or prop.startswith("_"):
                                continue
                            if not isinstance(pbody, dict):
                                continue
                            raw_type = pbody.get("type") or "string"
                            if isinstance(raw_type, list):
                                raw_type = next((t for t in raw_type if t and t != "null"), "string")
                            raw_type = str(raw_type) if raw_type else "string"
                            xsd = OPENMINDS_TYPE_MAP.get(raw_type.lower(), "xsd:string")
                            # prop may be a full URI — extract just the local name
                            prop_local = prop.split("/")[-1].split("#")[-1]
                            prop_local = re.sub(r"[^a-zA-Z0-9_]", "_", prop_local)
                            if not prop_local:
                                continue
                            desc = pbody.get("description") or ""
                            attributes[prop_local] = {
                                "description": desc,
                                "slot_uri": prop if prop.startswith("http") else f"https://openminds.ebrains.eu/vocab/{prop_local}",
                                "range":    xsd.replace("xsd:", ""),
                                "multivalued": raw_type == "array",
                                "required": prop in required,
                            }
                        if attributes:
                            all_classes[cls_name] = {
                                "description": schema.get("description", f"openMINDS {raw_name}"),
                                "class_uri":   f"https://openminds.ebrains.eu/core/{raw_name}",
                                "attributes":  attributes,
                            }
                            schema_files_fetched += 1
                    except Exception as e:
                        print(f"[openminds]   WARNING: {sf.get('name')} — {e}")
            except Exception as e:
                print(f"[openminds]   WARNING: module {module.get('name')} — {e}")

        print(f"[openminds]   Loaded {schema_files_fetched} schema files → {len(all_classes)} classes")

    except Exception as e:
        print(f"[openminds]   WARNING: fetch failed — {e}")

    if not all_classes:
        print("[openminds]   Using fallback core types")
        all_classes = {
            "Subject": {
                "description": "A subject studied in a neuroscience experiment.",
                "class_uri": "https://openminds.ebrains.eu/core/Subject",
                "attributes": {
                    "lookupLabel":   {"description": "Lookup label", "range": "string"},
                    "biologicalSex": {"description": "Biological sex", "range": "string"},
                    "species":       {"description": "Species", "range": "string"},
                    "strain":        {"description": "Strain", "range": "string"},
                },
            },
            "Dataset": {
                "description": "A neuroscience dataset.",
                "class_uri": "https://openminds.ebrains.eu/core/Dataset",
                "attributes": {
                    "title":             {"description": "Title", "range": "string", "slot_uri": "schema:name"},
                    "description":       {"description": "Description", "range": "string", "slot_uri": "schema:description"},
                    "license":           {"description": "License", "range": "string", "slot_uri": "schema:license"},
                    "digitalIdentifier": {"description": "Digital identifier (DOI, etc.)", "range": "uriorcurie", "slot_uri": "schema:identifier"},
                },
            },
            "BrainAtlas": {
                "description": "A brain atlas reference space.",
                "class_uri": "https://openminds.ebrains.eu/sands/BrainAtlas",
                "attributes": {
                    "shortName":          {"description": "Short name", "range": "string"},
                    "fullName":           {"description": "Full name", "range": "string"},
                    "ontologyIdentifier": {"description": "Ontology term URI", "range": "uriorcurie"},
                },
            },
        }

    return {
        "id":      "https://openminds.ebrains.eu/",
        "name":    "openminds",
        "title":   "openMINDS Schema",
        "description": "Open Metadata Initiative for Neuroscience Data Structures.",
        "license": "MIT",
        "version": "4.0.0",
        "prefixes": {
            "linkml":     "https://w3id.org/linkml/",
            "schema":     "https://schema.org/",
            "openminds":  "https://openminds.ebrains.eu/",
            "xsd":        "http://www.w3.org/2001/XMLSchema#",
        },
        "default_prefix": "openminds",
        "default_range":  "string",
        "imports": ["linkml:types"],
        "classes": all_classes,
        "slots":   all_slots,
    }


def run(out_path: Path = OUT_PATH) -> None:
    schema = convert()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        yaml.dump(schema, f, default_flow_style=False, allow_unicode=True)
    n_attrs = sum(len(c.get("attributes") or {}) for c in schema["classes"].values())
    print(f"[openminds] Wrote {out_path} ({len(schema['classes'])} classes, {n_attrs} attributes)")


if __name__ == "__main__":
    run()
