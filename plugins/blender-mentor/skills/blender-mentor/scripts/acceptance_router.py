#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验收 Profile 路由：按任务/模块选择专用验收清单。

用法：
    python scripts/acceptance_router.py --task "建筑内饰验收"
    python scripts/acceptance_router.py --task "产品验收" --profile PROD-HARD
    python scripts/acceptance_router.py --task "室内验收" --preflight .preflight.json
    python scripts/acceptance_router.py --task "室内验收" --json .acceptance.json
    python scripts/acceptance_router.py --selftest

原则：
    - profile 只选检查项，不提供阈值；
    - 显式 --profile 优先；
    - preflight 选中的模块映射优先于关键词；
    - 关键词平局时返回 ask，不猜；
    - 未命中任何 profile 时使用 GENERIC。
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "assets", "acceptance_profiles.json")


def load_data():
    with open(DATA, encoding="utf-8") as fh:
        return json.load(fh)


def norm(s):
    return s.casefold().strip()


def score(task, triggers):
    t = norm(task)
    hits = [x for x in triggers if norm(x) in t]
    # longer trigger is slightly more specific
    return (len(hits), sum(len(x) for x in hits), hits)


def all_primary(data):
    return list(data.get("profiles", [])) + [data.get("generic", {})]


def find_primary(data, pid):
    for p in all_primary(data):
        if p.get("id") == pid:
            return p
    return None


def find_overlay(data, oid):
    for p in data.get("overlay_profiles", []):
        if p.get("id") == oid:
            return p
    return None


def module_primary(data, selected):
    mapping = data.get("module_profile_map", {})
    ids = []
    for entry in selected or []:
        mid = entry.get("id") if isinstance(entry, dict) else entry
        pid = mapping.get(mid)
        if pid and pid not in ids:
            ids.append(pid)
    if len(ids) == 1:
        return find_primary(data, ids[0]), ids
    return None, ids


def keyword_primary(data, task):
    scored = []
    for p in data.get("profiles", []):
        n, total, hits = score(task, p.get("triggers", []))
        if n:
            scored.append((n, total, p.get("id"), p.get("name"), hits, p))
    if not scored:
        return None, [], []
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    top = (scored[0][0], scored[0][1])
    ties = [x for x in scored if (x[0], x[1]) == top]
    return scored[0][5], ties, scored


def select_overlays(data, task, primary_id, explicit):
    if explicit is not None:
        out = []
        for oid in [x.strip() for x in explicit.split(",") if x.strip()]:
            p = find_overlay(data, oid)
            if p:
                out.append(p)
        return out
    out = []
    for p in data.get("overlay_profiles", []):
        if p.get("id") == primary_id:
            continue
        n, _, _ = score(task, p.get("triggers", []))
        if n:
            out.append(p)
    return out[:2]


def build(data, task, explicit=None, preflight=None, no_overlays=False):
    warnings = []
    source = ""
    primary = None
    candidates = []

    if explicit:
        primary = find_primary(data, explicit)
        if not primary:
            return {"status": "error", "decision": "block",
                    "task": task, "error": "unknown profile: %s" % explicit,
                    "known": [p.get("id") for p in all_primary(data)]}
        source = "explicit"
        if primary.get("id") != "GENERIC":
            n, _, _ = score(task, primary.get("triggers", []))
            if not n:
                warnings.append("explicit profile overrides task keywords")
    elif preflight:
        with open(preflight, encoding="utf-8") as fh:
            pf = json.load(fh)
        if pf.get("decision") in ("ask", "block"):
            return {"status": pf.get("decision"), "decision": pf.get("decision"),
                    "task": task, "reason": "preflight not ready",
                    "questions": pf.get("questions", []), "preflight": pf}
        selected = pf.get("selected") or []
        mod_primary, mapped = module_primary(data, selected)
        if len(mapped) > 1:
            return {"status": "ask", "decision": "ask", "task": task,
                    "reason": "multiple modules map to different profiles",
                    "candidates": mapped, "preflight": pf}
        if mod_primary:
            primary = mod_primary
            source = "preflight"
        else:
            primary, ties, scored = keyword_primary(data, task)
            if ties and len(ties) > 1:
                return {"status": "ask", "decision": "ask", "task": task,
                        "reason": "keyword tie",
                        "candidates": [{"id": x[2], "name": x[3], "hits": x[4]} for x in ties]}
            source = "keyword"
    else:
        primary, ties, scored = keyword_primary(data, task)
        if ties and len(ties) > 1:
            return {"status": "ask", "decision": "ask", "task": task,
                    "reason": "keyword tie",
                    "candidates": [{"id": x[2], "name": x[3], "hits": x[4]} for x in ties]}
        source = "keyword"

    if not primary:
        primary = data.get("generic")
        source = "generic"
        warnings.append("no specific profile matched; use GENERIC and do not claim domain-specific acceptance")

    overlays = [] if no_overlays else select_overlays(data, task, primary.get("id"), None)
    checks = []
    seen = set()
    for p in [primary] + overlays:
        for c in p.get("checks", []):
            if c["id"] not in seen:
                seen.add(c["id"])
                checks.append(c)
    coverage = []
    for c in checks:
        cov = c.get("coverage")
        if cov and cov not in coverage:
            coverage.append(cov)

    return {
        "status": "ok",
        "decision": "proceed",
        "task": task,
        "source": source,
        "primary": {"id": primary.get("id"), "name": primary.get("name")},
        "overlays": [{"id": p.get("id"), "name": p.get("name")} for p in overlays],
        "checks": checks,
        "coverage_required": coverage,
        "not_applicable": primary.get("not_applicable", []),
        "warnings": warnings,
        "policy": data.get("policy")
    }


def selftest():
    data = load_data()
    cases = [
        ("建筑室内验收", None, None, "INT-INTERIOR", "proceed"),
        ("建筑内饰验收", None, None, "INT-INTERIOR", "proceed"),
        ("工业产品壁厚和拔模验收", None, None, "PROD-HARD", "proceed"),
        ("角色走路动画验收", None, None, "CHAR-RIG", "proceed"),
        ("实时游戏资产导出验收", None, None, "REALTIME-ASSET", "proceed"),
        ("室内和产品一起验收", None, None, "__ask__", "ask"),
        ("帮我看看这个", None, None, "GENERIC", "proceed"),
        ("建筑室内最终出图", None, None, "INT-INTERIOR", "proceed"),
        ("室内验收", "PROD-HARD", None, "PROD-HARD", "proceed"),
    ]
    ok = 0
    for task, explicit, preflight, want_primary, want_decision in cases:
        r = build(data, task, explicit=explicit, preflight=preflight)
        decision = r.get("decision")
        got = r.get("primary", {}).get("id") if decision == "proceed" else "__ask__"
        good = (decision == want_decision and got == want_primary)
        if good:
            ok += 1
        print(("PASS" if good else "FAIL"), task, "->", got, decision,
              "want", want_primary, want_decision)
        if task == "建筑室内最终出图" and r.get("decision") == "proceed":
            ov = [x["id"] for x in r.get("overlays", [])]
            good2 = "LOOKDEV" in ov
            print("  OVERLAY_LOOKDEV", "PASS" if good2 else "FAIL", ov)
            if good2:
                ok += 1
    print("SELFTEST %d/%d" % (ok, len(cases) + 1))
    return 0 if ok == len(cases) + 1 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default=None)
    ap.add_argument("--profile", default=None)
    ap.add_argument("--preflight", default=None)
    ap.add_argument("--json", default=None)
    ap.add_argument("--no-overlays", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    data = load_data()
    if args.list:
        for p in data.get("profiles", []):
            print(p["id"], "-", p["name"])
        for p in data.get("overlay_profiles", []):
            print(p["id"], "-", p["name"], "(overlay)")
        return 0
    if args.selftest:
        return selftest()
    if not args.task:
        ap.error("--task is required unless --list/--selftest")

    result = build(data, args.task, explicit=args.profile,
                   preflight=args.preflight, no_overlays=args.no_overlays)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json:
        with open(args.json, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(payload + "\n")
    print("ACCEPTANCE " + payload)
    return 2 if result.get("decision") in ("ask", "block") else 0


if __name__ == "__main__":
    sys.exit(main())
