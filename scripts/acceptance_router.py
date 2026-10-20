#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验收 Profile 路由：按任务/模块/项目上下文选择专用验收清单。

用法：
    python scripts/acceptance_router.py --task "建筑内饰验收" \
        --context assets/acceptance_context.example.json
    python scripts/acceptance_router.py --task "产品验收" --profile PROD-HARD \
        --context project_context.json
    python scripts/acceptance_router.py --task "室内验收" --preflight .preflight.json
    python scripts/acceptance_router.py --selftest

原则：
    - profile 只选检查项，不提供阈值；
    - check.applies_if 决定适用性，不适用项写明 reason；
    - 必需检查缺上下文 -> ask，不默认通过；
    - optional 检查不计入 coverage_required；
    - 显式 --profile 优先；preflight 模块映射优先于关键词；
    - 关键词平局返回 ask；无命中使用 GENERIC。
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


def load_context(path):
    if not path:
        return {}
    with open(path, encoding="utf-8") as fh:
        ctx = json.load(fh)
    if not isinstance(ctx, dict):
        raise ValueError("context must be a JSON object")
    return ctx


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


def get_path(context, path):
    cur = context
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def eval_condition(condition, context):
    """Return (True/False/None, path). None = context missing."""
    raw = condition
    negate = raw.startswith("!")
    if negate:
        raw = raw[1:]
    if "=" in raw:
        path, want = raw.split("=", 1)
        val = get_path(context, path)
        if val is None:
            return None, path
        ok = str(val) == want
    else:
        path = raw
        val = get_path(context, path)
        if val is None:
            return None, path
        ok = bool(val)
    if negate:
        ok = not ok
    return ok, path


def resolve_check(check, context):
    """Resolve one check against context.

    mode:
      required  - applicable and coverage-required
      optional  - applicable but not coverage-required
      na        - context explicitly says not applicable
      skip      - optional check whose context is missing
      ask       - required check whose context is missing
      include   - explicit missing_context=include
    """
    conditions = check.get("applies_if") or []
    missing = []
    for condition in conditions:
        ok, path = eval_condition(condition, context)
        if ok is None:
            missing.append(path)
        elif not ok:
            return {"mode": "na", "reason": "%s is false" % path}
    if missing:
        if check.get("optional") or check.get("missing_context") == "skip":
            return {"mode": "skip", "reason": "optional; missing context: " + ", ".join(missing)}
        if check.get("missing_context") == "include":
            return {"mode": "optional" if check.get("optional") else "required"}
        return {"mode": "ask", "missing": missing}
    return {"mode": "optional" if check.get("optional") else "required"}


def select_overlays(data, task, primary_id):
    out = []
    for p in data.get("overlay_profiles", []):
        if p.get("id") == primary_id:
            continue
        n, _, _ = score(task, p.get("triggers", []))
        if n:
            out.append(p)
    return out[:2]


def add_check(check, context, checks, not_applicable, na_details, skipped, missing_context,
              coverage_required, coverage_optional):
    resolved = resolve_check(check, context)
    mode = resolved["mode"]
    if mode == "na":
        not_applicable.append(check["id"])
        na_details.append({"check": check["id"], "reason": resolved["reason"]})
        return
    if mode == "skip":
        skipped.append({"check": check["id"], "reason": resolved["reason"]})
        return
    if mode == "ask":
        missing_context.append({"check": check["id"], "missing": resolved["missing"]})
        return
    item = dict(check)
    item["status"] = mode
    checks.append(item)
    coverage = check.get("coverage")
    if coverage:
        target = coverage_optional if mode == "optional" else coverage_required
        if coverage not in target:
            target.append(coverage)


def build(data, task, explicit=None, preflight=None, no_overlays=False, context=None):
    context = context or {}
    warnings = []
    source = ""
    primary = None

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
        try:
            with open(preflight, encoding="utf-8") as fh:
                pf = json.load(fh)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return {"status": "error", "decision": "block", "task": task,
                    "error": "cannot load --preflight: %s" % exc}
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

    overlays = [] if no_overlays else select_overlays(data, task, primary.get("id"))
    checks = []
    seen = set()
    not_applicable = []
    na_details = []
    skipped = []
    missing_context = []
    coverage_required = []
    coverage_optional = []
    for profile in [primary] + overlays:
        for check in profile.get("checks", []):
            if check["id"] in seen:
                continue
            seen.add(check["id"])
            add_check(check, context, checks, not_applicable, na_details, skipped,
                      missing_context, coverage_required, coverage_optional)

    external_tools = []
    for check in checks:
        tool = check.get("tool")
        scope = check.get("tool_scope")
        if scope == "project":
            external_tools.append({"check": check["id"], "tool": tool, "scope": "project"})
        elif tool == "manual" or scope == "manual":
            external_tools.append({"check": check["id"], "tool": tool, "scope": "manual"})
        elif tool and not os.path.isfile(os.path.join(ROOT, "scripts", tool)):
            external_tools.append({"check": check["id"], "tool": tool, "scope": "missing"})

    decision = "ask" if missing_context else "proceed"
    return {
        "status": "ok",
        "decision": decision,
        "task": task,
        "source": source,
        "primary": {"id": primary.get("id"), "name": primary.get("name")},
        "overlays": [{"id": p.get("id"), "name": p.get("name")} for p in overlays],
        "checks": checks,
        "coverage_required": coverage_required,
        "coverage_optional": coverage_optional,
        "not_applicable": not_applicable,
        "not_applicable_details": na_details,
        "skipped": skipped,
        "missing_context": missing_context,
        "external_tools": external_tools,
        "warnings": warnings,
        "policy": data.get("policy")
    }


def selftest():
    data = load_data()
    full_int = {"interior": {"bath": True, "kitchen": True, "fixed": True,
                              "movable": True, "chairs": 6, "cameras": 10}}
    prod_ctx = {"manufacturing": {"injection": True, "hollow": True}}
    char_prop = {"character": {"human": False}}
    char_human = {"character": {"human": True}}
    cases = [
        ("建筑室内验收", None, None, full_int, "INT-INTERIOR", "proceed"),
        ("建筑内饰验收", None, None, full_int, "INT-INTERIOR", "proceed"),
        ("工业产品壁厚和拔模验收", None, None, prod_ctx, "PROD-HARD", "proceed"),
        ("角色走路动画验收", None, None, char_prop, "CHAR-RIG", "proceed"),
        ("实时游戏资产导出验收", None, None, None, "REALTIME-ASSET", "proceed"),
        ("室内和产品一起验收", None, None, None, "__ask__", "ask"),
        ("帮我看看这个", None, None, None, "GENERIC", "proceed"),
        ("建筑室内最终出图", None, None, full_int, "INT-INTERIOR", "proceed"),
        ("室内验收", "PROD-HARD", None, prod_ctx, "PROD-HARD", "proceed"),
        ("建筑室内验收", None, None, None, "INT-INTERIOR", "ask"),
    ]
    ok = 0
    for task, explicit, preflight, ctx, want_primary, want_decision in cases:
        r = build(data, task, explicit=explicit, preflight=preflight, context=ctx)
        got = r.get("primary", {}).get("id", "__ask__") if r.get("decision") != "ask" or r.get("primary") else "__ask__"
        good = (r.get("decision") == want_decision and got == want_primary)
        if good:
            ok += 1
        print(("PASS" if good else "FAIL"), task, "->", got, r.get("decision"),
              "want", want_primary, want_decision)
        if task == "建筑室内最终出图" and r.get("decision") == "proceed":
            ov = [x["id"] for x in r.get("overlays", [])]
            good2 = "LOOKDEV" in ov
            print("  OVERLAY_LOOKDEV", "PASS" if good2 else "FAIL", ov)
            if good2:
                ok += 1
    # conditional checks: bath=false removes bath_door_clear, human=true adds biomech
    ctx_no_bath = {"interior": {"bath": False, "kitchen": False, "fixed": True,
                                "movable": True, "chairs": 0, "cameras": 2}}
    r = build(data, "室内验收", context=ctx_no_bath)
    ids = [c["id"] for c in r.get("checks", [])]
    checks = [
        ("NO_BATH", "bath_door_clear" not in ids and "kitchen_aisle" not in ids),
        ("BATH_NA", "bath_door_clear" in [x["check"] for x in r.get("not_applicable_details", [])]),
    ]
    r2 = build(data, "角色走路动画验收", context=char_human)
    checks.append(("HUMAN_BIOMECH", "biomech" in [c["id"] for c in r2.get("checks", [])]))
    ext = {x.get("tool") for x in r.get("external_tools", [])}
    checks.append(("PROJECT_TOOL_DECLARED", "layout_check.py" in ext))
    for name, good in checks:
        print(("PASS" if good else "FAIL"), name)
        if good:
            ok += 1
    total = len(cases) + 1 + len(checks)
    print("SELFTEST %d/%d" % (ok, total))
    return 0 if ok == total else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default=None)
    ap.add_argument("--profile", default=None)
    ap.add_argument("--preflight", default=None)
    ap.add_argument("--context", default=None)
    ap.add_argument("--json", default=None)
    ap.add_argument("--no-overlays", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    data = load_data()
    if args.list:
        for p in data.get("profiles", []):
            print(p["id"], "-", p["name"])
        generic = data.get("generic", {})
        if generic:
            print(generic.get("id"), "-", generic.get("name"))
        for p in data.get("overlay_profiles", []):
            print(p["id"], "-", p["name"], "(overlay)")
        return 0
    if args.selftest:
        return selftest()
    if not args.task:
        ap.error("--task is required unless --list/--selftest")

    try:
        context = load_context(args.context)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        ap.error("cannot load --context: %s" % exc)
    result = build(data, args.task, explicit=args.profile,
                   preflight=args.preflight, no_overlays=args.no_overlays,
                   context=context)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json:
        with open(args.json, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(payload + "\n")
    print("ACCEPTANCE " + payload)
    return 2 if result.get("decision") in ("ask", "block") else 0


if __name__ == "__main__":
    sys.exit(main())
