# INT-001 — 室内设计/内饰：中式风格两室两厅公寓

> 版本：0.1.3 · 状态：experimental · 来源：用户提供的模块草案，已转成 mentor-module/1
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
5. **布局校验（强制）**：任何 INT 资产交付前必须跑 §7 的 layout check；0 FAIL 才允许交付。门洞两侧 0.75 m keep-out、门洞断面、家具 AABB、支撑面、油烟机/吊柜/烟道、花盆支撑都不能只凭截图。
6. 来源元数据 pending，不能把本模块写成“当地规范已核验”。

## 5. 来源状态与可靠性分级

| 等级 | 含义 |
|---|---|
| `code_reference` | 政府网站/规范转发文件，可作为尺寸下限参考；**不等于当地现行合规判定** |
| `industry_reference` | 行业文章/案例，只作风格倾向参考，不替代规范与工具书 |
| `community_convention` | 社区通行惯例，用于 Blender 资产尺度基准，不具规范效力 |
| `pending` | 未锁定当地 jurisdiction，需补充 |

| source_id | 标题 | 类型 | 等级 | URL/备注 |
|---|---|---|---|---|
| `SRC-CODE-XJ-LIVING` | 新疆住建厅转发住宅规范文件（6.2 卧室、起居室尺寸） | 政府文件 | code_reference | zjt.xinjiang.gov.cn PDF |
| `SRC-CODE-XJ-BEDROOM` | 同上，双人/单人卧室短边轴线宽度 | 政府文件 | code_reference | 同上 |
| `SRC-CODE-HQ-HEIGHT` | 横琴政府文件：层高、净高、过道、门洞 | 政府文件 | code_reference | hengqin.gov.cn PDF |
| `SRC-CODE-HQ-CORRIDOR` | 同上，套内过道净宽 | 政府文件 | code_reference | 同上 |
| `SRC-CODE-HQ-DOOR` | 同上，门洞通行净宽 | 政府文件 | code_reference | 同上 |
| `SRC-CODE-HB-HEIGHT` | 湖北住建厅文件：层高 ≥3 m、净高 ≥2.6 m | 政府文件 | code_reference | zjt.hubei.gov.cn |
| `SRC-ERG-DINING` | 海南住建厅文件：餐厅通道、通行/转身宽度、家具尺寸表 | 政府文件 | code_reference | zjt.hainan.gov.cn PDF |
| `SRC-LAYOUT-PRINCIPLE` | 住宅套型功能分区与流线原则 | 政府文件/条文说明 | code_reference | 新疆 6.1.5、海南 4.3.3 |
| `SRC-STYLE-CHINESE-COLOR` | 中式/新中式色彩行业文章 | 行业文章 | industry_reference | kudashi / kujiale / modaiyun |
| `SRC-STYLE-CHINESE-MATERIAL` | 中式材料倾向 | 行业文章 | industry_reference | shangceng / zhuzhaibupin |
| `SRC-STYLE-CHINESE-LIGHT` | 中式卧室/茶室照明色温与照度建议 | 行业文章 | industry_reference | dfcgzs / smzdm |
| `SRC-STYLE-CHINESE-FORM` | 中式造型语言（对称、格栅、留白、明式/清式） | 行业文章 | industry_reference | 多篇行业文章综合 |
| `SRC-FURN-CORE` | 床/床头柜/衣柜/书桌尺寸附表 + 餐桌/餐椅人体工学参考 | 政府文件 + 行业资料 | code_reference / industry_reference | 海南附表 + Baidu 百科 |
| `SRC-BLENDER-UNITS` | Blender 单位惯例：1 BU = 1 m，标准门/餐椅/餐桌尺度 | 社区惯例 | community_convention | Blender Artists / Being Animator |

**当前审计：`source_audit` = warn**，不是 pass。原因：13 条来源均为 `pending`/`metadata-only`，尚未逐页核对条款/页码/版次；`SRC-CODE-*` 的 jurisdiction 登记为 `CN-UNKNOWN`，仅作参考下限，不能替代项目所在地现行规范。

## 6. 使用方式

```text
preflight → 命中 INT-001
→ 核对 styles/layouts
→ coverage 检查 data_keys
→ 按 INT-001 数据建模
→ 跑 layout_check.py（门洞/家具/支撑/吊柜/命名）
→ 读取 layout_report.md，0 FAIL 才交付
→ 交付时标注 experimental / 来源 pending / 需专业复核
```

若任务为“中式风格两室两厅公寓室内设计”，本模块应 `proceed`；  
若为“现代风格两室两厅公寓”或“中式风格别墅”，应 `ask` 并提示新建风格/布局变体。

## 7. 布局校验（强制，资产级）

### 7.1 必查项

| 检查 | 判据 | 失败示例 |
|---|---|---|
| 门洞 keep-out | 门洞两侧各 0.75 m、门宽范围、0..head 高度内无家具 | 床侧贴住衣帽间门、厨房柜横在次卧门前 |
| 门洞断面 | 家具不穿过墙体厚度 | 厨房后柜伸进次卧门洞 |
| 家具 AABB | 主要家具互不相交；允许接触进“接触例外表”（reason/owner/过期） | 床/衣柜/餐桌与柜体互顶 |
| 支撑/接触 | 家具底面 z≈0 或有支撑面；花盆底面≈几面/台面 | 花盆悬空、餐桌只有台面无腿 |
| 垂直净空 | 油烟机顶面 < 吊柜底面；烟道接到天花 | 烟机浮空、烟机与吊柜交叠 |
| 命名 | 灯光 `Light_*`；窗/门构件 `_L/_R`；避免 `*.001` | `Master_Ceiling` 被误当天花板 |

### 7.2 执行方式

```bash
blender -b interior_apartment.blend --python layout_check.py -- --out . --strict
```

- 输出 `layout_report.md` / `.csv` / `.json`；
- `--strict`：有 FAIL 时退出码 1，CI/批处理必须能拦住；
- 0 FAIL 才交付；WARN 必须写入 D2 自评；
- 门洞坐标必须来自项目实际门定义（`axis/wall/center/width/head`），不能只按平面图目测。

### 7.3 实现约束

- 逐 mesh 检查，不只用“整组包围盒”；组 union 会把两件独立家具跨接，产生假阴性或假阳性；
- 椅子/烟机/吊柜等接触对写入“接触例外表”（reason/owner/过期），不要为了“全绿”放宽阈值；
- 0.75 m 是**资产建模阈值**，不是当地规范净距；规范净距需按 jurisdiction 复核；
- AABB 是近似检查，不能替代精确碰撞、门扇开启轨迹、人体工学和使用动线评审。

## 8. Open questions（项目输入清单）

| ID | 优先级 | 问题 | 未回答时的默认处理 |
|---|---|---|---|
| OQ-001 | blocker | 项目所在地（国家/省/市）是什么？ | jurisdiction 保持 pending；所有规范条目降级为“参考”，交付说明必须写“需当地专业复核”。 |
| OQ-002 | high | 两室两厅的具体面积、开间/进深、层高、门窗位置与朝向？ | 按“起居室短边 ≥3.6 m、双人卧室短边 ≥3.3 m、层高 ≥3.0 m”建示意壳体，并在 open_questions 保留实测复尺项。 |
| OQ-003 | high | 中式子风格倾向：传统中式 / 新中式 / 明式倾向 / 清式倾向？ | 以“新中式”为默认建模基线：米白/浅棕基底 + 深木点缀 + 简化格栅 + 三层光。 |
| OQ-004 | medium | 家庭结构与次卧用途（长期居住/偶尔居住/书房/儿童房）？ | 次卧按“单人卧室 + 书桌”建模，家具按可移动设置。 |
| OQ-005 | medium | 厨房与卫生间是否已有固定管井/排水点位？灶台、水槽、马桶、淋浴的定位是否锁定？ | 仅建示意管井空物体，不建管线；厨房/卫生间按最小功能布局建模，标注“点位待现场复核”。 |
| OQ-006 | medium | Blender 交付的最终用途：渲染图/动画/实时引擎/GLB 导入？ | 按通用 Blender 渲染资产处理：1 BU = 1 m，Scale 应用为 (1,1,1)，材质用 Principled BSDF，保留分层灯光。 |
| OQ-007 | low | 预算档位与材料替代策略（实木 vs 木饰面，天然石材 vs 岩板，竹藤 vs 仿藤）？ | 按“中档可控预算”建模：木饰面 + 局部实木构件 + 岩板替代天然石 + 仿藤/竹编贴图。 |

> 规则：OQ-001 为 blocker；未锁定所在地时，规范条目只能标“参考”，不能判合规。其余问题不阻塞建模时，按默认值执行并在交付说明中保留。

