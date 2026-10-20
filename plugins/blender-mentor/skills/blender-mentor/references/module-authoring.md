# 模块写作说明（递给任意 AI 的独立指南）

> 用途：把一个「模块写作格式 + 研究任务」交给任意 AI，让它查权威资料并产出可插入
> `blender-mentor` 的模块文件。
>
> 本文件是写作说明，不是模块本身；正式模块由 `assets/modules/<ID>.json` +
> `references/module-<domain>.md` 两份文件组成。

---

## 0.0 一句话触发：skill 内怎么用

当用户只说一句 **“我想建模一个房子”** 时，skill 不会直接开做，也不会只说“缺模块”：

```bash
python scripts/preflight.py --task "我想建模一个房子" --json .preflight.json
# decision=block，gap_hints 命中 ARC-001

python scripts/module_gap.py --task "我想建模一个房子" --json .gap.json
```

`module_gap.py` 会返回四段固定内容：

1. **缺哪个模块**：`ARC-001 / 单层住宅（外建） / 为什么缺`；
2. **需要补哪些知识**：场地、平面、围护、结构边界、规范、施工图；
3. **可复制 Prompt**：`prompt` 字段，原样贴给任意 AI；
4. **并入步骤**：`merge_steps`，含 registry hash、load_plan、lint/preflight。

> 如果 `action=resolve_existing`，表示已有模块命中但数据不足，先补现有模块，不新建重复模块。

---

## 0. 先看结论：单层小房子需要什么

一栋**单层小房子（外建，暂不含内饰）**不是一个模块能覆盖的，它至少涉及：

| 知识域 | 内容 | 现有模块 | 判断 |
|---|---|---|---|
| 场地与规划 | 退线、朝向、占地率、出入口、排水 | 无 | **缺失** |
| 建筑平面/空间 | 房间尺寸、层高、门洞、走廊、采光、通风 | 无 | **缺失** |
| 建筑围护 | 墙体构造、保温、防水、气密、热桥、屋面 | 无 | **缺失** |
| 结构 | 荷载路径、跨度、过梁、基础、抗风/抗震 | 无 | **缺失，且高风险** |
| 建筑规范 | 疏散、防火、无障碍、能耗、地方规划条例 | 无 | **缺失，地域相关** |
| 施工/图纸 | 平立剖、尺寸链、节点、出图比例、标注 | 无 | **缺失** |
| 材料/制造 | 板厚、连接、公差、干涉 | `ENG-001` | **部分可用** |
| 生物力学/动画 | — | `BIO-001` / `ESD-001` | **不适用** |

### 已有模块怎么用

- **`ENG-001` 可以复用一部分**：墙体厚度/板厚、构件干涉、装配间隙、稳定性/重心；
- **但它不是建筑规范模块**：没有退线、疏散、防火、结构跨度、采光系数、热工等数据；
- **`BIO-001`、`ESD-001` 与房子无关**，不要为了“凑模块”强行加载。

### 建议新增什么

MVP 先做一个：

```text
ARC-001  单层住宅（外建）  kind=hybrid  status=experimental
```

它负责：场地/平面/剖面/立面/门窗/屋面/围护概念与尺寸检查；
结构、规范只做**提示与提问**，不自动判“安全”。

后续再拆：

```text
STR-001  结构（木/砌体/轻钢）——必须由当地结构工程师复核
COD-001  建筑规范（按 jurisdiction 分册）
ENV-001  围护/热湿/能耗
```

> 不要一开始做 4 个模块：按需加载最多 2 个，先把 `ARC-001` 做对。

---

## 1. 模块包的文件格式

每个模块 = 两份文件 + 两条注册信息：

```text
assets/modules/ARC-001.json          # 机器读：触发/数据/规则/覆盖
references/module-architecture.md    # 人读：原理/流程/误区/来源
assets/module_registry.json          # 注册表 + sha256
assets/load_plan.json                # 路由触发词（否则 load_router 不加载）
```

### 1.1 JSON 必填字段

```json
{
  "schema": "mentor-module/1",
  "id": "ARC-001",
  "version": "0.1.0",
  "status": "experimental",
  "kind": "hybrid",
  "domain": ["architecture", "residential", "construction"],
  "intent": {
    "include": ["房子", "住宅", "单层", "户型", "平面", "立面", "剖面", "屋面", "门窗"],
    "exclude": ["纯室内渲染", "家具建模"]
  },
  "coverage": [
    {"keywords": ["户型", "房间"], "data_keys": ["room_area_m2", "ceiling_height_m"]},
    {"keywords": ["门", "走廊"], "data_keys": ["door_width_m", "corridor_width_m"]}
  ],
  "data": [
    {
      "key": "ceiling_height_m",
      "value": [2.4, 3.0],
      "unit": "m",
      "scope": "residential",
      "source": "Neufert Architects' Data, 5th ed., section ...",
      "source_type": "book",
      "verification": "page-checked",
      "confidence": "medium"
    }
  ],
  "rules": [
    {
      "id": "door.width",
      "check": "door_width_m >= data.door_width_m",
      "severity": "warn",
      "evidence": "data.door_width_m"
    }
  ],
  "assumptions": ["单层、低层住宅；jurisdiction 待确认"],
  "unknown_policy": "ask",
  "requires": [],
  "conflicts_with": [],
  "references": ["references/module-architecture.md"],
  "tests": [],
  "changelog": ["0.1.0: initial draft"]
}
```

### 1.2 数据项的硬规则

每个 `data` 项必须有 `key`、`value`、`unit`，并且满足以下**之一**：

- `source`：可核对的来源（书/规范/论文/标准/实测）；
- `assumption: true`：显式假设，且 `confidence` 不能写 high。

新增可选字段（当前校验器允许，便于审核）：

```json
{
  "source_type": "book | code | standard | paper | web | measurement",
  "citation": "作者/机构，书名/条款，版次，年份，页码/章节，ISBN/DOI/URL",
  "verification": "page-checked | metadata-only | pending"
}
```

**禁止**：

- 编造 ISBN、页码、DOI、条款号；
- 把“网上看到的一句话”写成 `high`；
- 把美国 IRC 的条款写成“通用建筑规范”；
- 没有来源却填具体数值。

### 1.3 coverage 规则

`coverage` 是“用户说到某个能力时，必须有哪个数据键”：

```json
{"keywords": ["门", "走廊"], "data_keys": ["door_width_m", "corridor_width_m"]}
```

- 如果任务提到“门”，但 selected 模块没有 `door_width_m`，预审会 `ask`；
- 这是防“模块命中了但答不了”的关键；
- `coverage` 引用的每个 key 必须真的存在于 `data` 里。

### 1.4 Markdown 文档结构

`references/module-architecture.md` 建议照下面写：

```markdown
# 单层住宅（外建）

> 通用模块 **ARC-001 v0.1.0**（experimental）
- **版本**：v0.1.0
- **状态**：experimental
- **适用域**：单层独立住宅 / 小型附属建筑
- **依赖**：ENG-001（材料/干涉部分，可选）
- **不适用**：多层、复杂结构、室内精装、施工图签章

## 1. 何时加载 / 不加载
## 2. 输入输出
## 3. 核心模型
### 3.1 场地与退线
### 3.2 平面与房间尺寸
### 3.3 层高、门窗、走廊
### 3.4 屋面与挑檐
### 3.5 围护与热湿
### 3.6 结构与规范边界
## 4. 数据表（必须与 JSON 的 key 对齐）
## 5. 规则（与 JSON rules 对齐）
## 6. Blender 工作流
## 7. 验收与交付
## 8. 常见错误
## 9. 参考来源
## 10. 未决问题
```

**文件里必须出现模块 ID `ARC-001`**，否则 `module_lint` 会报引用不一致。

---

## 2. 单层小房子：需要哪些数据键

下面是建议的 `data` / `coverage` 清单。AI 不需要一次填满，但**每个填了的值必须有来源**。

### 2.1 场地/规划

| key | 说明 | 来源类型 |
|---|---|---|
| `site_setback_m` | 退线距离 | 当地规划条例 |
| `building_coverage_pct` | 占地率上限 | 当地规划条例 |
| `building_height_m` | 檐口/总高限制 | 当地规划条例 |
| `orientation_deg` | 朝向/日照 | 场地分析 |
| `site_drainage_slope_pct` | 排水坡度 | 场地/规范 |

### 2.2 平面/空间

| key | 说明 |
|---|---|
| `room_area_m2` | 客厅/卧室/厨房/卫生间面积区间 |
| `ceiling_height_m` | 净高 |
| `door_width_m` | 门洞宽 |
| `corridor_width_m` | 走廊宽 |
| `stair_riser_mm` / `stair_tread_mm` | 台阶/楼梯（单层也可能有高差） |
| `accessible_turn_radius_m` | 无障碍回转（如适用） |

### 2.3 围护/门窗/屋面

| key | 说明 |
|---|---|
| `wall_thickness_m` | 墙体构造总厚 |
| `window_floor_ratio` | 窗地比 |
| `glazing_u_value` | 玻璃传热系数 |
| `insulation_r_value` | 保温热阻 |
| `roof_pitch_deg` | 屋面坡度 |
| `eave_overhang_m` | 挑檐长度 |
| `airtightness_ach50` | 气密性（如适用） |

### 2.4 结构/规范（高风险）

| key | 说明 |
|---|---|
| `max_span_m` | 梁/屋架跨度（必须结构专业确认） |
| `lintel_depth_mm` | 过梁高度（必须结构专业确认） |
| `foundation_depth_m` | 基础埋深（冻深/地勘） |
| `snow_load_kpa` / `wind_speed_mps` | 荷载（按当地规范） |
| `seismic_category` | 抗震类别（按当地规范） |
| `egress_width_m` / `egress_travel_m` | 疏散宽度/距离 |
| `smoke_alarm_required` | 烟雾报警要求 |

### 2.5 图纸/交付

| key | 说明 |
|---|---|
| `drawing_scale` | 1:50 / 1:100 |
| `dimension_tolerance_mm` | 尺寸标注容差 |
| `annotation_standard` | 标注/图层标准 |
| `model_unit` | 场景单位（m/mm） |

> **结构、防火、无障碍、能耗**都取决于 jurisdiction（国家/省/市）和建筑类型；
> 没有 jurisdiction 时，`unknown_policy` 必须是 `ask`，不能给“通过”。

---

## 3. 哪些模块已有、缺失、或参考不齐

| 模块 | 与本任务关系 | 结论 |
|---|---|---|
| `ENG-001` | 材料厚度、稳定性、干涉、装配 | **部分可用**；不能替代建筑规范 |
| `BIO-001` | 人体/运动 | **不适用** |
| `ESD-001` | 次级动画 | **不适用** |
| `ARC-001` | 单层住宅外建 | **缺失，建议新建** |
| `STR-001` | 结构 | **缺失，高风险，后续单独建** |
| `COD-001` | 规范（按地区） | **缺失，地域相关，后续单独建** |
| `ENV-001` | 围护/热湿/能耗 | **缺失，可后补** |

**不要**把 `ENG-001` 当成“房子模块”直接回答；
它只能帮你查板厚/干涉/装配，不能给你退线、疏散、结构跨度。

---

## 4. 直接复制给任意 AI 的 Prompt

把下面整段（含方括号占位）复制给 AI。它会先问缺失条件，再给两份文件。

```text
你是 Blender Mentor 的模块作者。请严格按 mentor-module/1 格式，为一个新模块写两份内容：
1) assets/modules/ARC-001.json
2) references/module-architecture.md

任务：单层小房子（仅建筑外观与空间，不含室内精装；如用户需要室内，先问是否扩展）。
模块 ID：ARC-001
初始版本：0.1.0
状态：experimental
类型：hybrid

第一步：先不要写答案，先问我以下缺失信息：
- 国家/省/市（jurisdiction）
- 气候区（寒冷/夏热冬冷/夏热冬暖/温和）
- 结构类型（木/砌体/轻钢/混凝土）
- 占地/建筑面积、层数（单层）、房间需求
- 是否包含结构/规范审查，还是只做建筑方案
如果我不回答，把这些问题写进 open_questions，不要假设。

第二步：查资料。优先顺序：
1) 建筑规范/法规（当地现行版本，必须写 jurisdiction + edition）
2) 权威工具书：Neufert《Architects' Data》、Ching《Building Construction Illustrated》、
   Allen & Iano《Fundamentals of Building Construction》
3) 标准：ISO/ASHRAE/当地能耗与无障碍标准（写编号+年份）
4) 论文：只用于采光、通风、热舒适等非强制性结论；写 DOI/URL
禁止编造书名、版次、页码、ISBN、DOI、条款号。

第三步：输出 4 个部分：
A. ARC-001.json（严格按字段：schema/id/version/status/kind/domain/intent/coverage/data/rules/assumptions/unknown_policy/references）
B. module-architecture.md（按本说明第 1.4 节的结构）
C. 来源表：source_type / citation / verification（page-checked | metadata-only | pending）
D. open_questions：没有可靠来源、或需要用户确认的内容

硬规则：
- 每个 data 值必须有 source，或 assumption:true；没有来源就放到 open_questions。
- 结构/防火/无障碍/能耗：只能给“需当地专业复核”的提示，不能判 pass。
- coverage 里的 data_keys 必须存在于 data。
- 不要写“符合规范/安全”的结论，除非有明确 jurisdiction + 条款 + 复核人。
- 不要复制书中的长段原文，只给引用元数据。
```

---

## 5. AI 返回后怎么验收

### 5.1 结构检查

```bash
python scripts/module_lint.py
python scripts/module_conflict.py
```

`module_lint` 会检查：

- 必填字段、ID/semver/status/kind；
- data 是否有 `source` 或 `assumption`；
- coverage 引用的 data key 是否存在；
- rules 的 evidence 是否存在；
- references 文件是否存在且提到模块 ID；
- registry 的 sha256/版本是否一致。

### 5.2 预审检查

```bash
python scripts/preflight.py --task "设计一栋单层小房子，先做外观" --json .preflight.json
```

期望：`proceed`，选中 `ARC-001`；如果它返回 `ask`，看缺的是哪个 data key / 哪个 coverage。

### 5.3 插入注册表

```bash
python -c "import hashlib,pathlib; p=pathlib.Path('assets/modules/ARC-001.json'); print('sha256:'+hashlib.sha256(p.read_bytes()).hexdigest())"
```

把结果写进 `assets/module_registry.json`：

```json
{
  "id": "ARC-001",
  "file": "assets/modules/ARC-001.json",
  "version": "0.1.0",
  "hash": "sha256:...",
  "status": "experimental"
}
```

### 5.4 加入 load_plan

`load_router` 只加载 `load_plan.modules` 里登记的模块：

```json
{
  "id": "ARC-001",
  "file": "references/module-architecture.md",
  "reason": "单层住宅建筑方案（场地/平面/围护/屋面）",
  "triggers": ["房子", "住宅", "单层", "户型", "立面", "剖面", "屋面", "门窗"],
  "exclude": ["纯室内", "家具"]
}
```

### 5.5 跑整体自检

```bash
python scripts/selftest.py .
```

---

## 6. 审核清单（人审，不要全交给 AI）

- [ ] jurisdiction 明确了吗？没有就 `ask`，不要判通过；
- [ ] 每个数值都有 source/assumption 吗？
- [ ] 书/规范的版次、页码、条款号核对过吗？
- [ ] `verification=pending` 的条目是否已从“结论”降级为“待确认”？
- [ ] 结构/防火/无障碍是否明确“需当地专业复核”？
- [ ] coverage 是否覆盖了任务会提到的所有能力？
- [ ] module_lint / module_conflict / preflight 是否全绿？
- [ ] 是否更新了 registry hash（编辑 JSON 后必须重算）？

---

## 6.5 来源时效：最新版 / 失效 / 自动查询

### 数据字段

每个 `data` 项加 `source_id`，并到 `assets/source_registry.json` 登记：

```json
{
  "key": "ceiling_height_m",
  "source_id": "NEUFERT-5E",
  "verification": "pending"
}
```

来源记录至少包含：

```json
{
  "id": "NEUFERT-5E",
  "type": "book | code | standard | paper | web",
  "edition": "5th",
  "year": 2019,
  "status": "current | adopted | superseded | withdrawn | unknown | pending",
  "verification": "page-checked | metadata-only | pending",
  "jurisdiction": null,
  "checked_at": "2026-10-20",
  "next_check_due": "2027-10-20",
  "check_url": "官方目录/出版社/DOI 页面"
}
```

### 审计

```bash
python scripts/source_audit.py --json .source_audit.json
```

- `withdrawn/superseded` → fail，停止；
- 法规缺 `jurisdiction` → fail；
- `pending/metadata-only` / 过期 → warn，不能支撑 fail 级结论。

TTL 建议：code/standard 90 天，book/paper 365 天。

### 过期查询

```bash
python scripts/source_refresh.py --offline
python scripts/source_refresh.py --json .source_refresh.json
```

它只访问官方域名/Crossref，输出 `proposals`，**不自动改写 registry**。
“最新出版版”≠“当地 adopted edition”：规范必须确认 jurisdiction + 生效日期 + amendments。

### 可靠来源优先级

1. 官方标准机构（ISO/IEC/ITU、国家标准化机构、ICC、ASHRAE、ASTM、NFPA、CEN）；
2. 政府法规/规划部门官网；
3. 出版社页面 + ISBN；
4. 同行评审论文（Crossref/DOI、期刊官网、撤稿检查）；
5. 图书馆/WorldCat/Google Books 只做书目交叉核对。

不要用随机 PDF 站、二手“最新规范汇总”、AI 摘要页作为来源。

---

## 6.6 内饰模块（INT-*）的额外规则

- 内饰/室内建模必须独立 `INT-*` 模块，不能借用 ENG/BIO/ESD；
- 模块顶层必须声明 `styles` 与 `layouts`，ID 取自 `assets/style_taxonomy.json`；
- 任务的建筑风格/空间布局不在声明范围时，`preflight` 必须 `ask`，提示“扩展模块或新建风格/布局变体”；
- 布局数据至少覆盖：功能分区、动线、家具尺度、通道净空、门窗关系；
- 风格数据至少覆盖：造型/材料/色彩/照明语汇，以及对应风格的家具与收口；
- 不得把“现代风格”的数据静默复用到“中式/日式/工业”等不同风格。

## 7. 一句话总结

> **模块 = 机器可读的数据与规则 + 人读的文档 + 可核对的来源。**
> 把本说明和 Prompt 交给 AI，让它先问清 jurisdiction 与结构类型，再查规范/工具书，
> 最后按 `ARC-001.json` + `module-architecture.md` 两份文件填；
> 没有来源的内容一律进 `open_questions`，不要变成“看起来能用”的数值。
