# Worked commit message examples

Read alongside rule 1 in `RULES.md`. These are kept out of `RULES.md` on purpose: the rules
load into every session, examples only need to be read when a message is being written.

Limits used below: subject target 72, hard 100; body wrapped at 100.

---

## Bad

```
fix
```
Which fix? Useless in `git log --oneline`, useless to `git bisect`.

```
updates and fixes
```
Two or more logical changes in one commit. Split them.

```
WIP
```
Not a finished scope. Rule 2: unverified work is not committed.

```
Bug fixed. Now it works. Also refactored the login page and updated deps.
```
Three unrelated changes, no type prefix, past tense, trailing periods, and nothing about *why*.

```
fix(auth): Fixed the token bug.
```
Four violations at once: `Fixed` is past tense (use `fix`), the subject starts with a capital,
it ends with a period, and "the token bug" does not say which bug.

```
fix(ui): hide the panel

The user reported that the panel was confusing, so as I mentioned earlier it is hidden now.

Co-authored-by: Claude <noreply@anthropic.com>
```
Three forbidden things: a conversation reference, a narrative frame, and AI attribution. The
symptom belongs in the record, not its source — write `panel obscured the result table`.

---

## Good

### Short, no body needed

```
fix(auth): reject tokens with a future iat claim
```

The change is self-explanatory and the subject alone carries it.

### Rationale required

```
fix(scoring): clamp technical score to 100 before weighting

Weighted score could exceed 100 when a bidder scored above the reference value on more than
three criteria, because per-criterion normalisation was applied after the weight
multiplication instead of before.

This inverted the ranking in one evaluation: the second-place bidder received 103.4 and won.
Normalisation now happens per criterion, matching the formula in the specification.

Fixes #487
```

What the problem was, why this solution, and the consequence — with a concrete number.

### Breaking change

```
feat(api)!: return ISO-8601 timestamps instead of Unix epoch

All timestamp fields in /v2 responses are now RFC 3339 strings in UTC. Epoch integers made
client-side timezone handling error-prone and were inconsistent with the webhook payloads.

BREAKING CHANGE: created_at and updated_at change type from integer to string. Clients
parsing these as numbers must be updated before deploying.

Refs: #612
```

Both markers present: `!` in the subject and the `BREAKING CHANGE:` footer in capitals.

### Refactor with no behaviour change

```
refactor(parser): extract token normalisation into TokenNormalizer

The parse loop had grown to 340 lines with three distinct responsibilities. Splitting
normalisation out makes the remaining loop testable in isolation.

No behaviour change; existing parser tests pass unmodified.
```

Saying "no behaviour change" out loud is what makes this reviewable.

### Measured performance work

```
perf(index): parallelise the audit phase across chunk groups

The phase ran serially over chunk groups while each group's AI call spent most of its time
waiting. Groups are now submitted to the existing worker pool.

Measured on the same 41-document input: 1297 -> 770 s wall clock, recall unchanged at 0.88.
```

Before -> after, on a named input, with the quality metric that must not regress.

### Revert

```
revert: "feat(cache): enable Redis write-through"

This reverts commit 4a7f19c.

Write-through caching caused duplicate key errors under concurrent writes because the cache
write and the database write were not in one transaction. Reverting until the transactional
wrapper lands.
```

Git generates this subject shape, and the gate exempts it from the length and format checks.
The body still has to say why.

### Security fix, without describing the attack

```
security(upload): validate archive entry paths before extraction

Archive entries were joined to the destination directory without checking the resolved path,
so an entry could be written outside it. Extraction now rejects any entry whose resolved path
escapes the destination.
```

States what was wrong and what changed. Rule 4: no exploit recipe, no attack surface detail.

---

## Quick checklist

- Subject imperative, lowercase, no trailing period, under 72 where possible
- Blank line between subject and body
- Body explains why, not what; does not restate the diff
- Measurements as before -> after, on a named input
- Breaking change carries `!` or the `BREAKING CHANGE:` footer
- One logical change; no "and" in the subject
- No conversation reference, no first person singular, no AI attribution
- The subject stands alone in `git log --oneline`
