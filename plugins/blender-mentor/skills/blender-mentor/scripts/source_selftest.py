# -*- coding: utf-8 -*-
"""source_selftest.py — 来源审计回归（纯 Python）。

覆盖：current/page-checked → pass；过期 → warn；withdrawn → fail；
缺 source_id（strict）→ fail；法规缺 jurisdiction → fail。
"""
import datetime
import hashlib
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import source_audit  # noqa: E402

TODAY = datetime.date(2026, 10, 20)


def _source(sid, **kw):
    s = {"id": sid, "type": "book", "title": "Test source", "edition": "1",
         "year": 2020, "status": "current", "verification": "page-checked",
         "checked_at": "2026-10-20", "next_check_due": "2027-10-20",
         "check_url": "https://www.wiley.com/"}
    s.update(kw)
    return s


def _module(sid=None, mid="AAA-001"):
    data = {"key": "value_mm", "value": 10, "unit": "mm", "source": "fixture"}
    if sid:
        data["source_id"] = sid
    return {
        "schema": "mentor-module/1", "id": mid, "version": "1.0.0", "status": "stable",
        "kind": "reference", "domain": ["test"],
        "intent": {"include": ["test"], "exclude": []},
        "coverage": [{"keywords": ["test"], "data_keys": ["value_mm"]}],
        "data": [data], "rules": [], "unknown_policy": "ask",
        "requires": [], "conflicts_with": [], "references": [], "tests": [], "changelog": [],
    }


def _run_case(sources, mod, strict=False):
    with tempfile.TemporaryDirectory(prefix="src_case_") as tmp:
        os.makedirs(os.path.join(tmp, "assets", "modules"))
        mp = os.path.join(tmp, "assets", "modules", mod["id"] + ".json")
        open(mp, "w", encoding="utf-8").write(json.dumps(mod, ensure_ascii=False))
        h = hashlib.sha256(open(mp, "rb").read()).hexdigest()
        open(os.path.join(tmp, "assets", "module_registry.json"), "w", encoding="utf-8").write(
            json.dumps({"schema": "mentor-registry/1", "modules": [
                {"id": mod["id"], "file": "assets/modules/%s.json" % mod["id"],
                 "version": mod["version"], "hash": "sha256:" + h, "status": "stable"}]},
                ensure_ascii=False))
        open(os.path.join(tmp, "assets", "source_registry.json"), "w", encoding="utf-8").write(
            json.dumps({"schema": "mentor-source-registry/1", "sources": sources}, ensure_ascii=False))
        return source_audit.audit(tmp, today=TODAY, strict_legacy=strict)


def run():
    cases = []
    r = _run_case([_source("BOOK-1")], _module("BOOK-1"))
    cases.append(("current_pass", r["status"] == "pass"))
    r = _run_case([_source("BOOK-1", next_check_due="2026-01-01")], _module("BOOK-1"))
    cases.append(("overdue_warn", r["status"] == "warn"))
    r = _run_case([_source("BOOK-1", status="withdrawn")], _module("BOOK-1"))
    cases.append(("withdrawn_fail", r["status"] == "fail"))
    r = _run_case([_source("BOOK-1")], _module(None), strict=True)
    cases.append(("missing_source_id_fail", r["status"] == "fail"))
    r = _run_case([_source("CODE-1", type="code", jurisdiction=None)], _module("CODE-1"))
    cases.append(("code_no_jurisdiction_fail", r["status"] == "fail"))
    passed = sum(1 for _, ok in cases if ok)
    return {"status": "pass" if passed == len(cases) else "fail",
            "passed": passed, "total": len(cases),
            "cases": [{"case": n, "pass": ok} for n, ok in cases]}


if __name__ == "__main__":
    result = run()
    print("SOURCE_SELFTEST " + json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result["status"] == "pass" else 1)
