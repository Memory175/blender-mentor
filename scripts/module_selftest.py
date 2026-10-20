# -*- coding: utf-8 -*-
"""module_selftest.py — 预审闸门回归（纯 Python，不需要 Blender）。

覆盖：模块 proceed / 核心 proceed_core / 英文模块命中 / 无模块 block /
COM/UV 不误触发 / 数值冲突 ask / 覆盖缺数据 ask。
用法：python scripts/module_selftest.py [--root .]
"""
import argparse
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import preflight  # noqa: E402


def _fixture(mid, include, key, value):
    return {
        "schema": "mentor-module/1", "id": mid, "version": "1.0.0", "status": "stable",
        "kind": "reference", "domain": ["test"],
        "intent": {"include": include, "exclude": []},
        "coverage": [{"keywords": include, "data_keys": [key]}],
        "data": [{"key": key, "value": value, "unit": "mm", "scope": "test",
                  "source": "fixture", "confidence": "high"}],
        "rules": [], "unknown_policy": "ask", "requires": [], "conflicts_with": [],
        "references": [], "tests": [], "changelog": [],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.dirname(HERE))
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    cases = []

    r = preflight.evaluate(root, "马克杯能注塑吗？壁厚和拔模审一下")
    cases.append(("eng_covered_proceed", r["decision"] == "proceed" and
                  any(m["id"] == "ENG-001" for m in r["selected"]) and not r["missing"]))

    r = preflight.evaluate(root, "人体走路循环的 GRF 和重心")
    cases.append(("bio_covered_proceed", r["decision"] == "proceed" and
                  any(m["id"] == "BIO-001" for m in r["selected"])))

    r = preflight.evaluate(root, "焊接过渡怎么处理")
    cases.append(("weld_block", r["decision"] == "block" and not r["selected"]))

    r = preflight.evaluate(root, "建模入门")
    cases.append(("core_model_proceed", r["decision"] == "proceed_core" and not r["selected"]))

    r = preflight.evaluate(root, "Review this walk cycle")
    cases.append(("english_gait_proceed", r["decision"] == "proceed"
                  and any(m["id"] == "BIO-001" for m in r["selected"])))

    r = preflight.evaluate(root, "please compare these two meshes")
    cases.append(("com_no_bio", all(m["id"] != "BIO-001" for m in r["selected"])))

    r = preflight.evaluate(root, "拉伸一下这个 UV")
    cases.append(("uv_no_esd", all(m["id"] != "ESD-001" for m in r["selected"])))

    r = preflight.evaluate(root, "今天天气怎么样")
    cases.append(("no_module_block", r["decision"] == "block" and not r["selected"]))

    with tempfile.TemporaryDirectory(prefix="mod_gov_") as tmp:
        for name, obj in (("a.json", _fixture("AAA-001", ["壁厚"], "min_wall_mm", 1.5)),
                          ("b.json", _fixture("BBB-001", ["壁厚"], "min_wall_mm", 2.0))):
            with open(os.path.join(tmp, name), "w", encoding="utf-8") as fh:
                json.dump(obj, fh, ensure_ascii=False)
        r = preflight.evaluate(root, "壁厚检查", modules_dir=tmp)
        has_conflict = any(c["type"] == "data_value" for c in r["conflicts"])
        cases.append(("data_conflict_ask", r["decision"] == "ask" and has_conflict))

    with tempfile.TemporaryDirectory(prefix="mod_gov_missing_") as tmp:
        mod = _fixture("CCC-001", ["焊接"], "weld_leg_mm", 3.0)
        mod["data"] = []  # coverage 声明需要 weld_leg_mm，但模块没有该数据
        with open(os.path.join(tmp, "c.json"), "w", encoding="utf-8") as fh:
            json.dump(mod, fh, ensure_ascii=False)
        r = preflight.evaluate(root, "焊接过渡怎么处理", modules_dir=tmp)
        cases.append(("missing_data_ask", r["decision"] == "ask" and "weld_leg_mm" in r["missing"]))

    passed = sum(1 for _, ok in cases if ok)
    result = {"status": "pass" if passed == len(cases) else "fail",
              "passed": passed, "total": len(cases),
              "cases": [{"case": n, "pass": ok} for n, ok in cases]}
    print("MODULE_SELFTEST " + json.dumps(result, ensure_ascii=False))
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
