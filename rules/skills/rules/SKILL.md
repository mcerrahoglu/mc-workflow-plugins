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
  in the editor and `commit.template` are outside its view — compliance there
  is on you.
- **`-t <template>` given with `-m` IS judged:** git uses `-m` and ignores the template.
- **What the gate deliberately does not judge:** a message it cannot measure. `-m "$(cat <<'EOF'
  ... EOF)"` **is** resolved and judged; anything else inside the substitution (a pipe, a second
  command, an unquoted delimiter) changes what git receives and is skipped, as are `${VAR}`,
  ANSI-C quoting, a message piped on stdin, `--fixup`/`--squash` supplements, and formats git
  generates itself (`Revert "..."`, `fixup! ...`, `Merge ...`). A gate that rejects a legitimate
  command is worse than no gate.
- Changing the rules, the patterns or the thresholds is documented in the repository `README.md`,
  not here: this skill is for confirming a rule or auditing compliance.
