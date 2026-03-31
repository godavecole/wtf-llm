# Headline totals from WTF logs

This repository does **not** include the raw incident log. The **tables below** are a **snapshot** aggregated from a **private** corpus (coding-agent failures across multiple projects). You cannot reproduce these rows from this repo; they are here as **illustrative headline data** and as a check on **methodology** (same rules as the section after the tables).

---

## Snapshot headline data *(private corpus; not in this repository)*

**Incident count:** **73** titled entries in that corpus. Two “double-numbered” entries (one incident originally **002** appearing twice, one **020** appearing twice) were distinct incidents with different titles — kept separately and renumbered sequentially. **Two** Project A entries (from an original 035–038 sequence) were absent from batch archives; best estimate of the original Project A total remained **68**. A continuation log (Project B) contributed **7** incidents at the time of this summary.

### Dominant themes

**No fallbacks / fail loud / error suppression** dominated the log.

- Largest single *documented* damage rollup: **Incident 045** — systemwide fallback/default patterns (`747+` instances across `77` files), with that entry’s own **total estimated damage ~1,205,000 tokens** (including attributed historic and testing/remediation costs in the entry).
- Closely related: **056** (systemic backward-compatibility violations; **~700,000+** tokens logged; entry notes actual may exceed **1M**), **048** (fallbacks reintroduced after 045), **044** (archetype fallbacks), plus many per-file `**.get(..., default)`**, **try/except log-and-continue**, and **warning suppression** incidents.

**Runner-up themes:** destructive database operations without **“ask twice”** (e.g. local `supabase db reset`), **false completion** / deferred TODOs, **docs/rules not read** before answering or editing.

### Composer and model identity

- **26** incidents attribute the model line **Composer** (or **Composer (Cursor)** / **Composer (Cursor AI)**).
- **Identity-fabrication examples:** **017** — logged as **Claude Sonnet 4.5** while the agent was Composer; **053** — prior rows as **“Claude Opus 4.5 (Cursor)”**; user: *“YOU ARE NOT OPUS!”*; root cause noted: copied neighboring log rows instead of reading system instructions.

### Aggregated estimates *(as recorded in log damage sections)*

Figures sum **per-incident estimates** (implementation waste, testing/remediation, documentation, and **where given** rolled-up “total estimated damage”). Numbers are **as logged by agents**, not independently metered.

| Metric | Aggregated estimate |
|--------|---------------------|
| **Total tokens** (waste + remediation as logged) | **~3,900,000** (~**3.9M**) |
| **Total human time** (as logged) | **~5,830 minutes** ≈ **97.2 hours** ≈ **2.4 × 40h weeks** |

### Highest single-incident token lines *(from parsed totals in that log)*

1. **045** — Systemwide fallback defaults (~**1.2M** in-incident total)  
2. **056** — Systemic backward compatibility (~**700k+** logged; entry states actual may exceed **1M**)  
3. **011** — Rules unread; entire session invalid (~**120k**)  
4. **067** — Architecture misrepresentation + phase runner gap (~**120k**)  
5. **032** — Pytest without stack (~**85k**)  
6. **014** — Pagebreak loop (~**80k**)  
7. **010** — False completion / DEFERRED (~**80k**)  
8. **062** — CraftRAG / protections (~**75k**)  
9. **046** — Refactor without testing (~**68k** band)  
10. **008** (Project B) — Overwrite attempt + logging (~**60k** band)  

**Method used for the snapshot:** Prefer an explicit **“Total estimated damage: ~N tokens”** or **Token Cost** / **Token Accounting** line; else sum **Wasted Implementation** + **Wasted Testing/Remediation** where present; else take the largest plausible **“~Nk tokens”** line in the damage section while **excluding** dollar/embedding-pricing lines so **“1.5M records”** / **“per 1M tokens”** are not mistaken for incident token totals.

**Snapshot caveats:** Double-counting across systemwide vs narrow incidents; ranges taken as mid/max per entry rules; qualitative-only incidents contribute **0**; all quantities **self-reported** unless linked to metered telemetry.

---

## Deriving headline totals yourself

Use this when aggregating **your own** markdown log (or a private export).

### What to sum (per incident)

Prefer, in order:

1. An explicit line such as **"Total estimated damage: ~N tokens"** or a **"Token Accounting"** rollup, if present.
2. Otherwise, sum **Token Cost** lines under **ORIGINAL IMPLEMENTATION**, **DETECTION**, and **REMEDIATION** (or legacy **Wasted Implementation** / **Wasted Testing/Remediation** where your log uses those labels).
3. When only **ranges** appear (e.g. **80k–120k**), define whether you use **midpoint**, **max**, or **sum** of bounds — and apply that rule consistently across incidents.

**Exclude** lines that look like **record counts**, **embedding pricing**, or **per-1M-token** provider rates so values like **"1.5M records"** are not mistaken for incident token totals.

### General caveats

1. **Double-counting:** Some incidents describe **multi-session** or systemwide debt; others are narrow fixes of the same theme. Naive sums across all incidents **overlap** real-world cost with narrative scope.
2. **Ranges:** Many entries use ranges; your script or spreadsheet should state whether you took midpoint, upper bound, or something else.
3. **Qualitative damage:** Some incidents contribute **0** to token totals.
4. **Self-reported estimates:** Unless tied to metered events, numbers are **documentation**, not billing-grade audits.

### Metered (strict) rollups

Link provider **`event_id`s** to incidents with `wtf.py link-events`, keep rows in `.wtf/token_ledger.jsonl` (typically gitignored), then run `wtf.py rollup` for **strict** / **blended** / **upper** tiers. See **[PROTOCOL.md](./PROTOCOL.md)** and **`wtf.py`**.
