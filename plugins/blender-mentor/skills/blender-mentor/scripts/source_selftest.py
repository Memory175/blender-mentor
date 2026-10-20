# -*- coding: utf-8 -*-
"""source_selftest.py — 来源审计/查询回归（纯 Python）。

覆盖：current/page-checked → pass；过期 → warn；withdrawn → fail；
缺 source_id（strict）→ fail；法规缺 jurisdiction → fail；
有 source_id 但 registry 缺失 → fail；source_refresh 无 registry → skipped；
DOI 无 URL → 走 Crossref；preflight 遇到 source_audit 异常 → ask。
"""
import contextlib
import datetime
import hashlib
import io
import json
import os
import sys
import tempfile
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import module_lint  # noqa: E402
import preflight  # noqa: E402
import source_audit  # noqa: E402
import source_refresh  # noqa: E402

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


def _write_fixture(tmp, sources, mod, with_registry=True):
    os.makedirs(os.path.join(tmp, "assets", "modules"))
    mp = os.path.join(tmp, "assets", "modules", mod["id"] + ".json")
    open(mp, "w", encoding="utf-8").write(json.dumps(mod, ensure_ascii=False))
    h = hashlib.sha256(open(mp, "rb").read()).hexdigest()
    open(os.path.join(tmp, "assets", "module_registry.json"), "w", encoding="utf-8").write(
        json.dumps({"schema": "mentor-registry/1", "modules": [
            {"id": mod["id"], "file": "assets/modules/%s.json" % mod["id"],
             "version": mod["version"], "hash": "sha256:" + h, "status": "stable"}]},
            ensure_ascii=False))
    if with_registry:
        open(os.path.join(tmp, "assets", "source_registry.json"), "w", encoding="utf-8").write(
            json.dumps({"schema": "mentor-source-registry/1", "sources": sources}, ensure_ascii=False))
    return tmp


def _run_case(sources, mod, strict=False, with_registry=True):
    with tempfile.TemporaryDirectory(prefix="src_case_") as tmp:
        _write_fixture(tmp, sources, mod, with_registry)
        return source_audit.audit(tmp, today=TODAY, strict_legacy=strict)


def _refresh_missing_registry_case():
    with tempfile.TemporaryDirectory(prefix="src_noreg_") as tmp:
        old = sys.argv
        sys.argv = ["source_refresh.py", "--root", tmp, "--offline"]
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                rc = source_refresh.main()
        finally:
            sys.argv = old
        line = out.getvalue().strip()
        payload = json.loads(line.split(" ", 1)[1]) if line.startswith("SOURCE_REFRESH ") else {}
        return rc == 0 and payload.get("status") == "skipped"


def _doi_without_url_case():
    old = source_refresh._fetch
    calls = []
    source_refresh._fetch = lambda url, domains, timeout: (
        calls.append(url) or {"http_status": 200, "final_url": url})
    try:
        p = source_refresh._proposal(
            {"id": "PAPER-1", "doi": "10.1234/example", "check_url": None},
            ["api.crossref.org"], 5, False)
    finally:
        source_refresh._fetch = old
    return p.get("action") == "crossref_checked" and any("api.crossref.org" in u for u in calls)


def _preflight_source_error_case():
    with tempfile.TemporaryDirectory(prefix="src_pf_") as tmp:
        _write_fixture(tmp, [_source("BOOK-1")], _module("BOOK-1"))
        old = source_audit.audit

        def boom(*args, **kwargs):
            raise RuntimeError("simulated source audit crash")

        source_audit.audit = boom
        try:
            r = preflight.evaluate(tmp, "test")
        finally:
            source_audit.audit = old
        return r.get("decision") == "ask"


def _redirect_blocked_case():
    try:
        source_refresh._SafeRedirect(["wiley.com"]).redirect_request(
            None, None, 302, "Found", {}, "https://evil.example/")
        return False
    except urllib.error.URLError:
        return True


def _lint_source_id_only_case():
    mod = _module("BOOK-1")
    mod["data"][0].pop("source", None)
    with tempfile.TemporaryDirectory(prefix="src_lint_") as tmp:
        _write_fixture(tmp, [_source("BOOK-1")], mod)
        r = module_lint.run(tmp)
        return r["status"] in ("pass", "warn")


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
    r = _run_case([], _module("BOOK-1"), with_registry=False)
    cases.append(("missing_registry_fail", r["status"] == "fail"))
    cases.append(("refresh_missing_registry_skip", _refresh_missing_registry_case()))
    cases.append(("doi_without_url_crossref", _doi_without_url_case()))
    cases.append(("redirect_blocked", _redirect_blocked_case()))
    cases.append(("lint_source_id_only", _lint_source_id_only_case()))
    cases.append(("preflight_source_error_ask", _preflight_source_error_case()))
    passed = sum(1 for _, ok in cases if ok)
    return {"status": "pass" if passed == len(cases) else "fail",
            "passed": passed, "total": len(cases),
            "cases": [{"case": n, "pass": ok} for n, ok in cases]}


if __name__ == "__main__":
    result = run()
    print("SOURCE_SELFTEST " + json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result["status"] == "pass" else 1)
