"""biomech_check.py — BIO-001 acceptance (run inside Blender)

用法（采样区间由项目侧传入，人设文件不写死帧号）：
    blender -b file.blend --python biomech_check.py -- \
        --eccentric F0,F1 --support A-B;C-D \
        [--airtime TAKEOFF,LAND --height H] [--driver-binding] \
        [--rig NAME] [--bone hips] [--action NAME] \
        [--hips-min-mm 20] [--subframe 1.0] [--tol-frames 1]

未提供某检查的参数时对应项返回 skipped，整体 status=incomplete；fail / incomplete 退出码均为 1。
--hips-min-mm 默认 20（2 cm，与 BIO-001 §2.2/§6.3 一致）；--subframe <1 时离心段按亚帧采样。
Action 搜索顺序：`--action` 指定名 > 当前 Action > NLA strips；均未命中才报 curve not found。
NLA strip 按 `frame_start / scale / action_frame_start` 映射到 action 帧；repeat != 1 按 action 长度取模循环；静音 track/strip 跳过；use_animated_time 无法可靠映射，显式列入 `skipped_candidates` 并提示先烘焙为 Action。
"""
import bpy
import json
import math
import sys


def fcurves(action):
    out = []
    try:
        for layer in action.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    out.extend(cb.fcurves)
    except Exception:
        out.extend(getattr(action, "fcurves", []))
    return out


def all_fcurves():
    for act in bpy.data.actions:
        for fc in fcurves(act):
            yield act, fc


def check_manual_shapekeys():
    hits = []
    for act, fc in all_fcurves():
        if fc.data_path.startswith('key_blocks[') and fc.data_path.endswith('.value'):
            if len(fc.keyframe_points) > 0:
                hits.append({"action": act.name, "path": fc.data_path,
                             "frames": [round(k.co.x, 2) for k in fc.keyframe_points]})
    # 形态键自身 animation_data 的 drivers / action
    for sk in bpy.data.shape_keys:
        ad = sk.animation_data
        if not ad:
            continue
        drivers = {d.data_path for d in ad.drivers}
        for kb in sk.key_blocks:
            path = f'key_blocks["{kb.name}"].value'
            if path not in drivers and kb.value != 0:
                hits.append({"shape_key": kb.name, "has_driver": False, "value": round(kb.value, 4)})
    return hits


def _candidate_actions(arm, action_name=None):
    """返回 [(action, mapping, source, note)]；note 非空 = 未覆盖，调用方必须 skip。

    搜索顺序：--action 指定名 > 当前 Action > NLA strips。
    NLA strip 用 frame_start / scale / action_frame_start 做帧映射；
    repeat != 1 时按 action 长度取模循环；use_animated_time 无法可靠映射，note 记录原因。
    """
    if action_name:
        act = bpy.data.actions.get(action_name)
        return [(act, lambda f: f, "action:%s" % action_name, "")] if act else []
    found = []
    ad = arm.animation_data
    if not ad:
        return found
    if ad.action:
        found.append((ad.action, lambda f: f, "active_action", ""))
    for track in ad.nla_tracks:
        if getattr(track, "mute", False):
            continue
        for strip in track.strips:
            if getattr(strip, "mute", False):
                continue
            act = getattr(strip, "action", None)
            if not act:
                continue
            if getattr(strip, "use_animated_time", False):
                found.append((act, None, "nla:%s" % strip.name,
                              "use_animated_time not covered; bake NLA to Action"))
                continue
            scale = strip.scale or 1.0
            start = strip.frame_start
            end = strip.frame_end
            action_start = strip.action_frame_start
            action_end = strip.action_frame_end
            action_len = action_end - action_start
            repeat = getattr(strip, "repeat", 1.0) or 1.0
            if abs(repeat - 1.0) > 1e-6 and action_len > 1e-6:
                # depsgraph 定标：周期 = action_len；strip 末帧取 action_end
                mapping = (lambda f, _s=scale, _st=start, _en=end, _a=action_start,
                           _ae=action_end, _len=action_len:
                           _ae if abs(f - _en) < 1e-6
                           else _a + (((f - _st) / _s) % _len))
            else:
                mapping = (lambda f, _s=scale, _st=start, _a=action_start:
                           _a + (f - _st) / _s)
            found.append((act, mapping, "nla:%s" % strip.name, ""))
    return found


def check_eccentric(arm, f_start, f_end, bone="hips", data_path="location", idx=2,
                    action_name=None, step=1.0):
    """末端 3 帧：斜率单调递减且不归零；Action 与 NLA strip 均纳入搜索（含帧映射）。

    step < 1.0 时按亚帧采样（如 0.25 = 每 1/4 帧一个样本）。
    """
    path = f'pose.bones["{bone}"].{data_path}'
    skipped = []
    for act, mapping, source, note in _candidate_actions(arm, action_name):
        if note:
            skipped.append({"source": source, "reason": note})
            continue
        for fc in fcurves(act):
            if fc.data_path != path or fc.array_index != idx:
                continue
            if step <= 0:
                return {"pass": False, "reason": "subframe step must be > 0"}
            n = int(round((f_end - f_start) / step)) + 1
            if n < 3:
                return {"pass": False, "reason": "range too short (<3 samples)"}
            frames = [f_start + i * step for i in range(n)]
            values = [fc.evaluate(mapping(f)) for f in frames]
            slopes = [values[i + 1] - values[i] for i in range(len(values) - 1)]
            tail = slopes[-3:]
            ok = (all(tail[i] >= tail[i + 1] for i in range(len(tail) - 1))
                  and abs(tail[-1]) > 1e-5)
            result = {"pass": bool(ok), "action": act.name, "source": source,
                      "tail_slopes": [round(x, 6) for x in tail]}
            if skipped:
                result["skipped_candidates"] = skipped
            return result
    return {"pass": False,
            "reason": "curve not found / all candidates skipped (see skipped_candidates)",
            "skipped_candidates": skipped}


def check_hips_z(arm, support_frames, bone="hips", min_range_m=0.02):
    pose = getattr(arm, "pose", None)
    if pose is None:
        return {"pass": False, "reason": "armature has no pose data"}
    pose_bone = pose.bones.get(bone)
    if pose_bone is None:
        return {"pass": False, "reason": "bone not found: %s" % bone}
    if len(support_frames) < 2:
        return {"pass": False, "reason": "support_frames needs >=2 frames"}
    sc = bpy.context.scene
    frame_before = sc.frame_current
    zs = []
    try:
        for f in support_frames:
            whole = int(math.floor(f))
            sc.frame_set(whole, subframe=f - whole)
            bpy.context.view_layer.update()
            zs.append((arm.matrix_world @ pose_bone.matrix).translation.z)
    finally:
        sc.frame_set(frame_before)
    rng = max(zs) - min(zs)
    return {"pass": rng >= min_range_m, "range_mm": round(1000 * rng, 2),
            "min_range_mm": round(1000 * min_range_m, 2),
            "min_m": round(min(zs), 4), "max_m": round(max(zs), 4)}


def check_airtime(takeoff_frame, land_frame, height_m, fps=None, tol_frames=1.0):
    sc = bpy.context.scene
    fps = fps or (sc.render.fps / (sc.render.fps_base or 1.0))
    if land_frame <= takeoff_frame or height_m <= 0 or fps <= 0:
        return {"pass": False, "reason": "bad airtime inputs"}
    t_meas = (land_frame - takeoff_frame) / fps
    t_theory = 2.0 * math.sqrt(2.0 * height_m / 9.81)
    diff = abs(t_meas - t_theory)
    return {"pass": diff <= tol_frames / fps,
            "measured_s": round(t_meas, 4), "theory_s": round(t_theory, 4),
            "diff_frames": round(diff * fps, 2), "fps": round(fps, 3),
            "tol_frames": tol_frames}


def check_driver_binding(arm):
    issues, bound = [], 0
    for sk in bpy.data.shape_keys:
        ad = sk.animation_data
        if not ad:
            continue
        for fc in ad.drivers:
            if not fc.data_path.endswith(".value"):
                continue
            drv = getattr(fc, "driver", fc)
            has_bone = False
            for var in drv.variables:
                for tgt in getattr(var, "targets", []):
                    if getattr(tgt, "id", None) == arm and getattr(tgt, "bone_target", ""):
                        has_bone = True
            if has_bone:
                bound += 1
            else:
                issues.append("shape key driver not bound to bone: %s" % fc.data_path)
    ad = getattr(arm, "animation_data", None)
    if ad and ad.action and len(ad.nla_tracks) > 0:
        issues.append("residual active Action while NLA strips exist")
    return {"pass": not issues, "bound_drivers": bound, "issues": issues}


def _parse_ranges(argv):
    opts = {"eccentric": None, "support": None, "rig": None,
            "bone": "hips", "action": None, "airtime": None, "height": None,
            "driver_binding": False, "hips_min_mm": 20.0, "subframe": 1.0,
            "tol_frames": 1.0}
    i = 0
    while i < len(argv):
        key = argv[i]
        val = argv[i + 1] if i + 1 < len(argv) else None
        if key == "--eccentric" and val:
            a, b = val.split(",")
            opts["eccentric"] = (int(a), int(b))
            i += 2
        elif key == "--support" and val:
            frames = []
            for part in val.split(";"):
                a, b = part.split("-")
                frames.extend(range(int(a), int(b) + 1))
            opts["support"] = frames
            i += 2
        elif key == "--rig" and val:
            opts["rig"] = val
            i += 2
        elif key == "--bone" and val:
            opts["bone"] = val
            i += 2
        elif key == "--action" and val:
            opts["action"] = val
            i += 2
        elif key == "--airtime" and val:
            a, b = val.split(",")
            opts["airtime"] = (int(a), int(b))
            i += 2
        elif key == "--height" and val:
            opts["height"] = float(val)
            i += 2
        elif key == "--driver-binding":
            opts["driver_binding"] = True
            i += 1
        elif key == "--hips-min-mm" and val:
            opts["hips_min_mm"] = float(val)
            i += 2
        elif key == "--subframe" and val:
            opts["subframe"] = float(val)
            i += 2
        elif key == "--tol-frames" and val:
            opts["tol_frames"] = float(val)
            i += 2
        else:
            i += 1
    return opts


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    try:
        opts = _parse_ranges(argv)
    except (ValueError, IndexError) as exc:
        report = {"status": "fail", "error": "bad arguments: %s" % exc,
                  "usage": "--eccentric F0,F1 --support A-B;C-D "
                           "[--airtime TAKEOFF,LAND --height H] [--driver-binding] "
                           "[--rig NAME] [--bone hips] [--action NAME] "
                           "[--hips-min-mm 20] [--subframe 1.0] [--tol-frames 1]"}
        print("BIOMECH_CHECK " + json.dumps(report, ensure_ascii=False))
        return report
    arm = (bpy.data.objects.get(opts["rig"]) if opts["rig"]
           else next((o for o in bpy.data.objects if o.type == "ARMATURE"), None))
    report = {"manual_shapekey_keys": check_manual_shapekeys()}
    if arm is None:
        report["rig"] = {"pass": False, "reason": "no armature found; pass --rig NAME"}
    else:
        report["rig"] = {"pass": True, "name": arm.name}
        if opts["eccentric"]:
            report["eccentric_tail"] = check_eccentric(
                arm, opts["eccentric"][0], opts["eccentric"][1],
                bone=opts["bone"], action_name=opts["action"],
                step=opts["subframe"])
        else:
            report["eccentric_tail"] = {"pass": None, "skipped": "need --eccentric F0,F1"}
        if opts["support"]:
            report["hips_support"] = check_hips_z(
                arm, opts["support"], bone=opts["bone"],
                min_range_m=opts["hips_min_mm"] / 1000.0)
        else:
            report["hips_support"] = {"pass": None, "skipped": "need --support A-B;C-D"}
        if opts["driver_binding"]:
            report["driver_binding"] = check_driver_binding(arm)
        else:
            report["driver_binding"] = {"pass": None, "skipped": "need --driver-binding"}
    if opts["airtime"] is not None and opts["height"] is not None:
        report["airtime"] = check_airtime(
            opts["airtime"][0], opts["airtime"][1], opts["height"],
            tol_frames=opts["tol_frames"])
    else:
        report["airtime"] = {"pass": None, "skipped": "need --airtime F0,F1 --height H"}
    failed = [k for k, v in report.items() if isinstance(v, dict) and v.get("pass") is False]
    pending = [k for k, v in report.items() if isinstance(v, dict) and v.get("pass") is None]
    if report["manual_shapekey_keys"] or failed:
        status = "fail"
    elif pending:
        status = "incomplete"
    else:
        status = "pass"
    report["status"] = status
    print("BIOMECH_CHECK " + json.dumps(report, ensure_ascii=False))
    return report


def exit_code(report):
    """0=pass；fail / incomplete 都返回 1（CI 不能放行）。"""
    return 0 if report.get("status") == "pass" else 1


if __name__ == "__main__":
    sys.exit(exit_code(main()))
