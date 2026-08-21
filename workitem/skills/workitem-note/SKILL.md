---
name: workitem-note
description: Writes the result note for a finished work item, matching the tracker's note template for its type exactly, and proposes sub-tasks for work that happened outside the plan. Invoke when the user says the work is done and should be recorded, asks to close an item in the tracker, wants a result note or report of what was done, or asks for a test note or meeting minutes. Writes nothing to any tracker; the user enters it by hand.
---

# Result note

The step **after** the work. Produces **one file** per item, in the same directory as its
definition. Output language and label translation work exactly as in `/workitem-draft`.

## 1. Choose the template

| Work | Template |
|---|---|
| Code, feature, improvement, bug fix | `templates/task_note.md` |
| Test design or a verification run | `templates/test_note.md` |
| Production outage or failure | `templates/incident_note.md` |
| Meeting | `templates/meeting_minutes.md` |

If unsure, follow the item's type: Test -> test note, Incident -> incident note, Meeting ->
minutes, anything else -> task note.

## 2. The structure is fixed

**The template is the note, not a starting point.**

- **Add no rows** to the information table. The row set is exactly what the template lists.
- **Add no sections.** Do not invent Symptom, Diagnosis, Verification, Root cause or anything
  else, however useful it would be. Findings go inside the sections that exist.
- **Drop nothing and rename nothing.** A section that looks irrelevant still stays, because the
  tracker's page has it. Where a value is not knowable, leave it blank.
- Do not borrow a heading from another template: an incident note has no "Work done", a task note
  has no checklist table.
- The template being small **constrains how much belongs in the note.** Where the analysis does
  not fit, compress it and say the detail is attached — the page has an attachments area. Do not
  grow the note to fit the analysis.

## 3. Gather the material

**Code work.** The material comes from commits, and the rules plugin's commit discipline already
produces what the note needs:

```bash
python3 "$CLAUDE_PLUGIN_ROOT/scripts/workitem_output.py" commits \
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
  is not evidence. Status values are exactly three: passed, failed, pending. If any step failed or
  is pending, the findings section is mandatory.
- Impersonal voice, no conversation references — the same line as the commit rules.
- If a root cause is not yet known, say so; do not present a guess as one.
- Person names are absent from the reference on purpose. Inventing one puts wrong data in a
  company record.

## 5. Check it — mandatory

```bash
python3 "$CLAUDE_PLUGIN_ROOT/scripts/workitem_output.py" check \
  --file <path to the note> --template <task_note|test_note|incident_note|meeting_minutes>
```

The check compares the note's shape against the template: the number of information-table rows
and the sequence of heading levels. It exits non-zero and names what is off. **Fix the note; do
not extend the template.** It compares shape rather than wording, so it works in any language; a
renamed heading is the one deviation it cannot see, so that one is on you.

## 6. Hours

Estimate versus spent only makes sense if both are known. **Spent hours come from the user
alone** — ask. If the answer does not come, say so and leave it out; do not write 0 and do not
derive it from commit timestamps, which show elapsed time, not time worked.

## 7. Work outside the plan -> a sub-task

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

- a definition file following `templates/work_item.md`, with the parent named in the parent-issue
  row, the status it actually has, and the extra hours as its estimate and spent value
- a result note for its own type, checked like any other note

Then tell the user: this is a sub-task of `<parent>` — open it from the parent issue's sub-tasks
section, where the form is identical to the normal one — and here are its two files.

Do not fold unplanned work into the parent's note as a paragraph. That is precisely what the
sub-task exists to prevent.

## 8. Tell the user, in the output language

The file path, the suggested closing status and why, what was left blank, which files to attach
to the page, and any sub-tasks to open with their extra hours.
