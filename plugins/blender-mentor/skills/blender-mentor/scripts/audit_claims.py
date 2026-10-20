# -*- coding: utf-8 -*-
"""audit_claims.py — 输出引用审计（交付前闸门）。

规则：
- 只有模块支撑的交付（preflight=proceed 且有 selected 模块）才默认审计；
  `proceed_core` / `ask` / `block` 默认跳过（status=skipped）。
- 带单位/百分号/角度的数值，必须能追溯到：
    [MODULE-ID:data_key]      例如 [ENG-001:min_wall_mm]
    [PROJECT] / [MEASURED]    项目实测值（帧号、面数、项目数据）
    [EXAMPLE]                 教学示例值
    [ASSUMPTION] / [ASSUMPTION:reason]
- 引用必须在数值同一行；引用必须存在于 preflight 的 data 中，否则 dangling。
- 无法追溯的数值 = uncited，默认 exit 1。
- `--scope all` 可审计所有任务；`--warn-only` 只告警不阻断（便于诊断）。

用法：
    python scripts/audit_claims.py --text answer.md --preflight .preflight.json --json .claims.json
    python scripts/audit_claims.py --text answer.md --preflight .preflight.json --scope all
    cat answer.md | python scripts/audit_claims.py --preflight .preflight.json
"""
import argparse
import json
import re
import sys

CITATION_RE = re.compile(r"\[([A-Z]{2,4}-\d{3}):([A-Za-z0-9_.\-]+)\]")
ASSUMPTION_RE = re.compile(r"\[ASSUMPTION(?::([^\]]*))?\]")
PROJECT_RE = re.compile(r"\[(PROJECT|MEASURED|EXAMPLE)(?::([^\]]*))?\]")
UNIT_RE = re.compile(
    r"(?<![\w.])(-?\d+(?:\.\d+)?(?:\s*[–~\-至]\s*-?\d+(?:\.\d+)?)?)"
    r"\s*(mm²|mm³|mm|cm|kg|ms|MPa|Pa|rpm|°C|deg|°|%|percent|s|g|m|N|帧|面|tri|倍|BW)(?![A-Za-z])",
    re.IGNORECASE,
)


def _strip_code(text):
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"`[^`\n]+`", "", text)
    return text


def _load_preflight(path):
    if not path:
        return {"data": {}, "selected": []}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def audit(text, preflight, scope="module"):
    selected = preflight.get("selected") or []
    module_backed = preflight.get("decision") == "proceed" and bool(selected)
    empty = {"claims": [], "uncited": [], "dangling": [], "assumptions": [],
             "project_claims": [], "allowed_citations": []}
    if scope == "module" and not module_backed:
        return {"status": "skipped", "reason": "no module-backed preflight (proceed + selected); "
                "use --scope all to audit core/teaching output", **empty}
    clean = _strip_code(text)
    lines = clean.splitlines()
    allowed = set()
    for key, entry in (preflight.get("data") or {}).items():
        mid = entry.get("module") if isinstance(entry, dict) else None
        if mid:
            allowed.add((mid, key))
    claims, uncited, dangling, assumptions, project_claims = [], [], [], [], []
    for lineno, line in enumerate(lines, 1):
        for m in UNIT_RE.finditer(line):
            claim = {"line": lineno, "text": m.group(0).strip()}
            tail = line[m.start():]
            cites = CITATION_RE.findall(tail)
            ass = ASSUMPTION_RE.search(tail)
            proj = PROJECT_RE.search(tail)
            cited = bool(cites) or bool(ass) or bool(proj)
            claim["cited"] = cited
            claim["kind"] = ("module" if cites else "project" if proj
                             else "assumption" if ass else "uncited")
            if cites:
                claim["citations"] = ["%s:%s" % (a, b) for a, b in cites]
                for a, b in cites:
                    if (a, b) not in allowed:
                        dangling.append({"line": lineno, "citation": "%s:%s" % (a, b),
                                         "text": m.group(0).strip()})
            if proj:
                project_claims.append({"line": lineno, "text": m.group(0).strip(),
                                       "tag": proj.group(1), "note": (proj.group(2) or "").strip()})
            if ass:
                assumptions.append({"line": lineno, "text": m.group(0).strip(),
                                    "reason": (ass.group(1) or "").strip()})
            if not cited:
                uncited.append({"line": lineno, "claim": m.group(0).strip()})
            claims.append(claim)
    status = "pass"
    if dangling or uncited:
        status = "fail"
    elif assumptions:
        status = "warn"
    return {
        "status": status,
        "claims": claims,
        "uncited": uncited,
        "dangling": dangling,
        "assumptions": assumptions,
        "project_claims": project_claims,
        "allowed_citations": sorted("%s:%s" % (a, b) for a, b in allowed),
    }


def main():
    ap = argparse.ArgumentParser(description="Audit numeric claims against module preflight data")
    ap.add_argument("--text", default=None, help="answer markdown/text; stdin if omitted")
    ap.add_argument("--preflight", default=None, help=".preflight.json from preflight.py")
    ap.add_argument("--json", default=None)
    ap.add_argument("--scope", choices=["module", "all"], default="module",
                    help="module=only module-backed tasks (default); all=audit every task")
    ap.add_argument("--warn-only", action="store_true", help="exit 0 even when uncited/dangling")
    args = ap.parse_args()
    if args.text:
        text = open(args.text, encoding="utf-8").read()
    else:
        text = sys.stdin.read()
    try:
        result = audit(text, _load_preflight(args.preflight), scope=args.scope)
    except Exception as exc:  # noqa: BLE001
        print("CLAIM_AUDIT " + json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1
    if args.json:
        try:
            with open(args.json, "w", encoding="utf-8") as fh:
                json.dump(result, fh, ensure_ascii=False, indent=2)
        except OSError as exc:
            result["json_error"] = str(exc)
            print("CLAIM_AUDIT_JSON_ERROR " + str(exc), file=sys.stderr)
    print("CLAIM_AUDIT " + json.dumps(result, ensure_ascii=False))
    if result["status"] == "fail" and not args.warn_only:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
