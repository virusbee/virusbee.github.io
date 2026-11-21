#!/usr/bin/env python3
"""Check (and optionally fix) count/date fields driven by assets/cases.json.

Usage:
    python3 .agents/skills/workbuddy-replica/scripts/sync_site.py --check
    python3 .agents/skills/workbuddy-replica/scripts/sync_site.py --fix

The script only updates count-like fields. It never inserts a new card or
rewrites article copy; those still need a human edit.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]  # .agents/skills/workbuddy-replica/scripts -> repo root
CASES = ROOT / ".agents/skills/workbuddy-replica/assets/cases.json"
INDEX = ROOT / "index.html"
README = ROOT / "README.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def load_cases() -> dict:
    data = json.loads(read(CASES))
    cases = data["cases"]
    if not cases:
        raise SystemExit("cases.json has no cases")
    ids = [c["id"] for c in cases]
    if len(ids) != len(set(ids)):
        raise SystemExit("cases.json has duplicate ids")
    dates = [c["date"] for c in cases]
    latest = max(dates)
    log_count = len(cases)
    categories = int(data.get("site", {}).get("categories", 1))
    return {"data": data, "cases": cases, "log_count": log_count, "latest": latest, "categories": categories}


def check_pattern(errors: list[str], text: str, pattern: str, expected: int | str, label: str, flags: int = 0) -> None:
    m = re.search(pattern, text, flags)
    if not m:
        errors.append(f"{label}: pattern not found")
        return
    got = m.group(1)
    if str(got) != str(expected):
        errors.append(f"{label}: expected {expected}, got {got}")


def check(cases_info: dict) -> list[str]:
    data = cases_info["data"]
    cases = cases_info["cases"]
    n = cases_info["log_count"]
    latest = cases_info["latest"]
    categories = cases_info["categories"]
    errors: list[str] = []

    if int(data.get("site", {}).get("logCount", -1)) != n:
        errors.append(f"cases.json site.logCount: expected {n}, got {data.get('site', {}).get('logCount')}")
    if data.get("site", {}).get("latestDate") != latest:
        errors.append(f"cases.json site.latestDate: expected {latest}, got {data.get('site', {}).get('latestDate')}")

    for c in cases:
        for key in ("replica", "post"):
            if not (ROOT / c[key]).exists():
                errors.append(f"case {c['id']}: missing {key} -> {c[key]}")

    index = read(INDEX)
    check_pattern(errors, index, r"目前是第\s*(\d+)\s*篇", n, "index hero 篇数")
    check_pattern(errors, index, r'--latest\s*<strong>(\d+)</strong>', n, "index --latest")
    check_pattern(errors, index, r"共\s*(\d+)\s*篇构建日志", n, "index footer 篇数")
    check_pattern(errors, index, r"目前收录\s*(\d+)\s*篇复刻记录", n, "index meta description 篇数")
    check_pattern(errors, index, r"Total Logs</div>\s*<div class=\"kpi-num\"[^>]*data-target=\"(\d+)\"", n, "index Total Logs data-target")
    check_pattern(errors, index, r"Total Logs</div>\s*<div class=\"kpi-num\"[^>]*>(\d+)</div>", n, "index Total Logs 显示值")
    check_pattern(errors, index, r"Total Logs</div>[\s\S]{0,160}?共\s*(\d+)\s*篇构建日志", n, "index Total Logs note")
    check_pattern(errors, index, r"Categories</div>\s*<div class=\"kpi-num\"[^>]*data-target=\"(\d+)\"", categories, "index Categories data-target")
    check_pattern(errors, index, r"Categories</div>[\s\S]{0,160}?按\s*(\d+)\s*个主题", categories, "index Categories note")
    check_pattern(errors, index, r"分类分布饼图：复刻日志\s*(\d+)\s*篇", n, "index pie aria-label")
    check_pattern(errors, index, r"<title>分类分布：复刻日志\s*(\d+)\s*篇</title>", n, "index pie title")
    check_pattern(errors, index, r"复刻日志\s*(\d+)</span>", n, "index pie legend")

    date_m = re.search(r"Latest</div>\s*<div class=\"kpi-num\">([\d.]+)</div>\s*<div class=\"kpi-note\">([\d-]+)\s*更新", index)
    if not date_m:
        errors.append("index Latest block: pattern not found")
    else:
        expected_short = f"{int(latest[5:7])}.{latest[8:10]}"
        if date_m.group(1) != expected_short:
            errors.append(f"index Latest 显示日期: expected {expected_short}, got {date_m.group(1)}")
        if date_m.group(2) != latest:
            errors.append(f"index Latest note 日期: expected {latest}, got {date_m.group(2)}")

    readme = read(README)
    check_pattern(errors, readme, r"目前收录\s*(\d+)\s*篇日志", n, "README 篇数")
    for c in cases:
        if c["post"].split("/")[-1] not in readme:
            errors.append(f"README: missing post link {c['post']}")
        if c["replica"].split("/")[-1] not in readme:
            errors.append(f"README: missing replica link {c['replica']}")

    return errors


def fix(cases_info: dict) -> list[str]:
    """Fix count fields in place. Returns a list of changes."""
    n = cases_info["log_count"]
    latest = cases_info["latest"]
    categories = cases_info["categories"]
    short = f"{int(latest[5:7])}.{latest[8:10]}"
    changes: list[str] = []

    index = read(INDEX)
    before = index

    def sub(pattern: str, repl: str, label: str, text: str) -> str:
        new, count = re.subn(pattern, repl, text)
        if count and new != text:
            changes.append(f"{label}: {count} 处")
        return new

    index = sub(r"(目前是第\s*)\d+(\s*篇)", rf"\g<1>{n}\g<2>", "hero 篇数", index)
    index = sub(r"(--latest\s*<strong>)\d+(</strong>)", rf"\g<1>{n}\g<2>", "--latest", index)
    index = sub(r"(共\s*)\d+(\s*篇构建日志)", rf"\g<1>{n}\g<2>", "footer 篇数", index)
    index = sub(r"(目前收录\s*)\d+(\s*篇复刻记录)", rf"\g<1>{n}\g<2>", "meta 篇数", index)
    index = sub(r'(Total Logs</div>\s*<div class="kpi-num"[^>]*data-target=")\d+(")', rf"\g<1>{n}\g<2>", "Total Logs data-target", index)
    index = sub(r'(Total Logs</div>\s*<div class="kpi-num"[^>]*>)\d+(</div>)', rf"\g<1>{n}\g<2>", "Total Logs 显示值", index)
    index = sub(r"(Total Logs</div>[\s\S]{0,160}?共\s*)\d+(\s*篇构建日志)", rf"\g<1>{n}\g<2>", "Total Logs note", index)
    index = sub(r'(Categories</div>\s*<div class="kpi-num"[^>]*data-target=")\d+(")', rf"\g<1>{categories}\g<2>", "Categories data-target", index)
    index = sub(r"(Categories</div>[\s\S]{0,160}?按\s*)\d+(\s*个主题)", rf"\g<1>{categories}\g<2>", "Categories note", index)
    index = sub(r"(分类分布饼图：复刻日志\s*)\d+(\s*篇)", rf"\g<1>{n}\g<2>", "pie aria-label", index)
    index = sub(r"(<title>分类分布：复刻日志\s*)\d+(\s*篇</title>)", rf"\g<1>{n}\g<2>", "pie title", index)
    index = sub(r"(复刻日志\s*)\d+(</span>)", rf"\g<1>{n}\g<2>", "pie legend", index)
    index = sub(r'(Latest</div>\s*<div class="kpi-num">)[\d.]+(</div>\s*<div class="kpi-note">)[\d-]+(\s*更新)', rf"\g<1>{short}\g<2>{latest}\g<3>", "Latest 日期", index)
    if index != before:
        write(INDEX, index)

    readme = read(README)
    before = readme
    readme = sub(r"(目前收录\s*)\d+(\s*篇日志)", rf"\g<1>{n}\g<2>", "README 篇数", readme)
    if readme != before:
        write(README, readme)

    return changes


def main() -> int:
    parser = argparse.ArgumentParser(description="Check/fix index.html and README counts from cases.json.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="check only (default)")
    group.add_argument("--fix", action="store_true", help="fix count fields in place")
    args = parser.parse_args()

    info = load_cases()
    if args.fix:
        changes = fix(info)
        if changes:
            print("fixed:")
            for c in changes:
                print(f"  - {c}")
        else:
            print("nothing to fix")
        errors = check(info)
        if errors:
            print("remaining issues:")
            for e in errors:
                print(f"  ERROR {e}")
            return 1
        print("all counts consistent")
        return 0

    errors = check(info)
    if errors:
        for e in errors:
            print(f"ERROR {e}")
        print(f"\n{len(errors)} issue(s). Run --fix for count-only fields, or edit cards manually.")
        return 1
    print(f"all counts consistent: {info['log_count']} logs, latest {info['latest']}, {info['categories']} category")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
