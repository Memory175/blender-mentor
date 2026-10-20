# -*- coding: utf-8 -*-
"""source_audit.py — 来源注册表审计（标准/书籍/论文是否过期、失效、缺 jurisdiction）。

规则：
- data.source_id 必须存在于 assets/source_registry.json；
- status=withdrawn/superseded → fail；
- 法规 type=code 缺 jurisdiction → fail；
- verification=pending/metadata-only → warn；
- next_check_due 过期 → warn；
- 旧模块没有 source_id → legacy（默认 warn，--strict-legacy 才 fail）；
- 有 source_id 但 source registry 缺失/不可读 → fail（不能因为文件缺失就跳过）。

用法：
    python scripts/source_audit.py [--root .] [--json out.json]
    python scripts/source_audit.py --root _lab/ARC-001-draft
"""
import argparse
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import module_governance as mg  # noqa: E402


def _date(value):
    try:
        return datetime.date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def load_source_registry(root, path=None):
    p = path or os.path.join(root, "assets", "source_registry.json")
    if not os.path.isfile(p):
        return None, ["source registry missing: %s" % p]
    try:
        with open(p, encoding="utf-8") as fh:
            reg = json.load(fh)
    except Exception as exc:  # noqa: BLE001
        return None, ["source registry unreadable: %s" % exc]
    if reg.get("schema") != "mentor-source-registry/1":
        return None, ["source registry schema != mentor-source-registry/1"]
    return reg, []


def audit(root, source_path=None, modules_dir=None, today=None, strict_legacy=False, only_ids=None):
    today = today or datetime.date.today()
    mod_reg, mod_probs = mg.load_registry(root) if not modules_dir else (None, [])
    modules, load_probs = mg.load_modules(root, modules_dir, mod_reg)
    base_probs = list(mod_probs) + list(load_probs)
    if only_ids:
        modules = [m for m in modules if m.get("id") in only_ids]

    used = set()
    legacy = []
    entries = []
    for mod in modules:
        mid = mod.get("id", "?")
        for d in mod.get("data", []):
            sid = d.get("source_id")
            if not sid:
                legacy.append("%s.%s: missing source_id" % (mid, d.get("key", "?")))
                continue
            used.add(sid)
            entries.append((mid, d.get("key", "?"), sid))

    sources, probs = load_source_registry(root, source_path)
    if sources is None:
        if used:
            problems = base_probs + [
                "source registry missing/unreadable but %d data entries use source_id (%s)"
                % (len(used), ", ".join(sorted(used)))]
            return {"status": "fail", "reason": probs[0] if probs else "no source registry",
                    "sources": 0, "used_sources": sorted(used),
                    "problems": list(dict.fromkeys(problems)), "warnings": [],
                    "legacy": list(dict.fromkeys(legacy)), "checked_at": today.isoformat()}
        return {"status": "skipped", "reason": probs[0] if probs else "no source registry",
                "sources": 0, "problems": base_probs, "warnings": [], "legacy": legacy}

    by_id = {}
    problems, warnings = list(base_probs), []
    for s in sources.get("sources", []):
        sid = s.get("id")
        if not sid:
            problems.append("source missing id")
        elif sid in by_id:
            problems.append("duplicate source id: %s" % sid)
        by_id[sid] = s

    for mid, key, sid in entries:
        src = by_id.get(sid)
        if not src:
            problems.append("%s.%s: unknown source_id %s" % (mid, key, sid))
            continue
        status = src.get("status")
        if status in ("withdrawn", "superseded"):
            problems.append("%s.%s: source %s is %s" % (mid, key, sid, status))
        if status in ("pending", "unknown"):
            warnings.append("%s.%s: source %s status=%s" % (mid, key, sid, status))
        if src.get("verification") != "page-checked":
            warnings.append("%s.%s: source %s verification=%s" % (
                mid, key, sid, src.get("verification")))
        if src.get("type") == "code" and not src.get("jurisdiction"):
            problems.append("source %s: code missing jurisdiction" % sid)
        if src.get("type") == "paper" and not src.get("doi"):
            warnings.append("source %s: paper missing DOI" % sid)
        due = _date(src.get("next_check_due"))
        if due and due < today:
            warnings.append("source %s: overdue since %s" % (sid, due))
        if not _date(src.get("checked_at")):
            warnings.append("source %s: missing/invalid checked_at" % sid)
        if not src.get("check_url"):
            warnings.append("source %s: missing check_url" % sid)

    if strict_legacy:
        problems.extend(legacy)
    problems = list(dict.fromkeys(problems))
    warnings = list(dict.fromkeys(warnings))
    legacy = list(dict.fromkeys(legacy))
    status = "fail" if problems else ("warn" if (warnings or legacy) else "pass")
    return {
        "status": status,
        "sources": len(sources.get("sources", [])),
        "used_sources": sorted(used),
        "problems": problems,
        "warnings": warnings[:80],
        "legacy": legacy[:80],
        "checked_at": today.isoformat(),
    }


def main():
    ap = argparse.ArgumentParser(description="Audit source registry freshness and validity")
    ap.add_argument("--root", default=os.path.dirname(HERE))
    ap.add_argument("--source-registry", default=None)
    ap.add_argument("--modules-dir", default=None)
    ap.add_argument("--today", default=None)
    ap.add_argument("--strict-legacy", action="store_true")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    try:
        result = audit(os.path.abspath(args.root), args.source_registry, args.modules_dir,
                       _date(args.today) if args.today else None, args.strict_legacy)
    except Exception as exc:  # noqa: BLE001
        print("SOURCE_AUDIT " + json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=2)
    print("SOURCE_AUDIT " + json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] in ("pass", "warn", "skipped") else 1


if __name__ == "__main__":
    sys.exit(main())
