# -*- coding: utf-8 -*-
"""engineering_regression.py — ENG-001 回归测试（纯标准库 + Blender 子进程）。

用法：
    python scripts/engineering_regression.py --blender /path/to/blender
    python scripts/engineering_regression.py --update --blender /path/to/blender

fixtures: tests/engineering/fixtures/*.blend
configs:  tests/engineering/configs/<case>.json
expected: tests/engineering/expected/<case>.json

输出：ENGINEERING_REGRESSION {json}；exit 0=pass，1=fail，2=参数/环境错误。
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TESTS = os.path.join(ROOT, "tests", "engineering")
CHECK = os.path.join(HERE, "engineering_check.py")

COMPARE_KEYS = [
    "status", "fails", "warns",
    "stable", "margin_mm", "wall_min_mm",
    "draft_by_side", "draft_low_area_pct", "draft_undercut_area_pct",
    "overhang_bad_faces", "overhang_area_mm2", "support_volume_mm3_est",
    "interference_pairs", "proxy_skipped",
]


def _argv():
    out = {"root": ROOT, "blender": None, "update": False, "case": None}
    argv = list(sys.argv[1:])
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--root" and i + 1 < len(argv):
            out["root"] = os.path.abspath(argv[i + 1]); i += 2
        elif a == "--blender" and i + 1 < len(argv):
            out["blender"] = argv[i + 1]; i += 2
        elif a == "--update":
            out["update"] = True; i += 1
        elif a == "--case" and i + 1 < len(argv):
            out["case"] = argv[i + 1]; i += 2
        else:
            i += 1
    return out


def find_blender(explicit):
    if explicit:
        return explicit
    env = os.environ.get("BLENDER_BIN")
    if env:
        return env
    found = shutil.which("blender") or shutil.which("blender.exe")
    if found:
        return found
    candidates = [
        r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
        r"C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe",
        "/Applications/Blender.app/Contents/MacOS/Blender",
        "/usr/bin/blender",
        "/usr/local/bin/blender",
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def pick(data):
    s = data.get("summary", {}) if isinstance(data, dict) else {}
    pairs = []
    for p in s.get("interference_pairs", []):
        pairs.append([p.get("a"), p.get("b"), p.get("faces")])
    return {
        "status": data.get("status"),
        "fails": data.get("fails"),
        "warns": data.get("warns"),
        "stable": s.get("stable"),
        "margin_mm": s.get("margin_mm"),
        "wall_min_mm": s.get("wall_min_mm"),
        "draft_by_side": s.get("draft_by_side"),
        "draft_low_area_pct": s.get("draft_low_area_pct"),
        "draft_undercut_area_pct": s.get("draft_undercut_area_pct"),
        "overhang_bad_faces": s.get("overhang_bad_faces"),
        "overhang_area_mm2": s.get("overhang_area_mm2"),
        "support_volume_mm3_est": s.get("support_volume_mm3_est"),
        "interference_pairs": pairs,
        "proxy_skipped": s.get("proxy_skipped"),
    }


def close(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= max(0.05, abs(b) * 0.02)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return False
        return all(close(a[k], b[k]) for k in a)
    return a == b


def diff(expected, actual, path=""):
    issues = []
    if isinstance(expected, dict) and isinstance(actual, dict):
        for k in sorted(set(expected) | set(actual)):
            if k not in expected:
                issues.append("%s.%s unexpected" % (path, k))
            elif k not in actual:
                issues.append("%s.%s missing" % (path, k))
            else:
                issues.extend(diff(expected[k], actual[k], path + "." + k))
    elif isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            issues.append("%s length %d != %d" % (path, len(expected), len(actual)))
        else:
            for i, (e, a) in enumerate(zip(expected, actual)):
                issues.extend(diff(e, a, "%s[%d]" % (path, i)))
    elif not close(actual, expected):
        issues.append("%s %r != expected %r" % (path, actual, expected))
    return issues


def main():
    args = _argv()
    root = args["root"]
    tests = os.path.join(root, "tests", "engineering")
    fixtures = os.path.join(tests, "fixtures")
    configs = os.path.join(tests, "configs")
    expected_dir = os.path.join(tests, "expected")
    os.makedirs(expected_dir, exist_ok=True)
    if not os.path.isdir(fixtures):
        print("ENGINEERING_REGRESSION " + json.dumps(
            {"status": "fail", "error": "missing fixtures: " + fixtures}, ensure_ascii=False))
        return 2
    blender = find_blender(args["blender"])
    if not blender:
        print("ENGINEERING_REGRESSION " + json.dumps(
            {"status": "error", "error": "Blender not found; pass --blender"}, ensure_ascii=False))
        return 2
    check_script = os.path.join(root, "scripts", "engineering_check.py")
    cases = []
    failures = []
    for fname in sorted(os.listdir(fixtures)):
        if not fname.endswith(".blend"):
            continue
        case = os.path.splitext(fname)[0]
        if args["case"] and case != args["case"]:
            continue
        cfg = os.path.join(configs, case + ".json")
        if not os.path.isfile(cfg):
            failures.append({"case": case, "error": "missing config"})
            continue
        expected_path = os.path.join(expected_dir, case + ".json")
        with tempfile.TemporaryDirectory(prefix="eng_reg_") as tmp:
            out_json = os.path.join(tmp, "out.json")
            cmd = [blender, "-b", os.path.join(fixtures, fname),
                   "--python", check_script, "--",
                   "--config", cfg, "--json", out_json]
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=240)
            if not os.path.isfile(out_json):
                failures.append({"case": case, "error": "no json output",
                                 "stderr": (proc.stderr or "")[-500:]})
                continue
            actual = pick(json.load(open(out_json, encoding="utf-8")))
        if args["update"]:
            with open(expected_path, "w", encoding="utf-8") as fh:
                json.dump(actual, fh, ensure_ascii=False, indent=2, sort_keys=True)
            cases.append({"case": case, "status": "updated"})
            continue
        if not os.path.isfile(expected_path):
            failures.append({"case": case, "error": "missing expected; run --update"})
            continue
        expected = json.load(open(expected_path, encoding="utf-8"))
        issues = diff(expected, actual)
        cases.append({"case": case, "status": "pass" if not issues else "fail",
                      "diff": issues[:8]})
        if issues:
            failures.append({"case": case, "issues": issues[:8]})
    status = "pass" if not failures else "fail"
    result = {"status": status, "blender": blender, "cases": cases,
              "updated": args["update"], "failures": failures}
    print("ENGINEERING_REGRESSION " + json.dumps(result, ensure_ascii=False))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
