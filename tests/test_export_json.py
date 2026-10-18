from export_json import _effective_rules


def test_effective_rules_prefer_class_scoped_per_rule_type():
    """
    For a property used inside a class: per rule_type, the rules scoped to
    that class win over the schema-level ones; rule types the class doesn't
    refine fall back to schema level. A RANGE to a value set is labelled by
    its name.
    """
    src = frozenset({"s"})
    rules = [
        ("PATTERN",  "^[a-z]+$", None, src),     # schema-level, no refinement
        ("RANGE",    "xsd:string", None, src),   # schema-level default ...
        ("RANGE",    "vs-1", "cls-A", src),      # ... refined in class A
        ("REQUIRED", "true", "cls-A", src),      # only class A requires it
    ]
    names = {"vs-1": "StatusEnum"}

    assert _effective_rules(rules, "cls-A", {"s"}, names) == [
        {"type": "RANGE",    "value": "vs-1",     "label": "StatusEnum", "scope": "class"},
        {"type": "REQUIRED", "value": "true",     "label": "true",       "scope": "class"},
        {"type": "PATTERN",  "value": "^[a-z]+$", "label": "^[a-z]+$",   "scope": "schema"},
    ]
    assert _effective_rules(rules, "cls-B", {"s"}, names) == [
        {"type": "RANGE",    "value": "xsd:string", "label": "xsd:string", "scope": "schema"},
        {"type": "PATTERN",  "value": "^[a-z]+$",   "label": "^[a-z]+$",   "scope": "schema"},
    ]


def test_effective_rules_only_from_the_class_own_schemas():
    """
    A property shared by two schemas (same name + description) carries each
    schema's own schema-level rules. A class sees only the rules stated by a
    schema that also defines the class.
    """
    rules = [
        ("RANGE", "xsd:date",     None, frozenset({"schema.org"})),
        ("RANGE", "xsd:dateTime", None, frozenset({"dandiset", "asset"})),
    ]
    assert [r["label"] for r in _effective_rules(rules, "Dandiset", {"dandiset"}, {})] == ["xsd:dateTime"]
    assert [r["label"] for r in _effective_rules(rules, "CreativeWork", {"schema.org"}, {})] == ["xsd:date"]
