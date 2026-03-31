# `/wtf` — LLM failure protocol (portable)

Use this in any repository. Pick a **single log file path** (default: `docs/wtf/wtf_moments.md`) and keep it consistent across your Cursor command and rules.

Run `python wtf.py init` early — before the expensive week, not after.

When invoked, the agent logs a **willful** rule violation (not an honest typo) to that file. Full accountability, full stop on other work until the entry is prepended.

**Why structure matters:** Comparable entries surface repeat modes (fallbacks, destructive ops, wrong model line) without relying on memory. That feeds **prioritization**, **cost visibility**, and **prompt/rule tuning** — lift the quoted rule + concrete violation into `.cursor/rules` or docs, then check whether category frequency moves with **`analysis/trends.py`**.

## Steps

1. **Stop current work** until logging is complete.
2. **Open or create the log** at your chosen path (or `python wtf.py init`).
3. **Identify the violation** — which rule(s) from your project rules were broken, in which files.
4. **Prepend a new entry** below the header, most recent first.

## Spurious invocation

If the command fired by mistake or there is genuinely no willful rule breach:

1. Say so in chat. Ask the user to describe the violation or confirm cancel.
2. If confirmed no violation: skip the log entry and resume work.
3. Fabricating an incident to fill the template is itself an integrity failure.

## Context and token budget

The log lives on disk. Keep it **off** default project context for routine tasks. Load it when logging, reviewing patterns, or tuning rules. One pasted excerpt or `analysis/trends.py` output beats dumping the full file into chat.

## Log timing

Best at catch time, while context is fresh. There is no tool here that scans a codebase and outputs incidents — `wtf.py` reads markdown you already wrote. Late entries reconstructed from git are fine; mark costs as **estimated** or **range**.

## Using logged data

| Goal | Approach |
|------|----------|
| Spot repeats | Search for failure modes in **Specific Violations** / **Evidence** |
| Prioritize fixes | **Damage estimate** columns: is this worth a new gate? |
| Tighten rules | Copy **Evidence** (quoted rule + bad snippet) into `.cursor/rules` as a positive instruction or anti-pattern line |
| Check if tuning helped | Re-run `analysis/trends.py` after rule changes — same categories, different counts |
| Token rollups | `ingest-usage` + `link-events` + `rollup` (strict / blended / upper) |

## Required entry format

### Header

- **Incident ID**: Next sequential number (e.g. Incident 001)
- **Datetime**: YYYY-MM-DD HH:MM
- **Session**: Brief description
- **Detection method**: `user` | `test` | `linter` | `model_self` | `ci` | `other` — who first surfaced the failure.

### Identity confirmation

Prevents wrong model names (same "copy the neighbor row" failure as silent defaults).

- **System instruction line (verbatim):** Paste the line naming your model/product. If the host hides it: `N/A — not exposed by host` + host product name.
- **Model:** Match that line.

### Situational analysis

- **What Happened** — **Timeline of Failure** — **Specific Violations** table (File | Rule Violated | Status When First Seen)

### Damage estimate (quantifiable)

Three phases, each with:

- **Token Cost** (integer or tight range)
- **Token basis**: `metered` | `estimated` | `range`
- **Human Time Cost**

Phases: **ORIGINAL IMPLEMENTATION** · **DETECTION** (cost to investigate after surfacing) · **REMEDIATION**

### Root cause and accountability

Full accountability: what behavior failed, why that optimization won. Legacy logs may title this **Letter of Accountability** — same requirement.

### Evidence

- Quoted rule(s)
- Code snippet(s) showing the violation

### Telemetry hooks (optional)

- **Token event IDs:** link metered provider events to the incident via `wtf.py link-events`.
- **Overlaps with incidents:** cite earlier incident IDs sharing the same spend window.

Rollup tiers:

| Tier | What it includes |
|------|-----------------|
| **Strict** | Deduped linked metered events only |
| **Blended** | Strict + unlinked estimates (range midpoint) |
| **Upper** | Strict + unlinked estimates (range upper bound) |

Linked telemetry is the source of truth for that incident's rollup. Keep narrative estimates as documentation for unlinked rows.

### Third-party telemetry

`wtf.py ingest-usage` reads CSV matching **[`examples/usage_template.csv`](./examples/usage_template.csv)** (`event_id`, `timestamp`, `provider`, `model`, `input_tokens`, `output_tokens`, `total_tokens`, `cost_usd`, `source`). Any tool that exports that shape is compatible.

| Style | Examples |
|-------|----------|
| OSS observability | [Langfuse](https://github.com/langfuse/langfuse) — export traces → reshape to CSV |
| Managed tracing | [LangSmith](https://smith.langchain.com), [Braintrust](https://www.braintrust.dev) |
| Gateway / proxy | [Portkey](https://portkey.ai), [Helicone](https://www.helicone.ai) |
| Provider-native | OpenAI / Anthropic / Google usage dashboards — normalize columns |

Emerging: **OpenTelemetry GenAI** semantic conventions (`gen_ai.*` attributes → ledger rows).

Pick **one** system of record per project.

## Integrity

Full accountability in every entry. Minimizing the incident in the log is itself a protocol failure.

## CLI

| Command | Purpose |
|---------|---------|
| `python wtf.py init` | Create empty log (idempotent) |
| `python wtf.py new` | Prepend a full stub |
| `python wtf.py list` / `list --full` | Incident table or full log |
| `python wtf.py stats` | Counts + detection-method breakdown |
| `python wtf.py ingest-usage <csv>` | Import telemetry CSV into ledger |
| `python wtf.py link-events --incident N …` | Map event IDs to an incident |
| `python wtf.py rollup` | Strict / blended / upper token totals |

## Schema and trends

- **[schema.json](./schema.json)** — JSON Schema for the logical incident shape (markdown stays canonical).
- **`python analysis/trends.py`** — Parse incident `.md` files; counts by month and coarse category. `--json`, optional `--plot`.
- **Categories** — The script buckets each incident with `slug_category()` (keyword heuristics in `analysis/trends.py`). Those labels matched one corpus; **edit that function** for your own taxonomy, or add an optional `**Category:**` (or similar) line to your entries and parse it there.
