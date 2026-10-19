import bpy, os, json
sc = bpy.context.scene

# 标准布局补强：没有相机时明确失败，而不是抛 RuntimeError traceback
if sc.camera is None:
    cam = next((o for o in bpy.data.objects if o.type == "CAMERA"), None)
    if cam is not None:
        sc.camera = cam
if sc.camera is None:
    print('RENDER_PROBE {"status": "fail", "error": "no camera in scene"}')
    raise SystemExit(1)
sc.frame_set(1)
sc.render.filepath = bpy.path.abspath("//probe.png")
sc.render.image_settings.file_format = 'PNG'
try:
    bpy.ops.render.render(write_still=True)
except RuntimeError as exc:
    print('RENDER_PROBE {"status": "fail", "error": %s}' % json.dumps(str(exc), ensure_ascii=False))
    raise SystemExit(1)

exists = os.path.exists(sc.render.filepath)
print("probe exists", exists)
print('RENDER_PROBE {"status": "%s", "file": %s}' % ("pass" if exists else "fail",
                                                     json.dumps(sc.render.filepath, ensure_ascii=False)))
raise SystemExit(0 if exists else 1)
