#!/usr/bin/env python3
"""Static checks for the replica site.

Usage:
    python3 .agents/skills/workbuddy-replica/scripts/check_site.py --root .

Checks local links, anchors, images/srcset, script/link/source/video refs,
duplicate IDs, lang/title/meta description, image alt, and external link rel.
Exits 1 when errors are found. Warnings do not fail unless --strict is used.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

SKIP_SCHEMES = {"http", "https", "mailto", "tel", "data", "blob", "javascript", "ftp"}
REF_ATTRS = {
    "a": ("href",),
    "link": ("href",),
    "script": ("src",),
    "img": ("src", "srcset"),
    "source": ("src", "srcset"),
    "video": ("poster",),
    "iframe": ("src",),
}


@dataclass(frozen=True)
class Ref:
    tag: str
    attr: str
    value: str
    line: int


class Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[tuple[str, int]] = []
        self.refs: list[Ref] = []
        self.lang: str | None = None
        self.title_present = False
        self.title_text: list[str] = []
        self.in_title = False
        self.meta_description = False
        self.img_without_alt: list[int] = []
        self.external_links: list[tuple[str, str, int]] = []  # href, rel, line

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._handle(tag, attrs)
        if tag == "title":
            self.in_title = True

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._handle(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_text.append(data)

    def _handle(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        d = {k: (v or "") for k, v in attrs}
        line = self.getpos()[0]

        if tag == "html" and "lang" in d:
            self.lang = d["lang"].strip()
        if tag == "title":
            self.title_present = True
        if tag == "meta" and d.get("name", "").lower() == "description":
            self.meta_description = bool(d.get("content", "").strip())
        if "id" in d and d["id"].strip():
            self.ids.append((d["id"].strip(), line))

        for attr in REF_ATTRS.get(tag, ()):
            if attr in d:
                self.refs.append(Ref(tag, attr, d[attr].strip(), line))

        if tag == "img" and "alt" not in d:
            self.img_without_alt.append(line)

        if tag == "a" and d.get("href", "").strip():
            href = d["href"].strip()
            parsed = urlparse(href)
            if href.startswith("//") or parsed.scheme in {"http", "https"}:
                self.external_links.append((href, d.get("rel", ""), line))


def resolve_local(root: Path, page: Path, value: str) -> tuple[Path | None, str]:
    """Return (target, fragment). target=None means external/skip."""
    if not value:
        return None, ""
    if value.startswith("//"):
        return None, ""
    parsed = urlparse(value)
    if parsed.scheme:
        return None, ""
    if parsed.netloc:
        return None, ""
    path = unquote(parsed.path)
    fragment = unquote(parsed.fragment)
    if not path:
        return page, fragment
    if path.startswith("/"):
        target = (root / path.lstrip("/")).resolve()
    else:
        target = (page.parent / path).resolve()
    return target, fragment


def candidate_urls(value: str, attr: str) -> list[str]:
    if attr != "srcset":
        return [value]
    out: list[str] = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        out.append(part.split()[0])
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Static checks for the replica site.")
    parser.add_argument("--root", default=".", help="repository root (default: cwd)")
    parser.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    files = [root / "index.html", *sorted((root / "posts").glob("*.html")), *sorted((root / "replicas").glob("*.html"))]
    files = [f for f in files if f.exists()]
    if not files:
        print(f"no HTML files found under {root}", file=sys.stderr)
        return 1

    errors: list[str] = []
    warnings: list[str] = []
    ids_cache: dict[Path, set[str]] = {}

    def rel(f: Path) -> str:
        try:
            return str(f.relative_to(root))
        except ValueError:
            return str(f)

    def ids_for(f: Path) -> set[str]:
        if f not in ids_cache:
            p = Page()
            p.feed(f.read_text(encoding="utf-8", errors="replace"))
            ids_cache[f] = {i for i, _ in p.ids}
        return ids_cache[f]

    for f in files:
        page = Page()
        page.feed(f.read_text(encoding="utf-8", errors="replace"))

        if not page.lang:
            errors.append(f"{rel(f)}: missing <html lang>")
        if not page.title_present or not "".join(page.title_text).strip():
            errors.append(f"{rel(f)}: missing or empty <title>")
        if not page.meta_description:
            errors.append(f"{rel(f)}: missing or empty meta description")

        seen: dict[str, int] = {}
        for id_value, line in page.ids:
            if id_value in seen:
                errors.append(f"{rel(f)}:{line}: duplicate id '{id_value}' (first at line {seen[id_value]})")
            else:
                seen[id_value] = line

        for line in page.img_without_alt:
            errors.append(f"{rel(f)}:{line}: <img> missing alt attribute")

        for href, rel_value, line in page.external_links:
            tokens = set(rel_value.lower().split())
            if "noopener" not in tokens or "noreferrer" not in tokens:
                warnings.append(f"{rel(f)}:{line}: external link missing rel=\"noopener noreferrer\" -> {href}")

        for ref in page.refs:
            for raw in candidate_urls(ref.value, ref.attr):
                target, fragment = resolve_local(root, f, raw)
                if target is None:
                    continue
                if not target.exists():
                    errors.append(f"{rel(f)}:{ref.line}: missing {ref.tag}[{ref.attr}] target -> {raw}")
                    continue
                if fragment and fragment != "top" and target.suffix.lower() in {".html", ".htm"}:
                    if fragment not in ids_for(target):
                        errors.append(f"{rel(f)}:{ref.line}: missing anchor #{fragment} in {rel(target)}")

    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")

    print(f"\nchecked {len(files)} HTML files: {len(errors)} error(s), {len(warnings)} warning(s)")
    if errors or (args.strict and warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
