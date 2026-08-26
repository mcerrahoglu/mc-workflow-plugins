---
name: workitem-draft
description: Writes the work item file to open in an issue tracker before the work starts — title, right-panel field values and description, in one file ready to work from. Invoke when the user says they will open an issue or task, asks for a work definition, wants the work recorded in the tracker before starting, or says something like "create the work item". Writes nothing to any tracker; the user enters it by hand.
---

# Work item definition

The step **before** the work. Produces **one file** and nothing else.

## 1. Output language

**Read the stored preference first** — it is stored so this is asked once, not every time:

```bash
SCRIPT="${CLAUDE_PLUGIN_ROOT:-$(ls -d ~/.claude/plugins/cache/*/workitem/*/ 2>/dev/null | sort -V | tail -1)}/scripts/workitem_output.py"
python3 "$SCRIPT" language            # prints the stored language, or says there is none
python3 "$SCRIPT" language --set tr   # only when it was unknown and the user has said
```

If `CLAUDE_PLUGIN_ROOT` is empty the fallback above finds the installed copy; the cache path
carries a version number, so never hardcode one. If neither resolves, ask the user for the path
rather than guessing.

Dates are written in the output language's own convention — the format is in
`references/labels.md` (`GG.AA.YYYY` for Turkish, so `26.08.2026`). A range uses the same
format on both sides. The only exception is a git argument, which stays ISO.

Everything the user reads is written in that language: the file, its headings, and what you say
in chat. Translate the structural wording with `references/labels.md` — it holds the section
titles, the field names and the fixed phrases. Commit messages are unaffected; those are English
by the rules plugin's spec.

## 2. Understand the work — and whether this is a sub-task

If this is being written **mid-work**, because something unplanned came up that needs planning of
its own, it is a sub-task: name the parent in the parent-issue row and put it in a directory named
after the parent (`<parent-number>.1-<slug>/`, then `.2`, `.3`). It earns a sub-task when it had
its own scope, changed the parent's scope or estimate, blocked the parent, or would leave someone
asking where those hours went; `/workitem-note` section 8 carries the full judgement, including
when to interrupt rather than wait.

What will be done and why? If it is unclear, **ask**. A field filled on a guess becomes a record
someone corrects later.

## 3. Choose the type

Valid values and the decision table are in `references/field-reference.md` — read it and pick from
it. Regression -> Bug; wrong from the start -> Defect; new capability -> Feature; quality or speed
of something that works -> Improvement; nothing fits -> Task.

Only **type**, **status** and **estimate** are decided here. Priority, sprint, work package, due
date, assignee and labels depend on the project and the team, so they are marked as chosen in the
tracker. Never invent a value that is not on a list.

## 4. Write the file

Follow `templates/work_item.md`. Its shape, translated into the output language:

- a heading with the number and a short summary
- a note saying this is the content for the tracker's new-issue screen
- **title** — the exact line to type, in backticks so it is copied cleanly
- **right panel fields** — a table: the decided values in bold, the rest marked as chosen in the
  tracker
- **estimate basis** — one line under the table
- **description** — Purpose, Scope, Out of Scope, Completion Criteria, to paste into the editor

Rules for the description:

- It is a **definition, not a report.** Measurements and results are written at closing with
  `/workitem-note`.
- **Completion criteria must be verifiable** — "works well" is not a criterion; "X appears on
  screen Y" is.
- For a requirement type, write the description in the EARS form instead: `references/ears.md`.
- Delete a section that genuinely does not apply; do not write "none". Keep a section whose value
  is simply unknown and leave it blank.

## 5. Estimate

A **range with its basis**, never a bare number. The mechanics, the worked example and the
multiple-assignee case are in `references/field-reference.md`, already open from section 3.

## 6. Check it

```bash
python3 "$SCRIPT" check --file <path to the file> --template work_item
```

Same check the result note goes through, and for the same reason: the right panel has a fixed
row set, so a field invented here has to be reconciled by hand in the tracker. Fix the file, not
the template.

## 7. Where the file goes

`~/workitem-output/<number>-<slug>/` — one directory per work item. The definition file is
`gorev.md` in Turkish, `issue.md` in English. The result note joins it in the same directory
later, as `not.md` or `note.md`, and any annex as `ek-<n>-<slug>.md` or `annex-<n>-<slug>.md`.

**The number comes from the user** — it has to match what the tracker gave the item. Ask for it.
If they do not have it yet, offer one past the highest already in `~/workitem-output/` and say it
is a placeholder to be renamed once the tracker assigns the real one. Do not infer a scheme from
the directory listing: more than one may be in use there.

## 8. Tell the user, in the output language

The file path, which fields they select in the tracker (named as the tracker shows them — local
wording in `references/labels.md`), the estimate and what it rests on, and that the title goes in
the title box while the description block is pasted into the editor.
