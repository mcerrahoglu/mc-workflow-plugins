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
import html
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
TAG_RE = re.compile(r"</?[a-zA-Z][^>]*>")   # not r"<[^>]+>": that ate "alarm at < 1.500 ms"
TABLE_RE = re.compile(r"<table\b.*?</table>", re.S | re.I)
TBODY_RE = re.compile(r"<tbody\b.*?</tbody>", re.S | re.I)
ROW_RE = re.compile(r"<tr\b.*?</tr>", re.S | re.I)
CELL_RE = re.compile(r"<(t[dh])\b[^>]*>(.*?)</\1>", re.S | re.I)
TASKLIST_RE = re.compile(r'data-type\s*=\s*"taskList"', re.I)
TASKITEM_RE = re.compile(r'data-type\s*=\s*"taskItem"', re.I)
HEADING_RE = re.compile(r"<h([1-6])\b", re.I)


def looks_like_html(text):
    """Output has been HTML since 2.0.0; a markdown file must fail loudly, not silently.

    The test is the FIRST meaningful line, not "a tag appears somewhere": documentation that
    quotes markup in a code block would otherwise pass as HTML. Generated files open with
    `<meta charset="utf-8">`, which is why that line is required rather than merely suggested.
    """
    for line in text.split("\n"):
        if line.strip():
            return line.lstrip().startswith("<")
    return False


def strip_tags(fragment):
    return " ".join(html.unescape(TAG_RE.sub(" ", fragment)).split())


def first_table_labels(text):
    """First-column values of the first table's data rows: the information table's labels."""
    table = TABLE_RE.search(text)
    if not table:
        return []
    body = TBODY_RE.search(table.group(0))
    scope = body.group(0) if body else table.group(0)
    labels = []
    for row in ROW_RE.findall(scope):
        cells = CELL_RE.findall(row)
        if not cells:
            continue
        tag, first = cells[0]
        if tag.lower() == "th":
            continue        # a header row. Judged per cell, not by whether a tbody exists:
                            # editors that emit no thead put the header inside tbody, and the
                            # guard then read "Field" as an invented row.
        labels.append(strip_tags(first))
    return labels


def heading_shape(text):
    """Heading levels in order. Shape, not wording, so it is language independent."""
    return [int(level) for level in HEADING_RE.findall(text)]


def free_text_sections(text):
    """Text per section, whitespace normalised.

    Table cells are included. Dropping them made a filled-in test note read as a blank form,
    because a test note's substance IS its checklist table, and made an invented table
    invisible.
    """
    return [strip_tags(part) for part in re.split(r"<h[1-6]\b[^>]*>", text, flags=re.I)]


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
        cells = [c.strip() for c in line.strip().strip("|").split("|")] \
            if line.strip().startswith("|") else []
        if len(cells) != 2 or cells[0] in ("English", "") or set(cells[0]) <= {"-", ":"}:
            continue
        rev.setdefault(cells[1], cells[0])
    return rev


def is_subsequence(small, big):
    it = iter(big)
    return all(any(x == y for y in it) for x in small)


def compare_with_template(content, template_name):
    """Return a list of problems; empty means the note matches the template exactly."""
    template = TEMPLATES / f"{template_name}.html"
    if not template.is_file():
        available = ", ".join(sorted(t.stem for t in TEMPLATES.glob("*.html")))
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

    want_lists, got_lists = len(TASKLIST_RE.findall(want)), len(TASKLIST_RE.findall(content))
    if want_lists and not got_lists:
        problems.append('the checklist is missing its markup: a checklist is '
                        '<ul data-type="taskList"> with <li data-type="taskItem" '
                        'data-checked="true|false">. Without it the list pastes as plain '
                        'bullets, which is the whole reason this file is HTML.')
    elif want_lists != got_lists:
        problems.append(f"{got_lists} checklists, the template has {want_lists}.")
    elif got_lists and not TASKITEM_RE.search(content):
        problems.append('a taskList holds no taskItem: each line is '
                        '<li data-type="taskItem" data-checked="true|false">.')

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
    content = path.read_text(encoding="utf-8")
    if not looks_like_html(content):
        sys.exit(f"error: {path.name} is not HTML. Work item files and notes have been HTML since "
                 f"2.0.0, because a native checklist only survives a paste that carries text/html. "
                 f"A markdown file cannot be compared against an HTML template.")
    if args.template == "annex":
        # An annex has no fixed section list by design: what it holds depends on the work.
        # Comparing its shape against the starting point would fail every real annex.
        if not heading_shape(content):
            sys.exit(f"error: {path.name} carries no heading. An annex has no fixed section "
                     f"list, but it does have sections: a title and one per thing measured.")
        print(f"OK: {path.name} is HTML with {len(heading_shape(content))} sections. An annex "
              f"has no fixed shape, so nothing further was compared.")
        return 0
    problems = compare_with_template(content, args.template)
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
