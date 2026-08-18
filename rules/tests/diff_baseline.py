#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare two gate dumps on the ids they share.

New ids are listed separately: without that split, adding fixtures floods the diff and
the change in an existing case is lost in the noise. Accepts the older dump format that
stored only a decision string.

Usage: python3 tests/diff_baseline.py base.json after.json
"""
import json
import pathlib
import sys


def load(path):
    raw = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    out = {}
    for key, value in raw.items():
        if isinstance(value, str):
            out[key] = {"decision": value, "rules": []}
        else:
            out[key] = {"decision": value.get("decision"), "rules": value.get("rules") or []}
    return out


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: diff_baseline.py base.json after.json")
    base, after = load(sys.argv[1]), load(sys.argv[2])
    shared = sorted(set(base) & set(after))
    changed = [(k, base[k], after[k]) for k in shared
               if base[k]["decision"] != after[k]["decision"]
               or base[k]["rules"] != after[k]["rules"]]

    print(f"shared ids: {len(shared)}   changed: {len(changed)}")
    for key, before, now in changed:
        print(f"\n  {key}")
        print(f"    decision: {before['decision']} -> {now['decision']}")
        if before["rules"] != now["rules"]:
            print(f"    rules:    {before['rules'] or '-'} -> {now['rules'] or '-'}")

    only_after = sorted(set(after) - set(base))
    only_base = sorted(set(base) - set(after))
    if only_after:
        print(f"\nnew ids ({len(only_after)}): {', '.join(only_after)}")
    if only_base:
        print(f"\nremoved ids ({len(only_base)}): {', '.join(only_base)}")
    print("\nEvery changed line above must have a written justification.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
