---
name: workitem-note
description: Writes the result note for a finished work item, matching the tracker's note template for its type exactly, and proposes sub-tasks for work that happened outside the plan. Invoke when the user says the work is done and should be recorded, asks to close an item in the tracker, wants a result note or report of what was done, or asks for a test note or meeting minutes. Writes nothing to any tracker; the user enters it by hand.
---

# Result note

The step **after** the work. Produces **one file** per item — `not.html` in Turkish,
`note.html` in English — in the same directory as its definition, plus an annex when one is
needed (section 5).

## 0. How the file reaches the tracker

The file is **HTML**, and the route matters: download it, open it in a **browser**, select, copy,
paste into the tracker. Copying from the file itself puts `text/plain` on the clipboard and the
editor falls back to its own markdown rules, which do not cover a checklist — so a criterion
arrives as a bullet with a literal `[x]` beside it. Copying from a rendered page puts `text/html`
on the clipboard and every element arrives as itself: real headings, real tables, real
checkboxes. Measured both ways; `references/labels.md` records what survives.

Write plain HTML and only these elements: `h1`-`h3`, `p`, `strong`, `em`, `s`, `code`, `hr`,
`blockquote`, `table`/`thead`/`tbody`/`tr`/`th`/`td`, `ul`, `ol`, `li`, and the checklist form
below. No `<!doctype>`, no `<html>`, no `<body>`, no `<style>`, no classes — a fragment renders
in a browser and keeps the copy clean. Start the file with `<meta charset="utf-8">` so the
browser does not guess the encoding and mangle the output language's letters; it is not content,
so it is not copied.

A checklist item is written exactly like this, and `data-checked` is the whole state:

```html
<ul data-type="taskList">
  <li data-type="taskItem" data-checked="true"><p>met criterion</p></li>
  <li data-type="taskItem" data-checked="false"><p>not met yet</p></li>
</ul>
```

## 0. Output language

**Read the stored preference first**, the same way `/workitem-draft` does. That skill's text is
not loaded here, so the command is repeated rather than referred to:

```bash
SCRIPT="${CLAUDE_PLUGIN_ROOT:-$(ls -d ~/.claude/plugins/cache/*/workitem/*/ 2>/dev/null | sort -V | tail -1)}/scripts/workitem_output.py"
python3 "$SCRIPT" language            # prints the stored language, or says there is none
```

Dates are written in the output language's own convention — the format is in
`references/labels.md` (`GG.AA.YYYY` for Turkish, so `26.08.2026`). A range uses the same
format on both sides. The only exception is the `--since` argument below, which is a git
input and stays ISO.

Ask only if nothing is stored, then store the answer with `language --set <code>`. If
`CLAUDE_PLUGIN_ROOT` is empty the fallback finds the installed copy; the cache path carries a
version number, so never hardcode one. Structural wording is translated with
`references/labels.md`.

## 1. Choose the template

| Work | Template |
|---|---|
| Code, feature, improvement, bug fix | `templates/task_note.html` |
| Test design or a verification run | `templates/test_note.html` |
| Production outage or failure | `templates/incident_note.html` |
| Meeting | `templates/meeting_minutes.html` |

If unsure, follow the item's type: Test -> test note, Incident -> incident note, Meeting ->
minutes, anything else -> task note. None of them fitting is what the tracker's blank page is
for.

Paste the **whole note into a blank page** rather than picking the tracker's own template and
filling cells one at a time: pasted from a browser the whole structure arrives native, so it is
one step and nothing is retyped.

## 2. The structure is fixed

**The template is the note, not a starting point.**

- **Add no rows** to the information table. The row set is exactly what the template lists.
- **Add no sections.** Do not invent Symptom, Diagnosis, Verification, Root cause or anything
  else, however useful it would be. Findings go inside the sections that exist.
- **Rename nothing, and drop only what cannot apply.** A section that merely looks irrelevant
  stays, because the tracker's page has it; one that genuinely cannot apply to this work — a
  root cause for a new feature, dependencies where there are none — is dropped rather than
  filled with "none". Where a value is not knowable, leave it blank.
- Do not borrow a heading from another template: an incident note has no "Work done", a task note
  has no checklist table.
- The template being small **constrains how much belongs in the note.** Where the analysis does
  not fit, compress the note and put the rest in an annex — but see section 5: an annex is
  something you **produce**, never something you ask the user to find.

## 3. Gather the material

**Code work.** The material comes from commits, and the rules plugin's commit discipline already
produces what the note needs:

```bash
python3 "$SCRIPT" commits \
  --since <date|ref> --repo <path> [--repo <path> ...]
```

`--since` is required. "The commits from this session" is undefined when work spans several
repositories and days. If the range is unclear, **ask**.

**Work with no commits** — the material is elsewhere: a test run's command and output; an
incident's log lines, times and who reported it; a meeting's attendees, decisions and actions.

## 4. Write it

- **Measurements as before -> after** on a named input. Never present an unmeasured claim as
  measured.
- **In a test note the actual column carries evidence** — a measurement, a quote, output. "works"
  is not evidence. Status values are exactly the four the template's legend lists: passed, partial,
  failed, pending. If any step failed, was partial or is pending,
  is pending, the findings section is mandatory.
- Impersonal voice, no conversation references — the same line as the commit rules.
- If a root cause is not yet known, say so; do not present a guess as one.
- Person names are absent from the reference on purpose. Inventing one puts wrong data in a
  company record.

## 5. Overflow goes into an annex you produce

Never write "the details are attached" or "upload the measurements" and stop there. The user
cannot know what to attach; naming a thing without producing it is the same failure as naming a
field without filling it.

So where content does not fit the note, write an annex file next to the other two, following
`templates/annex.html`:

- named `ek-<n>-<slug>.html` in Turkish, `annex-<n>-<slug>.html` in English
- titled `EK-<n> — <name>`, with a line under the title saying which work item it belongs to,
  where the material came from, and whether anything was shortened
- free in shape: an annex has no fixed structure, because what it holds depends on the work.
  Only the note has a fixed structure.

**An annex holds measurement evidence, not engineering detail.** What belongs: A/B comparisons,
before and after tables, metric breakdowns, per-case results, the counts behind a claim — the
numbers a reader can weigh without running anything. These are exactly what would crowd the note
and pull it away from its purpose, while still needing to be shown.

What does not belong: commands to run, code, configuration, commit lists. Those live in the code
repository and its history; a tracker annex is read, not executed. If a claim rests on a command,
put the command's **result** in the annex and leave the command where the code is.

Give each table a line saying what was measured and how, so a number can be interpreted a month
later.

The note must then **name the annex** in its own text, so the two are linked: "Detail: EK-1 —
<name>". Say where each thing goes rather than offering a choice — deciding that is the work:

- **the annex itself** goes on its own page in the tracker (a second note, notebook or
  whatever the tool calls one), pasted the same way. A measurement annex runs to dozens of
  table rows and would bury the note it belongs to.
- **images and other binaries** go to the attachments area as files. They cannot be pasted.
- a short annex, a handful of rows, can stay in the note as its own titled section.

If something genuinely cannot be produced here — a screenshot, a file only on the user's
machine — then say exactly what to capture and where it goes. Never "attach the details".

## 6. Check it — mandatory

```bash
python3 "$SCRIPT" check \
  --file <path to the note> --template <task_note|test_note|incident_note|meeting_minutes>
```

It exits non-zero and names what is off. **Fix the note; do not extend the template.** What it
measures:

- **rows, by label.** Labels are canonicalised through `references/labels.md`, so an invented
  field is named in the error and a note written from the wrong template is caught — the four
  note templates all have five rows, so counting them proved nothing. Order is free.
- **sections, by level, as a subsequence.** A section that cannot apply may be dropped; an
  invented one is refused.
- **the blank form.** Prose identical to the template word for word is the empty form, not a
  note.

Not seen: a renamed section, section order, and — where the output language is one
`labels.md` does not cover — anything beyond the row count. Those are on you.

## 7. Hours

Estimate versus spent only makes sense if both are known. **Spent hours come from the user
alone** — ask. If the answer does not come, say so and leave it out; do not write 0 and do not
derive it from commit timestamps, which show elapsed time, not time worked.

## 8. Work outside the plan -> a sub-task

A sub-task records work that was **not planned**, came up while doing the planned work, and cost
extra hours. Recording it keeps that time visible as its own line instead of buried in the parent's
note.

**When it is opened does not matter. That it is recorded does.** Two paths, and choosing between
them is your judgement, not the user's to chase:

**It needs planning — raise it immediately.** Stop, say what came up, and propose opening the
sub-task before continuing. Then do it, then return to the main plan. Use this path when the thing
has scope of its own: it needs its own completion criteria, it changes the main work's scope or
estimate, it blocks the main work, or it will cost enough time that someone reading the parent's
note later would ask where those hours went. This is a plan-external situation, so the working
rules already require reporting it; what this skill adds is that the record takes the shape of a
sub-task.

**It is small and contained — do not break the flow.** Fix it, finish the planned work, and at
closing say: this came up, it was fixed, let us add it as a sub-task. Use this path when it has no
scope of its own and no planning to do — a one-line fix, an obvious oversight, a few minutes.

The failure to avoid is silence: fixing something unplanned and mentioning it nowhere. If you
cannot tell which path applies, say so and let the user choose — an unnecessary question costs a
sentence, an unrecorded hour costs the report.

### Producing it

For each unplanned item, a pair in a directory named after the parent, for example
`<parent-number>.1-<slug>/`:

- a definition file following `templates/work_item.html`, with the parent named in the parent-issue
  row, the status it actually has, and the extra hours as its estimate and spent value
- a result note for its own type, checked like any other note

Then tell the user: this is a sub-task of `<parent>` — open it from the parent issue's sub-tasks
section, where the form is identical to the normal one — and here are its two files.

Do not fold unplanned work into the parent's note as a paragraph. That is precisely what the
sub-task exists to prevent.

## 9. Tell the user, in the output language

The file paths — including any annex you produced — the suggested closing status and why, what
was left blank, and any sub-tasks to open with their extra hours.

Also give the reference for the commit footer: `Refs: #<the item's id>`. That footer is the only
thing tying a commit back to the item, and the id lives here, not in the repository.

