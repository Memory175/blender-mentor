# -*- coding: utf-8 -*-
"""load_router.py — 按任务描述生成"本次该加载哪些人设文件"的清单（纯标准库）。

用法：
    python scripts/load_router.py --task "人体走路循环动画，需要验收脚本"
    python scripts/load_router.py --task "教学备课：M3 动画" --budget 30000
    python scripts/load_router.py --list

输出最后一行：LOAD_PLAN {json}；exit 0=ok，2=参数/文件错误。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PLAN_PATH = os.path.join(ROOT, "assets", "load_plan.json")


def _load_plan():
    with open(PLAN_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def _tokens(path):
    full = os.path.join(ROOT, path)
    if not os.path.isfile(full):
        return 0
    return max(1, round(os.path.getsize(full) / 3.0))


def _matches(task, triggers, excludes=None):
    low = task.lower()
    if any(x.lower() in low for x in (excludes or [])):
        return []
    return [t for t in triggers if t.lower() in low]


def _entry(item, kind):
    return {"file": item["file"], "kind": kind, "reason": item.get("reason", ""),
            "triggers_hit": item.get("hits", []),
            "tokens_est": _tokens(item["file"])}


def route(task, budget=None, plan=None):
    plan = plan or _load_plan()
    selected, dropped = [], []
    for item in plan.get("always", []):
        selected.append(_entry(item, "always"))
    for item in plan.get("on_demand", []):
        hits = _matches(task, item.get("triggers", []), item.get("exclude"))
        if hits:
            entry = _entry(item, "on_demand")
            entry["triggers_hit"] = hits
            selected.append(entry)
    modules = []
    for item in plan.get("modules", []):
        hits = _matches(task, item.get("triggers", []), item.get("exclude"))
        if hits:
            entry = _entry(item, "module")
            entry["id"] = item["id"]
            entry["triggers_hit"] = hits
            modules.append(entry)
    modules.sort(key=lambda e: e["triggers_hit"][0])
    selected.extend(modules[:2])
    for extra in modules[2:]:
        dropped.append({"file": extra["file"], "kind": "module",
                        "reason": "max 2 modules per task"})

    def total():
        return sum(e["tokens_est"] for e in selected)

    if budget:
        # policy: curriculum -> toolbox -> modules (core never dropped)
        order = ["references/curriculum.md",
                 "references/toolbox_text.md"]
        for path in order:
            if total() <= budget:
                break
            for entry in list(selected):
                if entry["file"] == path:
                    selected.remove(entry)
                    dropped.append({"file": path, "kind": entry["kind"],
                                    "reason": "budget %d" % budget})
                    break
        if total() > budget:
            for entry in list(selected):
                if entry["kind"] == "module":
                    selected.remove(entry)
                    dropped.append({"file": entry["file"], "kind": "module",
                                    "reason": "budget %d" % budget})
    warnings = []
    for d in dropped:
        if d["kind"] == "module":
            warnings.append("module dropped: " + d["file"])
    result = {
        "task": task,
        "files": selected,
        "dropped": dropped,
        "tokens_est": total(),
        "budget": budget,
        "over_budget": bool(budget and total() > budget),
        "warnings": warnings,
        "policy": plan.get("policy", []),
        "tools_hint": plan.get("tools", []),
    }
    return result


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    task, budget, list_only = None, None, False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--task" and i + 1 < len(argv):
            task = argv[i + 1]
            i += 2
        elif a == "--budget" and i + 1 < len(argv):
            budget = int(float(argv[i + 1]))
            i += 2
        elif a == "--list":
            list_only = True
            i += 1
        else:
            i += 1
    try:
        plan = _load_plan()
    except (OSError, ValueError) as exc:
        print("LOAD_PLAN " + json.dumps(
            {"status": "fail", "error": type(exc).__name__ + ": " + str(exc)},
            ensure_ascii=False))
        return 2
    if list_only:
        catalog = {
            "always": [i["file"] for i in plan.get("always", [])],
            "on_demand": [i["file"] for i in plan.get("on_demand", [])],
            "modules": [{"id": m["id"], "file": m["file"],
                         "triggers": m.get("triggers", []),
                         "exclude": m.get("exclude", [])}
                        for m in plan.get("modules", [])],
            "tools": plan.get("tools", []),
        }
        print("LOAD_PLAN " + json.dumps(
            {"status": "ok", "catalog": catalog}, ensure_ascii=False))
        return 0
    if not task:
        print("LOAD_PLAN " + json.dumps(
            {"status": "fail", "error": "usage: load_router.py --task TEXT [--budget N]"},
            ensure_ascii=False))
        return 2
    result = route(task, budget, plan)
    print("LOAD_PLAN " + json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
