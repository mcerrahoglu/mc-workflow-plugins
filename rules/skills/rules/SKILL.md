---
name: rules
description: Shows and applies the project-independent engineering rules — commit message spec, commit structure, proceeding and reporting, security, solution design, plan hardening, surgical changes, goals and verification. The rules already load automatically at session start; invoke this to re-read them, confirm a specific rule, or audit whether something complies.
---

# Engineering rules

The single source of the rules is `RULES.md` at this plugin's root (two directories up from
this skill: `../../RULES.md`). **Read that file and apply it** — the text is not duplicated
here, so there is one source.

The `SessionStart` hook (`scripts/session_rules.py`) already injects the whole text into the
context of every new session. While the plugin is enabled the rules need no separate reading;
this skill exists to **confirm or audit** them.

Worked commit message examples live in `references/commit-examples.md` and are deliberately
kept out of `RULES.md`, so they cost nothing until they are needed.

## Notes

- These rules are **project-independent**. Project-specific rules (deployment flow,
  infrastructure pitfalls, service settings) belong in the project's own `CLAUDE.md`, which
  wins on conflict — including the choice of language for commit text.
- The verification depth in rule 2 **varies by project**: where tests or CI exist an
  unverified change is not committed; in an experimental project one piece of run evidence
  is enough and a missing test is not invented.
- Commit messages are additionally enforced by a `PreToolUse` gate
  (`scripts/commit_msg_gate.py`). It **denies** a hard pattern (conversation reference, AI
  attribution) or an objective structural error (missing or invalid `type(scope):`, subject
  over 100 characters, trailing period, no blank line before the body), and **asks** on style
  issues (subject over the 72 target, non-imperative subject, capitalised subject, body line
  over 100). The reason names the rule id and the measured value.
- **Gate scope:** the command line text and the file given with `-F`/`--file`. A message typed
  in the editor, `-t <template>` and `commit.template` are outside its view — compliance there
  is on you.
- **What the gate deliberately does not judge:** a message it cannot measure. Shell expansion
  (`$(...)`, `${VAR}`, ANSI-C quoting), a message piped on stdin, `--fixup`/`--squash`
  supplements, and formats git generates itself (`Revert "..."`, `fixup! ...`, `Merge ...`)
  are skipped rather than guessed at. A gate that rejects a legitimate command is worse than
  no gate.
- To change a rule, edit `RULES.md`. To change the forbidden patterns or the thresholds, edit
  `patterns.json` — data, not code. Its `_contract` field is binding: text patterns are matched
  against a lowercased ASCII-folded message, so no non-ASCII letters go in them, while
  structural checks read the raw message.
- Additional languages: drop a `patterns.<lang>.json` next to it and it is loaded as well.
  `patterns.tr.json` ships as an example.
- After any change run `python3 tests/run.py`; every case must pass. `--dump` writes decisions
  and rule ids so a migration can be compared before and after with `tests/diff_baseline.py`.
