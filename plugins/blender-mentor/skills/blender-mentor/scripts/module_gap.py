# -*- coding: utf-8 -*-
"""module_gap.py — 一句话任务的“缺模块”应答器。

当 preflight 返回 block/ask 且没有可执行模块时，输出：
1. 缺哪个模块（ID/name/why）
2. 需要补哪些知识
3. 可直接复制给任意 AI 的写作 Prompt
4. 并入模块包的步骤

用法：
    python scripts/module_gap.py --task "我想建模一个房子"
    python scripts/module_gap.py --task "..." --prompt-only
    python scripts/module_gap.py --task "..." --json .gap.json
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import preflight  # noqa: E402
import module_governance as mg  # noqa: E402


def load_hints(root):
    path = os.path.join(root, "assets", "module_gap_hints.json")
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return json.load(fh).get("hints", [])


def pick_hint(root, task):
    best, best_hits, best_score = None, [], (-1, -1)
    for h in load_hints(root):
        hits = [kw for kw in h.get("keywords", []) if mg.keyword_hit(kw, task)]
        score = (1 if h.get("force") else 0, len(hits))
        if hits and score > best_score:
            best, best_hits, best_score = h, hits, score
    if best:
        return best, best_hits
    return {
        "id": "NEW-001", "name": "待定义模块", "kind": "hybrid",
        "domain": ["to-be-defined"], "related": [],
        "knowledge": ["该任务所需的领域知识", "权威书籍/标准/规范", "Blender 表达与验收"],
        "sources": ["优先当地现行规范/标准", "权威工具书", "同行评审论文（如适用）"],
        "questions": ["任务所在地/适用规范", "目标用户与范围", "精度/交付要求"],
        "why": "模块包没有覆盖该任务领域的参考数据。",
    }, []


def build_prompt(root, task, hint, why):
    questions = "\n".join("- " + q for q in hint.get("questions", []))
    knowledge = "\n".join("- " + k for k in hint.get("knowledge", []))
    sources = "\n".join("- " + s for s in hint.get("sources", []))
    detected = mg.detect_style_layout(root, task)
    styles = ", ".join("%s（%s）" % (x["id"], x["name"]) for x in detected["styles"]) or "未识别，请先在 open_questions 里问用户"
    layouts = ", ".join("%s（%s）" % (x["id"], x["name"]) for x in detected["layouts"]) or "未识别，请先在 open_questions 里问用户"
    return """你是 Blender Mentor 的模块作者。请严格按 mentor-module/1 格式，为下面任务生成一个新模块。

任务原文：{task}
建议模块：{mid} / {name}
状态：experimental
类型：{kind}
领域：{domain}
缺失原因：{why}

第一步：先不要写答案，先问我以下缺失信息（如果我没有回答，就写进 open_questions，不要假设）：
{questions}

第二步：查资料。优先顺序：
1) 当地现行规范/标准（写 jurisdiction + edition + 条款）
2) 权威工具书/教材
3) 同行评审论文（只用于非强制性结论；写 DOI/URL）
建议重点：{sources}

推断建筑风格（任务原文）：{styles}
推断空间类型/布局（任务原文）：{layouts}

第三步：输出 4 个部分：
A. {mid}.json — 严格按 schema/id/version/status/kind/domain/intent/coverage/data/rules/assumptions/unknown_policy/references/styles/layouts 字段；每个 data 加 source_id
B. module-{slug}.md — 按 references/module-authoring.md 第 1.4 节结构
C. 来源表 + assets/source_registry.json：每条的 id/type/title/edition/status/verification/checked_at/next_check_due/check_url
D. open_questions：没有可靠来源、或需要我确认的内容

硬规则：
- INT-* 室内模块必须声明 `styles` 与 `layouts`；任务风格/布局不在声明范围内时，不要静默套用，必须在 open_questions 提示“扩展模块或新建风格变体”。
- 每个 data 值必须有 source_id，且 source_id 必须出现在 assets/source_registry.json；没有来源就放 open_questions。
- 没有可靠来源时不要编造，标 pending；status=withdrawn/superseded 或法规缺 jurisdiction 不得写成 current。
- coverage 里的 data_keys 必须存在于 data。
- 结构/防火/无障碍/能耗：只能提示“需当地专业/工程师复核”，不能判 pass。
- 不要编造书名、版次、页码、ISBN、DOI、条款号；不确定就标 pending。
- 不要复制书中长段原文，只给引用元数据。

建议填写的知识域：
{knowledge}
""".format(task=task, mid=hint.get("id", "NEW-001"), name=hint.get("name", "待定义模块"),
           kind=hint.get("kind", "hybrid"), domain=", ".join(hint.get("domain", [])),
           why=why, questions=questions or "- 任务范围/规范/精度",
           sources=sources or "- 权威资料", knowledge=knowledge or "- 领域知识",
           styles=styles, layouts=layouts,
           slug=(hint.get("id", "NEW-001").lower().replace("-", "")))


def merge_steps(hint):
    mid = hint.get("id", "NEW-001")
    slug = "architecture" if mid == "ARC-001" else mid.lower()
    return [
        "1. 保存两份文件：assets/modules/%s.json 与 references/module-%s.md" % (mid, slug),
        "2. 为 JSON 计算 sha256，写入 assets/module_registry.json（id/file/version/hash/status）",
        "3. 在 assets/load_plan.json 的 modules 增加 %s 的 triggers/exclude" % mid,
        "4. 运行 python scripts/module_lint.py",
        "5. 运行 python scripts/module_conflict.py",
        "6. 运行 python scripts/preflight.py --task \"<原任务>\" --json .preflight.json 确认 proceed",
        "7. 运行 python scripts/selftest.py .",
        "8. 模块状态 experimental 稳定后，再考虑升 stable / 并入正式版本",
    ]


def evaluate(root, task, modules_dir=None):
    pf = preflight.evaluate(root, task, modules_dir=modules_dir)
    decision = pf.get("decision")
    if decision in ("proceed", "proceed_core"):
        return {"action": "none", "decision": decision, "task": task,
                "selected": pf.get("selected", []),
                "message": "模块已覆盖或属于核心任务，不需要新建模块。"}
    if pf.get("style_mismatch") or pf.get("layout_mismatch"):
        return {"action": "style_mismatch", "decision": decision, "task": task,
                "selected": pf.get("selected", []),
                "styles": pf.get("styles", []), "layouts": pf.get("layouts", []),
                "style_mismatch": pf.get("style_mismatch", []),
                "layout_mismatch": pf.get("layout_mismatch", []),
                "questions": pf.get("questions", []),
                "message": "当前建筑风格/空间布局不在已有内饰模块覆盖范围；先扩展该模块的 styles/layouts，或新建对应风格/布局的 INT 模块，不能按旧模块静默执行。"}
    if pf.get("selected"):
        return {"action": "resolve_existing", "decision": decision, "task": task,
                "selected": pf.get("selected", []),
                "missing": pf.get("missing", []),
                "questions": pf.get("questions", []),
                "message": "已有模块命中但数据/覆盖不足，先补现有模块，不要新建重复模块。"}
    hint, hits = pick_hint(root, task)
    why = hint.get("why") or "；".join(pf.get("questions", []))
    return {
        "action": "fill_module",
        "decision": decision,
        "task": task,
        "matched_hint": hits,
        "gap": {
            "id": hint.get("id"), "name": hint.get("name"), "kind": hint.get("kind"),
            "domain": hint.get("domain", []), "why": why,
            "knowledge": hint.get("knowledge", []),
            "sources": hint.get("sources", []),
            "questions": hint.get("questions", []),
            "related": hint.get("related", []),
        },
        "styles": pf.get("styles", []),
        "layouts": pf.get("layouts", []),
        "prompt": build_prompt(root, task, hint, why),
        "merge_steps": merge_steps(hint),
    }


def main():
    ap = argparse.ArgumentParser(description="Generate a missing-module response for a one-line task")
    ap.add_argument("--root", default=os.path.dirname(HERE))
    ap.add_argument("--task", required=True)
    ap.add_argument("--json", default=None)
    ap.add_argument("--prompt-only", action="store_true")
    args = ap.parse_args()
    try:
        result = evaluate(os.path.abspath(args.root), args.task)
    except Exception as exc:  # noqa: BLE001
        print("MODULE_GAP " + json.dumps({"action": "error", "error": str(exc)}, ensure_ascii=False))
        return 1
    if args.json:
        try:
            with open(args.json, "w", encoding="utf-8") as fh:
                json.dump(result, fh, ensure_ascii=False, indent=2)
        except OSError as exc:
            print("MODULE_GAP_JSON_ERROR " + str(exc), file=sys.stderr)
    if args.prompt_only:
        print(result.get("prompt", ""))
    else:
        print("MODULE_GAP " + json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
