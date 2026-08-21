---
name: workitem-draft
description: Writes the work item file to open in an issue tracker before the work starts — title, right-panel field values and description, in one file ready to work from. Invoke when the user says they will open an issue or task, asks for a work definition, wants the work recorded in the tracker before starting, or says something like "create the work item". Writes nothing to any tracker; the user enters it by hand.
---

# Work item definition

The step **before** the work. Produces **one file** and nothing else.

## 1. Output language

If the language is unknown, **ask**, then store it:

```bash
python3 "$CLAUDE_PLUGIN_ROOT/scripts/workitem_output.py" language --set tr
```

Everything the user reads is written in that language: the file, its headings, and what you say
in chat. Translate the structural wording with `references/labels.md` — it holds the section
titles, the field names and the fixed phrases. Commit messages are unaffected; those are English
by the rules plugin's spec.

## 2. Understand the work

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

A **range with its basis**, never a bare number: `3-5 h; six files touched, a comparable change
took 4 h`. A bare figure reads as a measurement and an estimate is not one.

The tracker attaches the estimate to the assignment, so the order is assign the person, then
enter it. With more than one assignee, splitting it is the user's call.

## 6. Where the file goes

`~/workitem-output/<number>-<slug>/` — one directory per work item, numbered the way the user
numbers their work. The definition file is `gorev.md` in Turkish, `issue.md` in English. The
result note joins it in the same directory later.

## 7. Tell the user, in the output language

The file path, which fields they select in the tracker (named as the tracker shows them — local
wording in `references/labels.md`), the estimate and what it rests on, and that the title goes in
the title box while the description block is pasted into the editor.
