#!/usr/bin/env python3
"""Validate local markdown links and optional external URLs.

Usage:
  python scripts/validate_docs.py
  python scripts/validate_docs.py --check-urls
  python scripts/validate_docs.py README.md PROTOCOL.md
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GLOBS = ("*.md", "*.mdc")
LINK_RE = re.compile(r"(?<!\!)\[[^\]]+\]\(([^)]+)\)")
FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)


@dataclass
class LinkIssue:
    file: Path
    target: str
    message: str


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def strip_code_fences(text: str) -> str:
    return FENCE_RE.sub("", text)


def slugify_heading(text: str) -> str:
    cleaned = re.sub(r"<[^>]+>", "", text)
    cleaned = re.sub(r"[`*_~]", "", cleaned)
    cleaned = cleaned.strip().lower()
    cleaned = re.sub(r"[^a-z0-9 _-]+", "", cleaned)
    cleaned = cleaned.replace(" ", "-")
    cleaned = re.sub(r"-+", "-", cleaned)
    return cleaned.strip("-")


def collect_headings(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    text = strip_code_fences(text)
    return {slugify_heading(m.group(1)) for m in HEADING_RE.finditer(text)}


def split_target(target: str) -> tuple[str, str]:
    if "#" in target:
        path_part, fragment = target.split("#", 1)
        return path_part, fragment
    return target, ""


def validate_local_link(source: Path, target: str, issues: list[LinkIssue]) -> None:
    path_part, fragment = split_target(target)
    if not path_part:
        issues.append(LinkIssue(source, target, "empty relative target"))
        return

    target_path = (source.parent / path_part).resolve()
    if not target_path.exists():
        issues.append(LinkIssue(source, target, f"missing target: {rel(target_path)}"))
        return

    if fragment:
        if target_path.is_dir():
            issues.append(LinkIssue(source, target, "fragment points at a directory"))
            return
        headings = collect_headings(target_path)
        if fragment.lower() not in headings:
            issues.append(LinkIssue(source, target, f"missing heading anchor `#{fragment}` in {rel(target_path)}"))


def check_url(url: str, timeout: float = 8.0) -> tuple[bool, str]:
    req = Request(url, method="HEAD", headers={"User-Agent": "wtf-llm-doc-check/1.0"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            code = getattr(resp, "status", resp.getcode())
            return 200 <= code < 400, str(code)
    except HTTPError as exc:
        if exc.code == 405:
            req = Request(url, method="GET", headers={"User-Agent": "wtf-llm-doc-check/1.0"})
            try:
                with urlopen(req, timeout=timeout) as resp:
                    code = getattr(resp, "status", resp.getcode())
                    return 200 <= code < 400, str(code)
            except Exception as inner_exc:  # noqa: BLE001
                return False, f"GET failed: {inner_exc}"
        return False, f"HTTP {exc.code}"
    except URLError as exc:
        return False, str(exc.reason)
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def iter_docs(paths: list[str]) -> list[Path]:
    if paths:
        docs = [Path(p) for p in paths]
    else:
        docs = []
        for pattern in DEFAULT_GLOBS:
            docs.extend(REPO_ROOT.rglob(pattern))
        docs = [p for p in docs if p.is_file() and ".git" not in p.parts]
    return sorted({p.resolve() for p in docs})


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate markdown links in the wtf-llm repo")
    parser.add_argument("paths", nargs="*", help="Markdown files to validate (default: repo markdown files)")
    parser.add_argument("--check-urls", action="store_true", help="Also HEAD-check external http(s) links")
    args = parser.parse_args()

    docs = iter_docs(args.paths)
    if not docs:
        print("No docs found.", file=sys.stderr)
        return 1

    issues: list[LinkIssue] = []
    url_issues: list[str] = []
    checked_urls = set()

    for doc in docs:
        text = strip_code_fences(doc.read_text(encoding="utf-8", errors="replace"))
        for raw_target in LINK_RE.findall(text):
            target = raw_target.strip()
            if not target:
                continue
            if target.startswith(("http://", "https://")):
                if args.check_urls and target not in checked_urls:
                    ok, detail = check_url(target)
                    checked_urls.add(target)
                    if not ok:
                        url_issues.append(f"{rel(doc)} -> {target}: {detail}")
                continue
            if target.startswith(("mailto:", "tel:")):
                continue
            if target.startswith("#"):
                fragment = target[1:]
                headings = collect_headings(doc)
                if fragment.lower() not in headings:
                    issues.append(LinkIssue(doc, target, f"missing heading anchor `#{fragment}` in same file"))
                continue
            validate_local_link(doc, target, issues)

    if issues or url_issues:
        for issue in issues:
            print(f"BROKEN: {rel(issue.file)} -> {issue.target} ({issue.message})")
        for issue in url_issues:
            print(f"URL: {issue}")
        return 1

    print(f"OK: {len(docs)} markdown file(s) checked")
    if args.check_urls:
        print("OK: external URLs checked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
