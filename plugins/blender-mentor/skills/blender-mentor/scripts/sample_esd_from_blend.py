# -*- coding: utf-8 -*-
"""sample_esd_from_blend.py — 从 .blend 采样生成 ESD measured spec（Blender 4.2 / 5.x）。

用法：
    blender -b scene.blend --python sample_esd_from_blend.py -- \
        --config cfg.json --out spec.json
    blender -b --factory-startup --python sample_esd_from_blend.py -- --selftest [--out spec.json]

只读交付物的 fcurve / 形态键 / 骨骼 scale 生成 spec；event.value（driver）由 config 提供，
anchor 必须显式给。输出与 expand_esd_spec.py 同 schema，可直接喂 envelope_check.py。
输出：ESD_SAMPLE / ESD_SAMPLER_SELFTEST {json}；exit 0=ok，1=失败，2=参数错误。
"""
import hashlib
import json
import os
import sys

import bpy

TOOL_VERSION = "1.0.0"


def _parse_args(argv):
    opts = {"selftest": False, "blend": None, "config": None, "out": None}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--selftest":
            opts["selftest"] = True
            i += 1
        elif a in ("--blend", "--config", "--out") and i + 1 < len(argv):
            opts[a[2:]] = argv[i + 1]
            i += 2
        else:
            i += 1
    return opts


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _action_fcurves(action):
    out = []
    try:
        for layer in action.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    out.extend(cb.fcurves)
    except Exception:
        out.extend(getattr(action, "fcurves", []))
    return out


def _action_for(owner, name=None):
    if name:
        return bpy.data.actions.get(name)
    ad = getattr(owner, "animation_data", None)
    if not ad:
        return None
    if ad.action:
        return ad.action
    for track in ad.nla_tracks:
        if getattr(track, "mute", False):
            continue
        for strip in track.strips:
            if getattr(strip, "mute", False):
                continue
            return getattr(strip, "action", None)
    return None


def _new_action(owner, name):
    """返回 (action, fcurve 容器)；4.2 legacy 与 5.x layered 都支持。"""
    act = bpy.data.actions.new(name)
    if hasattr(act, "layers") and hasattr(act, "slots"):
        slot = act.slots.new(id_type="OBJECT", name=owner.name)
        layer = act.layers.new("L")
        strip = layer.strips.new(type="KEYFRAME")
        return act, strip.channelbag(slot, ensure=True)
    return act, act


def _resolve_channel(cfg, key="channel"):
    ch = cfg.get(key)
    if not ch:
        return None
    typ = ch.get("type")
    obj_name = ch.get("object")
    obj = bpy.data.objects.get(obj_name) if obj_name else None
    if obj is None:
        raise ValueError("object not found: %s" % obj_name)
    identity = float(ch.get("identity", 1.0 if typ in ("object_scale", "bone_scale") else 0.0))
    if typ == "object_scale":
        owner, path, idx = obj, "scale", int(ch.get("index", 2))
    elif typ == "shape_key":
        sk = getattr(getattr(obj, "data", None), "shape_keys", None)
        if sk is None:
            raise ValueError("object has no shape keys: %s" % obj_name)
        owner = sk
        path = 'key_blocks["%s"].value' % ch.get("key", "")
        idx = 0
    elif typ == "bone_scale":
        owner = obj
        path = 'pose.bones["%s"].scale' % ch.get("bone", "hips")
        idx = int(ch.get("index", 2))
    else:
        raise ValueError("unsupported channel type: %r" % typ)
    act = _action_for(owner, cfg.get("action"))
    if act is None:
        raise ValueError("no action found on %s (pass config.action)" % obj_name)
    for fc in _action_fcurves(act):
        if fc.data_path == path and fc.array_index == idx:
            return {"fcurve": fc, "identity": identity, "path": path,
                    "action": act.name, "object": obj_name, "index": idx}
    raise ValueError("fcurve not found: %s[%d]" % (path, idx))


def _frames(start, end):
    lo = int(round(start))
    hi = int(round(end))
    return list(range(lo, hi + 1))


def _measure_event(fc, identity, event, hold_eps):
    time = float(event["time"])
    seg = event.get("segments") or {}
    pre = _frames(*(seg.get("pre") or [time - 2, time - 1]))
    peak = _frames(*(seg.get("peak") or [time, time + 1]))
    settle = _frames(*(seg.get("settle") or [time + 2, time + 4]))
    pre_vals = [fc.evaluate(f) for f in pre]
    peak_vals = [fc.evaluate(f) for f in peak]
    stretch = max([v - identity for v in pre_vals] or [0.0])
    squash = identity - min(peak_vals)
    peak_frame = peak[peak_vals.index(min(peak_vals))]
    hold = 0
    for f in peak + settle:
        v = fc.evaluate(f)
        if abs(v - min(peak_vals)) <= hold_eps:
            hold += 1
        elif f > peak_frame:
            break
    return {
        "pre_frames": pre,
        "peak_frames": peak,
        "settle_frames": settle,
        "stretch": round(max(0.0, stretch), 4),
        "squash_depth": round(max(0.0, squash), 4),
        "hold": hold,
        "window": settle[-1] - pre[0] + 1,
        "peak_value": round(min(peak_vals), 4),
        "identity": identity,
    }


def measure(cfg):
    ch = _resolve_channel(cfg)
    tilt = _resolve_channel(cfg, "tilt_channel")
    hold_eps = float(cfg.get("hold_eps", 1e-3))
    events = []
    for ev in cfg.get("events", []):
        m = _measure_event(ch["fcurve"], ch["identity"], ev, hold_eps)
        tilt_amp = 0.0
        if tilt:
            tilt_vals = [tilt["fcurve"].evaluate(int(round(f))) for f in m["peak_frames"]]
            tilt_amp = max([abs(v - tilt["identity"]) for v in tilt_vals] or [0.0])
        events.append({"id": ev["id"], "time": float(ev["time"]),
                       "value": float(ev["value"]),
                       "squash_depth": m["squash_depth"],
                       "stretch": m["stretch"], "hold": int(m["hold"]),
                       "tilt": round(tilt_amp, 2), "window": int(m["window"])})
        m["tilt"] = round(tilt_amp, 2)
        ev["_measured"] = m
    return events, ch, tilt


def build_spec(cfg, events, ch):
    base = cfg.get("base") or {}
    base_value = base.get("value") if isinstance(base, dict) else base
    if base_value is None:
        raise ValueError("config.base.value is required")
    spec = {
        "driver": cfg.get("driver", "impact_speed_mps"),
        "base": {"value": float(base_value),
                 "anchor": cfg.get("anchor", (base or {}).get("anchor", "bottom_contact"))},
        "exponent_p": float(cfg.get("exponent_p", 0.8)),
        "tolerance_ratio": float(cfg.get("tolerance_ratio", 0.10)),
        "events": events,
    }
    if "cutoff" in cfg:
        spec["cutoff"] = cfg["cutoff"]
    spec["_measurement"] = {
        "tool": "sample_esd_from_blend.py",
        "version": TOOL_VERSION,
        "source": "fcurve",
        "channel": {"type": cfg["channel"]["type"], "object": ch["object"],
                    "path": ch["path"], "index": ch["index"]},
        "action": ch["action"],
        "blend": os.path.abspath(cfg.get("_blend", "")),
        "blend_sha256": cfg.get("_blend_sha256", ""),
        "events": [{"id": e["id"], "time": e["time"], "value": e["value"],
                    "pre_frames": ev["pre_frames"], "peak_frames": ev["peak_frames"],
                    "settle_frames": ev["settle_frames"]}
                   for e, ev in zip(events, [x["_measured"] for x in cfg["events"]])],
    }
    return spec


def _selftest():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    obj = bpy.data.objects.new("Ball", None)
    bpy.context.scene.collection.objects.link(obj)
    obj.animation_data_create()
    act, bag = _new_action(obj, "__t_scale")
    if hasattr(bag, "fcurves"):
        fc = bag.fcurves.new("scale", index=2)
    else:
        fc = bag.new("scale", index=2)
    values = {20: 1.075, 21: 1.075, 22: 0.72, 23: 0.72,
              24: 1.0, 25: 1.0, 26: 1.0, 27: 1.0, 28: 1.0}
    for frame, value in values.items():
        kp = fc.keyframe_points.insert(frame, value)
        kp.interpolation = "LINEAR"
    obj.animation_data.action = act
    cfg = {
        "base": {"value": 6.26, "anchor": "bottom_contact"},
        "driver": "impact_speed_mps",
        "exponent_p": 0.8,
        "tolerance_ratio": 0.10,
        "channel": {"type": "object_scale", "object": "Ball", "index": 2, "identity": 1.0},
        "events": [{"id": "e1", "time": 22, "value": 6.26,
                    "segments": {"pre": [20, 21], "peak": [22, 23],
                                 "settle": [24, 28]}}],
        "_blend": "selftest",
        "_blend_sha256": "selftest",
    }
    events, ch, _tilt = measure(cfg)
    e = events[0]
    checks = {
        "squash_depth": {"want": 0.28, "got": e["squash_depth"], "ok": abs(e["squash_depth"] - 0.28) <= 0.001},
        "stretch": {"want": 0.075, "got": e["stretch"], "ok": abs(e["stretch"] - 0.075) <= 0.001},
        "hold": {"want": 2, "got": e["hold"], "ok": e["hold"] == 2},
        "window": {"want": 9, "got": e["window"], "ok": e["window"] == 9},
    }
    spec = build_spec(cfg, events, ch)
    return spec, checks


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opts = _parse_args(argv)
    if opts["selftest"]:
        try:
            spec, checks = _selftest()
        except Exception as exc:  # noqa: BLE001
            print("ESD_SAMPLER_SELFTEST " + json.dumps(
                {"status": "fail", "error": type(exc).__name__ + ": " + str(exc)},
                ensure_ascii=False))
            return 1
        if opts["out"]:
            with open(opts["out"], "w", encoding="utf-8", newline="\n") as fh:
                json.dump(spec, fh, ensure_ascii=False, indent=2)
        ok = all(c["ok"] for c in checks.values())
        print("ESD_SAMPLER_SELFTEST " + json.dumps(
            {"status": "pass" if ok else "fail",
             "blender": bpy.app.version_string, "checks": checks,
             "spec_event": spec["events"][0] if spec.get("events") else None},
            ensure_ascii=False))
        return 0 if ok else 1
    if not opts["config"]:
        print("ESD_SAMPLE " + json.dumps(
            {"status": "fail", "error": "usage: --config cfg.json [--blend scene.blend] [--out spec.json]"},
            ensure_ascii=False))
        return 2
    try:
        with open(opts["config"], encoding="utf-8") as fh:
            cfg = json.load(fh)
        blend = opts["blend"] or cfg.get("blend")
        if blend:
            bpy.ops.wm.open_mainfile(filepath=os.path.abspath(blend))
            cfg["_blend"] = os.path.abspath(blend)
            cfg["_blend_sha256"] = _sha256(os.path.abspath(blend))
        bpy.context.view_layer.update()
        events, ch, _tilt = measure(cfg)
        spec = build_spec(cfg, events, ch)
        if opts["out"]:
            with open(opts["out"], "w", encoding="utf-8", newline="\n") as fh:
                json.dump(spec, fh, ensure_ascii=False, indent=2)
        print("ESD_SAMPLE " + json.dumps(
            {"status": "ok", "out": opts["out"], "events": len(events),
             "blender": bpy.app.version_string,
             "source": spec["_measurement"]["source"]}, ensure_ascii=False))
        return 0
    except Exception as exc:  # noqa: BLE001
        print("ESD_SAMPLE " + json.dumps(
            {"status": "fail", "error": type(exc).__name__ + ": " + str(exc)},
            ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
