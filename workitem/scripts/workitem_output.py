#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Work item helper: checks a note against its template, and collects commit material.

This script does NOT write the work item or the note. Those are written in the user's own
language, and a script handed a language code as a string cannot compose prose in it — an
earlier version tried and produced English headings while claiming otherwise. The files are
written by the skill, which is already speaking that language; here we keep only the two jobs
that need code.

  check    Compare a note's shape against the template it must match. The tracker's note pages
           have a fixed field set, so a note that adds a row or invents a section has to be
           reconciled by hand later. Shape is compared, not wording, so the check holds in any
           language; a renamed heading is the one deviation it cannot see.

  commits  Gather commits for a result note. --since is required: "the commits from this
           session" is undefined when work spans several repositories and days.

  language Remember the output language, so the skill asks once rather than every time.
"""
import datetime
import json
import pathlib
import subprocess
import sys

TEMPLATES = pathlib.Path(__file__).resolve().parent.parent / "templates"
CONFIG_PATH = pathlib.Path.home() / ".workitem" / "config.json"


# ------------------------------------------------------------------ language preference
def read_language():
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8")).get("language")
    except (OSError, json.JSONDecodeError, AttributeError):
        return None


def write_language(value):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps({"language": value}, ensure_ascii=False) + "\n",
                           encoding="utf-8")


# ------------------------------------------------------------------- structure checking
def first_table_rows(text):
    """Data rows of the first table: a note template's information table."""
    rows, in_table, seen_header = 0, False, False
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("|"):
            in_table = True
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(set(c) <= {"-", ":"} and c for c in cells):
                continue
            if not seen_header:
                seen_header = True
                continue
            rows += 1
        elif in_table and not stripped:
            break
    return rows


def heading_shape(text):
    """Heading levels in order. Shape, not wording, so it is language independent."""
    shape, in_fence = [], False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        stripped = line.lstrip()
        if stripped.startswith("#"):
            shape.append(len(stripped) - len(stripped.lstrip("#")))
    return shape


def compare_with_template(content, template_name):
    """Return a list of problems; empty means the note matches the template exactly."""
    template = TEMPLATES / f"{template_name}.md"
    if not template.is_file():
        available = ", ".join(sorted(t.stem for t in TEMPLATES.glob("*.md")))
        return [f"unknown template `{template_name}`; available: {available}"]
    want = template.read_text(encoding="utf-8")

    problems = []
    want_rows, got_rows = first_table_rows(want), first_table_rows(content)
    if want_rows != got_rows:
        problems.append(f"information table has {got_rows} rows, the template has "
                        f"{want_rows}. The row set is fixed: add none, remove none.")
    want_shape, got_shape = heading_shape(want), heading_shape(content)
    if want_shape != got_shape:
        problems.append(f"heading shape is {got_shape}, the template is {want_shape}. "
                        f"Sections are fixed: invent none, drop none, keep their level.")
    return problems


# ------------------------------------------------------------------------------ commands
def cmd_check(args):
    path = pathlib.Path(args.file)
    if not path.is_file():
        sys.exit(f"error: file not found: {path}")
    problems = compare_with_template(path.read_text(encoding="utf-8"), args.template)
    if problems:
        print(f"MISMATCH against `{args.template}`:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        print("Fix the note; do not extend the template.", file=sys.stderr)
        return 1
    print(f"OK: {path.name} matches `{args.template}`.")
    return 0


def cmd_commits(args):
    if not args.since:
        sys.exit("error: --since is required. 'the commits from this session' is an undefined "
                 "selector when work spans several repositories and days.")
    repos = args.repo or [pathlib.Path.cwd()]
    found = 0
    for repo in repos:
        repo = pathlib.Path(repo).expanduser()
        if not (repo / ".git").exists():
            print(f"\n## {repo}  — not a git repository, skipped", file=sys.stderr)
            continue
        try:
            out = subprocess.run(
                ["git", "-C", str(repo), "log", f"--since={args.since}", "--no-merges",
                 "--pretty=format:%h%x1f%ad%x1f%s%x1f%b%x1e", "--date=iso"],
                capture_output=True, text=True, timeout=30, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            print(f"\n## {repo}  — git log failed: {exc}", file=sys.stderr)
            continue
        records = [r for r in out.stdout.split("\x1e") if r.strip()]
        print(f"\n## {repo.name}  ({len(records)} commits, since={args.since})")
        for record in records:
            parts = record.strip("\n").split("\x1f")
            if len(parts) < 3:
                continue
            found += 1
            print(f"\n- **{parts[0]}** ({parts[1]}) {parts[2]}")
            for line in (parts[3].strip() if len(parts) > 3 else "").splitlines():
                if line.strip():
                    print(f"    {line}")
    if not found:
        print("\n(no commits found — check the --since range or the --repo paths)")
    else:
        print("\n> Timestamps show elapsed time, which is not time worked. Actual hours come "
              "from the user, never from this range.")
    return 0


def cmd_language(args):
    if args.set:
        write_language(args.set)
        print(f"Output language stored: {args.set}  ({CONFIG_PATH})")
    else:
        print(f"Output language: {read_language() or 'not set'}  ({CONFIG_PATH})")
    return 0


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Check a note's structure; collect commit material.")
    sub = ap.add_subparsers(dest="command", required=True)

    c = sub.add_parser("check", help="compare a note against its template")
    c.add_argument("--file", required=True)
    c.add_argument("--template", required=True,
                   help="task_note | test_note | incident_note | meeting_minutes")
    c.set_defaults(func=cmd_check)

    g = sub.add_parser("commits", help="collect commit material for a result note")
    g.add_argument("--since", help="date or git ref (REQUIRED)")
    g.add_argument("--repo", action="append")
    g.set_defaults(func=cmd_commits)

    l = sub.add_parser("language", help="show or store the output language")
    l.add_argument("--set")
    l.set_defaults(func=cmd_language)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
