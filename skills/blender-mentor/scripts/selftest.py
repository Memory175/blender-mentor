# -*- coding: utf-8 -*-
"""selftest.py — scripts 纯 Python 自检（lint + ESD 展开 + envelope 衔接）。

用法：
    python scripts/selftest.py [套件目录]
    # 技能目录默认 scripts 的上一级

输出：TOOLS_SELFTEST {json}；exit 0=pass，1=fail。
"""
import json
import os
import re
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)


def _load(name, path):
    ns = {"__name__": name, "__file__": path}
    with open(path, encoding="utf-8") as fh:
        exec(compile(fh.read(), path, "exec"), ns)
    return ns


def _check(checks, name, passed, detail=""):
    checks.append({"check": name, "pass": bool(passed), "detail": detail})


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    root = argv[0] if argv and not argv[0].startswith("-") else ROOT
    checks = []

    lint = _load("lint_tool", os.path.join(TOOLS, "persona_lint.py"))
    expand = _load("expand_tool", os.path.join(TOOLS, "expand_esd_spec.py"))

    # 1) lint: real deny pattern -> pass
    tmpdir = tempfile.mkdtemp(prefix="persona_selftest_")
    deny_ok = os.path.join(tmpdir, "deny.txt")
    with open(deny_ok, "w", encoding="utf-8") as fh:
        fh.write("# selftest\n__SELFTEST_NO_SUCH_TOKEN__\n")
    res_ok = lint["lint"](root, deny_ok)
    _check(checks, "lint_with_deny", res_ok["status"] == "pass",
           {c["check"]: c["pass"] for c in res_ok["checks"]})

    # 2) lint: template deny must fail (placeholder detection)
    res_example = lint["lint"](root, os.path.join(ROOT, "assets", "deny.example.txt"))
    _check(checks, "lint_placeholder_rejected", res_example["status"] == "fail",
           [c.get("error") for c in res_example["checks"] if not c["pass"]])

    # 2.1) 标准布局下 toolbox 已剥离代码，内嵌版等价性检查无法执行：记为 skip，不计入 pass
    checks.append({"check": "lint_equivalence", "skip": True, "pass": None,
                   "detail": "disabled: toolbox_text.md has no embedded code (standard layout)"})

    # 3) expand template -> params + envelope_check pass
    with open(os.path.join(ROOT, "assets", "esd_spec.template.json"), encoding="utf-8") as fh:
        template = json.load(fh)
    spec = expand["expand"](template, 6.0)
    keys_ok = all(k in spec["events"][0] for k in
                  ("squash_depth", "stretch", "hold", "tilt", "window"))
    _check(checks, "expand_has_envelope_params", keys_ok, sorted(spec["events"][0]))
    try:
        env = _load("env", os.path.join(TOOLS, "envelope_check.py"))
        env_result = env["check_spec"](spec)
        _check(checks, "expanded_spec_passes_envelope",
               env_result["status"] == "pass",
               {c["check"]: c["pass"] for c in env_result["checks"]})
    except Exception as exc:  # noqa: BLE001
        _check(checks, "expanded_spec_passes_envelope", False,
               type(exc).__name__ + ": " + str(exc))

    # 4) cutoff event -> params zeroed
    cut = json.loads(json.dumps(template))
    cut["events"] = [{"id": "e1", "time": 10, "value": "0.1*v0"}]
    spec_cut = expand["expand"](cut, 6.0)
    _check(checks, "cutoff_zeroed",
           spec_cut["events"][0]["squash_depth"] == 0
           and spec_cut["events"][0]["window"] == 0,
           spec_cut["events"][0])

    # 5) load router: plan valid / triggers / budget trim
    plan_path = os.path.join(ROOT, "assets", "load_plan.json")
    router_path = os.path.join(TOOLS, "load_router.py")
    _check(checks, "load_plan_exists",
           os.path.isfile(plan_path) and os.path.isfile(router_path))
    try:
        with open(plan_path, encoding="utf-8") as fh:
            plan = json.load(fh)
        _check(checks, "load_plan_schema",
               all(k in plan for k in ("always", "on_demand", "modules", "policy")))
        router = {"__name__": "load_router_tool", "__file__": router_path}
        exec(compile(open(router_path, encoding="utf-8").read(), router_path, "exec"),
             router)
        r1 = router["route"]("人体走路循环动画，需要验收脚本")
        files1 = [f["file"] for f in r1["files"]]
        _check(checks, "router_bio_task",
               any("module-biomechanics" in f for f in files1)
               and any("toolbox" in f for f in files1)
               and r1["tokens_est"] > 0, files1)
        r2 = router["route"]("教学备课：M3 动画")
        _check(checks, "router_curriculum_task",
               any("curriculum" in f["file"] for f in r2["files"]),
               [f["file"] for f in r2["files"]])
        r3 = router["route"]("弹跳次级动画，包络验收", budget=20000)
        _check(checks, "router_budget_trim",
               r3["over_budget"] is False
               and any("toolbox" in d["file"] for d in r3["dropped"]),
               {"tokens": r3["tokens_est"], "dropped": r3["dropped"]})
        r4 = router["route"]("跑脚本")
        files4 = [f["file"] for f in r4["files"]]
        _check(checks, "router_script_no_bio",
               not any("module-biomechanics" in f for f in files4), files4)
        r5 = router["route"]("帮我跑一下资产门脚本")
        files5 = [f["file"] for f in r5["files"]]
        _check(checks, "router_tool_no_bio",
               not any("module-biomechanics" in f for f in files5), files5)
        r6 = router["route"]("跑步循环验收")
        _check(checks, "router_running_loads_bio",
               any("module-biomechanics" in f["file"] for f in r6["files"]),
               [f["file"] for f in r6["files"]])
        r7 = router["route"]("这个马克杯能注塑吗？壁厚和拔模帮我审一下")
        _check(checks, "router_engineering_task",
               any("module-engineering" in f["file"] for f in r7["files"]),
               [f["file"] for f in r7["files"]])
        r8 = router["route"]("焊接过渡怎么处理")
        r9 = router["route"]("这个马克杯能注塑吗？壁厚和拔模帮我审一下")
        _check(checks, "router_preflight_gate",
               r8["modules_allowed"] is False
               and not any("module-engineering" in f["file"] for f in r8["files"])
               and r9["modules_allowed"] is True
               and any("module-engineering" in f["file"] for f in r9["files"]),
               {"weld": r8["modules_allowed"], "mug": r9["modules_allowed"]})
        r10 = router["route"]("建模入门")
        _check(checks, "router_core_task",
               r10["status"] == "ok" and r10["core_allowed"] is True
               and r10["modules_allowed"] is False
               and not any(f.get("kind") == "module" for f in r10["files"]),
               {"status": r10["status"], "modules": r10["modules_allowed"]})
        r11 = router["route"]("Review this walk cycle")
        _check(checks, "router_english_bio",
               any("module-biomechanics" in f["file"] for f in r11["files"]),
               [f["file"] for f in r11["files"]])
        eng_path = os.path.join(TOOLS, "engineering_check.py")
        try:
            compile(open(eng_path, encoding="utf-8").read(), eng_path, "exec")
            _check(checks, "engineering_script_compiles", True)
        except Exception as exc:  # noqa: BLE001
            _check(checks, "engineering_script_compiles", False, str(exc))
        reg_dir = os.path.join(root, "tests", "engineering")
        if not os.path.isdir(reg_dir):
            checks.append({"check": "engineering_regression_assets", "skip": True, "pass": None,
                           "detail": "tests/engineering not shipped; regression is optional"})
        else:
            fixtures = os.path.join(reg_dir, "fixtures")
            expected = os.path.join(reg_dir, "expected")
            try:
                fixtures_ok = os.path.isdir(fixtures) and any(
                    f.endswith(".blend") for f in os.listdir(fixtures))
                expected_ok = os.path.isdir(expected) and any(
                    f.endswith(".json") for f in os.listdir(expected))
                for f in os.listdir(expected) if expected_ok else []:
                    if f.endswith(".json"):
                        json.load(open(os.path.join(expected, f), encoding="utf-8"))
                _check(checks, "engineering_regression_assets", fixtures_ok and expected_ok,
                       {"fixtures": os.path.isdir(fixtures), "expected": expected_ok})
            except Exception as exc:  # noqa: BLE001
                _check(checks, "engineering_regression_assets", False, str(exc))
        # 2.5) 模块治理：格式 lint + 预审决策
        try:
            ml = _load("module_lint", os.path.join(TOOLS, "module_lint.py"))
            lint_result = ml["run"](root)
            _check(checks, "module_governance_lint",
                   lint_result["status"] in ("pass", "warn"),
                   {"status": lint_result["status"], "problems": lint_result["problems"][:5]})
            pf = _load("preflight", os.path.join(TOOLS, "preflight.py"))
            decisions = {
                "eng": pf["evaluate"](root, "马克杯能注塑吗？壁厚和拔模审一下")["decision"],
                "weld": pf["evaluate"](root, "焊接过渡怎么处理")["decision"],
                "none": pf["evaluate"](root, "今天天气怎么样")["decision"],
            }
            _check(checks, "module_preflight_gate",
                   decisions["eng"] == "proceed" and decisions["weld"] == "block" and decisions["none"] == "block",
                   decisions)
            mg_gap = _load("module_gap", os.path.join(TOOLS, "module_gap.py"))
            house = mg_gap["evaluate"](root, "我想建模一个房子")
            _check(checks, "module_gap_response",
                   house["action"] == "fill_module" and house["gap"]["id"] == "ARC-001"
                   and "ARC-001" in house["prompt"] and len(house["merge_steps"]) >= 5,
                   {"action": house["action"], "gap": house.get("gap", {}).get("id"),
                    "steps": len(house.get("merge_steps", []))})
            ac = _load("audit_claims", os.path.join(TOOLS, "audit_claims.py"))
            claim_dir = os.path.join(root, "tests", "module_governance", "claims")
            if not os.path.isdir(claim_dir):
                checks.append({"check": "claim_audit_gate", "skip": True, "pass": None,
                               "detail": "tests/module_governance not shipped; claim audit fixtures optional"})
            else:
                pf_data = json.load(open(os.path.join(claim_dir, "preflight_eng.json"), encoding="utf-8"))
                good = ac["audit"](open(os.path.join(claim_dir, "good.md"), encoding="utf-8").read(), pf_data)
                bad = ac["audit"](open(os.path.join(claim_dir, "uncited.md"), encoding="utf-8").read(), pf_data)
                dangling = ac["audit"](open(os.path.join(claim_dir, "dangling.md"), encoding="utf-8").read(), pf_data)
                _check(checks, "claim_audit_gate",
                       good["status"] == "pass" and bad["status"] == "fail" and bool(bad["uncited"])
                       and dangling["status"] == "fail" and bool(dangling["dangling"]),
                       {"good": good["status"], "uncited": len(bad["uncited"]), "dangling": len(dangling["dangling"])})
                core_pf = json.load(open(os.path.join(claim_dir, "preflight_core.json"), encoding="utf-8"))
                core = ac["audit"](open(os.path.join(claim_dir, "teaching.md"), encoding="utf-8").read(), core_pf)
                _check(checks, "claim_audit_core_skip",
                       core["status"] == "skipped", {"core": core["status"]})
        except Exception as exc:  # noqa: BLE001
            _check(checks, "module_governance_lint", False, str(exc))
            _check(checks, "module_preflight_gate", False, str(exc))
        cfg_path = os.path.join(root, "assets", "esd_sample_config.template.json")
        try:
            cfg = json.load(open(cfg_path, encoding="utf-8"))
            _check(checks, "esd_sample_config_schema",
                   all(k in cfg for k in ("base", "channel", "events"))
                   and all("segments" in e for e in cfg["events"]),
                   sorted(cfg.keys()))
        except Exception as exc:  # noqa: BLE001
            _check(checks, "esd_sample_config_schema", False, str(exc))
    except Exception as exc:  # noqa: BLE001
        _check(checks, "load_router", False, type(exc).__name__ + ": " + str(exc))

    active = [c for c in checks if not c.get("skip")]
    result = {"status": "pass" if all(c["pass"] for c in active) else "fail",
              "passed": sum(1 for c in active if c["pass"]),
              "total": len(active),
              "skipped": [c["check"] for c in checks if c.get("skip")],
              "checks": checks}
    print("TOOLS_SELFTEST " + json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
