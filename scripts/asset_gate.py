# asset_gate.py —— 用 blender -b file.blend --python asset_gate.py -- --json out.json
import bpy, bmesh, os, sys, json

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out_json = "asset_gate.json"
for i, a in enumerate(argv):
    if a == "--json" and i + 1 < len(argv):
        out_json = argv[i + 1]

issues = []
def add(level, check, detail):
    issues.append({"level": level, "check": check, "detail": detail})

sc = bpy.context.scene

# ---- scene ----
if sc.unit_settings.scale_length != 1.0:
    add("warn", "unit", "scale_length=%s" % sc.unit_settings.scale_length)
if sc.render.fps not in (24, 25, 30, 60):
    add("warn", "fps", "fps=%s" % sc.render.fps)
add("info", "scene", "fps=%s res=%sx%s engine=%s frames=%s-%s" % (
    sc.render.fps, sc.render.resolution_x, sc.render.resolution_y,
    sc.render.engine, sc.frame_start, sc.frame_end))

# ---- meshes ----
mesh_objs = [o for o in sc.objects if o.type == 'MESH']
total_tris = 0
for ob in mesh_objs:
    if not ob.data:
        add("fail", "mesh_data", ob.name)
        continue
    if any(abs(s - 1.0) > 1e-4 for s in ob.scale):
        add("warn", "scale", "%s scale=%s" % (ob.name, tuple(round(s, 3) for s in ob.scale)))
    if len(ob.data.materials) == 0:
        add("warn", "material", "%s has no material" % ob.name)
    me = ob.data
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    total_tris += tris
    bm = bmesh.new()
    bm.from_mesh(me)
    non_manifold = sum(1 for e in bm.edges if not e.is_manifold)
    bm.free()
    if non_manifold > 0:
        add("warn" if non_manifold < 10 else "fail", "non_manifold", "%s edges=%d" % (ob.name, non_manifold))
add("info", "polycount", "meshes=%d tris=%d" % (len(mesh_objs), total_tris))

# ---- textures ----
missing = []
for img in bpy.data.images:
    p = bpy.path.abspath(img.filepath) if img.filepath else ""
    if p and not os.path.exists(p):
        missing.append((img.name, p))
for name, p in missing:
    add("fail", "missing_texture", "%s -> %s" % (name, p))

# ---- animation ----
def _fcurves_of_action(act):
    """layered Action 优先；Blender 4.2 及更早回退到 act.fcurves。"""
    if act is None:
        return []
    try:
        out = []
        for layer in act.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    out.extend(cb.fcurves)
        return out
    except Exception:
        return list(getattr(act, "fcurves", []))


def fcurves_of(obj):
    """当前 Action + 未静音 NLA strips；读不到动画时不再静默返回 []。"""
    ad = getattr(obj, "animation_data", None)
    if not ad:
        return []
    out = _fcurves_of_action(ad.action)
    seen = {fc.as_pointer() for fc in out}
    for track in ad.nla_tracks:
        if getattr(track, "mute", False):
            continue
        for strip in track.strips:
            if getattr(strip, "mute", False):
                continue
            for fc in _fcurves_of_action(getattr(strip, "action", None)):
                if fc.as_pointer() not in seen:
                    seen.add(fc.as_pointer())
                    out.append(fc)
    return out

anim_objs = 0
for ob in sc.objects:
    fcs = fcurves_of(ob)
    if fcs:
        anim_objs += 1
        keys = sum(len(fc.keyframe_points) for fc in fcs)
        add("info", "anim", "%s curves=%d keys=%d" % (ob.name, len(fcs), keys))
    elif getattr(ob, "animation_data", None):
        add("warn", "anim_structure",
            "%s has animation_data but no readable fcurves" % ob.name)
if anim_objs == 0:
    add("info", "anim", "no animation data")

# ---- physics ----
if sc.rigidbody_world is not None:
    baked = sc.rigidbody_world.point_cache.is_baked
    add("info" if baked else "warn", "rigidbody_cache",
        "is_baked=%s substeps=%s iters=%s" % (
            baked, sc.rigidbody_world.substeps_per_frame,
            sc.rigidbody_world.solver_iterations))

# ---- camera / output ----
if sc.camera is None:
    add("fail", "camera", "scene has no active camera")
else:
    add("info", "camera", sc.camera.name)
fmt = getattr(sc.render.image_settings, "media_type", "")
add("info", "output", "format=%s media=%s path=%s" % (
    sc.render.image_settings.file_format, fmt, sc.render.filepath))

# ---- summary ----
fails = [i for i in issues if i["level"] == "fail"]
warns = [i for i in issues if i["level"] == "warn"]
status = "fail" if fails else ("warn" if warns else "pass")
result = {"status": status, "fails": len(fails), "warns": len(warns), "issues": issues}
with open(out_json, "w", encoding="utf-8") as fh:
    json.dump(result, fh, ensure_ascii=False, indent=2)
print("ASSET_GATE " + json.dumps({"status": status, "fails": len(fails), "warns": len(warns)}))
if fails:
    sys.exit(1)
