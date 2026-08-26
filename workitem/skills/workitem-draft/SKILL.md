---
name: workitem-draft
description: Writes the work item file to open in an issue tracker before the work starts — title, right-panel field values and description, in one file ready to work from. Invoke when the user says they will open an issue or task, asks for a work definition, wants the work recorded in the tracker before starting, or says something like "create the work item". Writes nothing to any tracker; the user enters it by hand.
---

# Work item definition

The step **before** the work. Produces **one file** and nothing else: `gorev.html` in Turkish,
`issue.html` in English.

## 0. How the file reaches the tracker

The file is **HTML**, and the route matters: download it, open it in a **browser**, select, copy,
paste into the tracker. Copying from the file itself puts `text/plain` on the clipboard and the
editor falls back to its own markdown rules, which do not cover a checklist — so a criterion
arrives as a bullet with a literal `[x]` beside it. Copying from a rendered page puts `text/html`
on the clipboard and every element arrives as itself: real headings, real tables, real
checkboxes. Measured both ways; `references/labels.md` records what survives.

Write plain HTML and only these elements: `h1`-`h3`, `p`, `strong`, `em`, `s`, `code`, `hr`,
`blockquote`, `table`/`thead`/`tbody`/`tr`/`th`/`td`, `ul`, `ol`, `li`, and the checklist form
below. No `<!doctype>`, no `<html>`, no `<body>`, no `<style>`, no classes, and no attributes
beyond `data-type` and `data-checked` — a fragment renders in a browser and keeps the copy
clean. Start the file with `<meta charset="utf-8">` so the
browser does not guess the encoding and mangle the output language's letters; it is not content,
so it is not copied.

A checklist item is written exactly like this, and `data-checked` is the whole state:

```html
<ul data-type="taskList">
  <li data-type="taskItem" data-checked="true"><p>met criterion</p></li>
  <li data-type="taskItem" data-checked="false"><p>not met yet</p></li>
</ul>
```

This file feeds **three** places, so it is not one paste: the title goes in the title field, the
right panel values are chosen in the tracker, and only the description block is pasted. The
template carries a rule and a line saying where to start selecting — keep it.

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

Follow `templates/work_item.html`. Its shape, translated into the output language:

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

### The out-of-scope pass — do this before the file is final

An out-of-scope list written and left alone is where the next incident comes from. Once the list
exists, take each item and answer four questions:

1. Does a completion criterion depend on it? Then it was never out of scope.
2. Would deferring it leave something **wrong now** — a false number, an open permission, a state
   the system reports incorrectly in the meantime?
3. Does doing it later cost materially more? The same code touched twice, a migration re-run, data
   accumulating in the wrong shape until then.
4. Is it a silent risk — nothing fails, nothing alerts, and the damage is only visible later?

**Yes to 2, 3 or 4 moves it into Scope**, with one line in the item saying why it moved. The
estimate is re-derived afterwards; pulling work in and leaving the estimate alone makes the item
lie.

**A claim has to be grounded.** "This will break later" counts only with the file, the measurement
or the code path that shows it. Where it cannot be grounded, say so and treat it as a watch item
rather than a certainty — a guess pulled into scope costs as much as a real risk left out.

**Then put the remainder to the user and wait.** Number them, and for each give: what it is, what
happens if it waits, and roughly what it costs to do now. Ask which ones to pull into this item.
This changes scope and estimate, so it is asked before the file is finished, not reported after.

**Whatever stays out keeps its reason.** Each remaining entry carries a short clause — why it is
safe to defer, or which risk is being accepted. A bare line is a decision nobody made; a line with
its risk is a decision on record, and it is where the next work item comes from.

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
`gorev.html` in Turkish, `issue.html` in English. The result note joins it in the same directory
later, as `not.html` or `note.html`, and any annex as `ek-<n>-<slug>.html` or
`annex-<n>-<slug>.html`.

**The number comes from the user** — it has to match what the tracker gave the item. Ask for it.
If they do not have it yet, offer one past the highest already in `~/workitem-output/` and say it
is a placeholder to be renamed once the tracker assigns the real one. Do not infer a scheme from
the directory listing: more than one may be in use there.

## 8. Tell the user, in the output language

The file path, which fields they select in the tracker (named as the tracker shows them — local
wording in `references/labels.md`), the estimate and what it rests on, and that the title goes in
the title box while the description block is pasted into the editor.
