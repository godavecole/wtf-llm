#!/usr/bin/env python3
"""
wtf.py — CLI for the wtf-llm incident log and token telemetry.

Commands:
  init          Create log file + parent dirs (idempotent; does not overwrite).
  new           Prepend a blank incident stub (full protocol fields).
  list          Table of incidents; --full dumps the log.
  stats         Count incidents; breakdown by detection method.
  ingest-usage  Import telemetry CSV into token ledger JSONL (dedup by event_id).
  link-events   Link token event IDs to an incident.
  rollup        Compute strict / blended / upper token totals.

Configure default log path in DEFAULT_LOG or pass `--log <path>` on commands
that read incidents.
"""
import argparse
import csv
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime

DEFAULT_LOG = "docs/wtf/wtf_moments.md"
DEFAULT_LEDGER = ".wtf/token_ledger.jsonl"
DEFAULT_LINKS = ".wtf/incident_links.json"

HEADER = (
    "# WTF Moments\n\n"
    "<!-- wtf-llm: start early — run `python wtf.py new` for each incident. "
    "See PROTOCOL.md for the full schema. -->\n\n"
)

STUB = """\
## Incident {id}
**Datetime:** {dt}
**Session:** 
**Detection method:** user

*(replace with one of: `user`, `test`, `linter`, `model_self`, `ci`, `other` — who or what first surfaced the failure)*

**Overlaps with incidents:** 
*(optional; comma-separated incident IDs when this incident shares spend window with earlier incidents)*

### Identity confirmation

**System instruction line (verbatim):** 

*(Paste the line from your system/developer prompt that names your model or product. If none is exposed, say `N/A — not exposed by host` and name the host product, e.g. Cursor Composer.)*

**Model:** 

*(Must match the cited line above. Do not copy a neighboring incident row.)*

### Situational Analysis

**What Happened:** 

**Timeline of Failure:**
1. 

**Specific Violations:**

| File | Rule Violated | Status When First Seen |
|------|---------------|------------------------|
|  |  |  |

### Damage Estimate (quantifiable)

Use integers or a tight range. Mark how each token line was produced.

**ORIGINAL IMPLEMENTATION**
- Token Cost: 
- Token basis: *(metered | estimated | range)*
- Human Time Cost:

**DETECTION**
- Token Cost:
- Token basis: *(metered | estimated | range)*
- Human Time Cost:

**REMEDIATION**
- Token Cost:
- Token basis: *(metered | estimated | range)*
- Human Time Cost:

**Token event IDs (optional):**
*(optional narrative reference; canonical links are stored via `wtf.py link-events`)*

### Root Cause and Accountability



### Evidence

Rule:
```
(quote rule here)
```

Code:
```
(paste violating code here)
```

---

"""


def resolve_log(args):
    return getattr(args, "log", None) or DEFAULT_LOG


def next_incident_id(text):
    ids = [int(m) for m in re.findall(r"## Incident (\d+)", text)]
    return max(ids, default=0) + 1


def split_incidents(text):
    parts = re.split(r"(?=## Incident \d+)", text)
    return [p for p in parts if re.match(r"## Incident \d+", p)]


def find_insert_offset(text):
    """Insert before the first incident, or append after header-only preamble."""
    first_incident = re.search(r"^## Incident \d+", text, flags=re.MULTILINE)
    if first_incident:
        return first_incident.start()
    return len(text)


def ensure_parent(path):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def parse_incident_id(value):
    text = str(value).strip()
    if text.isdigit():
        return f"{int(text):03d}"
    return text


def read_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path) as f:
        return json.load(f)


def write_json(path, payload):
    ensure_parent(path)
    with open(path, "w") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")


def read_jsonl(path):
    if not os.path.exists(path):
        return []
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def append_jsonl(path, rows):
    if not rows:
        return
    ensure_parent(path)
    with open(path, "a") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True))
            f.write("\n")


def parse_detection_method(block):
    m = re.search(r"\*\*Detection method:\*\*\s*([^\n]+)", block)
    if not m:
        return None
    raw = m.group(1).strip()
    raw = raw.strip("`").strip("*").strip()
    if not raw:
        return None
    token = raw.split()[0].lower()
    if token in ("user", "test", "linter", "model_self", "ci", "other"):
        return token
    return raw[:48]


def parse_datetime(block):
    m = re.search(r"\*\*Datetime:\*\*\s*(.+)", block)
    if m:
        return m.group(1).strip()
    return None


def parse_session(block):
    m = re.search(r"\*\*Session:\*\*\s*(.+)", block)
    if m:
        return m.group(1).strip()
    return None


def parse_model(block):
    m = re.search(r"\*\*Model:\*\* (.+)", block)
    if m:
        return m.group(1).strip()
    return None


def parse_overlaps(block):
    m = re.search(r"\*\*Overlaps with incidents:\*\*\s*(.+)", block)
    if not m:
        return []
    raw = m.group(1).strip()
    ids = []
    for hit in re.findall(r"\d+", raw):
        ids.append(parse_incident_id(hit))
    return ids


def parse_number_token(num_text, suffix):
    value = float(num_text.replace(",", ""))
    suffix = suffix.lower()
    if suffix == "k":
        value *= 1000
    elif suffix == "m":
        value *= 1_000_000
    return int(round(value))


def parse_token_value(text):
    """
    Parse token text like:
      12000
      ~12,000
      8,000-12,000
      80k-120k
      1–2.5 million
      700,000+   -> treated as single lower bound
    Returns (low, high) or None.
    """
    if not text:
        return None
    range_unit_scale = None
    if re.search(r"\bmillion\b", text, flags=re.IGNORECASE):
        range_unit_scale = 1_000_000
    elif re.search(r"\bthousand\b", text, flags=re.IGNORECASE):
        range_unit_scale = 1_000
    normalized = (
        text.replace("–", "-")
        .replace("—", "-")
        .replace("million", "m")
        .replace("thousand", "k")
    )
    matches = re.findall(r"(\d[\d,]*(?:\.\d+)?)\s*([kKmM]?)", normalized)
    if not matches:
        return None
    values = []
    for num, suf in matches:
        value = parse_number_token(num, suf)
        if range_unit_scale and not suf:
            value *= range_unit_scale
        values.append(value)
    if len(values) >= 2 and "-" in normalized and range_unit_scale:
        return values[0], values[1]
    if len(values) >= 2 and "-" in normalized:
        low = min(values[0], values[1])
        high = max(values[0], values[1])
        return low, high
    val = values[0]
    return val, val


def parse_incident_token_costs(block):
    totals = []
    for line in block.splitlines():
        m = re.search(r"Token Cost:\s*(.+)", line)
        if not m:
            continue
        parsed = parse_token_value(m.group(1))
        if parsed:
            totals.append(parsed)
    return totals


def cmd_init(args):
    log_path = resolve_log(args)
    if os.path.exists(log_path):
        print(f"Already exists (not overwriting): {log_path}")
        return
    ensure_parent(log_path)
    with open(log_path, "w") as f:
        f.write(HEADER)
    print(f"Initialized empty log: {log_path}")
    print("Next: `python wtf.py new` when you need an incident entry.")


def cmd_new(args):
    log_path = resolve_log(args)
    ensure_parent(log_path)
    existing = ""
    if os.path.exists(log_path):
        with open(log_path) as f:
            existing = f.read()
    incident_id = next_incident_id(existing)
    dt = datetime.now().strftime("%Y-%m-%d %H:%M")
    stub = STUB.format(id=str(incident_id).zfill(3), dt=dt)
    if existing.strip():
        if existing.startswith("# "):
            insert_offset = find_insert_offset(existing)
            new_content = existing[:insert_offset] + stub + existing[insert_offset:]
        else:
            new_content = HEADER + stub + existing
    else:
        new_content = HEADER + stub
    with open(log_path, "w") as f:
        f.write(new_content)
    print(f"Stubbed Incident {str(incident_id).zfill(3)} in {log_path}")


def cmd_list(args):
    log_path = resolve_log(args)
    if not os.path.exists(log_path):
        print(f"No log at {log_path}")
        sys.exit(0)
    with open(log_path) as f:
        text = f.read()
    if getattr(args, "full", False):
        print(text)
        return
    blocks = split_incidents(text)
    rows = []
    for block in blocks:
        id_match = re.search(r"## Incident (\d+)", block)
        if not id_match:
            continue
        inc_id = id_match.group(1)
        dt = parse_datetime(block) or "-"
        model = parse_model(block) or "-"
        session = parse_session(block) or "-"
        det = parse_detection_method(block) or "-"
        rows.append((
            inc_id,
            dt,
            det,
            model,
            session,
        ))
    if not rows:
        print("No incidents found.")
        return
    print(f"{'ID':<6} {'Date':<17} {'Detection':<12} {'Model':<22} Session")
    print("-" * 90)
    for row in rows:
        print(f"{row[0]:<6} {row[1]:<17} {row[2]:<12} {row[3]:<22} {row[4]}")
    print(f"\n{len(rows)} incident(s) in {log_path}")


def cmd_stats(args):
    log_path = resolve_log(args)
    if not os.path.exists(log_path):
        print(f"No log at {log_path}")
        sys.exit(0)
    with open(log_path) as f:
        text = f.read()
    blocks = split_incidents(text)
    if not blocks:
        print("No incidents found.")
        return
    detections = []
    for block in blocks:
        d = parse_detection_method(block)
        detections.append(d if d else "(unset)")
    c = Counter(detections)
    print(f"Incidents: {len(blocks)}  ({log_path})\n")
    print("Detection method (who surfaced the failure):")
    for k, v in c.most_common():
        print(f"  {k}: {v}")


def read_events_by_id(ledger_path):
    events = {}
    for row in read_jsonl(ledger_path):
        event_id = str(row.get("event_id", "")).strip()
        if not event_id:
            continue
        events[event_id] = row
    return events


def event_total_tokens(row):
    if "total_tokens" in row and str(row["total_tokens"]).strip():
        return int(row["total_tokens"])
    input_tokens = int(row.get("input_tokens", 0) or 0)
    output_tokens = int(row.get("output_tokens", 0) or 0)
    return input_tokens + output_tokens


def _csv_str(row, key, fallback=""):
    return str(row.get(key, fallback)).strip() or fallback


def _csv_int(row, key):
    return int(_csv_str(row, key, "0"))


def _csv_float(row, key):
    return float(_csv_str(row, key, "0"))


def cmd_ingest_usage(args):
    existing_ids = set(read_events_by_id(args.ledger).keys())
    added = []
    skipped = 0

    with open(args.csv_path, newline="") as f:
        for row in csv.DictReader(f):
            event_id = _csv_str(row, "event_id")
            if not event_id:
                continue
            if event_id in existing_ids:
                skipped += 1
                continue
            inp = _csv_int(row, "input_tokens")
            out = _csv_int(row, "output_tokens")
            total = _csv_int(row, "total_tokens") or (inp + out)
            added.append({
                "event_id": event_id,
                "timestamp": _csv_str(row, "timestamp"),
                "provider": _csv_str(row, "provider"),
                "model": _csv_str(row, "model"),
                "input_tokens": inp,
                "output_tokens": out,
                "total_tokens": total,
                "cost_usd": _csv_float(row, "cost_usd"),
                "source": _csv_str(row, "source", "import"),
            })
            existing_ids.add(event_id)

    append_jsonl(args.ledger, added)
    print(f"Ingested {len(added)} event(s) into {args.ledger}")
    if skipped:
        print(f"Skipped {skipped} duplicate event_id row(s)")


def cmd_link_events(args):
    log_path = resolve_log(args)
    if not os.path.exists(log_path):
        print(f"No log at {log_path}")
        sys.exit(1)

    with open(log_path) as f:
        text = f.read()
    blocks = split_incidents(text)
    existing_incidents = set()
    for b in blocks:
        m = re.search(r"## Incident (\d+)", b)
        if m:
            existing_incidents.add(parse_incident_id(m.group(1)))

    incident_id = parse_incident_id(args.incident)
    if incident_id not in existing_incidents:
        print(f"Incident {incident_id} not found in {log_path}")
        sys.exit(1)

    events = read_events_by_id(args.ledger)
    missing = [eid for eid in args.event_id if eid not in events]
    if missing:
        print(f"Unknown event_id in ledger {args.ledger}: {', '.join(missing)}")
        sys.exit(1)

    links = read_json(args.links, {})
    current = list(links.get(incident_id, []))
    for eid in args.event_id:
        if eid not in current:
            current.append(eid)
    links[incident_id] = current
    write_json(args.links, links)
    print(f"Incident {incident_id} linked to {len(current)} event(s) in {args.links}")


def cmd_rollup(args):
    log_path = resolve_log(args)
    if not os.path.exists(log_path):
        print(f"No log at {log_path}")
        sys.exit(1)

    with open(log_path) as f:
        text = f.read()
    blocks = split_incidents(text)
    incidents = []
    for block in blocks:
        m = re.search(r"## Incident (\d+)", block)
        if not m:
            continue
        incident_id = parse_incident_id(m.group(1))
        incidents.append((incident_id, block))
    incidents.sort(key=lambda x: int(x[0]) if x[0].isdigit() else 999999)

    links = read_json(args.links, {})
    events = read_events_by_id(args.ledger)

    # Strict: unique linked telemetry events only.
    linked_event_ids = set()
    for incident_id, _ in incidents:
        for eid in links.get(incident_id, []):
            linked_event_ids.add(eid)
    strict_total = sum(event_total_tokens(events[eid]) for eid in linked_event_ids if eid in events)

    # Blended/upper: add unlinked incident estimates, with overlap suppression.
    blended_estimate = 0
    upper_estimate = 0
    overlap_skipped = 0
    estimated_incidents_used = 0

    seen_incident_ids = set()
    for incident_id, block in incidents:
        seen_incident_ids.add(incident_id)
        if links.get(incident_id):
            continue
        overlaps = parse_overlaps(block)
        if any(ov in seen_incident_ids for ov in overlaps):
            overlap_skipped += 1
            continue
        parsed_costs = parse_incident_token_costs(block)
        if not parsed_costs:
            continue
        estimated_incidents_used += 1
        for low, high in parsed_costs:
            blended_estimate += int(round((low + high) / 2))
            upper_estimate += high

    blended_total = strict_total + blended_estimate
    upper_total = strict_total + upper_estimate

    print(f"Rollup for {log_path}")
    print(f"Ledger: {args.ledger}")
    print(f"Links:  {args.links}\n")
    print(f"strict_total_tokens:  {strict_total:,}")
    print(f"blended_total_tokens: {blended_total:,}")
    print(f"upper_total_tokens:   {upper_total:,}\n")
    print("details:")
    print(f"  linked_events_used:          {len(linked_event_ids)}")
    print(f"  estimated_incidents_used:    {estimated_incidents_used}")
    print(f"  overlap_incidents_skipped:   {overlap_skipped}")


def main():
    parser = argparse.ArgumentParser(description="wtf-llm incident log CLI")
    sub = parser.add_subparsers(dest="command")

    def add_log(p):
        p.add_argument(
            "--log",
            default=DEFAULT_LOG,
            help=f"Path to log file (default: {DEFAULT_LOG})",
        )

    def add_telemetry_paths(p):
        p.add_argument(
            "--ledger",
            default=DEFAULT_LEDGER,
            help=f"Token ledger JSONL path (default: {DEFAULT_LEDGER})",
        )
        p.add_argument(
            "--links",
            default=DEFAULT_LINKS,
            help=f"Incident->event mapping JSON path (default: {DEFAULT_LINKS})",
        )

    add_log(sub.add_parser("init", help="Create empty log file (does not overwrite)"))
    add_log(sub.add_parser("new", help="Prepend a blank incident stub"))
    list_p = sub.add_parser("list", help="List incidents")
    add_log(list_p)
    list_p.add_argument("--full", action="store_true", help="Dump full log")
    add_log(sub.add_parser("stats", help="Incident count and detection-method breakdown"))

    ingest_p = sub.add_parser("ingest-usage", help="Ingest provider telemetry CSV into ledger")
    ingest_p.add_argument("csv_path", help="CSV path with event_id + token columns")
    ingest_p.add_argument(
        "--ledger",
        default=DEFAULT_LEDGER,
        help=f"Token ledger JSONL path (default: {DEFAULT_LEDGER})",
    )

    link_p = sub.add_parser("link-events", help="Link token events to an incident")
    add_log(link_p)
    add_telemetry_paths(link_p)
    link_p.add_argument("--incident", required=True, help="Incident ID (e.g. 012)")
    link_p.add_argument("--event-id", action="append", required=True, help="Event ID to link; repeat flag for multiple")

    rollup_p = sub.add_parser("rollup", help="Compute strict/blended/upper token totals")
    add_log(rollup_p)
    add_telemetry_paths(rollup_p)

    args = parser.parse_args()
    if args.command == "init":
        cmd_init(args)
    elif args.command == "new":
        cmd_new(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "stats":
        cmd_stats(args)
    elif args.command == "ingest-usage":
        cmd_ingest_usage(args)
    elif args.command == "link-events":
        cmd_link_events(args)
    elif args.command == "rollup":
        cmd_rollup(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
