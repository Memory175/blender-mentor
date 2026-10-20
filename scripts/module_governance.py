# -*- coding: utf-8 -*-
"""module_governance.py — 模块格式校验、注册表读取、冲突巡查。

模块文件：assets/modules/<ID>.json（schema = mentor-module/1）
注册表：  assets/module_registry.json（schema = mentor-registry/1）
"""
import glob
import hashlib
import json
import os
import re

REQUIRED = ["schema", "id", "version", "status", "kind", "domain", "intent",
            "coverage", "data", "rules", "unknown_policy"]
STATUS = {"experimental", "stable", "deprecated"}
KINDS = {"reference", "procedure", "hybrid"}
POLICIES = {"block", "ask", "proceed_with_label"}
ID_RE = re.compile(r"^[A-Z]{2,4}-\d{3}$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def read_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(text):
    return (text or "").lower().replace("_", " ").strip()


CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def keyword_hit(keyword, text):
    """中文用子串；ASCII 用词边界，避免 COM 命中 compare/composition。"""
    kw, t = norm(keyword), norm(text)
    if not kw:
        return False
    if CJK_RE.search(kw):
        return kw in t
    pattern = r"(?<![a-z0-9])" + re.escape(kw) + r"(?![a-z0-9])"
    return re.search(pattern, t) is not None


def load_registry(root, registry_path=None):
    path = registry_path or os.path.join(root, "assets", "module_registry.json")
    if not os.path.isfile(path):
        return None, ["registry missing: %s" % path]
    try:
        reg = read_json(path)
    except Exception as exc:  # noqa: BLE001
        return None, ["registry unreadable: %s" % exc]
    if reg.get("schema") != "mentor-registry/1":
        return None, ["registry schema != mentor-registry/1"]
    return reg, []


def load_modules(root, modules_dir=None, registry=None):
    """返回 (modules, problems)。modules_dir 给定时忽略注册表（测试用）。"""
    modules, problems = [], []
    if modules_dir:
        files = sorted(glob.glob(os.path.join(modules_dir, "*.json")))
        for p in files:
            try:
                modules.append(read_json(p))
            except Exception as exc:  # noqa: BLE001
                problems.append("module unreadable: %s (%s)" % (p, exc))
        return modules, problems
    if registry is None:
        registry, problems = load_registry(root)
        if registry is None:
            return [], problems
    for item in registry.get("modules", []):
        rel = item.get("file", "")
        p = os.path.join(root, rel)
        if not os.path.isfile(p):
            problems.append("module file missing: %s" % rel)
            continue
        try:
            mod = read_json(p)
        except Exception as exc:  # noqa: BLE001
            problems.append("module unreadable: %s (%s)" % (p, exc))
            continue
        expected = (item.get("hash") or "").replace("sha256:", "")
        actual = sha256_file(p)
        if expected and expected != actual:
            problems.append("hash mismatch %s: registry=%s actual=%s" % (
                mod.get("id", rel), expected[:12], actual[:12]))
        if item.get("id") and mod.get("id") != item.get("id"):
            problems.append("id mismatch %s: file=%s" % (rel, mod.get("id")))
        if item.get("version") and mod.get("version") != item.get("version"):
            problems.append("version mismatch %s: registry=%s file=%s" % (
                mod.get("id"), item.get("version"), mod.get("version")))
        modules.append(mod)
    return modules, problems


def validate_module(mod, root=None):
    problems = []
    mid = str(mod.get("id", "?"))
    for key in REQUIRED:
        if key not in mod:
            problems.append("%s: missing field %s" % (mid, key))
    if mod.get("schema") != "mentor-module/1":
        problems.append("%s: schema != mentor-module/1" % mid)
    if not ID_RE.match(str(mod.get("id", ""))):
        problems.append("%s: id must match AAA-001" % mid)
    if not SEMVER_RE.match(str(mod.get("version", ""))):
        problems.append("%s: version must be semver" % mid)
    if mod.get("status") not in STATUS:
        problems.append("%s: bad status %s" % (mid, mod.get("status")))
    if mod.get("kind") not in KINDS:
        problems.append("%s: bad kind %s" % (mid, mod.get("kind")))
    if mod.get("unknown_policy") not in POLICIES:
        problems.append("%s: bad unknown_policy %s" % (mid, mod.get("unknown_policy")))
    intent = mod.get("intent") or {}
    if not isinstance(intent.get("include"), list) or not intent.get("include"):
        problems.append("%s: intent.include must be non-empty list" % mid)
    if not isinstance(mod.get("domain"), list) or not mod.get("domain"):
        problems.append("%s: domain must be non-empty list" % mid)
    data_keys = set()
    for d in mod.get("data", []):
        k = d.get("key")
        if not k:
            problems.append("%s: data entry missing key" % mid)
            continue
        data_keys.add(k)
        if "value" not in d:
            problems.append("%s.%s: missing value" % (mid, k))
        if not d.get("unit"):
            problems.append("%s.%s: missing unit" % (mid, k))
        if not d.get("source") and not d.get("source_id") and not d.get("assumption"):
            problems.append("%s.%s: needs source/source_id or assumption=true" % (mid, k))
    if mid.startswith("INT-"):
        if not isinstance(mod.get("styles"), list) or not mod.get("styles"):
            problems.append("%s: INT module needs non-empty styles[]" % mid)
        if not isinstance(mod.get("layouts"), list) or not mod.get("layouts"):
            problems.append("%s: INT module needs non-empty layouts[]" % mid)
        for d in mod.get("data", []):
            if d.get("confidence") not in (None, "high", "medium", "low"):
                problems.append("%s.%s: bad confidence" % (mid, d.get("key")))
    if len(data_keys) != len(mod.get("data", [])):
        problems.append("%s: duplicate data key" % mid)
    for cap in mod.get("coverage", []):
        if not isinstance(cap.get("keywords"), list) or not cap.get("keywords"):
            problems.append("%s: coverage entry missing keywords" % mid)
        for k in cap.get("data_keys", []):
            if k not in data_keys:
                problems.append("%s: coverage references unknown data key %s" % (mid, k))
    rule_ids = set()
    for r in mod.get("rules", []):
        rid = r.get("id")
        if not rid:
            problems.append("%s: rule missing id" % mid)
            continue
        if rid in rule_ids:
            problems.append("%s: duplicate rule id %s" % (mid, rid))
        rule_ids.add(rid)
        if not r.get("severity") in ("fail", "warn", "info"):
            problems.append("%s.%s: bad severity" % (mid, rid))
        ev = r.get("evidence")
        if ev and ev.startswith("data.") and ev.split(".", 1)[1] not in data_keys:
            problems.append("%s.%s: evidence references unknown data" % (mid, rid))
    for ref in mod.get("references", []):
        if root and not os.path.isfile(os.path.join(root, ref)):
            problems.append("%s: missing reference %s" % (mid, ref))
    return problems


def scan_conflicts(modules, registry_problems=None):
    """返回冲突列表；只在可判定的重复/矛盾上报冲突。"""
    conflicts = []
    for p in registry_problems or []:
        conflicts.append({"type": "registry", "severity": "block", "detail": p})
    by_id = {}
    for m in modules:
        mid = m.get("id", "?")
        if mid in by_id:
            conflicts.append({"type": "duplicate_id", "severity": "block",
                              "detail": "duplicate module id %s" % mid})
        by_id[mid] = m
    # 同一数据键，不同值/单位/作用域
    data_map = {}
    for m in modules:
        for d in m.get("data", []):
            key = d.get("key")
            if not key:
                continue
            sig = (json.dumps(d.get("value"), sort_keys=True), d.get("unit"), d.get("scope"))
            data_map.setdefault(key, []).append((m.get("id", "?"), sig, d))
    for key, entries in data_map.items():
        sigs = {e[1] for e in entries}
        if len(sigs) > 1:
            conflicts.append({"type": "data_value", "severity": "block", "key": key,
                              "detail": "same key has different value/unit/scope",
                              "entries": [{"module": e[0], "value": e[2].get("value"),
                                           "unit": e[2].get("unit"), "scope": e[2].get("scope")}
                                          for e in entries]})
    # 触发词重复（不同模块都声明同一 include，且未声明 conflicts_with）
    trig = {}
    for m in modules:
        for kw in (m.get("intent") or {}).get("include", []):
            trig.setdefault(norm(kw), []).append(m.get("id", "?"))
    for kw, ids in trig.items():
        if len(set(ids)) > 1:
            conflicts.append({"type": "trigger_overlap", "severity": "warn",
                              "detail": "trigger '%s' claimed by %s" % (kw, ", ".join(sorted(set(ids))))})
    # conflicts_with 双向性
    declared = {m.get("id", "?"): set(m.get("conflicts_with", [])) for m in modules}
    for mid, others in declared.items():
        for other in others:
            if other in declared and mid not in declared[other]:
                conflicts.append({"type": "conflict_asymmetry", "severity": "warn",
                                  "detail": "%s conflicts_with %s but not vice versa" % (mid, other)})
    return conflicts


def select_modules(modules, task, max_modules=2):
    t = norm(task)
    scored = []
    for m in modules:
        intent = m.get("intent") or {}
        includes = [norm(x) for x in intent.get("include", [])]
        excludes = [norm(x) for x in intent.get("exclude", [])]
        if any(x and keyword_hit(x, t) for x in excludes):
            continue
        hits = [x for x in includes if keyword_hit(x, t)]
        if not hits:
            continue
        cap_hits = 0
        for cap in m.get("coverage", []):
            if any(keyword_hit(k, t) for k in cap.get("keywords", [])):
                cap_hits += 1
        score = len(hits) * 10 + cap_hits * 3
        if m.get("status") == "deprecated":
            score -= 100
        scored.append((score, len(hits), m))
    scored.sort(key=lambda x: (-x[0], -x[1], str(x[2].get("id"))))
    return [m for _, _, m in scored[:max_modules]]


def coverage_for(selected, task):
    t = norm(task)
    matched = []
    required = set()
    for m in selected:
        for cap in m.get("coverage", []):
            if any(keyword_hit(k, t) for k in cap.get("keywords", [])):
                matched.append({"module": m.get("id"), "keywords": cap.get("keywords"),
                                "data_keys": cap.get("data_keys", [])})
                required.update(cap.get("data_keys", []))
    available = {}
    for m in selected:
        for d in m.get("data", []):
            available[d.get("key")] = {"module": m.get("id"), **d}
    return matched, required, available


def load_style_taxonomy(root):
    path = os.path.join(root, "assets", "style_taxonomy.json")
    if not os.path.isfile(path):
        return {"styles": [], "layouts": []}
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:  # noqa: BLE001
        return {"styles": [], "layouts": []}
    return {"styles": data.get("styles", []), "layouts": data.get("layouts", [])}


def detect_style_layout(root, task):
    """Return detected style/layout items from the task text."""
    taxonomy = load_style_taxonomy(root)
    result = {"styles": [], "layouts": []}
    for kind in ("styles", "layouts"):
        for item in taxonomy.get(kind, []):
            hits = [kw for kw in item.get("keywords", []) if keyword_hit(kw, task)]
            if hits:
                result[kind].append({"id": item.get("id"), "name": item.get("name"), "hits": hits})
    return result
