---
name: workitem-draft
description: Produces paste-ready content for a work item to be opened in an issue tracker before the work starts — title, description and type, plus an effort estimate with its basis. Invoke when the user says they will open an issue or task, asks for a work definition, wants the work recorded in the tracker before starting, or says something like "define this in the tracker". Writes nothing to any tracker; the user enters the output by hand.
---

# Work item definition

The step **before** the work: turns what is about to be done into content that can be pasted
into a tracker. Nothing is sent anywhere — the output is files, and the user enters them.

## 1. Output language

If the language is unknown, **ask** before generating, then store it:

```bash
python3 "$CLAUDE_PLUGIN_ROOT/scripts/workitem_output.py" language            # show
python3 "$CLAUDE_PLUGIN_ROOT/scripts/workitem_output.py" language --set tr   # store
```

The stored preference lives outside this repository. Section headings and table labels are
translated with `references/labels.md`; the structure stays the same in every language. Note
that **commit messages are unaffected** — those are English by the rules plugin's spec.

## 2. Understand the work

What will be done and why? If it is unclear, **ask**. Filling a field on a guess produces a
record someone has to correct later.

## 3. Choose the type

Valid values and the decision table are in `references/field-reference.md` — **read it and pick
from it**, do not produce values from memory. Regression -> `Bug`; wrong or incomplete from the
start -> `Defect`; new capability -> `Feature`; quality or speed of something that works ->
`Improvement`; nothing fits -> `Task`.

**Everything else is chosen by the user in the tracker**: priority, status, sprint, work package,
due date, assignee. Do not generate them. If a value is needed that is not on a list, do not
invent it.

## 4. Write the description

Use `templates/issue_description.md`: Purpose, Scope, Out of Scope, Completion Criteria, and
Dependencies or Risks where they exist.

- **A definition, not a report.** Measurements and results are written at closing time with
  `/workitem-note`, not here.
- **Completion criteria must be verifiable** — "works well" is not a criterion, "X appears on
  screen Y" is.
- If TYPE is `Customer Requirement` or `Software Requirement`, the description is written in the
  EARS form instead: see `references/ears.md`.
- **Delete a section that does not apply**; do not write "none".
- **Keep a section that applies but whose value is not knowable here** and leave it blank. Free
  text carries a single `…`; a table cell stays empty. The script lists these under "fill after
  pasting".

## 5. Estimate the effort

Give a **range with its basis**, not a bare number: `3-5 h; six files touched, a comparable
change took 4 h`. `--estimate-hours` requires `--rationale` and the script refuses without it,
because a bare figure reads as a measurement and an estimate is not one.

Many trackers attach the estimate to the assignment, so it only appears after a person is
assigned: the order is assign first, then enter the estimate.

## 6. Write the output

```bash
python3 "$CLAUDE_PLUGIN_ROOT/scripts/workitem_output.py" write --mode issue \
  --title "<title>" --type "<type>" \
  --estimate-hours "3-5" --rationale "<what the estimate rests on>" < content.md
```

## 7. Tell the user

The file path, which fields to select in the tracker, what was left blank, and the basis of the
estimate. Paste into a **blank page**, not into the tracker's own template — a Markdown pipe
table becomes a real table on paste, so one paste is enough and the result looks native. Save,
reload, and check the tables survived.
