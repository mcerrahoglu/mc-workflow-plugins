#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SessionStart hook: injects RULES.md into the session context.

Runs by itself in every new window while the plugin is enabled, so the rules never have
to be recalled by hand. RULES.md is the single source of the rule text.
"""
import json
import pathlib
import sys

RULES = pathlib.Path(__file__).resolve().parent.parent / "RULES.md"

try:
    text = RULES.read_text(encoding="utf-8")
except OSError:
    sys.exit(0)          # a missing rule file must not block the session

print(json.dumps({
    "suppressOutput": True,
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": (
            # The precedence rule itself lives in RULES.md, which follows immediately.
            # Stating it here as well put two copies side by side in the same context,
            # one of them inside a Python string that a rule edit would not reach.
            "The engineering rules below apply to this session "
            "(source: the rules plugin).\n\n" + text
        ),
    },
}, ensure_ascii=False))
