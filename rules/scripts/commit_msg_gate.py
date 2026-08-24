#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PreToolUse/Bash gate: rejects commit messages that break the spec in RULES.md.

Why there is no `if: Bash(git commit *)` matcher: in a compound command such as
`cd /x && git commit ...` the matcher may not fire and the gate is silently skipped.
This script runs on every Bash call and leaves early when the command holds no commit.

DESIGN ORDER: false-positive protection first, rules second. A gate that rejects a
legitimate command is worse than no gate, so every step prefers skipping the structural
check over guessing:

  * The command is split into segments; only a segment whose first tokens are
    `git [global options] commit` is inspected. Otherwise `git tag -m ...` in a tail
    command would be read as the commit message.
  * Heredoc bodies and quoted contents are masked before detection, so a command that
    merely writes *about* `git commit` (documentation, examples) is not detected.
  * The extractor reports NONE / UNPARSEABLE / SKIP / EXPANDED separately from a real
    message. In those states the structural check is skipped and nothing is denied.

TWO CHANNELS: text patterns run on the folded message (lowercase, ASCII); structural
checks run on the RAW message, because case carries meaning there.

Decisions: hard pattern or structural error -> deny · soft pattern or style issue -> ask ·
pattern file unreadable -> ask (fail closed, never a silent pass).

Gate scope: only the command line text and the file given with `-F`/`--file`. A message
written in the editor and `commit.template` are outside it. `-t <template>` is inspected
when `-m` is also given, because git then uses `-m` and ignores the template.

Measured cost: about 20 ms per Bash call, of which roughly 15 ms is Python interpreter
and module import; the gate's own work is 6.6 us and reading the pattern files 0.06 ms.
A command with no `commit` substring returns before any of that work is done.
"""
import json
import os
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_PATTERNS = HERE.parent / "patterns.json"
MAX_MESSAGE_FILE_BYTES = 64 * 1024

# Used when the structure block is missing or malformed. Keeping the gate working on
# defaults beats dropping every commit to `ask`; an empty type list would deny all.
DEFAULT_STRUCTURE = {
    "allowed_types": ["build", "chore", "ci", "docs", "feat", "fix",
                      "perf", "refactor", "revert", "security", "style", "test"],
    "type_suggestions": {},
    "subject_target": 72,
    "subject_hard": 100,
    "body_hard": 100,
    "non_imperative_first_words": [],
    "generated_prefixes": ["revert:", "revert \"", "fixup!", "squash!", "amend!", "merge "],
}

# folding: reduces non-ASCII letters so one pattern matches both spellings
_FOLD = str.maketrans({
    "ı": "i", "İ": "i", "I": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g",
    "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c", "â": "a", "î": "i",
})

SEGMENT_SEP = re.compile(r"\|\||&&|;|\||\n")
HEREDOC_OP = re.compile(r"<<(?!<)(-?)\s*(?:'([^']+)'|\"([^\"]+)\"|([A-Za-z_][A-Za-z0-9_]*))")
SUBJECT_RE = re.compile(
    r"^(?P<type>[A-Za-z]+)(?:\((?P<scope>[^)]*)\))?(?P<bang>!)?:(?P<sp>\s*)(?P<subject>.*)$")
TRAILER_RE = re.compile(r"^[A-Z][A-Za-z-]+: ")
BREAKING_RE = re.compile(r"(?i)^breaking[ -]change\s*:")
EXPANSION_RE = re.compile(r"\$\(|`|\$\{|\$[A-Za-z_]|\\n|\\t")
CD_RE = re.compile(r"^\s*cd\s+(\S+)")

GIT_GLOBAL_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace",
                         "--exec-path", "--config-env", "--super-prefix"}
# options that make `-m` something other than an authored subject line
SKIP_COMMIT_OPTS = {"--fixup", "--squash", "-C", "-c", "--reuse-message",
                    "--reedit-message"}
# short flags taking no argument, so they may be clustered before -m/-F
CLUSTERABLE_FLAGS = "asevqnzpoi"


def fold(text):
    return text.translate(_FOLD).lower()


# --------------------------------------------------------------------------- masking
def blank_heredoc_bodies(cmd):
    """Blank heredoc bodies, matching terminators as whole lines.

    Operators are queued in order so a command with two heredocs maps each body to the
    right delimiter. `<<-` strips leading tabs on the terminator, as the shell does.
    """
    lines = cmd.split("\n")
    offsets, pos = [], 0
    for line in lines:
        offsets.append(pos)
        pos += len(line) + 1
    out = list(cmd)

    def blank_line(index):
        start = offsets[index]
        for p in range(start, min(start + len(lines[index]), len(out))):
            out[p] = " "
        # also blank the preceding newline, so a heredoc stays inside one command segment
        if start > 0 and out[start - 1] == "\n":
            out[start - 1] = " "

    i = 0
    while i < len(lines):
        delims = [(m.group(1) == "-", m.group(2) or m.group(3) or m.group(4))
                  for m in HEREDOC_OP.finditer(lines[i])]
        i += 1
        for strip_tabs, delim in delims:
            while i < len(lines):
                probe = lines[i].lstrip("\t") if strip_tabs else lines[i]
                blank_line(i)
                i += 1
                if probe == delim:
                    break
    return "".join(out)


def blank_quoted(text):
    """Blank quoted string contents, preserving length.

    Newlines inside quotes are blanked too: a multi-line `-m "subject\\n\\nbody"` must not
    be split into separate command segments. Heredoc bodies were already blanked by line,
    so their newlines are untouched by this pass.
    """
    out = list(text)
    quote = None
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if quote is None:
            if c in "'\"":
                quote = c
            elif c == "\\":
                i += 1
        elif c == quote:
            quote = None
        else:
            if quote == '"' and c == "\\" and i + 1 < n:
                out[i] = out[i + 1] = " "
                i += 2
                continue
            out[i] = " "
        i += 1
    return "".join(out)


def mask_literals(cmd):
    """Mask what the shell treats as data, so detection only sees command words."""
    return blank_quoted(blank_heredoc_bodies(cmd))


def split_segments(cmd):
    """Return (original, masked) pairs split on shell command separators."""
    masked = mask_literals(cmd)
    pairs, start = [], 0
    for m in SEGMENT_SEP.finditer(masked):
        pairs.append((cmd[start:m.start()], masked[start:m.start()]))
        start = m.end()
    pairs.append((cmd[start:], masked[start:]))
    return pairs


# ------------------------------------------------------------------- commit detection
def tokenize(text):
    """Tokenise, falling back to whitespace split when quoting is unbalanced."""
    import shlex                 # deferred: ~9 ms of import on a path most calls skip
    try:
        return shlex.split(text), True
    except ValueError:
        return text.split(), False


def commit_arg_index(tokens):
    """Index just after the `commit` subcommand, or None if this is not a commit call."""
    try:
        gi = tokens.index("git")
    except ValueError:
        return None
    i = gi + 1
    while i < len(tokens):
        t = tokens[i]
        if t == "commit":
            return i + 1
        if t.startswith("--") and "=" in t:
            i += 1
        elif t in GIT_GLOBAL_WITH_VALUE:
            i += 2
        elif t.startswith("-"):
            i += 1
        else:
            return None          # a different subcommand: tag, stash, commit-graph, ...
    return None


# ------------------------------------------------------------------ message extraction
def _cluster_value(token, letter):
    """Handle -am / -m'attached' clusters. Returns (matched, attached_value)."""
    m = re.match(r"^-([" + CLUSTERABLE_FLAGS + r"]*)" + letter + r"(.*)$", token)
    if not m:
        return False, None
    return True, m.group(2)


def read_message_file(path, cwd):
    candidate = pathlib.Path(path)
    if not candidate.is_absolute():
        candidate = pathlib.Path(cwd) / candidate
    if not candidate.is_file():
        return None, f"Message file not found: {path}."
    try:
        if candidate.stat().st_size > MAX_MESSAGE_FILE_BYTES:
            return None, f"Message file too large to check: {path}."
        return candidate.read_text(encoding="utf-8", errors="replace"), None
    except OSError as exc:
        return None, f"Message file unreadable: {path} ({type(exc).__name__})."


def heredoc_body(segment, from_pos=0):
    """Return (body, delimiter_was_quoted) for the heredoc at/after from_pos, or None.

    from_pos anchors the search to the `-F -` that asked for stdin, so a command holding
    more than one heredoc does not hand back the wrong body.
    """
    offset = 0
    lines = segment.split("\n")
    for idx, line in enumerate(lines):
        line_end = offset + len(line)
        m = HEREDOC_OP.search(line, max(0, from_pos - offset)) if line_end >= from_pos else None
        offset = line_end + 1
        if not m:
            continue
        strip_tabs = m.group(1) == "-"
        delim = m.group(2) or m.group(3) or m.group(4)
        quoted = bool(m.group(2) or m.group(3))
        body = []
        for rest in lines[idx + 1:]:
            probe = rest.lstrip("\t") if strip_tabs else rest
            if probe == delim:
                if strip_tabs:
                    body = [b.lstrip("\t") for b in body]
                return "\n".join(body), quoted
            body.append(rest)
        return None                                   # unterminated
    return None


def cat_heredoc_body(token):
    """Return the body of a `$(cat <<TOKEN ... TOKEN)` message argument, or None.

    This is how a multi-line message is normally written, so skipping it left the
    structural check off for most multi-line commits. Only the plain form is resolved:
    anything else inside the substitution (a pipe, a second command) changes what git
    actually receives, so those keep being skipped instead of guessed at.
    """
    inner = token.strip()
    if not (inner.startswith("$(") and inner.endswith(")")):
        return None
    inner = inner[2:-1]
    lead = re.match(r"\s*cat\s*(?=<<)", inner)
    if not lead:
        return None
    op = HEREDOC_OP.search(inner, lead.end())
    if not op or op.start() != lead.end():
        return None
    line_end = inner.find("\n", op.end())
    if line_end == -1 or inner[op.end():line_end].strip():
        return None                               # a redirect or pipe on the operator line

    strip_tabs = op.group(1) == "-"
    quoted = bool(op.group(2) or op.group(3))
    delim = op.group(2) or op.group(3) or op.group(4)
    lines = inner[line_end + 1:].split("\n")
    body = []
    for idx, line in enumerate(lines):
        probe = line.lstrip("\t") if strip_tabs else line
        if probe == delim:
            if "".join(lines[idx + 1:]).strip():
                return None                       # a pipe or another command follows
            if strip_tabs:
                body = [b.lstrip("\t") for b in body]
            text = "\n".join(body)
            if not quoted and EXPANSION_RE.search(text):
                return None                       # unquoted delimiter: the shell expands it
            return text
        body.append(line)
    return None                                   # unterminated


def extract_message(segment, tokens, parsed_ok, arg_index, cwd):
    """Return (message, source).

    source: 'm' | 'file' | 'heredoc' for a real message, otherwise NONE / UNPARSEABLE /
    SKIP / EXPANDED / 'ERROR:<reason>'. Anything but a real message means the structural
    check is skipped.
    """
    if not parsed_ok:
        return None, "UNPARSEABLE"

    args = tokens[arg_index:]
    if any(a in SKIP_COMMIT_OPTS or a.split("=", 1)[0] in SKIP_COMMIT_OPTS for a in args):
        return None, "SKIP"

    messages, file_path = [], None
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("-m", "--message"):
            if i + 1 < len(args):
                messages.append(args[i + 1])
            i += 2
            continue
        if a.startswith("--message="):
            messages.append(a.split("=", 1)[1])
            i += 1
            continue
        if a in ("-F", "--file"):
            if i + 1 < len(args):
                file_path = args[i + 1]
            i += 2
            continue
        if a.startswith("--file="):
            file_path = a.split("=", 1)[1]
            i += 1
            continue
        if a.startswith("-") and not a.startswith("--"):
            matched, value = _cluster_value(a, "m")
            if matched:
                if value:
                    messages.append(value)
                    i += 1
                else:
                    if i + 1 < len(args):
                        messages.append(args[i + 1])
                    i += 2
                continue
            matched, value = _cluster_value(a, "F")
            if matched:
                if value:
                    file_path = value
                    i += 1
                else:
                    if i + 1 < len(args):
                        file_path = args[i + 1]
                    i += 2
                continue
        i += 1

    if messages and file_path:
        return None, "SKIP"                           # git itself rejects this combination

    if file_path:
        if file_path == "-":
            anchor = re.search(r"(?:-F|--file=)\s*-(?=\s|$)", segment)
            found = heredoc_body(segment, anchor.end() if anchor else 0)
            if found is None:
                return None, "NONE"                   # piped or redirected: not visible
            body, quoted = found
            if not quoted and EXPANSION_RE.search(body):
                return None, "EXPANDED"
            return body, "heredoc"
        text, err = read_message_file(file_path, cwd)
        return (None, "ERROR:" + err) if err else (text, "file")

    if not messages:
        return None, "NONE"
    resolved = [m if not EXPANSION_RE.search(m) else cat_heredoc_body(m) for m in messages]
    if any(r is None for r in resolved):
        return None, "EXPANDED"
    return "\n\n".join(resolved), "m"


# ------------------------------------------------------------- structural validation
def normalise(message):
    """Apply what git --cleanup=whitespace does, before anything is measured."""
    text = message.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in text.split("\n")]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return lines


def body_line_exempt(line):
    """Long lines that cannot be hand-wrapped are not style violations."""
    stripped = line.strip()
    return (" " not in stripped                       # single token: URL, path, symbol
            or line.startswith("    ")                # indented block
            or stripped.startswith("|")               # table row
            or bool(TRAILER_RE.match(line)))


def check_structure(lines, structure):
    """Return [(severity, rule_id, detail)]. severity is 'deny' or 'ask'."""
    if not lines:
        return []
    subject = lines[0]
    lowered = subject.lower()
    for prefix in structure["generated_prefixes"]:
        if lowered.startswith(prefix):
            return []                                 # git generated this, not an author

    findings = []
    m = SUBJECT_RE.match(subject)
    if not m:
        findings.append(("deny", "subject-format", "no `type(scope): subject` prefix"))
    else:
        gtype, scope = m.group("type"), m.group("scope")
        sp, text = m.group("sp"), m.group("subject")
        if not gtype.islower():
            findings.append(("deny", "type-case", f"type `{gtype}` must be lowercase"))
        elif gtype not in structure["allowed_types"]:
            hint = structure["type_suggestions"].get(gtype)
            detail = f"type `{gtype}` is not allowed"
            detail += (f"; use `{hint}`" if hint else
                       "; allowed: " + ", ".join(structure["allowed_types"]))
            findings.append(("deny", "type-enum", detail))
        if scope is not None and not scope.strip():
            findings.append(("ask", "scope-empty", "empty scope `()`; omit it instead"))
        if sp == "":
            findings.append(("deny", "subject-separator", "a space is required after the colon"))
        elif len(sp) > 1:
            findings.append(("ask", "subject-separator", f"{len(sp)} spaces after the colon"))
        if not text.strip():
            findings.append(("deny", "subject-empty", "subject is empty"))
        else:
            first = text.strip().split()[0].lower().rstrip(",:;")
            if first in structure["non_imperative_first_words"]:
                findings.append(("ask", "subject-imperative",
                                 f"`{first}` is not imperative; use the base verb"))
            if text.strip()[0].isupper():
                findings.append(("ask", "subject-case", "subject should start lowercase"))
    if subject.endswith("."):
        findings.append(("deny", "subject-full-stop", "subject must not end with a period"))
    if len(subject) > structure["subject_hard"]:
        findings.append(("deny", "subject-max-length",
                         f"{len(subject)} > {structure['subject_hard']} characters"))
    elif len(subject) > structure["subject_target"]:
        findings.append(("ask", "subject-target-length",
                         f"{len(subject)} > {structure['subject_target']} target characters"))

    if len(lines) >= 2 and lines[1] != "":
        findings.append(("deny", "body-leading-blank",
                         "a blank line is required between subject and body"))

    in_fence = False
    for line in lines[2:]:
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if len(line) > structure["body_hard"] and not body_line_exempt(line):
            findings.append(("ask", "body-max-line-length",
                             f"{len(line)} > {structure['body_hard']} characters"))
            break
    for line in lines[1:]:
        if BREAKING_RE.match(line) and not line.startswith(("BREAKING CHANGE:", "BREAKING-CHANGE:")):
            findings.append(("ask", "breaking-change-case", "write `BREAKING CHANGE:` in capitals"))
            break
    return findings


# --------------------------------------------------------------------------- config
def _compile(entries, kind):
    compiled = []
    for entry in entries:
        pattern, label = entry.get("pattern"), entry.get("label")
        if not pattern or not label:
            return None, f"an entry in '{kind}' is missing pattern or label"
        try:
            compiled.append((re.compile(pattern), label))
        except re.error as exc:
            return None, f"pattern `{label}` does not compile ({exc})"
    return compiled, None


def validate_structure(raw):
    """Fall back to defaults on anything malformed."""
    out = dict(DEFAULT_STRUCTURE)
    if not isinstance(raw, dict):
        return out
    types = raw.get("allowed_types")
    if isinstance(types, list) and types and all(isinstance(t, str) and t.islower() for t in types):
        out["allowed_types"] = types
    for key in ("subject_target", "subject_hard", "body_hard"):
        value = raw.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and value > 0:
            out[key] = value
    if out["subject_target"] > out["subject_hard"]:
        out["subject_target"] = out["subject_hard"]
    for key in ("non_imperative_first_words", "generated_prefixes"):
        value = raw.get(key)
        if isinstance(value, list) and all(isinstance(v, str) for v in value):
            out[key] = [v.lower() for v in value]
    hints = raw.get("type_suggestions")
    if isinstance(hints, dict):
        out["type_suggestions"] = {str(k): str(v) for k, v in hints.items()}
    return out


def load_config(path):
    """Return (hard, soft, structure, error). Language packs merge onto the base."""
    try:
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [], [], None, f"pattern file unreadable ({type(exc).__name__})"
    if not isinstance(data.get("hard"), list) or not isinstance(data.get("soft"), list):
        return [], [], None, "pattern file has no 'hard'/'soft' lists"

    hard, err = _compile(data["hard"], "hard")
    if err:
        return [], [], None, err
    soft, err = _compile(data["soft"], "soft")
    if err:
        return [], [], None, err

    for pack in sorted(pathlib.Path(path).parent.glob("patterns.*.json")):
        try:
            extra = json.loads(pathlib.Path(pack).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue                                  # a broken pack must not block work
        for kind, target in (("hard", hard), ("soft", soft)):
            entries = extra.get(kind)
            if isinstance(entries, list):
                compiled, packerr = _compile(entries, kind)
                if not packerr:
                    target.extend(compiled)

    if not hard and not soft:
        return [], [], None, "pattern file is empty"
    return hard, soft, validate_structure(data.get("structure")), None


def scan(text, rules):
    return [label for rx, label in rules if rx.search(text)]


def emit(decision, reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        },
    }, ensure_ascii=False))


SPEC_REMINDER = (
    "Required shape: `<type>(<scope>): <subject>`, blank line, body wrapped at 100. "
    "Subject imperative, lowercase, no trailing period. The body explains why, not what. "
    "No conversation references, no first person singular, no AI attribution."
)


def run(payload, patterns_path):
    cmd = (payload.get("tool_input") or {}).get("command") or ""
    if "commit" not in cmd:
        return                   # cheap guard: the gate runs on every Bash call
    cwd = payload.get("cwd") or os.getcwd()

    commit_calls = []
    for original, masked in split_segments(cmd):
        cd_match = CD_RE.match(masked)
        if cd_match:
            candidate = cd_match.group(1)
            cwd = candidate if os.path.isabs(candidate) else os.path.join(cwd, candidate)
        tokens, parsed_ok = tokenize(masked)
        arg_index = commit_arg_index(tokens)
        if arg_index is not None:
            commit_calls.append((original, arg_index, parsed_ok, cwd))
    if not commit_calls:
        return

    hard_rules, soft_rules, structure, err = load_config(patterns_path)
    if err:
        emit("ask", f"Commit message rules could not be checked: {err}. Expected file: "
                    f"{patterns_path}. Verify the message against RULES.md yourself.")
        return

    hard_hits, soft_hits, findings, notes = [], [], [], []
    for original, arg_index, parsed_ok, seg_cwd in commit_calls:
        raw_tokens, raw_ok = tokenize(original)
        message, source = extract_message(
            original, raw_tokens, parsed_ok and raw_ok, arg_index, seg_cwd)

        haystack = fold(original if message is None else original + "\n" + message)
        hard_hits.extend(scan(haystack, hard_rules))
        soft_hits.extend(scan(haystack, soft_rules))

        if source.startswith("ERROR:"):
            notes.append(source[len("ERROR:"):])
        elif message is not None:
            findings.extend(check_structure(normalise(message), structure))

    if not (hard_hits or soft_hits or findings or notes):
        return

    decision = "deny" if hard_hits or any(f[0] == "deny" for f in findings) else "ask"

    parts = []
    if notes:
        parts.append(" ".join(dict.fromkeys(notes)))
    forbidden = list(dict.fromkeys(hard_hits + soft_hits))
    if forbidden:
        parts.append("Forbidden content: " + "; ".join(forbidden) + ".")
    if findings:
        parts.append("Structure: " + "; ".join(
            f"[{rule}] {detail}" for _, rule, detail in findings) + ".")
    parts.append(SPEC_REMINDER)
    emit(decision, " ".join(parts))


def patterns_path_from_argv(argv):
    """Tiny hand-rolled flag scan: argparse costs ~10 ms of import on every Bash call."""
    for i, arg in enumerate(argv):
        if arg == "--patterns" and i + 1 < len(argv):
            return argv[i + 1]
        if arg.startswith("--patterns="):
            return arg.split("=", 1)[1]
    return str(DEFAULT_PATTERNS)


def main():
    patterns_path = patterns_path_from_argv(sys.argv[1:])
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return
    try:
        run(payload, patterns_path)
    except Exception as exc:                           # a gate must never fail open
        emit("ask", f"Commit message gate failed unexpectedly ({type(exc).__name__}). "
                    f"Verify the message against RULES.md yourself.")


if __name__ == "__main__":
    main()
