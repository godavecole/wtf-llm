# wtf-llm

Structured protocol, **Cursor `/wtf` command**, and **`wtf.py` CLI** for logging willful AI failures: the model had the rules, understood the task, and still chose the wrong thing.

## Why this repo exists (for reviewers)

This is a **slice of how I measure** creative and assistant surfaces. Comparable incidents beat vibes. You get **repeat failure modes**, **token and human-time cost**, and an **Evidence** block (quoted rule + snippet) that turns one bad session into **durable input** for rules, gates, and prompts.

The loop is explicit: **log → categorize → aggregate → change the system → check whether the curve moves.** That is the same muscle story-led and model-led teams need when “quality” is subjective but **frequency, cost, and category** are not.

| Piece | Role in the loop |
|--------|------------------|
| [PROTOCOL.md](./PROTOCOL.md) + [schema.json](./schema.json) | Same shape every time so entries are comparable |
| `wtf.py` `stats` / `rollup` / `ingest-usage` | Cost visibility and honest totals methodology |
| [TOP_LINE_REPORT.md](./TOP_LINE_REPORT.md) | Illustrative headline snapshot from a private corpus + how to derive totals yourself |
| [analysis/trends.py](./analysis/trends.py) | Month × coarse category — did interventions actually help? |

## What to do with the data

Comparable incidents beat one-off chat memory. You see **repeat failure modes**, attach **token and time cost**, and use the **Evidence** block (quoted rules + snippets) as input when you tighten `.cursor/rules` or project docs. **`analysis/trends.py`** shows whether those modes quiet down over time.

## Cursor: `/wtf`

1. Copy **[`.cursor/commands/wtf.md`](./.cursor/commands/wtf.md)** into your project's `.cursor/commands/`. Edit **LOG_PATH** for your log location.
2. Optionally add **[`examples/cursor-rule-wtf.mdc`](./examples/cursor-rule-wtf.mdc)** so agents use the same path.
3. Invoke **`/wtf`** in Cursor: agent stops work and prepends a full incident. Schema: **[PROTOCOL.md](./PROTOCOL.md)**.

## CLI: `wtf.py`

| Command | Purpose |
|--------|---------|
| `python wtf.py init` | Create empty log (idempotent) |
| `python wtf.py new` | Prepend a protocol stub |
| `python wtf.py list` / `list --full` | Incident table or full log |
| `python wtf.py stats` | Counts + detection-method breakdown |
| `python wtf.py ingest-usage <csv>` | Import metered rows into `.wtf/token_ledger.jsonl` |
| `python wtf.py link-events --incident N …` | Link `event_id`s to an incident |
| `python wtf.py rollup` | Strict / blended / upper token totals |

**Third-party telemetry:** Supply CSV; no built-in SDK hooks. Compatible stacks (Langfuse, LangSmith, Braintrust, Portkey, Helicone, provider dashboards) are listed under **[Third-party telemetry](./PROTOCOL.md#third-party-telemetry)** in **[PROTOCOL](./PROTOCOL.md)**.

**Reproduce analytics on your log** (point at any markdown file that follows the protocol):

```bash
python analysis/trends.py path/to/your_incidents.md --json
python wtf.py stats --log path/to/your_incidents.md
```

### Categories in `analysis/trends.py`

**Why not leave categories out?** Month counts alone only show volume. A **category** is a cheap way to ask whether a *specific failure mode* (fallbacks, spec drift, whatever you care about) is actually shrinking after you change prompts or rules.

**Will yours match mine?** No. The default `slug_category()` in [`analysis/trends.py`](./analysis/trends.py) is **heuristic keyword matching** tuned to one coding-agent log. It is a template, not a standard list.

**What to do:** Edit `slug_category()` in that file — add your keywords, regexes, or read a field you add to your incident template (for example a `**Category:**` line in the markdown). Use short `snake_case` labels; they show up in `--json` and in the printed "By category" breakdown.

### Docs QA

Run `python scripts/validate_docs.py` to check repo markdown links and heading anchors. Add `--check-urls` when you want the script to also HEAD-check external links.

## Examples

| Resource | Role |
|----------|------|
| [`examples/incident_example.md`](./examples/incident_example.md) | One full template-quality incident |
| [`examples/usage_template.csv`](./examples/usage_template.csv) | CSV shape for `ingest-usage` |
| [`examples/telemetry_sidecar_example.md`](./examples/telemetry_sidecar_example.md) | Ledger + links shapes |
| [`schema.json`](./schema.json) | JSON Schema (markdown stays canonical) |
| [`analysis/trends.py`](./analysis/trends.py) | Parse `## Incident N` headers → month/category (`--json`, `--plot`) |

## License

MIT — see [LICENSE](./LICENSE).
