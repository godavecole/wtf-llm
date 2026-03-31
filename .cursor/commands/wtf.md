---
description: Log a willful LLM rule violation (wtf protocol). Edit LOG_PATH below.
---

# /wtf

**LOG_PATH:** `docs/wtf/wtf_moments.md`
(Change this path to match your project.)

When invoked, log a willful rule violation to **LOG_PATH** if one exists. Full accountability. **Stop all current work until the entry is prepended.**

If there is genuinely no violation (mistaken command, dry run): say so in chat, ask the user to describe the violation or confirm cancel, and resume work. Fabricating an incident is itself an integrity failure — see **Spurious invocation** in **`PROTOCOL.md`**.

Full schema: **`PROTOCOL.md`** — copy it from [wtf-llm](https://github.com/godavecole/wtf-llm/blob/main/PROTOCOL.md) next to your project (or use your fork).

## Steps

1. **Stop current work.**
2. **Open or create the log** — or `python wtf.py init` / `python wtf.py new`.
3. **Identify the violation** — which rule(s) from `.cursor/rules` (or project docs) were broken, in which files.
4. **Prepend a new entry** (most recent first). `python wtf.py new` stubs all fields.

## Entry shape

- **Detection method:** `user` | `test` | `linter` | `model_self` | `ci` | `other`
- **Identity confirmation:** verbatim system line + **Model** (must match)
- **Situational analysis:** What Happened, Timeline, Specific Violations table
- **Damage estimate:** Token Cost + Token basis + Human Time for each phase (Implementation / Detection / Remediation)
- **Root cause and accountability** + **Evidence** (quoted rules, code)

Full accountability in every entry. Invoke with **`/wtf`**.
