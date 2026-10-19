import bpy


def _fcurves_of_action(act):
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


def fcs(obj):
    """当前 Action + 未静音 NLA strips（兼容 4.2 legacy Action）。"""
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


for ob in bpy.data.objects:
    for fc in fcs(ob):
        print(ob.name, fc.data_path, fc.array_index,
              len(fc.keyframe_points),
              sorted({kp.interpolation for kp in fc.keyframe_points}),
              sorted({kp.handle_left_type for kp in fc.keyframe_points}))
