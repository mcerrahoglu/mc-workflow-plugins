#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Work item output writer and commit material collector.

Writes nothing to any tracker. It produces paste-ready files; the user enters them by hand.
That keeps the plugin tracker-independent: nothing here knows or needs an API.

The script is FORMAT-AGNOSTIC. It writes the content it is given, unchanged. If a tracker's
editor turns out to need a different markup, only templates/*.md change and this code does not.

Output root is always ~/workitem-output; a relative path is refused so output cannot land
inside a repository by accident.

Usage:
  ... | workitem_output.py write --mode note --title "Gate false positives closed" \\
          --type Task --estimate-hours "3-5" --rationale "six files touched" --lang en

  workitem_output.py commits --since 2026-08-17 --repo ~/project-a --repo ~/project-b

  workitem_output.py language          # show the stored output language
  workitem_output.py language --set tr # store it (kept outside the repository)
"""
import argparse
import datetime
import json
import pathlib
import re
import subprocess
import sys

OUTPUT_ROOT = pathlib.Path.home() / "workitem-output"
CONFIG_PATH = pathlib.Path.home() / ".workitem" / "config.json"
TEMPLATES = pathlib.Path(__file__).resolve().parent.parent / "templates"

SELECT_IN_TRACKER = ["PRIORITY", "STATUS", "SPRINT", "WORK PACKAGE", "DUE DATE", "ASSIGNEE"]

# File names follow the output language, so the directory reads the way the user works. These
# are identifiers, not prose: a new language is one line here. ASCII only, to keep the names
# portable across filesystems.
FILE_NAMES = {
    "tr": {"issue": "gorev", "note": "not", "fields": "alanlar"},
}
DEFAULT_FILE_NAMES = {"issue": "issue", "note": "note", "fields": "fields"}


def file_name(kind, language):
    return FILE_NAMES.get((language or "").lower(), DEFAULT_FILE_NAMES).get(
        kind, DEFAULT_FILE_NAMES[kind]) + ".md"
PLACEHOLDER = "…"                       # the single character a blank section carries

_FOLD = str.maketrans({
    "ı": "i", "İ": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g", "ü": "u", "Ü": "u",
    "ö": "o", "Ö": "o", "ç": "c", "Ç": "c", "â": "a", "î": "i", "û": "u",
})


def slug(text, limit=40):
    s = text.translate(_FOLD).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:limit].rstrip("-") or "item"


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


# --------------------------------------------------------------- blanks left for the user
def find_blanks(content):
    """List what the generator left for the user to fill.

    Derived from the content itself rather than written by hand, so the list stays correct
    when a template changes. Two shapes count as blank: an info-table row whose value cell
    is empty, and a section whose only body is the placeholder character.
    """
    blanks, section, headers = [], None, None
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#"):
            section = stripped.lstrip("#").strip()
            headers = None
            continue
        if stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(set(c) <= {"-", ":"} and c for c in cells):
                continue                                  # separator row
            if headers is None:
                headers = cells
                continue
            label = cells[0].strip("*")
            if len(cells) == 2 and label and not cells[1]:
                blanks.append(label)
            elif len(cells) > 2 and not any(cells):
                where = section or "table"
                entry = f"{where}: {', '.join(h for h in headers if h)}"
                if entry not in blanks:
                    blanks.append(entry)
            continue
        if stripped in (PLACEHOLDER, f"- {PLACEHOLDER}", f"1. {PLACEHOLDER}") and section:
            if section not in blanks:
                blanks.append(section)
        if not stripped:
            headers = None
    return blanks


def fields_text(args, blanks, language):
    """Emit data only: no prose, so nothing here needs translating.

    The script cannot know the output language well enough to write sentences in it, and an
    earlier version wrote English prose while claiming to honour `--lang`. Headings and field
    names stay canonical English, exactly like the templates; the accompanying explanation is
    given by the skill, in the user's language. Anything a reader needs as a sentence belongs
    there, not here.
    """
    lines = [
        f"# {args.title}",
        "",
        f"{datetime.date.today().isoformat()} · {args.mode} · {language}",
        "",
        "## Generated",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| TITLE | {args.title} |",
        f"| TYPE | {args.type or '-'} |",
    ]
    if args.estimate_hours:
        lines.append(f"| ESTIMATE (hours) | {args.estimate_hours} |")
        lines.append(f"| ESTIMATE BASIS | {args.rationale} |")
    lines += ["", "## Select in the tracker", ""]
    lines += [f"- {field}" for field in SELECT_IN_TRACKER]
    lines += ["", "## Fill after pasting", ""]
    lines += [f"- {b}" for b in blanks] if blanks else ["- (none)"]
    lines.append("")
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------- structure checking
def first_table_rows(text):
    """Count data rows of the first table: the information table of a note template."""
    rows, in_table, seen_any = 0, False, False
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("|"):
            in_table = True
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(set(c) <= {"-", ":"} and c for c in cells):
                continue                                   # separator
            if not seen_any:
                seen_any = True                            # header row
                continue
            rows += 1
        elif in_table and not stripped:
            break                                          # first table ended
    return rows


def heading_shape(text):
    """Heading levels in order. Language independent: counts shape, not wording."""
    shape = []
    in_fence = False
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


def check_structure(content, template_name):
    """Return a list of problems; empty means the note matches the template exactly.

    Compares shape rather than wording, so it works whatever language the note is in.
    A renamed heading is not caught; an added row or an invented section is, and those are
    the deviations that actually happened.
    """
    template = TEMPLATES / f"{template_name}.md"
    if not template.is_file():
        available = ", ".join(sorted(t.stem for t in TEMPLATES.glob("*.md")))
        return [f"unknown template `{template_name}`; available: {available}"]
    want = template.read_text(encoding="utf-8")

    problems = []
    want_rows, got_rows = first_table_rows(want), first_table_rows(content)
    if want_rows != got_rows:
        problems.append(
            f"information table has {got_rows} rows, the template has {want_rows}. "
            f"The row set is fixed: add none, remove none.")
    want_shape, got_shape = heading_shape(want), heading_shape(content)
    if want_shape != got_shape:
        problems.append(
            f"heading shape is {got_shape}, the template is {want_shape}. "
            f"Sections are fixed: invent none, drop none, and do not change their level.")
    return problems


def issue_guide(args, content, language):
    """One file to work from: title, right-panel values, description. Data only."""
    lines = [
        f"# {args.title}",
        "",
        f"{datetime.date.today().isoformat()} · issue · {language}",
        "",
        "## Title",
        "",
        args.title,
        "",
        "## Right panel",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| TYPE | {args.type or '-'} |",
    ]
    if args.estimate_hours:
        lines.append(f"| ESTIMATE (hours) | {args.estimate_hours} |")
        lines.append(f"| ESTIMATE BASIS | {args.rationale} |")
    lines += [f"| {field} | select in the tracker |" for field in SELECT_IN_TRACKER]
    lines += ["", "## Description", "", content.rstrip(), ""]
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------------------ commands
def cmd_write(args):
    if args.estimate_hours and not args.rationale:
        sys.exit("error: --estimate-hours requires --rationale. A bare number reads as a "
                 "measurement; state what the estimate rests on.")
    content = (args.content_file.read_text(encoding="utf-8") if args.content_file
               else sys.stdin.read())
    if not content.strip():
        sys.exit("error: content is empty (expected on stdin or via --content-file)")

    language = args.lang or read_language()
    if not language:
        sys.exit("error: no output language known. Pass --lang, or store one with "
                 "`workitem_output.py language --set <code>`.")

    if args.mode == "note":
        if not args.template:
            sys.exit("error: --template is required for a note, so its structure can be "
                     "checked against the template it must match.")
        problems = check_structure(content, args.template)
        if problems:
            sys.exit("error: the note does not match `" + args.template + "`:\n  - "
                     + "\n  - ".join(problems)
                     + "\nNothing was written. Fix the structure, do not extend the template.")

    target = OUTPUT_ROOT / f"{datetime.date.today().isoformat()}-{slug(args.title)}"
    target.mkdir(parents=True, exist_ok=True)

    if args.mode == "issue":
        path = target / file_name("issue", language)
        path.write_text(issue_guide(args, content, language), encoding="utf-8")
        print(f"Written:\n  {path}")
        print("One file, in paste order: title, right panel values, description.")
        return 0

    content_path = target / file_name("note", language)
    content_path.write_text(content, encoding="utf-8")
    blanks = find_blanks(content)
    fields_path = target / file_name("fields", language)
    fields_path.write_text(fields_text(args, blanks, language), encoding="utf-8")
    print(f"Written:\n  {content_path}\n  {fields_path}")
    print(f"Structure matches `{args.template}`.")
    if blanks:
        print(f"Left blank for you ({len(blanks)}): " + ", ".join(blanks[:6])
              + (" ..." if len(blanks) > 6 else ""))
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
            body = parts[3].strip() if len(parts) > 3 else ""
            for line in body.splitlines():
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
        current = read_language()
        print(f"Output language: {current or 'not set'}  ({CONFIG_PATH})")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Produce paste-ready work item content.")
    sub = ap.add_subparsers(dest="command", required=True)

    w = sub.add_parser("write", help="write content under ~/workitem-output")
    w.add_argument("--mode", choices=("issue", "note"), required=True)
    w.add_argument("--title", required=True)
    w.add_argument("--type")
    w.add_argument("--estimate-hours", dest="estimate_hours")
    w.add_argument("--rationale")
    w.add_argument("--lang")
    w.add_argument("--template", help="note template the structure must match")
    w.add_argument("--content-file", type=pathlib.Path, dest="content_file")
    w.set_defaults(func=cmd_write)

    c = sub.add_parser("commits", help="collect commit material for a result note")
    c.add_argument("--since", help="date or git ref (REQUIRED)")
    c.add_argument("--repo", action="append")
    c.set_defaults(func=cmd_commits)

    l = sub.add_parser("language", help="show or store the output language")
    l.add_argument("--set")
    l.set_defaults(func=cmd_language)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
