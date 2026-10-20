# ENG-001 回归测试

固定 3 个场景，验证 `engineering_check.py` 的输出不会悄悄漂移。

```text
tests/engineering/
├── fixtures/   m1_mug.blend / m2_still_life.blend / m3_bounce.blend
├── configs/    <case>.json（ignore / proxy / intentional contacts）
├── expected/   <case>.json（只比较稳定字段）
└── README.md
```

## 运行

```bash
python scripts/engineering_regression.py --blender /path/to/blender
```

Windows 本机：

```powershell
C:\develop\python\python.EXE scripts\engineering_regression.py `
  --blender "C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe"
```

## 更新期望

```bash
python scripts/engineering_regression.py --update --blender /path/to/blender
```

`--update` 只在**确认检查逻辑变更符合预期**后使用；不要用它掩盖回归。

## 比较字段

`status / fails / warns / stable / margin_mm / wall_min_mm / draft_by_side /
draft_low_area_pct / draft_undercut_area_pct / overhang_bad_faces /
overhang_area_mm2 / support_volume_mm3_est / interference_pairs / proxy_skipped`

数值允许 2% 或 0.05 的容差；列表按顺序比较。

## 说明

- 回归测试需要本机 Blender；CI 若不装 Blender，只跑 `persona_lint` + `selftest`。
- `m3_bounce` 是动画件，期望就是 warn 一组（无支撑面/壁厚），用于防止“把非产品件判 pass”。
