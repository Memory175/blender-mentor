# 验收 Profile：按项触发（V5.16.1）

> 目的：**流程统一，验收分项。**
> 建筑室内、产品硬表面、角色动画、实时资产、环境场景的验收项不同，不能一套通用检查硬套所有模型。
> Profile 只决定“验哪些项”，不提供阈值；阈值来自模块/项目实测/当地规范。

## 0. 核心原则

```text
1. 验收前先确定 primary profile
2. 一个任务最多 1 个 primary + 2 个 overlay
3. 显式 --profile 优先
4. preflight 模块映射优先于关键词
5. 关键词平局 → ask，不猜
6. 未命中 → GENERIC，不得声称“专用验收”
7. 不适用项必须写 reason，不能静默跳过
8. 覆盖率必须按 profile 统计；100% 才允许 0 FAIL
9. `check.applies_if` 为假 → 不适用，写 reason
10. 必需检查缺上下文 → ask；optional 检查缺上下文 → skip
```

## 1. 预置 profile

| ID | 名称 | 适用 |
|---|---|---|
| `INT-INTERIOR` | 建筑室内/内饰验收 | 户型、室内、软装、门洞、家具、固定系统 |
| `ARCH-EXTERIOR` | 建筑外观/体量验收 | 体量、立面、总图、楼梯、栏杆、屋顶 |
| `PROD-HARD` | 工业设计/硬表面验收 | 壁厚、拔模、悬垂、装配、干涉、重心 |
| `CHAR-RIG` | 角色/绑定/动画验收 | 拓扑形变、权重、控制器、循环、接触 |
| `ANIM-FX` | 次级动画/特效验收 | 时间、接触、包络、粒子、镜头 |
| `ENV-SCENE` | 环境/场景/道具验收 | 尺度、分布、实例、碰撞、构图 |
| `REALTIME-ASSET` | 实时/游戏资产验收 | 拓扑、UV、texel、LOD、碰撞、导出 |
| `GENERIC` | 通用验收 | 未命中专用 profile 时的兜底 |

### overlay

| ID | 名称 | 触发 |
|---|---|---|
| `LOOKDEV` | 材质/灯光/出图 | 出图、渲染、灯光、材质、最终图 |
| `DELIVERY` | 交付 | 交付、打包、导出、文件、release |

## 2. 触发优先级

```text
1. 用户显式指定
   “按建筑内饰验收” / “按产品验收” / “按游戏资产验收”

2. preflight 选中模块
   INT-001/INT-002 → INT-INTERIOR
   ENG-001        → PROD-HARD
   BIO-001        → CHAR-RIG
   ESD-001        → ANIM-FX

3. 任务关键词
   取命中 trigger 数最多、长度最长的 profile

4. 平局/多域
   返回 ask，给 2–3 个候选，不猜

5. 无命中
   GENERIC，并在报告里写明“未做专用验收”
```

## 3. 使用方式

```bash
# 自动 + 项目上下文
python scripts/acceptance_router.py --task "建筑内饰验收" \
  --context assets/acceptance_context.example.json

# 显式指定
python scripts/acceptance_router.py --task "这次按产品验收" --profile PROD-HARD \
  --context project_context.json

# 复用 preflight
python scripts/preflight.py --task "室内验收" --json .preflight.json
python scripts/acceptance_router.py --task "室内验收" --preflight .preflight.json --json .acceptance.json

# 自检
python scripts/acceptance_router.py --selftest

# 列出 profile
python scripts/acceptance_router.py --list
```

输出：

```json
{
  "decision": "proceed",
  "primary": {"id": "INT-INTERIOR", "name": "建筑室内/内饰验收"},
  "overlays": [{"id": "LOOKDEV", "name": "材质/灯光/出图覆盖"}],
  "checks": [
    {"id": "axis_grid", "layer": "L0", "severity": "BLOCKER", "tool": "layout_check.py", "coverage": "rooms"},
    {"id": "door_keepout", "layer": "L3", "severity": "BLOCKER", "tool": "layout_check.py", "coverage": "doors"}
  ],
  "coverage_required": ["rooms", "mesh_objects", "doors", "bath_doors"],
  "external_tools": [
    {"check": "axis_grid", "tool": "layout_check.py", "scope": "project"}
  ],
  "not_applicable": ["draft_angle", "wall_thickness_dfm", "weight_paint", "rig_controls"]
}
```

`external_tools` 列出项目侧/人工工具；`tool_scope: "project"` 的检查不随技能包分发，必须在项目里提供对应脚本。

### 3.1 项目上下文 `--context`

`applies_if` 让检查按项目事实启用/禁用；上下文文件示例：

```json
{
  "interior": {
    "bath": true,
    "kitchen": true,
    "fixed": true,
    "movable": true,
    "chairs": 6,
    "cameras": 10
  },
  "architecture": {"stairs": false, "railings": false, "roof": true},
  "manufacturing": {"hollow": false, "injection": false, "3d_printing": false},
  "character": {"human": false, "rigged": false}
}
```

规则：

```text
interior.bath=true       → 检查 bath_door_clear
interior.kitchen=false  → kitchen_aisle 写 N/A，不进入 coverage_required
manufacturing.injection=true → draft_angle 必需
character.human=true    → 追加 biomech
必需检查上下文缺失      → decision=ask，列出 missing_context
optional 检查上下文缺失  → skipped，原因写清楚
```

支持的条件表达式：

```text
"interior.bath"             路径为真
"!architecture.stairs"      路径为假
"manufacturing.process=injection"  字符串相等
```

省略 `--context` 时，无条件检查照常；有条件的必需检查会返回 `ask`，不会默认通过。

## 4. 验收项分层

| 层 | 含义 | 示例 |
|---|---|---|
| L0 | 数据/单位/轴网 | 房间在轮廓内、门宽、窗高 |
| L1 | 几何 | non-manifold、loose、n-gon、UV |
| L2 | 空间/部件 | AABB/BVH 碰撞、壁厚、拔模 |
| L3 | 使用/运动 | 门扇扫掠、通道、权重、接触 |
| L4 | 表现 | 相机穿模、曝光、材质缺失 |
| L5 | 交付 | 文件、manifest、导出 |

**不同 profile 只加载自己需要的层**。室内不要求拔模；产品不要求门洞；角色不要求房间面积。

## 5. 报告要求

```text
Primary: INT-INTERIOR
Overlays: LOOKDEV
Decision: proceed

Coverage:
  rooms: 17/17
  doors: 11/11
  fixed_groups: 7/7
  movable_groups: 15/15
  cameras: 10/10

FAIL: 0
WARN: 0
NOT APPLICABLE:
  draft_angle — 室内资产，不做模具
  weight_paint — 无角色
```

## 6. 与现有文件接口

```text
assets/acceptance_profiles.json   机器可读注册表
assets/acceptance_context.example.json  项目上下文示例
scripts/acceptance_router.py      选择 primary/overlay/checks + context 过滤
SKILL.md §0.8                     强制路由规则
main.md §2.12                     验收分项协议
production-pipeline.md            G0–G6 流程
model-qa.md                       通用模型层检查
module-*                          领域阈值/规则
```

## 7. 反模式

```text
室内模型查拔模
产品模型查门洞
角色模型查房间面积
没有 profile 却声称“已按室内标准验收”
profile 自己编阈值
不适用项不写 reason
缺上下文就默认通过
把 optional 检查算进覆盖率
覆盖率不到 100% 就写 0 FAIL
```

> Profile 是“验收索引”，不是“验收结论”。  
> 结论必须来自工具输出 + 覆盖率 + 人工确认。
