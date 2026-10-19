# -*- coding: utf-8 -*-
"""expand_esd_spec.py — 把 ESD 模板展开成可执行 JSON spec（项目侧工具）。

用法：
    python expand_esd_spec.py template.json --base 6.0 -o spec.json

模板支持：
    "value": 1.25          # 已是数值，原样保留
    "value": "v0"          # -> base
    "value": "0.707*v0"    # -> 0.707 * base
    "params0": {...}       # 可选：基准包络参数，按 k=(v/v0)^p 缩放到每个事件

输出最后一行：ESD_EXPAND {json}；exit 0=ok，1=失败，2=参数错误。
"""
import json
import re
import sys

_EXPR = re.compile(r"^\s*(?:(\d+(?:\.\d+)?)\s*\*\s*)?v0\s*$")
_PARAM_KEYS = ("squash_depth", "stretch", "hold", "tilt", "window")


def _expand_value(value, base):
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        raise ValueError("unsupported value type: %r" % (value,))
    m = _EXPR.match(value)
    if not m:
        raise ValueError("unsupported expression: %r" % value)
    factor = float(m.group(1)) if m.group(1) else 1.0
    return factor * base


def _scale_params(params0, k):
    out = {
        "squash_depth": round(params0["squash_depth"] * k, 4),
        "stretch": round(params0["stretch"] * k, 4),
        "hold": int(round(params0["hold"] * k)),
        "tilt": round(params0["tilt"] * k, 2),
        "window": max(2, min(int(params0["window"]), int(round(params0["window"] * k)))),
    }
    return out


def expand(spec, base):
    out = json.loads(json.dumps(spec))  # deep copy
    out.setdefault("base", {})["value"] = base
    p = float(spec.get("exponent_p", 0.8))
    params0 = spec.get("params0")
    if params0 is not None:
        missing = [k for k in _PARAM_KEYS if k not in params0]
        if missing:
            raise ValueError("params0 missing keys: %s" % ", ".join(missing))
    events = out.get("events", [])
    v_min = (spec.get("cutoff") or {}).get("v_min")
    for idx, event in enumerate(events):
        v = _expand_value(event.get("value"), base)
        event["value"] = v
        if params0 is None:
            continue
        s = min(1.0, max(0.0, v / base)) if base else 0.0
        k = s ** p
        event.update(_scale_params(params0, k))
        if v_min is not None and v < v_min:
            for key in _PARAM_KEYS:
                event[key] = 0
            continue
        if idx + 1 < len(events):
            gap = events[idx + 1]["time"] - event["time"] - 1
            event["window"] = max(1, min(event["window"], gap))
    return out


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    path, out_path, base = None, None, None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--base" and i + 1 < len(argv):
            base = float(argv[i + 1])
            i += 2
        elif a in ("-o", "--out") and i + 1 < len(argv):
            out_path = argv[i + 1]
            i += 2
        elif not a.startswith("-"):
            path = a
            i += 1
        else:
            i += 1
    if not path or base is None:
        print("ESD_EXPAND " + json.dumps(
            {"status": "fail", "error": "usage: expand_esd_spec.py template.json --base B -o out.json"},
            ensure_ascii=False))
        return 2
    try:
        with open(path, encoding="utf-8") as fh:
            spec = json.load(fh)
        expanded = expand(spec, base)
        out_path = out_path or "esd_spec.json"
        with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(expanded, fh, ensure_ascii=False, indent=2)
    except (OSError, ValueError, KeyError) as exc:
        print("ESD_EXPAND " + json.dumps(
            {"status": "fail", "error": type(exc).__name__ + ": " + str(exc)},
            ensure_ascii=False))
        return 1
    print("ESD_EXPAND " + json.dumps(
        {"status": "ok", "base": base, "events": len(expanded.get("events", [])),
         "with_params": bool(spec.get("params0")), "out": out_path},
        ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
