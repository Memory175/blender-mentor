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
    gap_hints = _load_gap_hints(root)
    selected = mg.select_modules(modules, task, max_modules=max_modules)
    sel_ids = {m.get("id") for m in selected}
    style_info = mg.detect_style_layout(root, task)
    hint_hits = []
    for h in gap_hints:
        hits = [kw for kw in h.get("keywords", []) if mg.keyword_hit(kw, task)]
        if hits:
            hint_hits.append({"id": h.get("id"), "name": h.get("name"),
                              "hits": hits, "why": h.get("why", ""),
                              "force": bool(h.get("force", False))})
    # 强制缺口优先：内饰/室内建模必须独立模块，不能被普通建模或 ENG/BIO/ESD 放行
    hint_hits.sort(key=lambda x: (1 if x.get("force") else 0, len(x["hits"])), reverse=True)
    force_hits = [h for h in hint_hits if h.get("force") and h["id"] not in sel_ids]
    interior_selected = [m for m in selected
                         if "interior" in (m.get("domain") or [])
                         or str(m.get("id", "")).startswith("INT-")]
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
    style_mismatch = []
    layout_mismatch = []
    if force_hits:
        decision = "block"
        top = force_hits[0]
        questions.append("任务命中未覆盖领域：%s。必须新增独立模块 %s（%s）；"
                         "内饰/室内建模不能借用 ENG/BIO/ESD 或普通建模。"
                         "运行 module_gap.py 获取可复制 Prompt。" % (
                             ", ".join(top["hits"]), top["id"], top["name"]))
        if not style_info["styles"]:
            questions.append("请先指定建筑风格（现代/极简/北欧/日式/中式/工业/美式/法式/奶油/轻奢等）；新模块必须是带 styles 的 INT-* 模块。")
        if not style_info["layouts"]:
            questions.append("请先指定空间类型/布局（公寓/别墅/单间/办公/商业/餐饮/酒店等）；新模块必须是带 layouts 的 INT-* 模块。")
    elif not selected:
        core_hits = [kw for kw in core_triggers if mg.keyword_hit(kw, task)]
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
    elif interior_selected:
        if not style_info["styles"]:
            decision = "ask"
            questions.append("内饰/室内建模需要先指定建筑风格；请补充风格，或说明按哪个已有风格模块执行。")
        if not style_info["layouts"]:
            decision = "ask"
            questions.append("内饰/室内建模需要先指定空间类型/布局；请补充公寓/别墅/单间/办公/商业/餐饮/酒店等。")
        if style_info["styles"] and style_info["layouts"]:
            for m in interior_selected:
                declared_styles = list(m.get("styles") or [])
                declared_layouts = list(m.get("layouts") or [])
                if not declared_styles:
                    decision = "ask"
                    questions.append("模块 %s 没有声明 styles，无法判断是否覆盖当前建筑风格；请补充模块或新建 INT 模块。" % m.get("id"))
                if not declared_layouts:
                    decision = "ask"
                    questions.append("模块 %s 没有声明 layouts，无法判断是否覆盖当前空间布局；请补充模块或新建 INT 模块。" % m.get("id"))
                for item in style_info["styles"]:
                    if item["id"] not in declared_styles:
                        style_mismatch.append({"module": m.get("id"), "requested": item["id"], "name": item["name"]})
                for item in style_info["layouts"]:
                    if item["id"] not in declared_layouts:
                        layout_mismatch.append({"module": m.get("id"), "requested": item["id"], "name": item["name"]})
            if style_mismatch:
                decision = "ask"
                questions.append("当前建筑风格不在已有内饰模块覆盖范围：%s。需要扩展模块 %s 或新建 INT 模块；不能静默按旧风格执行。" % (
                    ", ".join(x["name"] for x in style_mismatch), ", ".join(sorted({x["module"] for x in style_mismatch}))))
            if layout_mismatch:
                decision = "ask"
                questions.append("当前空间布局不在已有内饰模块覆盖范围：%s。需要扩展模块或新建 INT 模块，并单独考虑该布局的动线/尺度。" % (
                    ", ".join(x["name"] for x in layout_mismatch)))
    elif relevant:
        decision = "ask"
        questions.append("检测到模块冲突。请选择：修改哪个模块 / 新增 override 模块 / 以哪个为准 / 放弃该项检查。")
    elif source_result and source_result.get("status") in ("fail", "error"):
        decision = "ask"
        if source_result.get("status") == "error":
            questions.append("来源审计执行失败（注册表损坏/读取异常）。为安全起见先停止，请修复来源数据后重试。")
        else:
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
        "forced_gap_hints": [h["id"] for h in force_hits],
        "styles": style_info["styles"],
        "layouts": style_info["layouts"],
        "style_mismatch": style_mismatch,
        "layout_mismatch": layout_mismatch,
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
