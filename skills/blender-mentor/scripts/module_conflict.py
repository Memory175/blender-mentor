# -*- coding: utf-8 -*-
"""module_conflict.py — 模块间冲突巡查（只报告，不自动裁决）。

用法：python scripts/module_conflict.py [--root .] [--json out.json]
退出码：0=无冲突，2=有冲突（必须停下来问用户）。
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import module_governance as mg  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.dirname(HERE))
    ap.add_argument("--modules-dir", default=None)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    try:
        registry, problems = (None, []) if args.modules_dir else mg.load_registry(root)
        modules, load_problems = mg.load_modules(root, args.modules_dir, registry)
        conflicts = mg.scan_conflicts(modules, list(problems) + list(load_problems))
    except Exception as exc:  # noqa: BLE001
        print("MODULE_CONFLICT " + json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1
    result = {"status": "conflict" if conflicts else "pass",
              "modules": [m.get("id") for m in modules], "conflicts": conflicts}
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=2)
    print("MODULE_CONFLICT " + json.dumps(result, ensure_ascii=False))
    return 2 if conflicts else 0


if __name__ == "__main__":
    sys.exit(main())
