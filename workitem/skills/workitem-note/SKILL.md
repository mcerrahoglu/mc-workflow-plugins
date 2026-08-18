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

Fill the template, then:

- **Measurements as before -> after** on a named input: `1297 -> 770 s, recall unchanged at 0.88`.
  Never present an unmeasured claim as measured.
- **In a test note the ACTUAL column carries evidence** — a measurement, a quote or output.
  "works" is not evidence. Status values are exactly three: `✅ Passed`, `❌ Failed`,
  `🟪 Pending`. If any step failed or is pending, the Findings section is mandatory.
- **Impersonal voice**, no conversation references — the same line as the commit rules.
- In an incident note, if the root cause is not yet known say so; do not present a guess as one.
- **Delete a section that does not apply. Keep a section that applies but whose value is not
  knowable here and leave it blank** — tested by, owner, dates, reported by, witness names and
  contacts, attendee names, minutes taker, time, location. Person names are deliberately absent
  from the reference; inventing one puts wrong data in a company record.

## 5. Write the output and suggest a status

```bash
python3 "$CLAUDE_PLUGIN_ROOT/scripts/workitem_output.py" write --mode note \
  --title "<title>" --type "<type>" < content.md
```

**Status suggestion** (a suggestion, not a selection — the user sets it): done and verified ->
`Done`; done but awaiting verification -> `In Review` or `Test`; partly done -> leave
`In Progress` and record what is open in the note. Valid values are in
`references/field-reference.md`.

## 6. Tell the user

The file path, the suggested status and why, what was left blank, and **which files to attach**
to the page — output logs, screenshots, exported results.
