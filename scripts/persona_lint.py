"""persona_lint.py — V5 人设套件结构自检（纯标准库，不依赖 Blender）。

用法：
    python persona_lint.py [套件目录] [--deny 拒绝词文件] [--allow-no-deny]
    # 套件目录默认当前目录
    # 拒绝词文件每行一个正则，只放项目侧，不进人设
    # 默认 strict（发布模式）：缺少 --deny 即判 fail，防"跳过扫描"假绿
    # --allow-no-deny：仅做结构检查时放行（不推荐用于交付验收）

检查项：
    1. 六件套齐全，版本锚点一致（主文档 / 三件套 / 两个模块注册表）
    2. 章节交叉引用可解析（写法：`工具名 §x.y`）
    3. rubric §4.7 权重合计 = 100，§5 每个角色列合计 = 100
    4. 红线 1–40、误区 1–130 计数完整
    5. （标准布局）toolbox 已剥离代码；scripts/ 由构建脚本做编译检查
    6. 拒绝词扫描（--deny；默认强制，--allow-no-deny 放行）

输出：PERSONA_LINT {json}；exit 0=pass，1=fail，2=参数错误。
"""
import json
import os
import re
import sys

FILES = [
    "references/main.md",
    "references/rubric.md",
    "references/curriculum.md",
    "references/toolbox_text.md",
    "references/module-esd.md",
    "references/module-biomechanics.md",
    "references/module-engineering.md",
]
ALIAS = {
    "main": FILES[0],
    "rubric": FILES[1],
    "curriculum": FILES[2],
    "toolbox": FILES[3],
    "ESD-001": FILES[4],
    "BIO-001": FILES[5],
    "ENG-001": FILES[6],
}


def _read(root):
    texts, missing = {}, []
    for f in FILES:
        path = os.path.join(root, f)
        if not os.path.isfile(path):
            missing.append(f)
            continue
        with open(path, encoding="utf-8") as fh:
            texts[f] = fh.read()
    return texts, missing


def _sections(text):
    return {m.group(1) for m in
            re.finditer(r"^#{2,4}\s+(\d+(?:\.\d+)*)[\.、]?\s", text, re.M)}


def _check_refs(texts):
    heads = {f: _sections(t) for f, t in texts.items()}
    all_heads = set()
    for hs in heads.values():
        all_heads |= hs
    ref = re.compile(r"(主文档|rubric|curriculum|toolbox|ESD-001|BIO-001)"
                     r"\s*[`]?\s*§\s*(\d+(?:\.\d+)*)")
    bare = re.compile(r"§\s*(\d+(?:\.\d+)*)")
    broken = []
    for f, text in texts.items():
        in_fence = False
        for i, line in enumerate(text.splitlines(), 1):
            if line.strip().startswith("`" * 3):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for m in ref.finditer(line):
                tgt = "main" if m.group(1) == "主文档" else m.group(1)
                if m.group(2) not in heads[ALIAS[tgt]]:
                    broken.append({"file": f, "line": i,
                                   "ref": "%s §%s" % (m.group(1), m.group(2))})
            # changelog lines mention historical section names on purpose
            if f == FILES[0] and re.match(r"\s*-\s*V\d", line):
                continue
            # bare refs: accept if the section exists in THIS file or in any suite file
            masked = ref.sub(" ", line)
            for m in bare.finditer(masked):
                sec = m.group(1)
                if sec not in heads[f] and sec not in all_heads:
                    broken.append({"file": f, "line": i, "ref": "§" + sec})
    return broken


def _check_versions(texts):
    main = texts[FILES[0]]
    m = re.search(r"当前 \*\*(V\d+\.\d+\.\d+)\*\*", main)
    if not m:
        return {"pass": False, "reason": "main version anchor not found"}
    ver = m.group(1)
    problems = []
    if not re.search(r"本文件 \*\*%s\*\*" % re.escape(ver), main):
        problems.append("main version line mismatch")
    for f in FILES[1:4]:
        if not re.search(r"版本：%s · 状态：stable" % re.escape(ver), texts[f]):
            problems.append("%s missing %s anchor" % (f, ver))
    esd = re.search(r"^\| 版本 \| ([\d.]+) \|", texts[FILES[4]], re.M)
    bio = re.search(r"- \*\*版本\*\*：v([\d.]+)", texts[FILES[5]])
    eng = re.search(r"- \*\*版本\*\*：v([\d.]+)", texts[FILES[6]])
    reg_esd = re.search(r"`ESD-001`.*\| stable v([\d.]+) \|", main)
    reg_bio = re.search(r"`BIO-001`.*\| stable v([\d.]+) \|", main)
    reg_eng = re.search(r"`ENG-001`.*\| stable v([\d.]+) \|", main)
    if not (esd and reg_esd and esd.group(1) == reg_esd.group(1)):
        problems.append("ESD-001 registry/module version mismatch")
    if not (bio and reg_bio and bio.group(1) == reg_bio.group(1)):
        problems.append("BIO-001 registry/module version mismatch")
    if not (eng and reg_eng and eng.group(1) == reg_eng.group(1)):
        problems.append("ENG-001 registry/module version mismatch")
    return {"pass": not problems, "suite": ver,
            "module_versions": {"ESD-001": esd.group(1) if esd else None,
                                "BIO-001": bio.group(1) if bio else None,
                                "ENG-001": eng.group(1) if eng else None},
            "problems": problems}


def _check_weights(texts):
    rub = texts[FILES[1]]
    out = {}
    try:
        sec47 = rub.split("### 4.7 动画")[1].split("### 4.8")[0]
        w47 = [int(x) for x in re.findall(r"\|\s*(\d+)%\s*\|", sec47)]
        out["4_7"] = {"sum": sum(w47), "pass": sum(w47) == 100, "values": w47}
    except IndexError:
        out["4_7"] = {"pass": False, "reason": "section 4.7 not found"}
    try:
        sec5 = rub.split("## 5. 域权重")[1].split("## 6.")[0]
        rows = [l for l in sec5.splitlines() if l.strip().startswith("|")]
        header = [c.strip() for c in rows[0].strip("|").split("|")]
        roles = header[1:]
        sums = {r: 0 for r in roles}
        for line in rows[2:]:
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) != len(header):
                continue
            for i, r in enumerate(roles):
                try:
                    sums[r] += int(cells[i + 1])
                except ValueError:
                    pass
        out["5"] = {"sums": sums, "pass": all(v == 100 for v in sums.values())}
    except IndexError:
        out["5"] = {"pass": False, "reason": "section 5 not found"}
    return {"pass": out["4_7"]["pass"] and out["5"]["pass"], "detail": out}


def _check_counts(texts):
    main = texts[FILES[0]]
    try:
        sec8 = main.split("## 8. 新手红线 40 条")[1].split("## 9.")[0]
    except IndexError:
        sec8 = ""
    missing_red = [n for n in range(1, 41)
                   if not re.search(r"(?<![\d.])%d(?![\d.])" % n, sec8)]
    tb = texts[FILES[3]]
    nums = [int(n) for n in re.findall(r"^\| (\d{1,3}) \|", tb, re.M)]
    return {"pass": not missing_red and sorted(set(nums)) == list(range(1, 131)),
            "redlines_missing": missing_red,
            "misconceptions": {"count": len(set(nums)),
                               "max": max(nums) if nums else None}}


def _check_py_blocks(texts):
    tb = texts[FILES[3]]
    fence = "`" * 3
    blocks = re.findall(fence + r"python\n(.*?)" + fence, tb, re.S)
    errors = []
    for i, code in enumerate(blocks):
        try:
            compile(code, "<toolbox-block-%d>" % i, "exec")
        except SyntaxError as exc:
            errors.append({"block": i, "error": str(exc)})
    return {"pass": not errors, "blocks": len(blocks), "errors": errors}


_PLACEHOLDER_RE = re.compile(r"PLACEHOLDER|REPLACE_ME|CHANGEME|<[^>]+>", re.I)


def _check_deny(texts, deny_path, strict=False):
    if not deny_path:
        if strict:
            return {"pass": False, "error": "strict: --deny required"}
        return {"pass": True, "skipped": "no --deny file"}
    try:
        with open(deny_path, encoding="utf-8") as fh:
            raw = [l.strip() for l in fh
                   if l.strip() and not l.strip().startswith("#")]
    except OSError as exc:
        return {"pass": False, "error": str(exc)}
    placeholders = [p for p in raw if _PLACEHOLDER_RE.search(p)]
    if placeholders:
        return {"pass": False,
                "error": "deny file still contains template placeholders",
                "placeholders": placeholders}
    if not raw:
        return {"pass": False, "error": "deny file has no active patterns"}
    hits = []
    for f, text in texts.items():
        for i, line in enumerate(text.splitlines(), 1):
            for pat in raw:
                try:
                    if re.search(pat, line):
                        hits.append({"file": f, "line": i, "pattern": pat,
                                     "text": line.strip()[:100]})
                except re.error as exc:
                    return {"pass": False, "error": "bad regex %r: %s" % (pat, exc)}
    return {"pass": not hits, "patterns": len(raw), "hits": hits}


def lint(root=".", deny_path=None, strict=True):
    texts, missing = _read(root)
    checks = [{"check": "files_present", "pass": not missing, "missing": missing}]
    if missing:
        result = {"status": "fail", "checks": checks}
        return result
    refs = _check_refs(texts)
    checks.append({"check": "cross_refs", "pass": not refs, "broken": refs})
    checks.append(dict({"check": "versions"}, **_check_versions(texts)))
    checks.append(dict({"check": "weights"}, **_check_weights(texts)))
    checks.append(dict({"check": "counts"}, **_check_counts(texts)))
    checks.append(dict({"check": "toolbox_python_blocks"}, **_check_py_blocks(texts)))
    checks.append(dict({"check": "deny_scan"}, **_check_deny(texts, deny_path, strict)))
    return {"status": "pass" if all(c["pass"] for c in checks) else "fail",
            "checks": checks}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    root, deny, strict = ".", None, True
    i = 0
    while i < len(argv):
        if argv[i] == "--strict":
            strict = True
            i += 1
        elif argv[i] == "--allow-no-deny":
            strict = False
            i += 1
        elif argv[i] == "--deny" and i + 1 < len(argv):
            deny = argv[i + 1]
            i += 2
        elif not argv[i].startswith("--"):
            root = argv[i]
            i += 1
        else:
            i += 1
    if not os.path.isdir(root):
        print("PERSONA_LINT " + json.dumps(
            {"status": "fail", "error": "not a directory: %s" % root},
            ensure_ascii=False))
        return 2
    result = lint(root, deny, strict)
    print("PERSONA_LINT " + json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
