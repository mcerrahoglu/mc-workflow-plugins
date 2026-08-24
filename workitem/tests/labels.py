#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guard the label map, which `check` reads as data.

references/labels.md is a documentation table that the structure check parses to canonicalise
a note's row labels. A missing entry does not raise anything: the check quietly falls back to
comparing row counts, which every five-row template passes. That is what this test is for.

    python3 workitem/tests/labels.py
"""
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("wo", ROOT / "scripts" / "workitem_output.py")
wo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wo)


def main():
    failures = []
    text = (ROOT / "references" / "labels.md").read_text(encoding="utf-8")

    seen = {}
    for line in text.split("\n"):
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 2 or cells[0] in ("English", "") or set(cells[0]) <= {"-", ":"}:
            continue
        english, target = cells
        if target in seen and seen[target] != english:
            failures.append(f"{target!r} maps to both {seen[target]!r} and {english!r}: "
                            f"the reverse direction is ambiguous")
        seen.setdefault(target, english)

    known = set(seen.values())
    for template in sorted((ROOT / "templates").glob("*.md")):
        for label in wo.first_table_labels(template.read_text(encoding="utf-8")):
            if label and label not in known:
                failures.append(f"{template.name} uses {label!r}, which the map does not carry: "
                                f"a note in another language would not resolve it")

    for line in failures:
        print("FAIL " + line)
    print(f"{len(seen)} entries, {'FAILED' if failures else 'ok'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
