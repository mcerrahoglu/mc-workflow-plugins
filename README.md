# mc-workflow

Two Claude Code plugins. One carries a set of project-independent engineering rules and enforces
the commit message spec; the other turns finished work into paste-ready content for an issue
tracker.

| Plugin | Version | What it does |
|---|---|---|
| `rules` | 1.2.0 | Loads engineering rules into every session and gates commit messages |
| `workitem` | 1.1.0 | Generates work item definitions and result notes for any issue tracker |

They are independent: install either one on its own. `workitem` does not need `rules`.

---

## Requirements

- **Python 3** on PATH as `python3`. Both plugins are Python: the `rules` hooks and the
  `workitem` script are run by the interpreter, so nothing works without it.
- **git**, for the `workitem` commit collector.

### Windows

`python3` on Windows is usually a Microsoft Store alias stub rather than an interpreter, and the
python.org installer does not create a `python3.exe` at all — so `python3 --version` reports
"Python was not found" even with Python installed. Create the missing name next to the real
interpreter:

```cmd
copy "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" "%LOCALAPPDATA%\Programs\Python\Python311\python3.exe"
```

Adjust the version directory to yours. Python resolves its home from the executable's location
rather than its name, so the copy behaves exactly like the original, and that directory precedes
`WindowsApps` on PATH, so it wins over the stub without touching the Store alias. Confirm with
`python3 --version`.

Renaming the hook command to `python` instead is not a fix: many Linux distributions ship only
`python3` and no `python`, so a single name breaks one platform or the other.

## Install

```bash
git clone https://github.com/mcerrahoglu/mc-workflow-plugins ~/mc-workflow-plugins
```

Register the clone as a marketplace, then install what you want:

```bash
claude plugin marketplace add ~/mc-workflow-plugins
claude plugin install rules@mc-workflow
claude plugin install workitem@mc-workflow
```

Hooks are read at session start, so a **new window** is needed before the rules plugin takes
effect.

Windows works once `python3` resolves — see Requirements. Verified on Windows 11 with Python
3.11: the session hook injects the rules and the commit gate denies a non-conforming message
with its rule ids.

### After editing anything: refresh the cache

A plugin does **not** run from the directory you edit. On install it is copied to
`~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`, so editing the source has no effect
on the running code until you bump the version and reinstall.

```bash
# 1) raise "version" in both the plugin's plugin.json and .claude-plugin/marketplace.json
claude plugin marketplace update mc-workflow
# 2) reinstall — `install` alone will not upgrade a plugin that is already installed
claude plugin uninstall rules@mc-workflow && claude plugin install rules@mc-workflow
# 3) prove it — output must be empty
diff -r ~/mc-workflow-plugins/rules ~/.claude/plugins/cache/mc-workflow/rules/<new-version>
```

Skipping this is the easiest way to test the wrong copy of your own change. The old version
directory stays behind under the cache; remove it only when nothing points at it any more.

---

## Plugin: `rules`

### Three components

| Component | Trigger | Effect |
|---|---|---|
| `scripts/session_rules.py` | `SessionStart` | Injects `RULES.md` into the session (`suppressOutput`, so nothing appears on screen) |
| `scripts/commit_msg_gate.py` | `PreToolUse` / `Bash` | Checks commit messages: denies hard violations, asks on style |
| `skills/rules/SKILL.md` | `/rules` | Shows the rules for confirmation or an audit |

### The eight rules

`RULES.md` is the single source. In short:

1. **Commit messages** — Conventional Commits, English, subject target 72 / hard 100, imperative,
   lowercase, no trailing period; the body explains *why*; measurements as before -> after. No
   conversation references, no first person singular, no AI attribution.
2. **Commit structure** — commit scope by scope; verification depth is read from the project, so
   a project without tests is not asked to invent one.
3. **Proceeding and reporting** — do not ask permission at every step; present multiple readings
   instead of silently picking one; push, deploy, deletion and sending data outward always ask.
4. **Security** — no attack surface, defensive detail or secrets in comments, logs or messages.
5. **Solution design** — general solutions, minimum machinery. *General in approach, minimal in
   structure.* No claim of "faster" without a measurement.
6. **Plan hardening** — independent subagents review a plan before approval; every finding is
   closed as fixed, rejected with a reason, or out of scope.
7. **Surgical changes** — touch only what the request needs; mention unrelated dead code instead
   of deleting it; every changed line traces to the request.
8. **Goals and verification** — define a verifiable criterion before starting; each step carries
   a runnable command and its expected output.

Worked good and bad commit examples: `rules/references/commit-examples.md`. They are kept out of
`RULES.md` on purpose, so they cost nothing until they are read.

An optional message template is in `rules/templates/gitmessage.txt`:

```bash
git config --global commit.template ~/mc-workflow-plugins/rules/templates/gitmessage.txt
```

### How the commit gate works

It runs on **every** Bash call and returns immediately when the command contains no `commit`.

**Detection is deliberately conservative.** The command is split into segments and only a segment
whose first tokens are `git [global options] commit` is inspected, so a `git tag -m ...` in a tail
command is not mistaken for the commit message. Heredoc bodies and quoted contents are masked
first, so a command that merely writes *about* committing — documentation, examples — is not
treated as a commit.

**The message is extracted, not guessed.** `-m` (repeatable, clustered as `-am`, attached, or
`--message=`), `-F <file>` resolved against the command's working directory, and `-F -` with a
heredoc are all handled. When the message cannot be seen or cannot be measured the structural
check is **skipped and nothing is denied**: a piped message, shell expansion (`$(...)`, `${VAR}`,
ANSI-C quoting), `--fixup`/`--squash` supplements, an editor-written message, and the shapes git
generates itself (`Revert "..."`, `fixup! ...`, `Merge ...`).

**Decisions.** Deny for a hard pattern or an objective structural error: missing or invalid
`type(scope):`, subject over 100 characters, trailing period, no blank line before the body. Ask
for style: subject over the 72 target, non-imperative or capitalised subject, body line over 100.
The reason names the rule id and the measured value (`[subject-max-length] 104 > 100`), so a
rejection can actually be acted on.

**Two channels.** Text patterns are matched against a lowercased, ASCII-folded message; structural
checks read the raw message, because case carries meaning there (lowercase type, capitalised
`BREAKING CHANGE`). The `_contract` field in `patterns.json` states this and is binding.

**Fail closed.** If `patterns.json` is unreadable or malformed the gate asks with a reason rather
than passing silently. An unexpected error does the same. A malformed `structure` block falls back
to code defaults instead of dropping every commit to `ask`.

**Scope.** Only the command line and the file given with `-F`/`--file`. A message typed in the
editor, `-t <template>` and `commit.template` are outside its view.

### Configuration

Thresholds and forbidden patterns live in `rules/patterns.json` — data, not code:

```json
"structure": {
  "allowed_types": ["build", "chore", "ci", "docs", "feat", "fix",
                    "perf", "refactor", "revert", "security", "style", "test"],
  "subject_target": 72, "subject_hard": 100, "body_hard": 100
}
```

Additional languages: drop a `patterns.<lang>.json` beside it and it is loaded as well.
`patterns.tr.json` ships as a working example, useful when messages are occasionally written in
another language out of habit.

A language pack may also carry `foreign_markers` — wordings that give its language away. Any
single match makes the message "not in English" and yields `ask`, never `deny`. Markers read the
resolved message only, not the command line, and each must be word-bounded and at least three
letters: unbounded markers matched every English control message. Measured on 551 real commits,
the Turkish set flags 39% of them and 11% of subject lines on their own — a one-line message
often carries no marker, so this warns rather than enforces.

### Tests

```bash
cd ~/mc-workflow-plugins/rules && python3 tests/run.py
```

98 cases: false-positive protection, the message extractor, boundary values, case handling,
pattern health, fail-closed behaviour, and one full conforming message. The gate is exercised as
a subprocess, so the tests run with the plugin disabled and need no repository.

`--dump` records decisions **and** rule ids; `tests/diff_baseline.py` compares two dumps on the
ids they share, so a migration can be proven not to change behaviour it was not meant to change.

---

## Plugin: `workitem`

Turns work into content for an issue tracker. **Tracker-independent and writes nothing anywhere:**
no API, no credentials, no requests. Two files per work item, entered by hand.

### Two commands

| Command | When | Produces |
|---|---|---|
| `/workitem-draft` | Before starting | The work item definition: title, right-panel values, description |
| `/workitem-note` | When finished | The result note, plus sub-tasks for unplanned work |

Only **type, status and estimate** are decided. Priority, sprint, work package, due date, assignee
and labels depend on the project and the team, so they are marked as chosen in the tracker. A value
that is not on a list is never invented.

### The files are written by the skill, not the script

The output is in the user's language, and a script handed a language code as a string cannot
compose prose in it — an earlier version tried and produced English headings while claiming
otherwise. So the skill writes the files, following `templates/` for structure and
`references/labels.md` for wording, and the script keeps only the jobs that need code:

```bash
# refuse a note whose shape does not match its template
workitem_output.py check --file <note> --template <task_note|test_note|incident_note|meeting_minutes>

# collect commit material for a result note (--since is required)
workitem_output.py commits --since 2026-08-17 --repo ~/project-a --repo ~/project-b

# remember the output language, so the skill asks once
workitem_output.py language --set tr
```

### The note structure is enforced, not merely requested

A tracker's note page has a fixed field set. Two notes written in real use drifted from it: one
added a row, another mixed two templates and invented four sections of its own. An instruction to
"fill the template" had already failed twice, so the check is mechanical: it compares the number of
information-table rows and the sequence of heading levels against the template and exits non-zero
naming what is off. It compares shape rather than wording, so it holds in any output language; a
renamed heading is the one deviation it cannot see.

### Sub-tasks are for unplanned work

A sub-task records work that was not in the plan, came up while doing the planned work, and cost
extra hours — so that time is visible as its own line rather than buried in the parent's note. At
closing, `/workitem-note` proposes one for each such item: its own definition file naming the
parent, plus its own checked note.

### Effort

The estimate is a **range with its basis** — a bare figure reads as a measurement and an estimate
is not one. The tracker attaches it to the assignment, so assign first, then enter it. Spent hours
come from the user alone: commit timestamps show elapsed time, which is not time worked.

### Templates and the format probe

`templates/` holds `work_item` plus four note templates as Markdown with GFM pipe tables. Paste a
note into a **blank page** rather than picking the tracker's own template and filling cells: on
paste a pipe table becomes a real table, so one paste is enough and the result looks native.

**Verify the format in your own tracker once.** Paste a small probe — a heading, bold text, a list,
a two-column pipe table, an emoji — save, reload, and see what survived. Editors differ; some
accept Markdown and reject HTML. If yours needs something else only the templates change, because
the script does not generate content.

### Fields left blank on purpose

A field that is meaningful but whose value cannot be known here is kept and left empty, never
guessed: tested by, owner, dates, reported by, witness and attendee names. Person names are
deliberately absent from the reference. Empty cells stay empty and free-text sections carry a
single ellipsis, so an unfinished note is visibly unfinished.

## File map

```
.claude-plugin/marketplace.json   catalogue of both plugins
LICENSE                           MIT
README.md                         this file

rules/
  RULES.md                        single source of the eight rules
  patterns.json                   forbidden patterns + thresholds (+ _contract)
  patterns.tr.json                example language pack
  hooks/hooks.json                SessionStart + PreToolUse(Bash)
  scripts/session_rules.py        injects the rules at session start
  scripts/commit_msg_gate.py      commit message gate
  skills/rules/SKILL.md           /rules
  references/commit-examples.md   worked good and bad examples
  templates/gitmessage.txt        optional git commit template
  tests/                          76 cases, harness, baseline differ

workitem/
  skills/workitem-draft/SKILL.md  /workitem-draft  (before the work)
  skills/workitem-note/SKILL.md   /workitem-note   (after the work)
  references/field-reference.md   types, statuses, estimate mechanics
  references/labels.md            English -> other language wording
  references/ears.md              requirement patterns
  templates/work_item.md          the definition file's structure
  templates/*_note.md, meeting_minutes.md   the four note structures
  scripts/workitem_output.py      structure checker + commit collector
```

---

## Measurements

- **Gate cost:** about 20 ms per Bash call, of which roughly 15 ms is Python interpreter and
  module import. The gate's own work is 6.6 µs and reading the pattern files 0.06 ms. A command
  with no `commit` substring returns before any of it.
- **Context cost:** `rules` adds ~112 tokens of always-on metadata and the SessionStart hook
  injects `RULES.md` (8,403 bytes) on top — **estimated** at ~2,050 tokens from the byte count,
  not measured with a tokenizer. `workitem` adds ~271 always-on and ~1.2-1.3k when a skill fires.
  Note that `claude plugin details` reports hooks as having no context cost, which understates
  the real figure: it cannot see what a hook injects at runtime.
- **Thresholds were calibrated, not guessed.** 500 commits from a real repository were measured
  against the candidate limits. At 72 characters 45% of subjects and 64% of body lines would have
  been flagged; at 100 the figures are 7.2% and 0.1%. The 100/100 pair matches
  `@commitlint/config-conventional`, the reference configuration behind Conventional Commits.
- **Tests:** 76/76. The migration from the previous gate changed six decisions, each with a
  written justification in the fixture notes.

## Not verified yet

- Whether a given tracker's editor accepts Markdown — run the probe described above.
- Whether the type list matches trackers other than the one it was drawn from. Treat
  `field-reference.md` as a starting point and edit it.

## Credits

The behavioural rules 5, 7 and 8 were shaped after reading
[forrestchang/andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills)
(MIT), which collects Karpathy's observations on LLM coding pitfalls. The wording here is our
own; the ideas we took are surgical changes, simplicity over speculative machinery, and
verifiable success criteria.

## License

MIT — see `LICENSE`.
