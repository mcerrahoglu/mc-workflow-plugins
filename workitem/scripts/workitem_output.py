#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Work item helper: checks a note against its template, and collects commit material.

This script does NOT write the work item or the note. Those are written in the user's own
language, and a script handed a language code as a string cannot compose prose in it — an
earlier version tried and produced English headings while claiming otherwise. The files are
written by the skill, which is already speaking that language; here we keep only the two jobs
that need code.

  check    Compare a note against the template it must match. The tracker's note pages have a
           fixed field set, so a note that adds a row or invents a section has to be reconciled
           by hand later. Rows are compared by LABEL, canonicalised through references/labels.md,
           so an invented field is named in the error and a note written from the wrong template
           is caught. Sections are compared by LEVEL as a subsequence, so a section that does not
           apply may be dropped while an invented one is not. When no row label resolves, the
           language is one the map does not cover and the old count comparison is used instead,
           saying so. Not seen either way: a renamed section, and section order.

  commits  Gather commits for a result note. --since is required: "the commits from this
           session" is undefined when work spans several repositories and days.

  language Remember the output language, so the skill asks once rather than every time.
"""
import datetime
import json
import pathlib
import re
import subprocess
import sys

TEMPLATES = pathlib.Path(__file__).resolve().parent.parent / "templates"
LABELS = pathlib.Path(__file__).resolve().parent.parent / "references" / "labels.md"
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


def label_map():
    """Reverse map {target wording -> English label} from references/labels.md.

    The map is a documentation table read as data, so a missing or duplicated entry would
    silently change what the check measures. tests/labels.py guards both.
    """
    rev = {}
    try:
        text = LABELS.read_text(encoding="utf-8")
    except OSError:
        return rev
    for line in text.split("\n"):
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.strip().startswith("|") else []
        if len(cells) != 2 or cells[0] in ("English", "") or set(cells[0]) <= {"-", ":"}:
            continue
        rev.setdefault(cells[1], cells[0])
    return rev


def first_table_labels(text):
    """First-column values of the first table's data rows."""
    labels, in_table, seen_header = [], False, False
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
            labels.append(re.sub(r"[*`]", "", cells[0]).strip() if cells else "")
        elif in_table and not stripped:
            break
    return labels


def is_subsequence(small, big):
    it = iter(big)
    return all(any(x == y for y in it) for x in small)


def free_text_sections(text):
    """Section bodies with table rows removed, whitespace-normalised, blank lines dropped."""
    sections, current = [], None
    for line in text.split("\n"):
        if line.lstrip().startswith("#"):
            if current is not None:
                sections.append(current)
            current = []
        elif current is not None and not line.strip().startswith("|"):
            current.append(line)
    if current is not None:
        sections.append(current)
    return [[ln.strip() for ln in s if ln.strip()] for s in sections]


def compare_with_template(content, template_name):
    """Return a list of problems; empty means the note matches the template exactly."""
    template = TEMPLATES / f"{template_name}.md"
    if not template.is_file():
        available = ", ".join(sorted(t.stem for t in TEMPLATES.glob("*.md")))
        return [f"unknown template `{template_name}`; available: {available}"]
    want = template.read_text(encoding="utf-8")

    problems = []
    want_labels = first_table_labels(want)
    got_labels = first_table_labels(content)
    rev = label_map()

    english = set(rev.values())

    def canonical(raw):
        # Recognised means "the map knows this label", NOT "the template wants it".
        # Conflating the two made a note written from the wrong template fall through to
        # the count comparison, which every five-row template passes.
        if raw in english:
            return raw
        return rev.get(raw)

    resolved = [canonical(r) for r in got_labels]
    if got_labels and all(r is None for r in resolved):
        # A language the map does not cover: fall back to counting rather than call every
        # row invented. Said out loud, because a silent fallback measures nothing.
        if len(got_labels) != len(want_labels):
            problems.append(f"information table has {len(got_labels)} rows, the template has "
                            f"{len(want_labels)}. The row set is fixed: add none, remove none. "
                            f"(No row label resolved through references/labels.md, so only the "
                            f"count was compared.)")
    else:
        unknown = [raw for raw, res in zip(got_labels, resolved)
                   if res is None or res not in want_labels]
        missing = [w for w in want_labels if w not in resolved]
        if unknown:
            problems.append("rows not in the template: " + ", ".join(unknown)
                            + ". The row set is fixed: add none, remove none.")
        if missing:
            problems.append("rows missing: " + ", ".join(missing)
                            + ". A field that cannot be known is left empty, not removed.")

    want_shape, got_shape = heading_shape(want), heading_shape(content)
    if not is_subsequence(got_shape, want_shape):
        problems.append(f"heading shape is {got_shape}, the template is {want_shape}. "
                        f"Invent no section and keep the levels; a section that does not apply "
                        f"to this work may be dropped.")

    # Untouched-template test. Comparing against the template beats looking for placeholder
    # marks: three of the templates ship fixed prose of their own (a status legend, a date
    # line), so "every section is only dots" would never fire for them.
    if free_text_sections(content) == free_text_sections(want):
        problems.append("the prose is still the template's, word for word: this is the blank "
                        "form, not a note.")
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
                   help="work_item | task_note | test_note | incident_note | meeting_minutes | annex")
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
