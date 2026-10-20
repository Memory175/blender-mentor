# -*- coding: utf-8 -*-
"""module_lint.py — 模块格式 / 证据 / 注册表 / 引用一致性检查。

用法：python scripts/module_lint.py [--root .] [--json out.json]
退出码：0=pass/warn，1=fail。
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import module_governance as mg  # noqa: E402


def run(root, registry_path=None, modules_dir=None):
    registry, reg_problems = (None, []) if modules_dir else mg.load_registry(root, registry_path)
    modules, load_problems = mg.load_modules(root, modules_dir, registry)
    problems = list(reg_problems) + list(load_problems)
    for mod in modules:
        problems.extend(mg.validate_module(mod, root))
        for ref in mod.get("references", []):
            p = os.path.join(root, ref)
            if os.path.isfile(p):
                text = open(p, encoding="utf-8").read()
                mid = mod.get("id", "")
                if mid and mid not in text:
                    problems.append("%s: reference %s does not mention module id" % (mid, ref))
    conflicts = mg.scan_conflicts(modules, [])
    blocking = [c for c in conflicts if c.get("severity") == "block"]
    status = "fail" if (problems or blocking) else ("warn" if conflicts else "pass")
    return {"status": status, "modules": [m.get("id") for m in modules],
            "problems": problems, "conflicts": conflicts}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.dirname(HERE))
    ap.add_argument("--registry", default=None)
    ap.add_argument("--modules-dir", default=None)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    try:
        result = run(os.path.abspath(args.root), args.registry, args.modules_dir)
    except Exception as exc:  # noqa: BLE001
        print("MODULE_LINT " + json.dumps({"status": "fail", "error": str(exc)}, ensure_ascii=False))
        return 1
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=2)
    print("MODULE_LINT " + json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] in ("pass", "warn") else 1


if __name__ == "__main__":
    sys.exit(main())
