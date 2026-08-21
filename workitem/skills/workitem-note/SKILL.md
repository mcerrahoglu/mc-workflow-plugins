---
name: workitem-note
description: Produces the paste-ready result note for a finished work item — task, test, incident or meeting template — together with a suggested closing status. Invoke when the user says the work is done and should be recorded, asks to close an item in the tracker, wants a result note or report of what was done, or asks for a test note or meeting minutes. Writes nothing to any tracker; the user enters the output by hand.
---

# Result note

The step **after** the work: turns what was done into a note that can be pasted into a tracker,
and proposes the item's new status.

Output language: as in `/workitem-draft`, ask if unknown and translate labels with
`references/labels.md`.

## 1. Choose the template

| Work | Template |
|---|---|
| Code, feature, improvement, bug fix | `templates/task_note.md` |
| Test design or a verification run | `templates/test_note.md` |
| Production outage or failure | `templates/incident_note.md` |
| Meeting | `templates/meeting_minutes.md` |

If unsure, follow the item's type: Test -> test note, Incident -> incident note, Meeting ->
minutes, anything else -> task note.

## 2. Gather the material

**Code work.** The material comes from commits. The rules plugin's commit discipline already
produces "what the problem was -> root cause -> what changed -> how it was verified", which is
exactly what the note needs.

```bash
python3 "$CLAUDE_PLUGIN_ROOT/scripts/workitem_output.py" commits \
  --since <date|ref> --repo <path> [--repo <path> ...]
```

`--since` is **required**. "The commits from this session" is an undefined selector: work spans
several repositories and several days. If the range is unclear, **ask** — do not guess.

**Work with no commits.** Do not go looking for commits; the material is elsewhere:
- Test note -> the command that was run, its output, the environment (version, URL)
- Incident note -> log lines, dashboards, alerts, times, who reported it
- Meeting minutes -> what the user recounts; ask for attendees, decisions and actions
- Support -> the request text and what was done

## 3. Effort

Estimate versus actual only makes sense if both are known. **Actual hours come from the user
alone** — ask. If the answer does not come, **delete the actual and variance rows entirely**:
do not write 0, and do not derive them from commit timestamps. Timestamps show elapsed time,
which is not time worked.

## 4. Write the note

**The structure is fixed by the template. It is not a starting point to build on.**

- Use the template for the item's type and no other. Do not borrow a heading from a different
  template: an incident note has no "Work Done / Description", a task note has no checklist table.
- **Add no rows to the information table.** The row set is exactly what the template lists.
  Effort is a tracker field, not a note row — the estimate belongs in `fields.md`. If the user
  gives actual hours, write them as a sentence inside `Notes`, not as a new row.
- **Add no sections.** Do not invent `Symptom`, `Diagnosis`, `Verification`, `Root cause` or
  anything else, however useful it would be. Findings go inside the sections that exist.
- **Rename nothing.** Headings and row labels come from the template, translated only through
  `references/labels.md`.
- The template being small is a constraint on how much belongs in the note. Where the analysis
  does not fit, compress it and say the detail is attached — the page has an attachments area.
  Do not grow the note to fit the analysis.

Then fill it:

- **Measurements as before -> after** on a named input: `1297 -> 770 s, recall unchanged at 0.88`.
  Never present an unmeasured claim as measured.
- **In a test note the ACTUAL column carries evidence** — a measurement, a quote or output.
  "works" is not evidence. Status values are exactly three: `✅ Passed`, `❌ Failed`,
  `🟪 Pending`. If any step failed or is pending, the Findings section is mandatory.
- **Impersonal voice**, no conversation references — the same line as the commit rules.
- In an incident note, if the root cause is not yet known say so; do not present a guess as one.
- **Nothing is deleted, nothing is added.** Where a value is not knowable here, keep the row or
  section and leave it blank — tested by, owner, dates, reported by, witness names and contacts,
  attendee names, minutes taker, time, location. Person names are deliberately absent from the
  reference; inventing one puts wrong data in a company record. A section that seems irrelevant
  still stays: the tracker's page has that section, so the note has it too.

## 5. Write the output and suggest a status

```bash
python3 "$CLAUDE_PLUGIN_ROOT/scripts/workitem_output.py" write --mode note \
  --title "<title>" --type "<type>" --template <task_note|test_note|incident_note|meeting_minutes> \
  < content.md
```

`--template` is **required** and is not a formality: the script compares the note's shape against
that template — the number of information-table rows and the sequence of heading levels — and
**refuses to write anything** if they differ, listing what is off. An added row, an invented
section or a heading borrowed from another template is rejected before it reaches a file. The
check compares shape, not wording, so it works in any output language; a renamed heading is the
one deviation it cannot see, so that one is on you.

The output directory is named in the output language: `not.md` plus `alanlar.md` in Turkish,
`note.md` plus `fields.md` in English.

**Status suggestion** (a suggestion, not a selection — the user sets it): done and verified ->
`Done`; done but awaiting verification -> `In Review` or `Test`; partly done -> leave
`In Progress` and record what is open in the note. Valid values are in
`references/field-reference.md`.

## 6. Tell the user — in the output language

`fields.md` carries **data only**: canonical English headings and field names, no sentences. The
script cannot write prose in the user's language, so the explanation is yours to give, in the
chosen language.

Report:

- The file paths.
- The suggested status and why it is suggested.
- Which fields to select in the tracker, named the way the tracker shows them — local wording in
  `references/labels.md` under "Tracker fields chosen by the user".
- What was left blank and needs filling.
- **Which files to attach** to the page: output logs, screenshots, exported results.
- How to paste: copy the whole content file into a **blank page**, not into the tracker's own
  template. Save, reload, and check the tables survived.
