# -*- coding: utf-8 -*-
"""self_audit.py — 自动发现模块 + 自审查索引（不再维护手写模块清单）。

扫描：
  assets/modules/*.json
  references/module-*.md（排除 module-format / module-authoring）
  assets/module_registry.json
  assets/load_plan.json
  assets/source_registry.json

输出：
  assets/self_audit_index.json   # 自动生成，不要手改

用法：
    python scripts/self_audit.py --root . --check
    python scripts/self_audit.py --root . --write --sync
"""
import argparse
import datetime
import glob
import hashlib
import json
import os
import re
import sys

GOVERNANCE_REFS = {"module-format.md", "module-authoring.md"}


def _read_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _module_ref(root, mod):
    """优先模块 JSON 的 references；否则按 ID 猜 module-<id>.md。"""
    refs = mod.get("references") or []
    for ref in refs:
        if str(ref).endswith(".md"):
            return str(ref).replace("\\", "/")
    return "references/module-%s.md" % str(mod.get("id", "")).lower()


def _doc_version(text):
    patterns = [
        r"版本[：:]\s*v?([\d]+\.[\d]+\.[\d]+)",
        r"版本\s*\|\s*v?([\d]+\.[\d]+\.[\d]+)",
        r"\*\*版本\*\*[：:]\s*v?([\d]+\.[\d]+\.[\d]+)",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1)
    return None


def _module_title(mod, doc_text):
    if mod.get("title"):
        return mod["title"]
    m = re.search(r"^#\s+(.+)$", doc_text or "", re.M)
    return m.group(1).strip() if m else str(mod.get("id"))


def discover(root):
    modules_dir = os.path.join(root, "assets", "modules")
    registry_path = os.path.join(root, "assets", "module_registry.json")
    plan_path = os.path.join(root, "assets", "load_plan.json")
    source_path = os.path.join(root, "assets", "source_registry.json")
    main_path = os.path.join(root, "references", "main.md")
    issues = []
    modules = []

    registry = _read_json(registry_path) if os.path.isfile(registry_path) else {}
    plan = _read_json(plan_path) if os.path.isfile(plan_path) else {}
    sources = _read_json(source_path) if os.path.isfile(source_path) else {}
    source_ids = {s.get("id") for s in sources.get("sources", [])}
    registry_map = {m.get("id"): m for m in registry.get("modules", [])}
    plan_map = {m.get("id"): m for m in plan.get("modules", [])}
    main_text = open(main_path, encoding="utf-8").read() if os.path.isfile(main_path) else ""

    json_files = sorted(glob.glob(os.path.join(modules_dir, "*.json")))
    json_files = [p for p in json_files if os.path.basename(p) != "_template.json"]
    referenced_refs = set()

    for jp in json_files:
        rel_json = os.path.relpath(jp, root).replace("\\", "/")
        try:
            mod = _read_json(jp)
        except Exception as exc:  # noqa: BLE001
            issues.append({"severity": "fail", "code": "module_json_unreadable",
                           "module": os.path.basename(jp), "detail": str(exc)})
            continue
        mid = mod.get("id")
        ver = mod.get("version")
        entry = {"id": mid, "version": ver, "status": mod.get("status"),
                 "json": rel_json, "json_sha256": _sha256(jp),
                 "styles": mod.get("styles", []), "layouts": mod.get("layouts", [])}
        if not mid:
            issues.append({"severity": "fail", "code": "module_id_missing", "json": rel_json})
            continue
        ref = _module_ref(root, mod)
        entry["reference"] = ref
        referenced_refs.add(os.path.basename(ref))
        ref_path = os.path.join(root, ref)
        ref_text = ""
        if not os.path.isfile(ref_path):
            issues.append({"severity": "fail", "code": "reference_missing", "module": mid, "reference": ref})
            entry["reference_present"] = False
        else:
            ref_text = open(ref_path, encoding="utf-8").read()
            entry["reference_present"] = True
            if mid not in ref_text[:5000]:
                issues.append({"severity": "fail", "code": "reference_id_missing", "module": mid, "reference": ref})
            dv = _doc_version(ref_text)
            entry["doc_version"] = dv
            if ver and dv != ver:
                issues.append({"severity": "fail", "code": "doc_version_mismatch",
                               "module": mid, "json_version": ver, "doc_version": dv})

        reg = registry_map.get(mid)
        entry["registry_present"] = bool(reg)
        if not reg:
            issues.append({"severity": "fail", "code": "registry_missing", "module": mid})
        else:
            entry["registry_version"] = reg.get("version")
            entry["registry_hash_match"] = ("sha256:" + entry["json_sha256"]) == reg.get("hash")
            if reg.get("version") != ver:
                issues.append({"severity": "fail", "code": "registry_version_mismatch",
                               "module": mid, "json_version": ver, "registry_version": reg.get("version")})
            if not entry["registry_hash_match"]:
                issues.append({"severity": "fail", "code": "registry_hash_mismatch", "module": mid})

        if mid not in plan_map:
            issues.append({"severity": "fail", "code": "load_plan_missing", "module": mid})
        entry["load_plan_present"] = mid in plan_map

        if str(mid).startswith("INT-"):
            if not entry["styles"]:
                issues.append({"severity": "fail", "code": "int_styles_missing", "module": mid})
            if not entry["layouts"]:
                issues.append({"severity": "fail", "code": "int_layouts_missing", "module": mid})

        data_keys = set()
        for d in mod.get("data", []):
            key = d.get("key")
            if not key:
                issues.append({"severity": "fail", "code": "data_key_missing", "module": mid})
                continue
            if key in data_keys:
                issues.append({"severity": "fail", "code": "data_key_duplicate", "module": mid, "key": key})
            data_keys.add(key)
            sid = d.get("source_id")
            if not sid and not d.get("assumption"):
                issues.append({"severity": "fail", "code": "data_source_missing", "module": mid, "key": key})
            elif sid and source_ids and sid not in source_ids:
                issues.append({"severity": "fail", "code": "source_id_unknown",
                               "module": mid, "key": key, "source_id": sid})
        for cap in mod.get("coverage", []):
            for key in cap.get("data_keys", []):
                if key not in data_keys:
                    issues.append({"severity": "fail", "code": "coverage_key_unknown",
                                   "module": mid, "key": key})

        if main_text and not re.search(r"\|\s*`?%s`?\s*\|.*\|\s*(?:stable|experimental)\s+v%s\s*\|"
                                        % (re.escape(str(mid)), re.escape(str(ver))), main_text):
            issues.append({"severity": "warn", "code": "main_table_missing", "module": mid})
        entry["main_table_present"] = bool(main_text and re.search(
            r"\|\s*`?%s`?\s*\|" % re.escape(str(mid)), main_text))
        modules.append(entry)

    ref_files = sorted(glob.glob(os.path.join(root, "references", "module-*.md")))
    orphan_refs = []
    for p in ref_files:
        name = os.path.basename(p)
        if name in GOVERNANCE_REFS:
            continue
        if name not in referenced_refs:
            orphan_refs.append("references/" + name)
            issues.append({"severity": "warn", "code": "orphan_reference", "reference": "references/" + name})

    # registry / load_plan 中引用了不存在的模块 JSON
    json_ids = {m.get("id") for m in modules}
    for mid in sorted(set(registry_map) - json_ids):
        issues.append({"severity": "fail", "code": "registry_orphan", "module": mid})
    for mid in sorted(set(plan_map) - json_ids):
        issues.append({"severity": "warn", "code": "load_plan_orphan", "module": mid})

    fail = sum(1 for i in issues if i.get("severity") == "fail")
    warn = sum(1 for i in issues if i.get("severity") == "warn")
    return {
        "schema": "mentor-self-audit/1",
        "generated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "root": ".",
        "modules": modules,
        "orphan_references": orphan_refs,
        "issues": issues,
        "summary": {"modules": len(modules), "issues": len(issues), "fail": fail, "warn": warn},
    }


def _sync(root, data):
    """把发现的模块补进 registry / load_plan；不手写新索引。"""
    reg_path = os.path.join(root, "assets", "module_registry.json")
    plan_path = os.path.join(root, "assets", "load_plan.json")
    registry = _read_json(reg_path) if os.path.isfile(reg_path) else {"schema": "mentor-registry/1", "modules": []}
    plan = _read_json(plan_path) if os.path.isfile(plan_path) else {"version": 1, "modules": []}
    reg_map = {m.get("id"): m for m in registry.get("modules", [])}
    plan_map = {m.get("id"): m for m in plan.get("modules", [])}
    changed = False
    for entry in data["modules"]:
        mid = entry["id"]
        new_reg = {"id": mid, "file": entry["json"], "version": entry["version"],
                   "hash": "sha256:" + entry["json_sha256"], "status": entry["status"]}
        if reg_map.get(mid) != new_reg:
            existing = reg_map.get(mid)
            if existing:
                existing.update(new_reg)
            else:
                registry.setdefault("modules", []).append(new_reg)
            changed = True
        if mid not in plan_map:
            mod = _read_json(os.path.join(root, entry["json"]))
            title = (mod.get("title") or mid)
            plan.setdefault("modules", []).append({
                "id": mid,
                "file": entry["reference"],
                "reason": title,
                "triggers": list(dict.fromkeys(
                    list(mod.get("intent", {}).get("include", []))
                    + list(mod.get("styles", [])) + list(mod.get("layouts", [])))),
            })
            changed = True
    if changed:
        registry["modules"] = sorted(registry.get("modules", []), key=lambda x: str(x.get("id")))
        plan["modules"] = sorted(plan.get("modules", []), key=lambda x: str(x.get("id")))
        _write_json(reg_path, registry)
        _write_json(plan_path, plan)
    return changed


def audit(root=".", write=False, sync=False):
    root = os.path.abspath(root)
    if sync:
        first = discover(root)
        _sync(root, first)
    data = discover(root)
    if write:
        _write_json(os.path.join(root, "assets", "self_audit_index.json"), data)
    return data


def main(argv=None):
    ap = argparse.ArgumentParser(description="Auto-discover modules and self-audit index")
    ap.add_argument("--root", default=".")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--sync", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    try:
        data = audit(args.root, write=args.write, sync=args.sync)
    except Exception as exc:  # noqa: BLE001
        print("SELF_AUDIT " + json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1
    print("SELF_AUDIT " + json.dumps({
        "status": "pass" if data["summary"]["fail"] == 0 else "fail",
        "modules": data["summary"]["modules"],
        "issues": data["summary"]["issues"],
        "fail": data["summary"]["fail"],
        "warn": data["summary"]["warn"],
        "index": "assets/self_audit_index.json" if args.write else None,
    }, ensure_ascii=False))
    return 0 if (not args.check or data["summary"]["fail"] == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
