#!/usr/bin/env python3
"""envelope_check.py — ESD-001 acceptance checker.

Usage:
    python envelope_check.py spec.json

Spec (JSON):
{
  "driver": "impact_speed_mps",
  "base": {"value": 6.000, "anchor": "bottom_contact"},
  "exponent_p": 0.8,
  "tolerance_ratio": 0.10,
  "cutoff": {"v_min": 1.0, "amplitude_min": 0.03},
  "events": [
    {"id": "e1", "time": 20, "value": 6.000,
     "squash_depth": 0.28, "stretch": 0.075,
     "hold": 2, "tilt": 13.5, "window": 8},
    ...  # 按时间升序
  ]
}
"""
import json
import sys


def check_spec(spec):
    checks = []
    ev = spec["events"]
    required = ("squash_depth", "stretch", "hold", "tilt", "window")
    missing = [k for k in required if any(k not in e for e in ev)]
    if missing:
        raise ValueError("events missing envelope fields: %s" % ", ".join(missing))
    base = spec["base"]["value"]
    p = spec.get("exponent_p", 0.8)
    tol = spec.get("tolerance_ratio", 0.10)
    cut = spec.get("cutoff", {})
    v_min = cut.get("v_min", 0.0)
    amp_min = cut.get("amplitude_min", 0.0)
    anchor = spec["base"].get("anchor")

    # 1) monotonic non-increasing
    for key in ("squash_depth", "stretch", "hold", "tilt"):
        vals = [e[key] for e in ev]
        ok = all(vals[i + 1] <= vals[i] + 1e-3 for i in range(len(vals) - 1))
        checks.append({"check": "monotonic:" + key, "pass": ok,
                       "detail": vals})

    # 2) power-law ratio: A_i ≈ A_0 * (v_i/v_0)^p
    for key in ("squash_depth", "stretch"):
        a0 = ev[0][key]
        worst = 0.0
        detail = []
        for e in ev:
            if v_min and e["value"] < v_min:
                continue  # cutoff 事件参数允许归零，不参与幂律拟合
            s = min(1.0, max(0.0, e["value"] / base)) if base else 0.0
            expected = a0 * (s ** p)
            actual = e[key]
            rel = abs(actual - expected) / expected if expected > 1e-9 else 0.0
            worst = max(worst, rel)
            detail.append({"id": e["id"], "actual": actual,
                           "expected": round(expected, 4), "rel_err": round(rel, 3)})
        checks.append({"check": "power_law:" + key, "pass": worst <= tol,
                       "detail": detail, "worst_rel_err": round(worst, 3)})

    # 3) cutoff
    cutoff_ok = True
    for e in ev:
        if e["value"] < v_min and e["squash_depth"] > amp_min:
            cutoff_ok = False
    checks.append({"check": "cutoff", "pass": cutoff_ok,
                   "detail": {"v_min": v_min, "amplitude_min": amp_min}})

    # 4) window non-overlap
    overlap = []
    for i in range(len(ev) - 1):
        end = ev[i]["time"] + ev[i]["window"]
        if end >= ev[i + 1]["time"]:
            overlap.append({"a": ev[i]["id"], "b": ev[i + 1]["id"],
                            "end": end, "next": ev[i + 1]["time"]})
    checks.append({"check": "window_non_overlap", "pass": not overlap,
                   "detail": overlap})

    # 5) anchor consistency (per-event override not allowed)
    anchors = {e.get("anchor", anchor) for e in ev}
    checks.append({"check": "anchor_consistent", "pass": len(anchors) == 1,
                   "detail": sorted(a for a in anchors if a is not None)})

    # 6) manual: apex/free-flight must not contain pre-stretch/overshoot
    checks.append({"check": "no_deform_at_apex", "pass": None,
                   "detail": "manual: verify pre-stretch/overshoot keys are not inside free-flight windows"})

    status = "pass" if all(c["pass"] is not False for c in checks) else "fail"
    return {"status": status, "checks": checks}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python envelope_check.py spec.json")
        sys.exit(2)
    with open(sys.argv[1], encoding="utf-8-sig") as fh:
        spec = json.load(fh)
    result = check_spec(spec)
    print("ENVELOPE_CHECK " + json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result["status"] == "pass" else 1)
