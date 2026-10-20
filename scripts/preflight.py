# -*- coding: utf-8 -*-
"""preflight.py — 按需加载前的强制预审闸门。

用法：
    python scripts/preflight.py --task "用户原话" [--json .preflight.json]
    python scripts/preflight.py --task "..." --modules-dir <dir>     # 测试用

决策：
    proceed : 找到相关模块、无冲突、数据覆盖完整
    ask     : 有冲突，或缺数据但可补 → 必须停下来问用户
    block   : 没有任何相关模块，或模块策略要求硬停 → 不得编造

退出码：0=proceed，2=ask/block，1=内部错误。
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import module_governance as mg  # noqa: E402
try:
    import source_audit as _source_audit  # noqa: E402
except Exception:  # noqa: BLE001
    _source_audit = None


def _load_gap_hints(root):
    path = os.path.join(root, "assets", "module_gap_hints.json")
    if not os.path.isfile(path):
        return []
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh).get("hints", [])
    except Exception:  # noqa: BLE001
        return []


def evaluate(root, task, modules_dir=None, registry_path=None, max_modules=2):
    registry, reg_problems = mg.load_registry(root, registry_path) if not modules_dir else (None, [])
    modules, problems = mg.load_modules(root, modules_dir, registry)
    all_problems = list(reg_problems) + list(problems)
    core_triggers = (registry or {}).get("core_triggers", [])
    gap_hints = _load_gap_hints(root) if not modules_dir else []
    selected = mg.select_modules(modules, task, max_modules=max_modules)
    sel_ids = {m.get("id") for m in selected}
    source_result = None
    if selected and _source_audit is not None:
        try:
            source_result = _source_audit.audit(root, modules_dir=modules_dir, only_ids=sel_ids)
        except Exception as exc:  # noqa: BLE001
            source_result = {"status": "error", "problems": [str(exc)], "warnings": [], "legacy": []}
    matched, required, available = mg.coverage_for(selected, task)
    missing = sorted(k for k in required if k not in available)
    unmapped = bool(selected) and not matched
    conflicts = mg.scan_conflicts(modules, all_problems)
    # 只把与本次选中模块相关的冲突算进来；注册表/全局问题始终算
    relevant = []
    for c in conflicts:
        detail = str(c.get("detail", ""))
        if c.get("type") in ("registry", "duplicate_id"):
            relevant.append(c)
        elif any(mid and mid in detail for mid in sel_ids):
            relevant.append(c)
        elif c.get("type") == "data_value":
            entries = c.get("entries", [])
            if any(e.get("module") in sel_ids for e in entries):
                relevant.append(c)
        elif c.get("type") == "conflict_asymmetry" and any(mid and mid in detail for mid in sel_ids):
            relevant.append(c)
    decision = "proceed"
    questions = []
    core_hits = []
    hint_hits = []
    if not selected:
        core_hits = [kw for kw in core_triggers if mg.keyword_hit(kw, task)]
        for h in gap_hints:
            hits = [kw for kw in h.get("keywords", []) if mg.keyword_hit(kw, task)]
            if hits:
                hint_hits.append({"id": h.get("id"), "name": h.get("name"),
                                  "hits": hits, "why": h.get("why", "")})
        hint_hits.sort(key=lambda x: len(x["hits"]), reverse=True)
        if hint_hits:
            decision = "block"
            top = hint_hits[0]
            questions.append("任务命中未覆盖领域：%s。建议先新增模块 %s（%s），再执行；"
                             "运行 module_gap.py 获取可复制写作 Prompt。" % (
                                 ", ".join(top["hits"]), top["id"], top["name"]))
        elif core_hits:
            decision = "proceed_core"
        else:
            decision = "block"
            questions.append("模块包没有命中任何相关模块，且任务不在核心教学覆盖范围。我不会编造数据；请选择：补充参考数据、允许显式假设、或缩小任务。")
    elif relevant:
        decision = "ask"
        questions.append("检测到模块冲突。请选择：修改哪个模块 / 新增 override 模块 / 以哪个为准 / 放弃该项检查。")
    elif source_result and source_result.get("status") == "fail":
        decision = "ask"
        questions.append("模块来源审计失败（withdrawn/superseded 或法规缺 jurisdiction）。请先更新来源注册表与模块数据，再执行。")
    elif missing or unmapped:
        policies = [m.get("unknown_policy", "ask") for m in selected]
        decision = "block" if "block" in policies else "ask"
        if unmapped:
            questions.append("模块命中了，但没有声明对「当前任务能力」的覆盖；我不会补造数据。请补充覆盖项或新增模块。")
        if missing:
            questions.append("缺少参考数据键：%s。请提供数据、新增参考模块，或明确允许显式假设。" % ", ".join(missing))
    result = {
        "decision": decision,
        "task": task,
        "selected": [{"id": m.get("id"), "version": m.get("version"),
                      "status": m.get("status"), "unknown_policy": m.get("unknown_policy")}
                     for m in selected],
        "matched_coverage": matched,
        "missing": missing,
        "coverage_unmapped": unmapped,
        "conflicts": relevant,
        "questions": questions,
        "core_triggers_hit": core_hits,
        "gap_hints": hint_hits,
        "source_audit": source_result,
        "data": {k: available[k] for k in sorted(required) if k in available},
        "modules_considered": len(modules),
    }
    return result


def main():
    ap = argparse.ArgumentParser(description="Blender Mentor module preflight gate")
    ap.add_argument("--root", default=os.path.dirname(HERE))
    ap.add_argument("--task", required=True)
    ap.add_argument("--json", default=None)
    ap.add_argument("--modules-dir", default=None)
    ap.add_argument("--registry", default=None)
    ap.add_argument("--max-modules", type=int, default=2)
    args = ap.parse_args()
    try:
        result = evaluate(os.path.abspath(args.root), args.task,
                          modules_dir=args.modules_dir, registry_path=args.registry,
                          max_modules=args.max_modules)
    except Exception as exc:  # noqa: BLE001
        print("PREFLIGHT " + json.dumps({"decision": "error", "error": str(exc)}, ensure_ascii=False))
        return 1
    if args.json:
        try:
            with open(args.json, "w", encoding="utf-8") as fh:
                json.dump(result, fh, ensure_ascii=False, indent=2)
        except OSError as exc:
            result["json_error"] = str(exc)
            print("PREFLIGHT_JSON_ERROR " + str(exc), file=sys.stderr)
    print("PREFLIGHT " + json.dumps(result, ensure_ascii=False))
    return 0 if result["decision"] in ("proceed", "proceed_core") else 2


if __name__ == "__main__":
    sys.exit(main())
