"""
converters/aind.py — Fetch AIND schemas and convert to LinkML
-------------------------------------------------------------
Source: the official `aind-data-schema` PyPI package. Every model in
`aind_data_schema.core` is a Pydantic model, and `model_json_schema()` yields
plain JSON Schema — so there is no AIND-specific conversion here: each model's
JSON Schema goes through the generic JSON Schema converter
(`converters/from_jsonschema.py`, the same path schema submissions use) and the
results are merged into one LinkML schema.

Property names stay bare (`species`, not `Subject__species`). The same name
with a different meaning in another class is kept apart at ingest
(ingest_linkml._slot_key), so no class-name prefixing is needed.

Models are enumerated dynamically, which keeps this robust to the package
reorganizing its module layout.
"""
from __future__ import annotations

import importlib
import inspect
import pkgutil
import subprocess
import sys
from pathlib import Path

import yaml

from converters.from_jsonschema import convert as jsonschema_to_linkml

OUT_PATH = Path("registry_schemas/aind.yml")
DOCS     = "https://aind-data-schema.readthedocs.io/en/stable/"


def _load_core():
    try:
        import aind_data_schema.core as core
    except ImportError:
        print("[aind] Installing aind-data-schema…")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "aind-data-schema", "-q"],
            check=True,
        )
        importlib.invalidate_caches()
        import aind_data_schema.core as core
    return core


def _package_version() -> str:
    from importlib.metadata import version
    return version("aind-data-schema")


def _core_models():
    """Every Pydantic model defined in an aind_data_schema.core module."""
    from pydantic import BaseModel

    core = _load_core()
    seen: set[str] = set()
    for mod_info in pkgutil.iter_modules(core.__path__):
        mod = importlib.import_module(f"aind_data_schema.core.{mod_info.name}")
        for name, obj in inspect.getmembers(mod, inspect.isclass):
            if issubclass(obj, BaseModel) and obj.__module__ == mod.__name__ and name not in seen:
                seen.add(name)
                yield name, obj


def convert() -> dict:
    classes: dict = {}
    slots:   dict = {}
    enums:   dict = {}
    for name, model in _core_models():
        try:
            schema = jsonschema_to_linkml(model.model_json_schema(), "aind")
        except Exception as e:
            print(f"[aind]   WARNING: {name} — {e}")
            continue
        # Models share $defs (Device, Subject, ...), so the same class/slot/enum
        # arrives from several models with the same definition; keep the first.
        for target, part in ((classes, "classes"), (slots, "slots"), (enums, "enums")):
            for key, value in (schema.get(part) or {}).items():
                target.setdefault(key, value)

    if not classes:
        raise RuntimeError("no AIND models could be converted")
    print(f"[aind]   Loaded {len(classes)} classes, {len(slots)} slots, "
          f"{len(enums)} enums from aind-data-schema")

    return {
        "id":      DOCS,
        "name":    "aind",
        "title":   "AIND Data Schema",
        "description": "Allen Institute for Neural Dynamics data schema.",
        "license": "MIT",
        "version": _package_version(),
        "prefixes": {
            "linkml": "https://w3id.org/linkml/",
            "aind":   DOCS,
        },
        "default_prefix": "aind",
        "default_range":  "string",
        "imports": ["linkml:types"],
        "enums":   enums,
        "slots":   slots,
        "classes": classes,
    }


def run(out_path: Path = OUT_PATH) -> None:
    schema = convert()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        yaml.dump(schema, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    print(f"[aind] Wrote {out_path} "
          f"({len(schema['classes'])} classes, {len(schema['slots'])} slots)")


if __name__ == "__main__":
    run()
