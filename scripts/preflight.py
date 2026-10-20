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


def evaluate(root, task, modules_dir=None, registry_path=None, max_modules=2):
    registry, reg_problems = mg.load_registry(root, registry_path) if not modules_dir else (None, [])
    modules, problems = mg.load_modules(root, modules_dir, registry)
    all_problems = list(reg_problems) + list(problems)
    selected = mg.select_modules(modules, task, max_modules=max_modules)
    matched, required, available = mg.coverage_for(selected, task)
    missing = sorted(k for k in required if k not in available)
    unmapped = bool(selected) and not matched
    conflicts = mg.scan_conflicts(modules, all_problems)
    # 只把与本次选中模块相关的冲突算进来；注册表/全局问题始终算
    sel_ids = {m.get("id") for m in selected}
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
    if not selected:
        decision = "block"
        questions.append("模块包没有命中任何相关模块。我不会编造数据；请选择：补充参考数据、允许显式假设、或缩小任务。")
    elif relevant:
        decision = "ask"
        questions.append("检测到模块冲突。请选择：修改哪个模块 / 新增 override 模块 / 以哪个为准 / 放弃该项检查。")
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
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=2)
    print("PREFLIGHT " + json.dumps(result, ensure_ascii=False))
    return 0 if result["decision"] == "proceed" else 2


if __name__ == "__main__":
    sys.exit(main())
