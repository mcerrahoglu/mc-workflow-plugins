# Engineering rules

Project-independent rules that apply to every session. Project-specific rules (deployment flow,
infrastructure pitfalls, service settings) do not belong here — their place is the project's own
`CLAUDE.md`, which is loaded automatically. On conflict the project's `CLAUDE.md` is more
specific and wins.

**Tradeoff:** these rules favour care over speed. On trivial, easily reversible work, use
judgement instead of ceremony.

## 1. Commit messages

A commit message is the only durable record of **why** the code changed. The code already shows
what it does; the message gives context to whoever reads `git log` six months later.

**Commit text is written in English** — for tooling compatibility and readability outside the
team. The project's `CLAUDE.md` may override this.

### Anatomy

```
<type>(<scope>): <subject>
                                    <- blank line (required)
Body: what the problem was, why this solution, whether there are side effects.
                                    <- blank line
Refs: #142
BREAKING CHANGE: config.timeout is now seconds, not milliseconds
```

### Subject

- Target 72 characters, hard limit 100.
- **Imperative mood:** `add`, `fix`, `remove` — not `added` or `adds`. Test: "Applying this
  commit will ___".
- Start lowercase. No trailing period.
- State the outcome, not the activity: not `fix bug`, but which bug.
- It must stand alone in `git log --oneline` output.

### Types

`feat` (MINOR) · `fix` `perf` `security` (PATCH) · `refactor` `docs` `test` `build` `ci` `chore`
`revert` `style` (no version effect).

Breaking change: `<type>!:` or a `BREAKING CHANGE:` footer -> MAJOR.

### Body

- Answer three questions: what the problem was (previous behaviour) · why this solution (why
  alternatives were dropped) · whether there are side effects (migration, performance, behaviour
  change).
- Wrap lines at 100.
- Do not restate the diff. The diff shows *what*; the body explains *why*.
- Where something was measured, give the number as before -> after: `54.9 -> 14.6 ms`.
- Never present an unmeasured claim as measured; mark an assumption as an assumption.
- Impersonal voice. If behaviour does not change, say so: `No behaviour change; existing tests
  pass unmodified.`

### Footer

- `Refs: #142`, `Fixes #487`
- `BREAKING CHANGE:` in capitals.
- A real human co-author is fine: `Co-authored-by: Ada Lovelace <ada@example.com>`

### Forbidden

- References to the conversation: `user said / asked / reported / requested`, `per user request`
- Verbatim quotes from the conversation
- First person singular: `I fixed`, `I measured`
- Narrative frames: `QUESTION:`, `as I mentioned`, `my initial assessment was`
- AI or bot attribution: `Generated with ...`, `Co-authored-by: Claude`, robot emoji

When a symptom came from the user, record the symptom, not its source:
`user reported the X button is broken` -> `X button does not respond to clicks.`

### Atomicity

One commit = one logical change. If the message needs an "and", it should have been two commits.
`git revert` then undoes one thing and `git bisect` narrows to one thing. Separate mixed changes
with `git add -p`.

Worked good and bad examples: `references/commit-examples.md`.

## 2. Commit structure

- **Follow the commit structure agreed during planning.** If the plan defined separate scopes,
  that split is preserved.
- **Commit scope by scope.** Once a scope is done, tested and verified, commit it — the next
  scope then starts from solid ground.
- **Verification depth is read from the project itself.** In a project that has tests, CI or a
  way to run it, an unverified change is not committed — untested work does not count as done.
  In an experimental or one-off project with no such setup, one piece of run evidence is enough;
  do not invent a test that does not exist and do not demand that one be built. If it is unclear
  which level applies, the project's `CLAUDE.md` decides.
- Do not pile unrelated changes into one commit, and do not split a single scope needlessly.

## 3. Proceeding and reporting

- **If a plan is agreed and the steps are running cleanly, do not ask for permission to
  continue.** Do not ask "shall I go on" at the start of every step.
- Report only when something falls **outside the plan**.
- If what you report **requires a user decision**, ask and wait. If it does not, report it and
  carry on.
- **If more than one reading of the request is possible, present them — do not silently pick
  one.**
- Do not narrow or widen the scope on your own. If part of it is genuinely blocked, finish the
  rest and say plainly what was left out and why.
- **These always require approval first:** push, force-push, deploy, rewriting history,
  deletion, sending data to an external service.
- On long external work (build, deploy, long run) do not sit silently polling; report status.

## 4. Security

- Never write attack surface, defensive detail or secrets into comments, logs or error messages.
- Scan changed files for secrets and vulnerabilities before committing.
- Secrets are not embedded in code; `.env`, keys and tokens never enter a commit.

## 5. Solution design

- **Produce a general solution, independent of language and of the particular source or site.**
  Do not hardcode for a single case.
- **Minimum code that solves the stated problem.** No features that were not asked for. No
  abstraction for single-use code. No flexibility or configurability that was not requested. No
  error handling for impossible scenarios. If you wrote 200 lines and 50 would do, rewrite it.
  Ask: would a senior engineer call this overcomplicated?
- **General in approach, minimal in structure.** These two only look contradictory. Not
  hardcoding a site-specific prefix and not building a three-class strategy pattern are both
  correct at once: generality belongs to the approach, not to the amount of machinery.
- **inform > gate:** do not constrain the agent with hardcoded gates; improve the inputs to its
  decisions.
- Never say "faster" or "better" without measuring. If you claim it, show the measurement.

## 6. Plan hardening

- Before a plan is submitted for approval it is reviewed by independent subagents. The goal is
  not approval but **finding gaps**: skipped steps, unverified assumptions, verification that
  cannot be run.
- **Threshold:** plans that touch more than three files, change schema, data or deployment, or
  are expensive to reverse get reviewed. Single-file, reversible work skips it; say in one line
  that it was skipped.
- The review gets the plan text **and the real files** to be touched. A finding produced without
  reading the files does not count.
- A finding is not automatically correct. One not grounded in code, output or measurement is
  marked **speculative**; it is verified first, then enters the plan.
- Every finding is closed one of three ways: **fixed** (folded into the plan) · **rejected** (one
  sentence of reasoning) · **out of scope** (recorded under deferred work). No finding is dropped
  silently.
- If a second review round still produces new critical findings, the plan is inadequate: rewrite
  it rather than patch it.

## 7. Surgical changes

- **Touch only what you must.** Do not "improve" adjacent code, comments or formatting.
- Do not refactor what is not broken.
- Match the existing style even where you would do it differently.
- If you notice unrelated dead code, **mention it — do not delete it.**
- Remove the imports, variables and functions that **your own change** orphaned. Do not remove
  pre-existing dead code unless asked.
- The test: every changed line traces directly to the request.

## 8. Goals and verification

- Define a verifiable success criterion **before** starting: "add validation" becomes "write a
  failing test for invalid input, then make it pass"; "fix the bug" becomes "write a test that
  reproduces it, then make it pass".
- For multi-step work, state the plan as `step -> verification` pairs.
- Every step carries a **runnable verification command and its expected output**.
- A strong criterion lets the work loop independently; a weak one ("make it work") forces
  constant clarification.

---

**These rules are working if:** diffs contain fewer unrelated changes, fewer rewrites are caused
by overcomplication, and clarifying questions arrive before the mistake rather than after it.
