#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test harness for commit_msg_gate.py.

Runs the gate as a subprocess with a PreToolUse payload on stdin, so it works with the
plugin disabled and needs no repository. Fixtures may declare `files` to be created in a
temporary directory, which becomes the payload cwd; that is how the -F path is exercised.

The dump records the decision AND the rule ids named in the reason. Recording only the
decision hides a regression where a case stays `deny` but for a different reason.

Usage:
  python3 tests/run.py                      # table, exit 1 on any failure
  python3 tests/run.py --dump after.json    # machine-readable results
  python3 tests/run.py --quiet              # summary only
  python3 tests/run.py --only str-          # run ids starting with a prefix
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
GATE = HERE.parent / "scripts" / "commit_msg_gate.py"
FIXTURES = HERE / "fixtures.jsonl"
RULE_RE = re.compile(r"\[([a-z][a-z-]+)\]")


def run_gate(cmd, cwd):
    payload = json.dumps({"tool_input": {"command": cmd}, "cwd": str(cwd)},
                         ensure_ascii=False)
    try:
        proc = subprocess.run([sys.executable, str(GATE)], input=payload,
                              capture_output=True, text=True, timeout=20)
    except subprocess.TimeoutExpired:
        return "ERR:timeout", [], ""
    out = (proc.stdout or "").strip()
    if proc.returncode not in (0, 2):
        return f"ERR:exit{proc.returncode}", [], (proc.stderr or "").strip()[:300]
    if not out:
        return "pass", [], ""
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return "ERR:badjson", [], out[:300]
    hso = data.get("hookSpecificOutput") or {}
    decision = hso.get("permissionDecision")
    reason = hso.get("permissionDecisionReason", "")
    if decision not in ("deny", "ask", "allow"):
        return "ERR:nodecision", [], out[:300]
    return decision, sorted(set(RULE_RE.findall(reason))), reason


def load_fixtures():
    items = []
    with FIXTURES.open(encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError as exc:
                sys.exit(f"fixtures.jsonl line {lineno} is malformed: {exc}")
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", metavar="FILE")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    if not GATE.exists():
        sys.exit(f"gate script not found: {GATE}")

    results, failed = {}, []
    for fx in load_fixtures():
        if args.only and not fx["id"].startswith(args.only):
            continue
        with tempfile.TemporaryDirectory() as tmp:
            for rel, content in (fx.get("files") or {}).items():
                target = pathlib.Path(tmp) / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8", newline="")
            decision, rules, reason = run_gate(fx["cmd"], tmp)

        results[fx["id"]] = {"decision": decision, "rules": rules}
        ok = decision == fx["expect"]
        missing = [r for r in (fx.get("expect_rules") or []) if r not in rules]
        if missing:
            ok = False
        if not ok:
            failed.append((fx, decision, rules, missing, reason))
        if not args.quiet:
            mark = "OK  " if ok else "FAIL"
            extra = f"  rules={','.join(rules)}" if rules else ""
            print(f"  [{mark}] {fx['id']:26} want={fx['expect']:5} got={decision:5}{extra}")

    total = len(results)
    print(f"\n  {total - len(failed)}/{total} passed" + (f", {len(failed)} FAILED" if failed else ""))
    if failed and not args.quiet:
        print("\n  Failures:")
        for fx, decision, rules, missing, reason in failed:
            print(f"    - {fx['id']}: want={fx['expect']} got={decision}")
            if missing:
                print(f"        missing rules: {', '.join(missing)}")
            print(f"        cmd: {fx['cmd'][:100]!r}")
            if reason:
                print(f"        reason: {reason[:200]}")
    if args.dump:
        pathlib.Path(args.dump).write_text(
            json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
        print(f"  results written: {args.dump}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
