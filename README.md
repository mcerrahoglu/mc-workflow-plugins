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

### Tests

```bash
cd ~/mc-workflow-plugins/rules && python3 tests/run.py
```

76 cases: false-positive protection, the message extractor, boundary values, case handling,
pattern health, fail-closed behaviour, and one full conforming message. The gate is exercised as
a subprocess, so the tests run with the plugin disabled and need no repository.

`--dump` records decisions **and** rule ids; `tests/diff_baseline.py` compares two dumps on the
ids they share, so a migration can be proven not to change behaviour it was not meant to change.

---

## Plugin: `workitem`

Turns work into content for an issue tracker. **Tracker-independent and writes nothing anywhere:**
no API, no credentials, no requests. It produces files and you paste them.

### Two commands

| Command | When | Produces |
|---|---|---|
| `/workitem-draft` | Before starting | Title, description, type, effort estimate with its basis |
| `/workitem-note` | When finished | Result note plus a suggested closing status |

Only **three fields are generated**: title, description, type. Priority, status, sprint, work
package, due date and assignee depend on the project and the team, so you choose them in the
tracker. A value that is not on a list is never invented; the output says so instead.

### Output language

The plugin is in English; the content it generates is in **your** language. If the language is
unknown the skill asks, and the answer is stored outside the repository:

```bash
python3 ~/mc-workflow-plugins/workitem/scripts/workitem_output.py language --set tr
```

Templates hold canonical English labels and `references/labels.md` maps them to another language,
so wording stays consistent across notes. Adding a column there is all a new language needs.
Commit messages are unaffected — those are English by the rules spec.

### Templates

`templates/` holds `issue_description`, `task_note`, `test_note`, `incident_note` and
`meeting_minutes` as Markdown with GFM pipe tables. Paste the whole note into a **blank page**
rather than picking your tracker's own template and filling cells: on paste a pipe table becomes
a real table, so one paste is enough and the result looks native.

**Verify the format in your own tracker once.** Paste a small probe — a heading, bold text, a
list, a two-column pipe table, an emoji — save, reload, and see what survived. Editors differ;
some accept Markdown and reject HTML. If yours needs something else only the templates change,
because the writer script is format-agnostic.

### Fields left blank on purpose

A field that is meaningful but whose value cannot be known here is **kept and left empty**, never
guessed: tested by, owner, dates, reported by, witness names and contacts, attendee names,
minutes taker, time, location. Person names are deliberately absent from the reference. A section
that does not apply to the work is deleted instead — "none" is not written.

Empty table cells stay empty and free-text sections carry a single `…`, so an unfinished note is
visibly unfinished. Alongside the content the script writes `fields.md` with two lists: what to
select in the tracker, and what was left blank. That second list is derived from the generated
content, so it stays correct when a template changes.

### Effort

The estimate is a **range with its basis**, not a bare number — `--estimate-hours` is refused
without `--rationale`, because a bare figure reads as a measurement and an estimate is not one.
Many trackers attach the estimate to the assignment, so assign first, then enter it.

Actual hours come from you alone. If you do not give them the actual and variance rows are
removed rather than filled with a guess: commit timestamps show elapsed time, which is not time
worked.

### Commit material for a result note

```bash
python3 ~/mc-workflow-plugins/workitem/scripts/workitem_output.py commits \
  --since 2026-08-17 --repo ~/project-a --repo ~/project-b
```

`--since` is required. "The commits from this session" is an undefined selector when work spans
several repositories and several days.

---

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
  references/labels.md            English -> other language labels
  references/ears.md              requirement patterns
  templates/*.md                  five note templates
  scripts/workitem_output.py      writer + commit collector
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
