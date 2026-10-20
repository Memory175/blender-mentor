# INT-002 — 现代轻奢大平层室内设计

> 版本：0.1.0 · 状态：experimental · 来源：用户提供的平面图（布局/房间程序），未提供实测尺寸
> 范围：现代轻奢（modern + luxury）+ 大平层/平层公寓（apartment）+ Blender 资产级建模
> **不是施工图，不是当地合规判定。** 结构、消防、无障碍、能耗必须当地专业复核。

## 1. 覆盖范围

| 维度 | 声明 |
|---|---|
| 建筑风格 | `modern` + `luxury`（现代 + 轻奢） |
| 空间布局 | `apartment`（大平层/电梯平层） |
| 交付深度 | Blender asset-level modeling（1 BU = 1 m） |

**不覆盖**：中式/新中式（用 `INT-001`）、别墅/独栋、办公/商业/酒店；未提供尺寸时不能做 1:1 施工级复刻。

## 2. 风格数据（STY-LUX-*）

| key | 内容 |
|---|---|
| `sty_lux_color_base` | 暖灰/米白/浅石材色 + 深木色 |
| `sty_lux_color_accent` | 黑钛、黄铜、深胡桃木（小面积） |
| `sty_lux_material_pref` | 大理石/岩板、木饰面、金属收边、玻璃、皮革/织物 |
| `sty_lux_light_cct` | 主光 3000–3500 K；辅助/重点 2700–3000 K（资产级基线） |
| `sty_lux_form_language` | 大面积石材、通高木饰面、金属收边、低饱和软装、无主灯/线性灯 |

以上全部是**从用户平面图和常见做法归纳的示意基线**，不是材料样板或照明设计。

## 3. 布局数据（LAY-FLAT-*）

| key | 内容 |
|---|---|
| `lay_flat_room_program` | 玄关、客厅、餐厅、厨房、老人房、书房、衣帽间、过厅、双卫、休闲阳台、设备阳台、电梯厅、楼梯间 |
| `lay_flat_public_private` | 公共区（玄关—客餐厅—厨房）与私密区（老人房—衣帽间—书房）分开；过厅作缓冲 |
| `lay_flat_circulation` | 入户→玄关→客餐厅；过厅分流到私密区；服务动线连接厨房/双卫/设备阳台/电梯楼梯 |
| `lay_flat_service_core` | 厨房、双卫、设备阳台、电梯/楼梯形成服务核，不穿私密区 |
| `lay_flat_furniture_core` | 床/餐桌/书桌/衣帽间通道的资产级示意尺寸 |
| `lay_flat_balcony` | 南向休闲阳台与设备/生活阳台分开，保留通行与排水 |

> 图中未标注开间、进深、层高、墙厚、门窗尺寸；以上是**示意程序**。正式建模前必须补实测，或显式标 `[ASSUMPTION]`。

## 4. 硬规则

1. 只覆盖 `modern` + `luxury` 与 `apartment`；不匹配时 `ask`，不得复用 INT-001 的中式数据。
2. 入户必须先到玄关，不能直接进入卧室/卫生间。
3. 公共区与私密区必须有玄关/过厅缓冲；服务动线不得穿老人房/书房。
4. 图面房间程序至少覆盖：玄关、客餐厅、厨房、老人房、书房、衣帽间、双卫、双阳台、设备阳台。
5. 交付前必须跑 `layout_check.py --strict`：门洞两侧 0.75 m keep-out、门洞断面、家具 AABB、支撑、油烟机/吊柜/烟道；**0 FAIL 才交付**。
6. 未提供实测尺寸时，不得声称 1:1 或施工级；所有布局/家具数据标 `[ASSUMPTION]`。
7. 结构、消防、无障碍、能耗不判 `pass`；来源保持 pending。

## 5. 来源状态与假设

当前 `jurisdiction = pending`；本模块没有外部规范/标准 source_id，全部数据为 `assumption: true`，`confidence: low`。

| 假设 | 内容 |
|---|---|
| A-01 | 房间程序来自用户平面图，未现场复尺 |
| A-02 | 门宽按 0.9 m、家具按常规资产尺度反推 |
| A-03 | 现代轻奢为图面视觉归纳，不是材料样板 |
| A-04 | 双阳台/电梯楼梯只做资产表达，不做结构与 MEP |

`source_audit` 不能把本模块写成“当地规范已核验”；需要专业复核。

## 6. 使用方式

```text
preflight → 命中 INT-002
→ 核对 styles/layouts
→ coverage 检查 data_keys
→ 补实测尺寸或确认示意假设
→ 按 INT-002 程序建模
→ 跑 layout_check.py --strict
→ 读取 layout_report.md，0 FAIL 才交付
→ 标注 experimental / 来源 pending / 需专业复核
```

## 7. 布局校验（强制，资产级）

```bash
blender -b interior_apartment.blend --python layout_check.py -- --out . --strict
```

- 门洞 keep-out 两侧各 0.75 m；逐 mesh 检查，不用整组 union；
- 门洞断面不得穿墙/穿门；
- 主要家具 AABB 互交；允许接触进“接触例外表”（reason/owner/过期）；
- 家具底面 z≈0 或有支撑面；花盆落台面；
- 油烟机顶面 < 吊柜底面；烟道接到天花；
- 输出 `layout_report.md/.csv/.json`；`--strict` 有 FAIL 返回非 0；0 FAIL 才交付。

0.75 m 是资产建模阈值，不是当地规范净距；AABB 不替代精确碰撞、门扇轨迹、人体工学评审。

## 8. Open questions

| ID | 优先级 | 问题 | 未回答时默认 |
|---|---|---|---|
| OQ-101 | blocker | 项目所在地与实测开间/进深/层高？ | jurisdiction pending；只做示意资产 |
| OQ-102 | high | 是否保留电梯/楼梯核心与双阳台？ | 保留资产级示意，不建结构 |
| OQ-103 | high | 老人房/书房/衣帽间实际用途与门洞？ | 按图面程序 + 0.9 m 门宽假设 |
| OQ-104 | medium | 现代轻奢材质档位？ | 岩板 + 木饰面 + 小面积金属 |

## 9. 接口

- 风格/布局 taxonomy：`assets/style_taxonomy.json`（`modern`, `luxury`, `apartment`）
- 类似风格模块：`INT-001` 仅用于 `chinese`，不得混用
- 布局校验：项目侧 `layout_check.py`；报告 `layout_report.md`
- 交付：D1–D4 闭环 + 0 FAIL 布局校验
