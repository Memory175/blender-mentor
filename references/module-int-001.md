# INT-001 — 室内设计/内饰：中式风格两室两厅公寓

> 版本：0.1.0 · 状态：experimental · 来源：用户提供的模块草案，已转成 mentor-module/1
> 范围：中式风格 + 两室两厅公寓 + Blender 资产级建模
> **不是施工图，不是当地合规判定。** 结构/消防/无障碍/能耗必须当地专业复核。

## 1. 覆盖范围

| 维度 | 声明 |
|---|---|
| 建筑风格 | `chinese`（中式/新中式；子风格明式/清式/新中式未细分） |
| 空间布局 | `apartment`（两室两厅公寓） |
| 交付深度 | Blender asset-level modeling（1 BU = 1 m） |

**不覆盖**：modern/minimal/nordic/japanese/industrial/american/french/mediterranean/rustic/cream/luxury 风格；studio/villa/office/retail/restaurant/hotel 或一室/三室布局。  
遇到不覆盖的风格/布局：必须提示“扩展模块或新建变体”，不能复用本模块数据。

## 2. 风格数据（STY-CHN-*）

| key | 内容 |
|---|---|
| `sty_chn_color_base` | 基调：黑/白/灰/米白/浅棕；传统偏深木色，新中式偏米白/浅棕 + 深木点缀 |
| `sty_chn_color_accent` | 点缀：暗红/琉璃黄/玉脂白/水墨黑/木原色；小面积使用 |
| `sty_chn_material_pref` | 主材：实木/石材/竹/藤；辅材：玻璃/不锈钢；避免大面积亮面金属/冷色工业涂料 |
| `sty_chn_light_cct` | 主光 3000–3500 K，辅光 2700–3000 K，重点 2700–3200 K；忌冷白光 |
| `sty_chn_form_language` | 对称轴线、格栅/月洞/屏风、留白、明式线条/清式简化、木作收口 |

## 3. 布局数据（LAY-APT-*）

| key | 参考值 |
|---|---|
| `lay_apt_living_short_axis` | 起居室短边轴线 ≥ 3.60 m |
| `lay_apt_bedroom_short_axis` | 双人卧室短边 ≥ 3.30 m；单人卧室 ≥ 2.40 m（另有 2.20 m 地方值） |
| `lay_apt_clear_height` | 层高 ≥ 3.00 m；卧室/起居净高 ≥ 2.60 m；局部 ≥ 2.20 m |
| `lay_apt_corridor_width` | 入口 ≥ 1.10 m；卧室/起居 ≥ 1.00 m；厨卫/贮藏 ≥ 0.90 m |
| `lay_apt_door_width` | 户门 ≥ 0.90 m；卧室门 ≥ 0.80 m；厨卫门 ≥ 0.70 m |
| `lay_apt_dining_aisle` | 主通道 ≥ 0.90 m；舒适 1.20–1.30 m；拉椅 0.60–0.80 m |
| `lay_apt_furniture_core` | 床 2.0×1.5×0.45；衣柜深 ≥ 0.55、高 ≥ 1.8；书桌 0.9–1.2×0.5–0.6×0.7–0.8 m |
| `lay_apt_room_program` | 玄关/起居/餐厅/厨房/主卧/次卧/卫生间/阳台；动静分区、洁污分区、避免穿行卧室 |

以上是**参考下限/常见值**，不是报建依据；Blender 建模需按净尺寸扣完成面。

## 4. 硬规则

1. 本模块只覆盖 `chinese` 风格；风格不在 `styles` 内 → `ask`，新建变体。
2. 本模块只覆盖两室两厅 `apartment`；布局不在 `layouts` 内 → `ask`，新建变体。
3. 风格/布局变化不得复用 `STY-CHN-*` / `LAY-APT-*` 数据。
4. 结构、消防、无障碍、能耗只能提示专业复核，不判 `pass`。
5. 来源元数据 pending，不能把本模块写成“当地规范已核验”。

## 5. 来源状态

| source_id | 类型 | 状态 |
|---|---|---|
| `SRC-STYLE-CHINESE-*` | web | pending / 未提供 URL |
| `SRC-CODE-XJ-*` / `SRC-CODE-HQ-*` | code | pending / jurisdiction CN-UNKNOWN |
| `SRC-ERG-DINING` / `SRC-FURN-CORE` | book/code | pending / 未提供版次 |
| `SRC-BLENDER-UNITS` | web | metadata-only / Blender Manual |

来源审计结果预期为 **warn**，不是 pass；使用前必须补 URL、版次、条款/页码并复核。

## 6. 使用方式

```text
preflight → 命中 INT-001
→ 核对 styles/layouts
→ coverage 检查 data_keys
→ 按 INT-001 数据建模
→ 交付时标注 experimental / 来源 pending / 需专业复核
```

若任务为“中式风格两室两厅公寓室内设计”，本模块应 `proceed`；  
若为“现代风格两室两厅公寓”或“中式风格别墅”，应 `ask` 并提示新建风格/布局变体。

## 7. Open questions

- 所在地（省/市）与适用规范版次？
- 明式/清式/新中式，具体子风格？
- 套内面积、层高、房间尺寸、门窗位置？
- 是否含水电/暖通/消防/无障碍？
- 家具/软装/材料预算与交付深度？
