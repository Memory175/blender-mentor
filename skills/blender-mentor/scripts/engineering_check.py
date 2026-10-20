# -*- coding: utf-8 -*-
"""engineering_check.py — ENG-001 规则预检（Blender headless）。

用法：
    blender -b file.blend --python engineering_check.py -- --json out.json
    blender -b file.blend --python engineering_check.py -- --config cfg.json --json out.json

检查：单位/缩放、稳定性（CoG vs 支撑面）、壁厚、拔模、悬垂、零件干涉。
输出：ENGINEERING_CHECK {json}；exit 0=pass/warn，1=fail，2=参数错误。
注意：这是几何规则预检，不是 FEA/强度认证。
"""
import bpy
import bmesh
import json
import math
import os
import sys
from mathutils import Vector
from mathutils.bvhtree import BVHTree

DEFAULTS = {
    "pull_direction": [0, 0, 1],
    "print_direction": [0, 0, 1],
    "min_wall_mm": 1.5,
    "draft_min_deg": 1.0,
    "draft_min_face_area_mm2": 0.05,
    "draft_undercut_area_pct": 0.5,
    "draft_low_area_pct": 5.0,
    "overhang_max_deg": 45.0,
    "support_volume_max_mm3": 0,
    "clearance_min_mm": 0.1,
    "clearance_pairs": [],
    "stability_margin_pct": 10.0,
    "support_tol_mm": 0.5,
    "wall_samples_per_object": 400,
    "ignore": ["Table", "Ground", "Floor", "Backdrop", "Camera"],
    "proxy_objects": [],
    "intentional_contacts": [],
    "side_actions": [],
    "mold_sides": [
        {"name": "+Z", "pull": [0, 0, 1]},
        {"name": "-Z", "pull": [0, 0, -1]}
    ],
    "max_objects": 100,
}


def _argv():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = {"json": "engineering_check.json", "config": None, "pull": None, "print_dir": None}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--json" and i + 1 < len(argv):
            out["json"] = argv[i + 1]; i += 2
        elif a == "--config" and i + 1 < len(argv):
            out["config"] = argv[i + 1]; i += 2
        elif a == "--pull" and i + 1 < len(argv):
            out["pull"] = argv[i + 1]; i += 2
        elif a == "--print-dir" and i + 1 < len(argv):
            out["print_dir"] = argv[i + 1]; i += 2
        else:
            i += 1
    return out


ARGS = _argv()
CONFIG = dict(DEFAULTS)
if ARGS["config"]:
    try:
        with open(ARGS["config"], encoding="utf-8") as fh:
            CONFIG.update(json.load(fh))
    except (OSError, ValueError) as exc:
        print("ENGINEERING_CHECK " + json.dumps(
            {"status": "fail", "error": "config: %s" % exc}, ensure_ascii=False))
        raise SystemExit(2)


def _vec(values):
    v = Vector((float(values[0]), float(values[1]), float(values[2])))
    if v.length < 1e-9:
        raise ValueError("zero direction")
    return v.normalized()


if ARGS["pull"]:
    CONFIG["pull_direction"] = [float(x) for x in ARGS["pull"].split(",")]
if ARGS["print_dir"]:
    CONFIG["print_direction"] = [float(x) for x in ARGS["print_dir"].split(",")]
PULL = _vec(CONFIG["pull_direction"])
PRINT_DIR = _vec(CONFIG["print_direction"])

scene = bpy.context.scene
issues = []


def add(level, check, detail):
    issues.append({"level": level, "check": check, "detail": detail})


def _fmt(v):
    return round(v, 3)


ignore = {str(x).lower() for x in CONFIG.get("ignore", [])}
proxy_names = {str(x).lower() for x in CONFIG.get("proxy_objects", [])}


def _is_ignored(ob):
    name = ob.name.lower()
    return any(name == x or name.startswith(x) for x in ignore)


def _is_proxy(ob):
    name = ob.name.lower()
    return any(name == x or name.startswith(x) for x in proxy_names)


meshes = [o for o in scene.objects
          if o.type == "MESH" and o.name != "ENGINEERING_CHECK"
          and not _is_ignored(o) and not _is_proxy(o)]
meshes = meshes[: int(CONFIG.get("max_objects", 100))]
skipped_proxies = [o.name for o in scene.objects
                   if o.type == "MESH" and not _is_ignored(o) and _is_proxy(o)]
if skipped_proxies:
    add("info", "proxy", "跳过渲染代理：%s" % ", ".join(skipped_proxies))
if CONFIG.get("side_actions"):
    names = []
    for item in CONFIG.get("side_actions", []):
        if isinstance(item, dict):
            names.append(str(item.get("feature") or item.get("name") or "side_action"))
        else:
            names.append(str(item))
    add("info", "side_actions", "已声明侧向机构：%s（几何上未自动验证，需人工确认）" % ", ".join(names))

# ---- scene ----
if scene.unit_settings.scale_length != 1.0:
    add("warn", "unit", "scale_length=%s（脚本假设米制）" % scene.unit_settings.scale_length)
for ob in meshes:
    if any(abs(s - 1.0) > 1e-4 for s in ob.scale):
        add("warn", "scale", "%s scale=%s（请先 apply scale）" % (
            ob.name, tuple(round(s, 3) for s in ob.scale)))
if not meshes:
    add("fail", "mesh", "场景里没有可分析的 mesh 对象（或都被 ignore 了）")


def volume_centroid(ob):
    mw = ob.matrix_world
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.transform(mw)
    vol = 0.0
    cen = Vector((0.0, 0.0, 0.0))
    for f in bm.faces:
        vs = [v.co for v in f.verts]
        if len(vs) < 3:
            continue
        a = vs[0]
        for i in range(1, len(vs) - 1):
            b, c = vs[i], vs[i + 1]
            v = a.dot(b.cross(c)) / 6.0
            vol += v
            cen += (a + b + c) / 4.0 * v
    bm.free()
    if abs(vol) < 1e-12:
        return 0.0, mw.translation.copy()
    return abs(vol), cen / vol


# ---- 1. stability: CoG vs support polygon ----
total_vol = 0.0
cog = Vector((0.0, 0.0, 0.0))
min_z = None
for ob in meshes:
    vol, c = volume_centroid(ob)
    if vol <= 0:
        add("warn", "volume", "%s volume=0（非封闭网格？）" % ob.name)
        continue
    total_vol += vol
    cog += c * vol
    mw = ob.matrix_world
    for v in ob.data.vertices:
        z = (mw @ v.co).z
        min_z = z if min_z is None else min(min_z, z)
if total_vol > 0:
    cog /= total_vol
else:
    cog = Vector((0.0, 0.0, 0.0))

support = []
tol = float(CONFIG.get("support_tol_mm", 0.5)) / 1000.0
if min_z is not None:
    for ob in meshes:
        mw = ob.matrix_world
        for v in ob.data.vertices:
            p = mw @ v.co
            if p.z <= min_z + tol:
                support.append((p.x, p.y))
support = sorted(set((round(x, 6), round(y, 6)) for x, y in support))


def convex_hull(points):
    pts = sorted(set(points))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


hull = convex_hull(support)
stable = None
margin_mm = None
if len(hull) >= 3:
    def inside(pt, poly):
        sign = 0
        for i in range(len(poly)):
            a, b = poly[i], poly[(i + 1) % len(poly)]
            c = (b[0] - a[0]) * (pt[1] - a[1]) - (b[1] - a[1]) * (pt[0] - a[0])
            if abs(c) < 1e-12:
                continue
            s = 1 if c > 0 else -1
            if sign == 0:
                sign = s
            elif s != sign:
                return False
        return True

    stable = inside((cog.x, cog.y), hull)
    # 到支撑边界的最近距离
    best = 1e9
    for i in range(len(hull)):
        a, b = Vector(hull[i]), Vector(hull[(i + 1) % len(hull)])
        p = Vector((cog.x, cog.y))
        ab = b - a
        t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-12)))
        best = min(best, (p - (a + ab * t)).length)
    margin_mm = best * 1000.0
    width_mm = max(
        max(x for x, _ in hull) - min(x for x, _ in hull),
        max(y for _, y in hull) - min(y for _, y in hull)) * 1000.0
    if not stable:
        add("fail", "stability", "重心投影在支撑面外（CoG %.1f, %.1f mm）" % (
            cog.x * 1000, cog.y * 1000))
    elif margin_mm < width_mm * float(CONFIG.get("stability_margin_pct", 10.0)) / 100.0:
        add("warn", "stability", "重心离支撑边界 %.1f mm，低于 %.0f%% 裕度" % (
            margin_mm, float(CONFIG.get("stability_margin_pct", 10.0))))
else:
    add("warn", "stability", "接地点不足 3 个，无法构造支撑面（support=%d）" % len(hull))

# ---- 2. wall thickness ----
wall_min = None
wall_per_obj = {}
sample_cap = max(10, int(CONFIG.get("wall_samples_per_object", 400)))
for ob in meshes:
    me = ob.data
    if not me.polygons:
        continue
    step = max(1, len(me.polygons) // sample_cap)
    inv = ob.matrix_world.inverted()
    vals = []
    for idx in range(0, len(me.polygons), step):
        poly = me.polygons[idx]
        center_l = inv @ (ob.matrix_world @ poly.center)
        normal_l = (inv.to_3x3() @ (ob.matrix_world.to_3x3() @ poly.normal)).normalized()
        if normal_l.length < 1e-9:
            continue
        origin = center_l - normal_l * 1e-4
        hit, loc, nrm, face = ob.ray_cast(origin, -normal_l, distance=0.20)
        if not hit:
            continue
        d = (loc - origin).length
        if 2e-4 < d < 0.199:
            vals.append(d)
    if vals:
        lo = min(vals)
        wall_per_obj[ob.name] = {"min_mm": round(lo * 1000, 2),
                                 "samples": len(vals)}
        wall_min = lo if wall_min is None else min(wall_min, lo)
if wall_min is None:
    add("warn", "wall", "没有采到有效壁厚（开放网格或全部射线未命中）")
else:
    limit = float(CONFIG.get("min_wall_mm", 1.5)) / 1000.0
    if wall_min < limit:
        add("fail", "wall", "最小壁厚 %.2f mm < %.2f mm" % (
            wall_min * 1000, limit * 1000))
    else:
        add("info", "wall", "最小壁厚 %.2f mm（阈值 %.2f mm）" % (
            wall_min * 1000, limit * 1000))

# ---- 3. draft（面积加权，区分倒扣/低拔模） ----
draft_min = None
draft_checked = 0
draft_area = 0.0
undercut_faces = 0
undercut_area = 0.0
low_faces = 0
low_area = 0.0
bad_faces = []
min_face_area = float(CONFIG.get("draft_min_face_area_mm2", 0.05)) / 1e6
draft_limit = float(CONFIG.get("draft_min_deg", 1.0))


def _world_area(ob, poly):
    mw = ob.matrix_world
    vs = [mw @ ob.data.vertices[i].co for i in poly.vertices]
    if len(vs) < 3:
        return 0.0
    total = 0.0
    for i in range(1, len(vs) - 1):
        total += (vs[i] - vs[0]).cross(vs[i + 1] - vs[0]).length * 0.5
    return total


for ob in meshes:
    mw = ob.matrix_world
    nm = mw.to_3x3().inverted().transposed()
    for poly in ob.data.polygons:
        area = _world_area(ob, poly)
        if area < min_face_area:
            continue
        n = (nm @ poly.normal).normalized()
        dot = max(-1.0, min(1.0, n.dot(PULL)))
        # 只统计“侧壁”；接近上/下表面的法线不参与拔模
        if abs(dot) > 0.7:
            continue
        draft_checked += 1
        draft_area += area
        # 单方向拉模时外壁/内腔符号相反，这里先统计“壁面与拉模轴的夹角”，
        # 倒扣只作为候选单独提示，最终需按模具侧确认。
        mag = math.degrees(math.asin(min(1.0, abs(dot))))
        if draft_min is None or mag < draft_min:
            draft_min = mag
        if dot < -0.5:
            undercut_faces += 1
            undercut_area += area
        if mag < draft_limit:
            low_faces += 1
            low_area += area
            bad_faces.append({"object": ob.name,
                              "draft_deg": round(mag, 2),
                              "area_mm2": round(area * 1e6, 2),
                              "z_mm": round((mw @ poly.center).z * 1000, 1)})
if draft_checked == 0:
    add("warn", "draft", "没有侧面可检查（全部接近水平/竖直？）")
else:
    undercut_pct = (undercut_area / draft_area * 100.0) if draft_area else 0.0
    low_pct = (low_area / draft_area * 100.0) if draft_area else 0.0
    if undercut_faces:
        level = "warn" if undercut_pct > float(CONFIG.get("draft_undercut_area_pct", 0.5)) else "info"
        add(level, "draft", "疑似倒扣面 %d 个 / %.2f%% 面积（法线朝拉模反向，需按模具侧确认）" % (
            undercut_faces, undercut_pct))
    if low_faces:
        level = "warn" if low_pct > float(CONFIG.get("draft_low_area_pct", 5.0)) else "info"
        add(level, "draft", "低拔模面 %d 个 / %.2f%% 面积（<%0.1f°）" % (
            low_faces, low_pct, draft_limit))
    if not undercut_faces and not low_faces:
        add("info", "draft", "最小壁面角 %.2f°（阈值 %.1f°）" % (draft_min, draft_limit))
    if bad_faces:
        top = sorted(bad_faces, key=lambda x: x["area_mm2"], reverse=True)[:5]
        add("info", "draft_top", top)

# ---- 3.1 分模具侧拔模 ----
draft_by_side = {}
side_dirs = []
for side in (CONFIG.get("mold_sides") or []):
    try:
        side_dirs.append((str(side.get("name", "side")), _vec(side.get("pull", [0, 0, 1]))))
    except Exception:
        continue
if side_dirs:
    for sname, sdir in side_dirs:
        checked = 0
        area_sum = 0.0
        low_n = 0
        low_a = 0.0
        min_deg = None
        for ob in meshes:
            mw = ob.matrix_world
            nm = mw.to_3x3().inverted().transposed()
            for poly in ob.data.polygons:
                area = _world_area(ob, poly)
                if area < min_face_area:
                    continue
                n = (nm @ poly.normal).normalized()
                dot = n.dot(sdir)
                # 只统计该模具侧可见、且不是顶/底面的侧壁
                if dot <= 0.01 or dot > 0.7:
                    continue
                checked += 1
                area_sum += area
                deg = math.degrees(math.asin(min(1.0, dot)))
                if min_deg is None or deg < min_deg:
                    min_deg = deg
                if deg < draft_limit:
                    low_n += 1
                    low_a += area
        if checked:
            low_pct = low_a / area_sum * 100.0 if area_sum else 0.0
            draft_by_side[sname] = {
                "checked_faces": checked,
                "min_draft_deg": round(min_deg, 2) if min_deg is not None else None,
                "low_faces": low_n,
                "low_area_pct": round(low_pct, 2),
            }
            level = "warn" if low_pct > float(CONFIG.get("draft_low_area_pct", 5.0)) else "info"
            add(level, "draft_side", "%s：最小 %.2f° / 低拔模 %.2f%% 面积（%d 面）" % (
                sname, min_deg, low_pct, low_n))
    # 所有模具侧都不收的“近垂直壁”单独提示
    vertical_area = 0.0
    for ob in meshes:
        mw = ob.matrix_world
        nm = mw.to_3x3().inverted().transposed()
        for poly in ob.data.polygons:
            n = (nm @ poly.normal).normalized()
            if max(abs(n.dot(d)) for _, d in side_dirs) <= 0.01:
                vertical_area += _world_area(ob, poly)
    if vertical_area > 0:
        add("info", "draft_vertical", "近垂直壁面积 %.1f mm²（两侧均无拔模，按需确认）" % (
            vertical_area * 1e6))

# ---- 4. overhang（含面积与支撑体积估算） ----
overhang_bad = 0
overhang_area = 0.0
overhang_volume = 0.0
overhang_max = None
overhang_top = []
limit_overhang = float(CONFIG.get("overhang_max_deg", 45.0))
for ob in meshes:
    mw = ob.matrix_world
    nm = mw.to_3x3().inverted().transposed()
    obj_min_z = min((mw @ v.co).z for v in ob.data.vertices) if ob.data.vertices else 0.0
    for poly in ob.data.polygons:
        n = (nm @ poly.normal).normalized()
        dot = n.dot(PRINT_DIR)
        if dot > -0.01:
            continue
        center = mw @ poly.center
        # 贴在该零件自身最低点的底面通常是 build plate，不算悬垂
        if center.z <= obj_min_z + 1e-4:
            continue
        ang = math.degrees(math.asin(max(0.0, min(1.0, -dot))))
        if overhang_max is None or ang > overhang_max:
            overhang_max = ang
        if ang > limit_overhang:
            area = _world_area(ob, poly)
            overhang_bad += 1
            overhang_area += area
            height_mm = max(0.0, (center.z - obj_min_z) * 1000.0)
            overhang_volume += area * 1e6 * height_mm
            overhang_top.append({"object": ob.name, "angle_deg": round(ang, 1),
                                 "area_mm2": round(area * 1e6, 2),
                                 "z_mm": round(center.z * 1000, 1)})
if overhang_max is not None and overhang_bad:
    overhang_top = sorted(overhang_top, key=lambda x: x["area_mm2"], reverse=True)[:5]
    add("warn", "overhang", "最大悬垂 %.1f°，%d 面 / %.1f mm² / 支撑体积约 %.0f mm³" % (
        overhang_max, overhang_bad, overhang_area * 1e6, overhang_volume))
    add("info", "overhang_top", overhang_top)
    vmax = float(CONFIG.get("support_volume_max_mm3", 0) or 0)
    if vmax > 0 and overhang_volume > vmax:
        add("warn", "support_volume", "支撑体积约 %.0f mm³ > 上限 %.0f mm³" % (
            overhang_volume, vmax))
else:
    add("info", "overhang", "没有超过阈值的向下悬垂面")

# ---- 5. interference ----
trees = {}
for ob in meshes:
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.transform(ob.matrix_world)
    try:
        trees[ob.name] = BVHTree.FromBMesh(bm, epsilon=0.0)
    except Exception:
        pass
    bm.free()
pairs = []
names = list(trees)
for i in range(len(names)):
    for j in range(i + 1, len(names)):
        try:
            overlap = trees[names[i]].overlap(trees[names[j]])
        except Exception:
            continue
        if overlap:
            pairs.append((names[i], names[j], len(overlap)))
if pairs:
    intentional = set()
    for p in CONFIG.get("intentional_contacts", []):
        try:
            intentional.add(frozenset((str(p[0]).lower(), str(p[1]).lower())))
        except Exception:
            continue
    for a, b, n in pairs:
        key = frozenset((a.lower(), b.lower()))
        if key in intentional or frozenset((b.lower(), a.lower())) in intentional:
            add("info", "interference", "intentional contact: %s ↔ %s" % (a, b))
        else:
            add("warn", "interference", "%s ↔ %s: %d 对相交面" % (a, b, n))
else:
    add("info", "interference", "未检测到零件间相交")

# ---- 6. clearance pairs（指定配合对的最小间隙） ----
clearance_results = []
obj_by_name = {o.name: o for o in meshes}
pair_cap = max(10, int(CONFIG.get("clearance_samples_per_object", 200)))
for pair in CONFIG.get("clearance_pairs", []):
    try:
        a_name, b_name = str(pair[0]), str(pair[1])
    except Exception:
        continue
    ob_a, ob_b = obj_by_name.get(a_name), obj_by_name.get(b_name)
    if not (ob_a and ob_b and trees.get(a_name)):
        continue
    def _min_gap(src, dst):
        tree = trees.get(dst)
        src_ob = obj_by_name.get(src)
        if not (tree and src_ob):
            return None
        best = None
        mw = src_ob.matrix_world
        verts = list(src_ob.data.vertices)[:pair_cap]
        for v in verts:
            loc, nrm, idx, dist = tree.find_nearest(mw @ v.co)
            if loc is None:
                continue
            best = dist if best is None else min(best, dist)
        return best
    gap_a = _min_gap(a_name, b_name)
    gap_b = _min_gap(b_name, a_name)
    gaps = [g for g in (gap_a, gap_b) if g is not None]
    if not gaps:
        continue
    gap_mm = min(gaps) * 1000.0
    clearance_results.append({"a": a_name, "b": b_name, "min_gap_mm": round(gap_mm, 2)})
    limit = float(CONFIG.get("clearance_min_mm", 0.1))
    if abs(gap_mm) < 0.01:
        continue  # 相交对由 interference 处理
    if gap_mm < limit:
        add("warn", "clearance", "%s ↔ %s 最小间隙 %.2f mm < %.2f mm" % (
            a_name, b_name, gap_mm, limit))
    else:
        add("info", "clearance", "%s ↔ %s 最小间隙 %.2f mm" % (a_name, b_name, gap_mm))

# ---- summary ----
fails = [i for i in issues if i["level"] == "fail"]
warns = [i for i in issues if i["level"] == "warn"]
status = "fail" if fails else ("warn" if warns else "pass")
summary = {
    "objects": [o.name for o in meshes],
    "cog_m": [_fmt(cog.x), _fmt(cog.y), _fmt(cog.z)],
    "stable": stable,
    "margin_mm": _fmt(margin_mm) if margin_mm is not None else None,
    "wall_min_mm": _fmt(wall_min * 1000) if wall_min is not None else None,
    "wall_per_object": wall_per_obj,
    "draft_min_deg": _fmt(draft_min) if draft_min is not None else None,
    "draft_checked_faces": draft_checked,
    "draft_undercut_faces": undercut_faces,
    "draft_undercut_area_pct": round(undercut_area / draft_area * 100.0, 2) if draft_area else 0.0,
    "draft_low_faces": low_faces,
    "draft_low_area_pct": round(low_area / draft_area * 100.0, 2) if draft_area else 0.0,
    "draft_by_side": draft_by_side,
    "proxy_skipped": skipped_proxies,
    "overhang_max_deg": _fmt(overhang_max) if overhang_max is not None else None,
    "overhang_bad_faces": overhang_bad,
    "overhang_area_mm2": round(overhang_area * 1e6, 2),
    "support_volume_mm3_est": round(overhang_volume, 1),
    "interference_pairs": [{"a": a, "b": b, "faces": n} for a, b, n in pairs],
    "clearance_pairs": clearance_results,
}
result = {"status": status, "fails": len(fails), "warns": len(warns),
          "issues": issues, "summary": summary}
try:
    with open(ARGS["json"], "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)
except OSError:
    pass
print("ENGINEERING_CHECK " + json.dumps(
    {"status": status, "fails": len(fails), "warns": len(warns)}, ensure_ascii=False))
raise SystemExit(0 if status != "fail" else 1)
