# 通用模块格式与预审闸门（module-governance v1）

> 目标：让「有没有参考数据」和「模块是否冲突」变成**可机器检查**的事，而不是靠模型自觉。
> 适用：`blender-mentor` 的所有通用模块（ESD/BIO/ENG 及后续新增模块）。

## 0. 三条硬规则

1. **先预审，再加载**：任何任务先跑 `preflight.py`，只有 `proceed` / `proceed_core` 才继续。
2. **无数据不编造**：模块没有的数值/标准，不得凭经验补；只能走「用户提供 / 显式假设 / 缩小范围」。
3. **冲突必停**：模块之间数值、触发、规则冲突时，不得自动按优先级裁决；必须输出冲突表并询问用户。

## 1. 文件布局

```text
references/module-<domain>.md      # 人读：原理、流程、误区
assets/modules/<ID>.json           # 机器读：元数据、数据、规则、覆盖
assets/module_registry.json        # 注册表：ID、文件、版本、sha256、状态
assets/module.schema.json          # JSON Schema（结构参考）
assets/modules/_template.json      # 新模块模板
scripts/module_governance.py       # 共享校验/冲突/选择逻辑
scripts/preflight.py               # 预审闸门（proceed / proceed_core / ask / block）
scripts/module_selftest.py         # 预审回归（10 个场景）
scripts/module_lint.py             # 格式/证据/注册表检查
scripts/module_conflict.py         # 冲突巡查
```

## 2. 模块字段

必填：`schema id version status kind domain intent coverage data rules unknown_policy`。

| 字段 | 说明 |
|---|---|
| `schema` | 固定 `mentor-module/1` |
| `id` | `AAA-001` 形式，全局唯一 |
| `version` | semver；改数据/规则必须升版本 |
| `status` | `experimental / stable / deprecated` |
| `kind` | `reference`（只有数据）/ `procedure`（只有流程）/ `hybrid` |
| `domain` | 领域标签，用于冲突判断 |
| `intent.include` | 命中词；空则模块永远不会被选中 |
| `intent.exclude` | 排除词，优先级高于 include |
| `coverage` | **能力 → 数据键**映射：任务提到哪些词时，必须有哪些数据 |
| `data` | 数值/区间；每项必须有 `source` 或 `assumption: true` |
| `rules` | 可执行检查；`evidence` 指向 `data.<key>` |
| `unknown_policy` | 缺数据时：`block` / `ask` / `proceed_with_label` |
| `requires` | 依赖模块 ID |
| `conflicts_with` | 已知冲突，必须双向声明 |
| `references` | 人读文件路径；文件内必须出现模块 ID |

### 数据项示例

```json
{
  "key": "min_wall_mm",
  "value": 1.5,
  "unit": "mm",
  "scope": "injection",
  "source": "references/module-engineering.md §3.1",
  "confidence": "high"
}
```

无来源时必须显式：

```json
{"key": "weld_leg_mm", "value": 3.0, "unit": "mm", "assumption": true, "confidence": "low"}
```

## 3. 覆盖与预审

`coverage` 是防「模块命中了但答不了」的关键：

```json
"coverage": [
  {"keywords": ["壁厚", "注塑"], "data_keys": ["min_wall_mm"]},
  {"keywords": ["拔模"], "data_keys": ["draft_min_deg"]}
]
```

预审逻辑：

```text
task → 命中模块（include/exclude）
     → 命中 coverage？
     → 所需 data_keys 是否都在 selected 模块里？
     → 模块间是否冲突？
     → decision
```

| decision | 触发条件 | 行为 |
|---|---|---|
| `proceed` | 有模块、有覆盖、无冲突 | 只加载 selected，继续 |
| `proceed_core` | 任务不需要参考模块，但命中核心教学/操作触发词 | 加载 main/rubric/课程；不加载模块，不跑模块引用审计 |
| `ask` | 冲突，或缺数据但 `unknown_policy=ask` | 停下，输出问题与选项 |
| `block` | 需要参考数据但没有模块覆盖，或 `unknown_policy=block` | 不进入执行，不编造 |

命令：

```bash
python scripts/preflight.py --task "马克杯能注塑吗？壁厚和拔模审一下" --json .preflight.json
```

退出码：`0=proceed/proceed_core`，`2=ask/block`。

## 3.1 输出引用审计

预审只保证「有数据」；交付前还要保证「输出用了数据」。规则：

- **只对 `proceed` 的模块支撑交付审计**；`proceed_core` 默认 skip，不强迫给教学帧号/面数挂模块引用；
- 带单位/百分号/角度的数字，行内必须带以下之一：
  - `[模块ID:data_key]`（模块数据）
  - `[PROJECT]` / `[MEASURED]`（项目实测：帧号、面数、采样值）
  - `[EXAMPLE]`（教学示例值）
  - `[ASSUMPTION]` / `[ASSUMPTION:原因]`（显式假设）
- 引用必须存在于本次 `preflight` 的 `data` 中，否则算 dangling；
- `audit_claims.py` 返回 `fail` 时不得交付；`--scope all` 仅用于诊断；`--warn-only` 只告警。

```bash
python scripts/audit_claims.py --text answer.md --preflight .preflight.json --json .claims.json
```

退出码：`0=pass/warn/skipped`，`1=uncited/dangling`。

## 3.2 Router 强制

`load_router.py` 默认自己跑预审；也可以传入外部结果：

```bash
python scripts/load_router.py --task "..." --preflight .preflight.json
```

- `proceed_core` / `ask` / `block` → `modules_allowed=false`，不输出任何模块文件；
- `core_allowed` 决定是否还能加载核心文件；`false` 时停止执行；
- 只加载 `preflight.selected` 里的模块；
- `--strict` → core 被阻断时 exit 2；
- `--no-preflight` 只用于诊断，正式流程禁止。

## 4. 冲突类型与处理

必须检查：

1. `duplicate_id` — 模块 ID 重复；
2. `data_value` — 同一 `key` 不同值/单位/作用域；
3. `trigger_overlap` — 多个模块声明同一触发词；
4. `conflict_asymmetry` — `conflicts_with` 单向声明；
5. `registry` — 注册表缺失、hash 不符、版本不符；
6. 格式/证据问题由 `module_lint` 报 fail。

处理协议：

```text
检测到冲突 → 停止执行
→ 输出 conflict 表（谁和谁、冲突字段、各自值）
→ 询问用户四选一：
   A. 修改现有模块（升版本）
   B. 新增 override 模块（显式 overrides，不静默覆盖）
   C. 新建独立模块（新领域）
   D. 明确放弃该检查
→ 记录 conflict_log，再重跑 lint + preflight
```

禁止：按 `priority` 自动选一个、静默覆盖、把冲突值取平均。

## 5. 新增模块 SOP

```text
1. cp assets/modules/_template.json assets/modules/NEW-001.json
2. 填 id/version/domain/intent/coverage/data/rules
3. 每个数值写 source 或 assumption
4. python scripts/module_lint.py
5. python scripts/module_conflict.py
6. 加测试：模块命中 / 缺数据 / 冲突 至少各 1 例
7. 更新 module_registry.json（含 sha256）与 load_plan
8. 更新 main.md 模块注册表与版本锚点
9. 人审 + changelog + 升 suite 版本
```

`module_lint` 会检查：

- 必填字段、ID/semver/status/kind/policy 合法性；
- data 有 `source` 或 `assumption`；
- coverage 引用的 data key 存在；
- rules 的 evidence 指向存在的数据；
- references 文件存在且提到模块 ID；
- registry hash / version 与文件一致；
- 冲突双向声明。

## 6. 禁止事项

- 不准用「经验值」填 `data` 而不标 `assumption`；
- 不准在 `preflight=block` 时继续给具体数值；
- 不准让模型自己决定「哪个模块优先」；
- 不准跳过 `module_lint` 直接改正式模块；
- 不准把 `experimental` 模块当 `stable` 发布。

## 7. 当前模块

| ID | 文件 | 覆盖 |
|---|---|---|
| `ENG-001` | `references/module-engineering.md` | 工程/制造/人体工学/装配 |
| `BIO-001` | `references/module-biomechanics.md` | 生物力学/步态/跳跃/肌肉 |
| `ESD-001` | `references/module-esd.md` | 次级动画/弹跳/形变/能量 |
