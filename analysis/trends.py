#!/usr/bin/env python3
"""
Parse WTF-style incident markdown logs and summarize counts by month and coarse category.

Why categories at all?
  Trends need a bucket name per incident so you can answer "did this *kind* of failure
  get rarer after we changed rules?" Month-only counts don't show *which* mode moved.

  The built-in names (fallbacks, destructive_ops, …) are not a universal ontology. They
  are keyword heuristics that matched *this* repo's coding-agent corpus. Your domains
  (creative tools, billing, whatever) will differ — edit slug_category() below to match
  your vocabulary, or add structured tags in markdown and parse those instead.

How to customize:
  Change slug_category(title, body_preview): add branches, regexes, or map from a
  **Category:** line if you add one to your protocol. Return short snake_case labels;
  they appear as keys in --json output and in the "By category" table.

Usage:
  python analysis/trends.py FILE.md [FILE.md ...]
  python analysis/trends.py examples/incident_example.md
  python analysis/trends.py --plot   # requires matplotlib; writes trends.png in cwd

Legacy logs may use **Timestamp:**; current protocol uses **Datetime:**.
Incident headers: ## Incident NNN: Title  or  ## Incident NNN
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


# Headers must match "## Incident …" (corpus style); theme summaries without that pattern are skipped.
INCIDENT_START = re.compile(r"^## Incident\s+(.+)$", re.MULTILINE)
TS_LINE = re.compile(
    r"\*\*(?:Timestamp|Datetime):\*\*\s*([0-9]{4}-[0-9]{2}-[0-9]{2})",
    re.IGNORECASE,
)


def slug_category(title: str, body_preview: str) -> str:
    """Assign one label per incident; customize this for your project."""
    t = (title + " " + body_preview[:800]).lower()
    if "truncation" in t or "context overflow" in t or "chunk extraction" in t:
        return "truncation_context"
    if re.search(r"\breset\b|db reset|destructive|wipe|drop schema", t):
        return "destructive_ops"
    if re.search(r"\btruncate\b", t) and "truncation" not in t:
        return "destructive_ops"
    if "fallback" in t or "graceful degradation" in t:
        return "fallbacks"
    if "backward compat" in t or "legacy alias" in t or "backcompat" in t:
        return "backward_compat"
    if "model" in t and (
        "fabricat" in t
        or "opus" in t and "not" in t
        or "identified" in t
        or "incorrectly identified" in t
    ):
        return "model_identity"
    if "monkey patch" in t or "monkey-patch" in t:
        return "monkey_patch"
    if "evasion" in t or "wrong tool" in t or "delete_file" in t:
        return "remediation_evasion"
    if "spec" in t or "architecture" in t or "v3" in t:
        return "spec_architecture"
    return "other"


def month_key(iso_date: str) -> str:
    return iso_date[:7] if len(iso_date) >= 7 else "unknown"


def split_blocks(text: str) -> list[tuple[str, str, str]]:
    """Return list of (id_str, title, full_block)."""
    matches = list(INCIDENT_START.finditer(text))
    out = []
    for i, m in enumerate(matches):
        rest = m.group(1).strip()
        id_m = re.match(r"^(\d+)\s*:\s*(.*)$", rest)
        if id_m:
            incident_id, title = id_m.group(1), id_m.group(2).strip()
        else:
            colon = rest.find(":")
            if colon != -1:
                incident_id, title = rest[:colon].strip(), rest[colon + 1 :].strip()
            else:
                incident_id, title = rest, ""
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[m.start() : end]
        out.append((incident_id, title, block))
    return out


def parse_file(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="replace")
    rows = []
    for incident_id, title, block in split_blocks(text):
        tm = TS_LINE.search(block)
        iso = tm.group(1) if tm else "unknown"
        preview = block.split("\n", 15)[-1] if block else ""
        cat = slug_category(title, block)
        rows.append(
            {
                "file": str(path),
                "incident_id": incident_id,
                "title": title,
                "date": iso,
                "month": month_key(iso),
                "category": cat,
            }
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="WTF incident trends by month/category")
    ap.add_argument("paths", nargs="*", help="Markdown files containing incidents")
    ap.add_argument("--glob", dest="glob_pat", help="Glob pattern of markdown files")
    ap.add_argument("--json", action="store_true", help="Print JSON summary to stdout")
    ap.add_argument(
        "--plot",
        action="store_true",
        help="If matplotlib is installed, write trends.png (incidents per month)",
    )
    args = ap.parse_args()

    files: list[Path] = []
    for p in args.paths:
        files.append(Path(p))
    if args.glob_pat:
        for p in glob.glob(args.glob_pat, recursive=True):
            files.append(Path(p))

    files = sorted({f.resolve() for f in files if f.is_file()})

    if not files:
        print(
            "No files. Example:\n"
            "  python analysis/trends.py path/to/incidents/*.md",
            file=sys.stderr,
        )
        return 1

    all_rows: list[dict] = []
    for f in files:
        all_rows.extend(parse_file(f))

    if not all_rows:
        print("No incidents parsed (need ## Incident N headers).", file=sys.stderr)
        return 1

    by_month = Counter(r["month"] for r in all_rows)
    by_cat = Counter(r["category"] for r in all_rows)
    by_month_cat: dict[str, Counter[str]] = defaultdict(Counter)
    for r in all_rows:
        by_month_cat[r["month"]][r["category"]] += 1

    summary = {
        "files": [str(f) for f in files],
        "incident_count": len(all_rows),
        "by_month": dict(sorted(by_month.items())),
        "by_category": dict(by_cat.most_common()),
        "by_month_category": {m: dict(by_month_cat[m]) for m in sorted(by_month_cat)},
    }

    if args.json:
        print(json.dumps(summary, indent=2))
        return 0

    print(f"Files: {len(files)}  Incidents parsed: {len(all_rows)}\n")
    print("By month:")
    for m, c in sorted(by_month.items()):
        print(f"  {m}: {c}")
    print("\nBy category:")
    for cat, c in by_cat.most_common():
        print(f"  {cat}: {c}")

    if args.plot:
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            print("\n--plot skipped: pip install matplotlib", file=sys.stderr)
            return 0

        months = sorted(by_month.keys())
        counts = [by_month[m] for m in months]
        plt.figure(figsize=(10, 4))
        plt.bar(months, counts, color="#2d2d2d")
        plt.title("Incidents logged per month (coarse parse)")
        plt.xlabel("Month")
        plt.ylabel("Count")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        out = Path("trends.png")
        plt.savefig(out, dpi=120)
        print(f"\nWrote {out.resolve()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
