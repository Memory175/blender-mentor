#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_skill.py — 把 Blender 导师 V5.4.0 六件套重构为标准 AI Skill 目录。

用法（在能访问六件套的机器上）：
    python build_skill.py --source <V5.4.0 套件目录> --out <输出目录> [--force]
    # 省略 --source/--out 时：source="."，out="."

输入（source 下）：
    blender-mentor-v5.md
    blender-mentor-v5-rubric.md
    blender-mentor-v5-curriculum.md
    blender-mentor-v5-toolbox.md
    blender-mentor-v5-module-esd.md
    blender-mentor-v5-module-biomechanics.md
    persona_tools/  （可选但推荐：load_router.py / selftest.py /
                     sample_esd_from_blend.py / expand_esd_spec.py /
                     esd_spec.template.json / esd_sample_config.template.json /
                     deny.example.txt / load_plan.json）

输出（out 下）：
    blender-mentor/
    ├── SKILL.md
    ├── references/
    │   ├── main.md                 # 额外保留：否则身份/边界/40 条红线/模块注册表丢失
    │   ├── rubric.md
    │   ├── curriculum.md
    │   ├── toolbox_text.md         # 已剥离 python/json/bash 代码块
    │   ├── module-esd.md
    │   └── module-biomechanics.md
    ├── scripts/
    │   ├── asset_gate.py           # 从 toolbox §1 提取
    │   ├── envelope_check.py       # 从 toolbox §5 提取
    │   ├── biomech_check.py        # 从 toolbox §6 提取
    │   ├── persona_lint.py         # 从 toolbox §7 提取 + 布局补丁
    │   ├── sample_esd_from_blend.py
    │   ├── expand_esd_spec.py
    │   ├── load_router.py          # 布局补丁
    │   └── selftest.py             # 布局补丁
    └── assets/
        ├── load_plan.json
        ├── esd_sample_config.template.json
        ├── esd_spec.template.json
        ├── esd_spec.example.json   # 从 toolbox 的 json 代码块提取
        └── deny.example.txt

设计说明：
  * 脚本会断言每个补丁点都存在——套件升级后如果这些位置变了，构建会直接
    fail，而不是悄悄产出一个跑不起来的技能包。
  * 构建完成后会自动跑 persona_lint + selftest 做自检，两者都 pass 才算成功。
  * 退出码：0=成功，1=构建/自检失败，2=参数错误。
"""
import argparse
import json
import os
import re
import shutil
import sys

FILES = {
    "main": "blender-mentor-v5.md",
    "rubric": "blender-mentor-v5-rubric.md",
    "curriculum": "blender-mentor-v5-curriculum.md",
    "toolbox": "blender-mentor-v5-toolbox.md",
    "esd": "blender-mentor-v5-module-esd.md",
    "bio": "blender-mentor-v5-module-biomechanics.md",
}

# docs 复制到 references/ 后的新文件名
REF_NAMES = {
    "main": "main.md",
    "rubric": "rubric.md",
    "curriculum": "curriculum.md",
    "toolbox": "toolbox_text.md",
    "esd": "module-esd.md",
    "bio": "module-biomechanics.md",
}

# 从 toolbox 的 python 代码块里提取的脚本：标题里出现哪个文件名就存成哪个
EXTRACTED = {
    "asset_gate.py": "asset_gate.py",
    "envelope_check.py": "envelope_check.py",
    "biomech_check.py": "biomech_check.py",
    "persona_lint.py": "persona_lint.py",
}

# toolbox §2 的片段本身也是完整脚本（starter 的 curve_audit / render_probe 即由它们提取），
# 标准布局把它们一并落到 scripts/，避免「剥离代码后功能丢失」。
EXTRA_EXTRACTS = (
    ("曲线审计", "curve_audit.py"),
    ("渲染探针", "render_probe.py"),
)


def match_script(heading):
    for fname in EXTRACTED:
        if fname in heading:
            return fname
    for marker, fname in EXTRA_EXTRACTS:
        if marker in heading:
            return fname
    return None

# 这些脚本不在 md 里，来自 person_tools/；缺失时构建失败（标准布局要求 8 个脚本）
COPIED_TOOLS = [
    "sample_esd_from_blend.py",
    "expand_esd_spec.py",
    "engineering_check.py",
    "engineering_regression.py",
    "module_governance.py",
    "preflight.py",
    "module_lint.py",
    "module_conflict.py",
    "module_selftest.py",
    "audit_claims.py",
    "module_gap.py",
    "source_audit.py",
    "source_refresh.py",
    "source_selftest.py",
]

ASSET_FILES = [
    "load_plan.json",
    "esd_sample_config.template.json",
    "esd_spec.template.json",
    "deny.example.txt",
    "engineering_check.template.json",
    "module.schema.json",
    "module_registry.json",
    "module_gap_hints.json",
    "source_registry.template.json",
    "source_registry.json",
]

SKILL_MD =  r"""---
name: blender-mentor
description: Blender 全栈导师（V5.9.2：建模/拓扑/UV/材质/灯光/渲染/动画/绑定/物理/几何节点/bpy/管线；含 ESD/BIO/ENG 模块）。凡是 Blender 教学、作业批改、工程评审、资产验收、次级动画（ESD）、生物力学（BIO）或可制造性/装配/人体工学（ENG），以及用户要求「像导师一样带我 / 审我的工程 / 给我打分」时必须使用本技能。English triggers include teach me Blender, review my .blend, grade my animation, Blender mentor, critique my render or rig, design for manufacturing, draft angle, wall thickness, assembly review.
---

# Blender 全栈导师（V5.9.2 · 标准技能布局）

角色一句话：把 Blender 任务当**可交付工程**来带——先诊断，再给原理/步骤/验证；交付必须自评 + 修改清单 + 明确询问。

> `<SKILL>` = 本技能目录的绝对路径（下文命令同）；路径含空格时给命令加引号。

## 0. 预审闸门（强制，先于路由）

任何任务（教学、批改、建模、验收、问答）**第一步**都先跑：

```bash
python "<SKILL>/scripts/preflight.py" --task "<用户原话>" --json .preflight.json
```

按 `decision` 行动，不得跳过：

| decision | 含义 | 必须做什么 |
|---|---|---|
| `proceed` | 命中模块、数据覆盖完整、无冲突 | 只加载 `selected` 模块，进入 §1 路由 |
| `proceed_core` | 任务不需要参考模块，核心文档可覆盖 | 加载 main/rubric/课程等核心文件；**不加载模块**，不跑模块引用审计 |
| `ask` | 有冲突，或缺数据但可补 | **停止执行**；输出冲突表/缺数据表，等用户选：改模块 / 加 override / 补数据 / 显式假设 / 放弃 |
| `block` | 任务要求参考数据但无模块覆盖，或策略要求硬停 | **不得进入教学/建模/给数值**；按 §0.2 输出“缺什么模块 + 如何补 + 可复制 Prompt + 并入步骤” |

> `proceed_core` 只适用于核心 Blender 教学/操作任务；它不会为数值提供模块证据，因此不能拿来回答“壁厚/拔模/GRF/次级动画参数”这类模块问题。

硬规则：

1. 模块没有的数值/标准，不得凭经验补；只能标 `[ASSUMPTION]`（需用户同意）或拒绝。
2. 模块冲突不得自动按优先级裁决；必须让用户选。
3. 新增/修改模块前，必须先过 `module_lint.py` 与 `module_conflict.py`。
4. 模块格式见 `references/module-format.md`；新增模块照 `assets/modules/_template.json`。
5. 无 Python/Blender 时降级为手动检查清单，不得假装已跑过脚本。

### 0.1 输出审计（交付前）

**只对 `proceed` 的模块支撑交付执行**；`proceed_core` / `ask` / `block` 默认 skip。
带单位/百分号/角度的数字必须能追溯，否则不得交付：

```bash
python "<SKILL>/scripts/audit_claims.py" --text answer.md --preflight .preflight.json --json .claims.json
```

| 结果 | 处理 |
|---|---|
| `pass` | 可交付 |
| `warn` | 有 `[ASSUMPTION]`；必须让用户确认假设 |
| `fail` | 有 `uncited` 或 `dangling`；补引用/删数字/标假设后重跑 |
| `skipped` | 非模块支撑任务；不要强行给教学帧号/面数挂模块引用 |

引用格式：

- `[ENG-001:min_wall_mm]` —— 模块数据；
- `[PROJECT]` / `[MEASURED]` —— 项目实测（帧号、面数、采样值）；
- `[EXAMPLE]` —— 教学示例值；
- `[ASSUMPTION]` / `[ASSUMPTION:原因]` —— 显式假设。

`--scope all` 可强制审计所有任务（诊断用）；`--warn-only` 只告警不阻断。

### 0.2 缺模块时：一句话任务的标准回答

当 `preflight` 返回 `block`，且 `gap_hints` 非空（例如“我想建模一个房子”），
**不能只回答“做不到”**。先跑：

```bash
python "<SKILL>/scripts/module_gap.py" --task "<用户原话>" --json .gap.json
```

然后按固定结构回答，四段都不能少：

1. **缺哪个模块**：`ID / 名称 / 为什么缺`；
2. **需要补哪些知识**：领域拆解 + 建议权威资料类型；
3. **可复制 Prompt**：把 `prompt` 字段原样放进代码块，让用户丢给任意 AI；
4. **并入步骤**：把 `merge_steps` 列成清单（文件名、registry hash、load_plan、lint/preflight）。

若 `action=resolve_existing`，说明已有模块命中但数据/覆盖不足：
先补现有模块，不要新建重复模块。若 `action=none`，按正常流程继续。

### 0.3 标准/书籍来源时效

**新模块，或 data 里声明了 `source_id` 的模块**，必须通过 `source_id` 引用
`assets/source_registry.json`。ENG-001 / BIO-001 / ESD-001 的 data 已全部使用 `source_id`；内置 registry 将其登记为
`internal / metadata-only`，外部标准/书页码仍需另行核验。

交付前跑：

```bash
python "<SKILL>/scripts/source_audit.py" --json .source_audit.json
```

处理规则：

| 结果 | 处理 |
|---|---|
| `pass` | 来源当前、核验通过 |
| `warn` | `pending/metadata-only`、过期、缺 DOI/URL；不能支撑 fail 级结论 |
| `fail` | `withdrawn/superseded`、法规缺 `jurisdiction`、或有 `source_id` 但 registry 缺失；**停止执行** |
| `error` | 审计本身失败；按 `fail` 处理，先修复注册表 |

过期后只允许“查询 + 提议”，不自动替换：

```bash
python "<SKILL>/scripts/source_refresh.py" --offline          # 无 registry 时 skipped
python "<SKILL>/scripts/source_refresh.py" --json .source_refresh.json
```

`source_refresh` 只访问注册表允许的官方域名/Crossref；重定向目标也会校验；输出
`proposals`，**不写回 registry**。
“最新出版版”不等于“当地 adopted edition”；规范必须按 jurisdiction + 生效日期确认。

### 0.4 建模/交付质量门（通用）

任何建模、场景、资产或工程/建筑体量任务，**出结果前先过 6 道门**；不通过就说明缺什么，不要用“看起来像”交付：

1. **范围**：用途、交付物、验收项、专业边界先写清；
2. **坐标/楼层**：米制、scale 已应用；楼层用参数偏移，2F 对象不能手写 z；每层独立 collection；
3. **几何**：non-manifold=0、loose=0、n-gon 尽量 0、每个 mesh 有 UV、法线一致；
4. **构件关系**：门窗洞口/窗台/过梁、台阶/栏杆/阳台/屋顶檐沟的净空与连接；
5. **相机/出图**：默认主相机正确、相机不穿模；front/iso/detail/plan/interior 按需；
6. **交付/边界**：`.blend` + 预览 + README + 按需 GLB/OBJ；明确未做结构计算、规范、MEP。

详见 `references/model-qa.md`（通用检查表、反模式、交付前 10 问）。

## 1. 路由规则（先读对文件，不要全读）

| 用户意图 | 读这个 |
|---|---|
| 身份、边界、六段回答模板、提示分级 L1–L3、纠错/救火、40 条红线 | `references/main.md`（评审/交付前至少读 §1、§2.8、§8） |
| 评分、批改、评审、自评表、关键项与通过线 | `references/rubric.md` |
| 备课、课程、作业、前测后测、Capstone | `references/curriculum.md` |
| 报错排查、bpy、资产门、验收口径、130 条误区库 | `references/toolbox_text.md` |
| 次级动画/形变/包络/弹跳/粒子/镜头震动 | `references/module-esd.md` |
| 人体/类人/走路/跑跳/受击/动力链/肌肉体积 | `references/module-biomechanics.md` |
| 可制造性/壁厚/拔模/悬垂/装配/人体工学/重心/干涉 | `references/module-engineering.md`（ENG-001） |
| 模块格式/预审/冲突/新增模块 | `references/module-format.md` + `assets/module_registry.json` |
| 写新模块 / 让 AI 查资料填表 / 单层小房子模块 | `references/module-authoring.md` |
| 建模/交付前的通用质量门、反模式、10 问 | `references/model-qa.md` |

加载规则：模块最多同时 2 个；`main.md` 与 `rubric.md` 不裁剪；超预算裁剪顺序
curriculum → toolbox_text → 非当前任务模块。
需要机器清单时，必须先预审再路由：

```bash
python "<SKILL>/scripts/preflight.py" --task "<用户原话>" --json .preflight.json
python "<SKILL>/scripts/load_router.py" --task "<用户原话>" --preflight .preflight.json
```

`load_router.py` 只加载 `preflight` 选中的模块；若输出 `modules_allowed=false`，
**不得加载任何模块**。`proceed_core` 时仍可加载 main/rubric/curriculum，但不加载模块。
`status=blocked` / `core_allowed=false` 时停止执行，回到 §0 处理缺数据/冲突。
`--strict` 会在 core 被阻断时 exit 2，可用于自动化。
`.preflight.json` 是本次任务的临时文件，不要提交到仓库。
用户明确只要生产结果、不要教学时，可跳过教学流程，但交付仍须走 D2–D4。

## 2. 交付闭环（D1 → D4，强制）

- **D1 交付**：文件/链接 + 规格 + 复现命令。
- **D2 自评**：对**产物**采样（数值/截图/日志/fcurve/渲染探针），同时写通过项与未修项；
  禁止用生成器常量、参数表、自证 spec 当证据；按 `references/rubric.md` §11 出表。
- **D3 修改清单**：每条含编号（P0/P1/P2）、问题、证据、修法、成本/风险、建议顺序；
  至少 3 项、最多 8 项，区分“路线性缺陷”与“打磨项”。
- **D4 询问**（固定选项，不许开放式追问）：

```text
下一步选一个：
A. 全改（P0+P1+P2，分轮执行）
B. 只改 P0
C. 只改指定项（报编号）
D. 不改，交付验收完成
E. 换方向（重新定义目标）
```

用户不回复修改指令 = 视为 D，不擅自继续修改。

## 3. 机器验收命令

> `<SKILL>` 见文首定义。

| 场景 | 命令 |
|---|---|
| 资产门（场景/网格/贴图/动画/物理/输出） | `blender -b file.blend --python <SKILL>/scripts/asset_gate.py -- --json out.json` |
| 曲线审计（插值/手柄统计） | `blender -b file.blend --python <SKILL>/scripts/curve_audit.py` |
| 渲染探针（输出 `//probe.png`） | `blender -b file.blend --python <SKILL>/scripts/render_probe.py` |
| 包络断言（ESD spec 自洽） | `python <SKILL>/scripts/envelope_check.py spec.json` |
| ESD 模板展开 | `python <SKILL>/scripts/expand_esd_spec.py <SKILL>/assets/esd_spec.template.json --base 6.0 -o esd_spec.json` |
| ESD 从 .blend 采样 | `blender -b scene.blend --python <SKILL>/scripts/sample_esd_from_blend.py -- --config cfg.json --out spec.json` |
| 生物力学验收 | `blender -b scene.blend --python <SKILL>/scripts/biomech_check.py -- --eccentric F0,F1 --support A-B --airtime T,L --height H`（人体/类人动画**必须跑**；退出码 0=pass，1=fail/incomplete，不得判通过） |
| 工程预检（稳定性/壁厚/拔模/悬垂/干涉） | `blender -b file.blend --python <SKILL>/scripts/engineering_check.py -- --json eng.json`（规则预检，不能替代 FEA） |
| 套件结构门 | `python <SKILL>/scripts/persona_lint.py <SKILL> --allow-no-deny` |
| 工具链自检 | `python <SKILL>/scripts/selftest.py <SKILL>` |

数据与模板：`assets/esd_spec.template.json`（模板）、`assets/esd_spec.example.json`
（虚构示例）、`assets/esd_sample_config.template.json`（采样配置）、
`assets/engineering_check.template.json`（工程预检配置）、
`assets/load_plan.json`（加载规则）、`assets/deny.example.txt`（拒绝词模板）。

`persona_lint.py` 默认 strict：发布验收用 `--deny <项目侧 deny.txt>`（先把
`assets/deny.example.txt` 复制成项目侧 `deny.txt` 并填真实正则）；只做结构检查用
`--allow-no-deny`。路径含空格时给命令加引号。

## 4. 版本与治理

- 套件 **V5.9.2**；改动 `references/` 后必须重跑 `persona_lint.py`。
- 项目日志、帧号、实测值只写项目目录，不写入人设文件；只有用户明确说“写入人设”才允许修改。
- `references/toolbox_text.md` 已剥离内嵌代码：脚本统一在 `scripts/`，数据在 `assets/`。
"""


README_EN_MD =  r"""# Blender Mentor

**Turn Claude Code / DSH / Cursor into a senior Blender mentor + technical director.**

It diagnoses your level, teaches a structured lesson, grades your work with a 0–3 rubric, and runs machine acceptance on your `.blend` — assets, curves, renders, ESD secondary animation, and biomechanics.

**English** | [简体中文](README.zh-CN.md)

[![validate-skill](https://github.com/OWNER/REPO/actions/workflows/validate.yml/badge.svg)](https://github.com/OWNER/REPO/actions)
[![release](https://img.shields.io/github/v/release/OWNER/REPO?color=2f81f7)](https://github.com/OWNER/REPO/releases)
[![license](https://img.shields.io/github/license/OWNER/REPO?color=3fb950)](https://github.com/OWNER/REPO/blob/main/LICENSE)
[![last commit](https://img.shields.io/github/last-commit/OWNER/REPO?color=8b5cf6)](https://github.com/OWNER/REPO/commits/main)
[![Blender](https://img.shields.io/badge/Blender-4.2%20LTS%20%7C%205.x-orange)](https://www.blender.org/download/)

## What it looks like

```text
you    › Review this walk cycle. Grade it with the rubric and give me a P0/P1/P2 fix list.

mentor › L2 · Review mode · score 2.1 / 3 — critical: foot sliding
         P0  Lock contact frames 1 / 13 / 25; add heel roll.
         P1  Reduce hip Y translation 18%; clean shoulder counter-rotation.
         P2  Add toe flex on push-off; re-check the 12-frame cadence.
         acceptance  asset_gate PASS · curve_audit 3 warnings · render_probe PASS
```

![Example session: prompt, rubric score, P0/P1/P2 fixes, machine acceptance](docs/demo.svg)

> **Not a Blender add-on.** The skill gives your AI agent the mentor's playbook. It can generate commands and, when the host has shell/Blender access (or an MCP bridge), run `blender -b ... --python ...` automatically. Without that access it cannot operate Blender's UI for you. You still need Blender installed to open `.blend` files and run acceptance checks (see [Requirements](#requirements)).

## Rubric at a glance

| Score | Meaning | Walk-cycle example |
|---|---|---|
| **0** | A critical item vetoes the delivery | foot sliding → 0, not deliverable regardless of the other items |
| **2** | Shippable | contacts locked, no interpenetration |
| **3** | Production-ready | contacts locked + heel roll + reusable cadence |

Full scoring anchors and self-review template: [`references/rubric.md`](references/rubric.md).

## Quick start

**DSH** — clone and install (Windows / Linux / macOS / WSL):

```bash
git clone --depth 1 https://github.com/OWNER/REPO.git
cd blender-mentor

# Windows
powershell -NoProfile -ExecutionPolicy Bypass -File dsh/install.ps1

# Linux / macOS / WSL
bash dsh/install.sh
```

**Claude Code** — install as a plugin:

```text
/plugin marketplace add OWNER/REPO
/plugin install blender-mentor@blender-mentor-marketplace
```

**Cursor / other Agent Skills clients** — clone the repo and point your client at `SKILL.md` (in Cursor, mention `@SKILL.md`; for an always-on rule, add a project rule that references it).

Then open a new agent session and try:

```text
Use blender-mentor to walk me through M1 modeling and topology.
```

## What you get

| Component | What it does |
|---|---|
| **Mentor behavior** | L0–L3 level diagnosis; explain / coach / accept / firefight / review modes |
| **D1–D4 delivery loop** | deliver → self-review → P0/P1/P2 fix list → explicit next-step question |
| **0–3 rubric** | critical items, scoring anchors, and a self-review template |
| **Engineering precheck (ENG-001)** | stability, wall thickness, draft, overhang/support, interference, clearance |
| **M0–M6 curriculum** | modeling & topology → UV/materials/lighting/render → animation/rigging → physics/geometry nodes/pipeline |
| **22 executable tools** | 6 `.blend` acceptance scripts + engineering precheck + module governance (preflight/lint/conflict/claim audit) + source governance (audit/refresh) + regression/routing tools |
| **Delivery QA gate** | floors/coordinates, mesh/UV, camera/export, professional-boundary checks |
| **Knowledge base** | 130 common misconceptions + 40 red lines |

## Requirements

| Requirement | Needed for |
|---|---|
| Blender 4.2 LTS / 5.x | `.blend` acceptance scripts (`blender -b ... --python scripts/...`) |
| Python 3 | `selftest.py`, `persona_lint.py`, `load_router.py`, `preflight.py` |
| Optional: shell or Blender MCP/RT bridge | Automatic script execution; without it, copy commands into Blender Scripting or a terminal manually |

## How it works

```text
SKILL.md       routing + D1–D4 delivery loop + machine-acceptance commands
references/    10 reference files (7 persona docs + module format + authoring guide + model QA), loaded on demand
scripts/       22 executable tools
assets/        ESD templates, load plans, deny-word example, source registry template
```

1. `SKILL.md` routes the request and sets the delivery loop.
2. `preflight.py` classifies it: `proceed` (module-backed), `proceed_core` (teaching/operations, no module needed), `ask`, or `block` (reference data required but not covered).
3. `load_router.py` builds a per-task load plan and only loads modules selected by preflight; `proceed_core` tasks get core docs, never modules.
4. `source_audit.py` checks standards/books/papers before module-backed delivery: TTL, withdrawn/superseded, and missing jurisdiction block.
5. Acceptance scripts run against your local `.blend` through headless Blender.
6. Your files stay local; the acceptance tools do not upload anything.

<details>
<summary><strong>Advanced installation</strong></summary>

### Claude.ai

Zip the skill folder (`SKILL.md` + `references/`, `scripts/`, `assets/`) and add it to your Skills library.

### DSH plugin market

This repository is also a DSH skill plugin: `package.json` declares `dsh.bundle.patch → cordis.patch.yml`, which mounts the bundled `skills/blender-mentor/`. After the dsh.so listing is approved:

```bash
dsh plugin --profile web add github:OWNER/REPO
```

### Downloadable installers

`dsh-install.ps1` and `dsh-install.sh` are attached to the [latest release](https://github.com/OWNER/REPO/releases/latest); download and run them if you prefer not to clone.

</details>

<details>
<summary><strong>Repository layout</strong></summary>

```text
.
├── SKILL.md                     # Agent Skill entry point (required)
├── README.md / README.zh-CN.md  # English / 简体中文
├── LICENSE                      # MIT
├── CHANGELOG.md
├── package.json                 # DSH plugin manifest (dsh.bundle.patch)
├── cordis.patch.yml             # DSH Cordis patch (skill-filesystem provider)
├── lib/index.js                 # DSH plugin adapter
├── skills/blender-mentor/       # DSH bundled skill (generated)
├── .claude-plugin/marketplace.json
├── plugins/blender-mentor/      # Claude Code plugin wrapper (generated)
├── dsh/install.ps1 / install.sh # DSH one-line installers
├── references/                  # 10 reference files (7 persona docs + module format + authoring guide + model QA)
├── scripts/                     # 22 executable tools
├── assets/                      # ESD templates, load plans, deny example
├── docs/                        # banner + example session image
└── tools/build_skill.py         # maintainer build tool
```

</details>

## FAQ

**Is this a Blender add-on?**
No. It is an Agent Skill: instructions + scripts that an AI client loads. Blender itself is a separate install.

**Do I need Blender installed?**
For teaching, critique, and planning: no. For opening `.blend` files, rendering probes, and machine acceptance: yes, Blender 4.2 LTS / 5.x.

**Does it control the Blender GUI?**
No. It writes and runs bpy/headless scripts and reviews the artifacts you provide; it does not click through the interface.

**Is my `.blend` uploaded?**
No. Acceptance scripts run locally and print JSON/text; they do not upload files.

**How do you keep standards/books current?**
New modules, or modules that declare a `source_id`, reference `assets/source_registry.json`. `source_audit.py` checks TTL, `withdrawn`/`superseded`, and missing jurisdiction; `source_refresh.py` queries official catalogs/Crossref but only proposes changes. All shipped module data now use `source_id`; the built-in registry maps them to module reference sections as `internal / metadata-only`, so external standards/books still need page-checking. “Latest published” is not “locally adopted”: codes stay tied to jurisdiction and effective edition.

**Which clients are supported?**
DSH, Claude Code, Claude.ai, Cursor, and any client that supports the standard Agent Skills layout (`SKILL.md` + resources).

**What do the two version numbers mean?**
The persona suite is **V5.9.2**; the packaged skill release is **v5.9.2**.

## Development

```bash
python -m compileall -q scripts tools
python scripts/persona_lint.py . --allow-no-deny   # structure gate
python scripts/selftest.py .                       # 27 pass + 1 skipped
```

Blender-side checks:

```bash
blender -b file.blend --python scripts/asset_gate.py -- --json gate.json
blender -b scene.blend --python scripts/biomech_check.py -- --eccentric 1,4 --support 1-4
```

Rebuild the skill directory:

```bash
python tools/build_skill.py --source <V5.9.2 suite> --out <repo parent> --force
```

## License

MIT — see [LICENSE](LICENSE). Third-party references in the course documents are cited only; copyright remains with their authors.

---

If this saves you time, a ⭐ helps others find it · [Report an issue](https://github.com/OWNER/REPO/issues) · [Releases](https://github.com/OWNER/REPO/releases)
"""


README_ZH_MD =  r"""# Blender Mentor

**把 Claude Code / DSH / Cursor 变成一位 Blender 资深导师 + 技术总监。**

先诊断你的水平，再用结构化课程带你做；交付后用 0–3 评分表打分，并对你的 `.blend` 跑机器验收——资产、曲线、渲染、ESD 次级动画、生物力学。

**简体中文** | [English](README.md)

[![validate-skill](https://github.com/OWNER/REPO/actions/workflows/validate.yml/badge.svg)](https://github.com/OWNER/REPO/actions)
[![release](https://img.shields.io/github/v/release/OWNER/REPO?color=2f81f7)](https://github.com/OWNER/REPO/releases)
[![license](https://img.shields.io/github/license/OWNER/REPO?color=3fb950)](https://github.com/OWNER/REPO/blob/main/LICENSE)
[![last commit](https://img.shields.io/github/last-commit/OWNER/REPO?color=8b5cf6)](https://github.com/OWNER/REPO/commits/main)
[![Blender](https://img.shields.io/badge/Blender-4.2%20LTS%20%7C%205.x-orange)](https://www.blender.org/download/)

## 实际效果

```text
你   › 帮我审这个走路循环，按评分表打分并给 P0/P1/P2 修改清单。

导师 › L2 · Review 模式 · 评分 2.1 / 3 — 关键项：脚底滑动
       P0  锁定 1 / 13 / 25 帧接触点；补脚跟滚动。
       P1  髋部 Y 位移减少 18%；清理肩部反向旋转。
       P2  蹬地阶段加脚趾弯曲；重新核对 12 帧步频。
       验收  asset_gate PASS · curve_audit 3 warnings · render_probe PASS
```

![示例会话：提问、评分、P0/P1/P2 修改清单、机器验收](docs/demo.svg)

> **这不是 Blender 插件。** 技能给 AI 客户端装上导师的“工作手册”。当宿主有 shell/Blender 执行权限（或 MCP 桥接）时，它可以自动跑 `blender -b ... --python ...`；没有这些条件时，它只能生成命令，不能替你操作 Blender 界面。打开 `.blend` 和跑验收脚本仍然需要你本机安装 Blender（见[环境要求](#环境要求)）。

## 评分速览

| 分数 | 含义 | 走路循环示例 |
|---|---|---|
| **0** | 关键项一票否决 | 脚底滑动 → 0 分，无论其他项多好都不通过 |
| **2** | 达标、可交付 | 接触点锁定、无穿帮 |
| **3** | 生产级 | 接触点锁定 + 脚跟滚动 + 步频可复用 |

完整评分锚点与自评模板：[`references/rubric.md`](references/rubric.md)。

## 快速开始

**DSH** — 克隆并安装（Windows / Linux / macOS / WSL）：

```bash
git clone --depth 1 https://github.com/OWNER/REPO.git
cd blender-mentor

# Windows
powershell -NoProfile -ExecutionPolicy Bypass -File dsh/install.ps1

# Linux / macOS / WSL
bash dsh/install.sh
```

**Claude Code** — 作为插件安装：

```text
/plugin marketplace add OWNER/REPO
/plugin install blender-mentor@blender-mentor-marketplace
```

**Cursor / 其他 Agent Skills 客户端** — 克隆仓库，让你的客户端加载 `SKILL.md`（Cursor 里可用 `@SKILL.md`；想常驻就加一条指向它的项目规则）。

然后新开一个 agent 会话，直接说：

```text
用 blender-mentor 带我过 M1 建模与拓扑。
```

## 包含什么

| 组成 | 作用 |
|---|---|
| **导师行为** | L0–L3 水平诊断；讲解 / 教练 / 验收 / 救火 / 评审 五种模式 |
| **D1–D4 交付闭环** | 交付 → 自评 → P0/P1/P2 修改清单 → 明确的下一步问题 |
| **0–3 评分表** | 关键项、评分锚点、自评模板 |
| **工程预检（ENG-001）** | 稳定性、壁厚、拔模、悬垂/支撑、干涉、配合间隙 |
| **M0–M6 课程包** | 建模与拓扑 → UV/材质/灯光/渲染 → 动画/绑定 → 物理/几何节点/管线 |
| **22 个可执行工具** | 6 个 `.blend` 验收脚本 + 工程预检 + 模块治理（预审/lint/冲突/引用审计）+ 来源治理（审计/查询）+ 回归/路由工具 |
| **交付质量门** | 楼层/坐标、mesh/UV、相机/导出、专业边界检查 |
| **知识库** | 130 条常见误区 + 40 条红线 |

## 环境要求

| 需要 | 用途 |
|---|---|
| Blender 4.2 LTS / 5.x | `.blend` 验收脚本（`blender -b ... --python scripts/...`） |
| Python 3 | `selftest.py`、`persona_lint.py`、`load_router.py`、`preflight.py` |
| 可选：shell 或 Blender MCP/RT 桥接 | 自动执行脚本；没有时需手动把命令粘到 Scripting 或终端 |

## 工作原理

```text
SKILL.md       路由 + D1–D4 交付闭环 + 机器验收命令
references/    10 个参考文件（7 份人设文档 + 模块格式 + 写作说明 + 建模质量门），按需加载
scripts/       22 个可执行工具
assets/        ESD 模板、加载清单、拒绝词示例、来源注册表模板
```

1. `SKILL.md` 负责路由，并设定交付闭环。
2. `preflight.py` 先分类：`proceed`（模块支撑）、`proceed_core`（教学/操作，无需模块）、`ask`、`block`（需要参考数据但无模块覆盖）。
3. `load_router.py` 生成该任务的加载清单，只加载预审选中的模块；`proceed_core` 只加载核心文档，不加载模块。
4. `source_audit.py` 在模块交付前检查标准/书籍/论文：TTL、withdrawn/superseded、缺 jurisdiction 会阻断。
5. 验收脚本通过无头 Blender 操作你本地的 `.blend`。
6. 文件不出本机；验收工具不会上传任何内容。

<details>
<summary><strong>高级安装方式</strong></summary>

### Claude.ai

把技能目录（`SKILL.md` + `references/`、`scripts/`、`assets/`）打成 zip，上传到 Skills 库。

### DSH 插件市场

本仓库同时是 DSH 技能插件：`package.json` 声明 `dsh.bundle.patch → cordis.patch.yml`，挂载内置的 `skills/blender-mentor/`。dsh.so 收录通过后可用：

```bash
dsh plugin --profile web add github:OWNER/REPO
```

### 下载安装脚本

`dsh-install.ps1` / `dsh-install.sh` 已附在 [latest release](https://github.com/OWNER/REPO/releases/latest)；不想 clone 时可直接下载运行。

</details>

<details>
<summary><strong>仓库结构</strong></summary>

```text
.
├── SKILL.md                     # Agent Skill 入口（必须）
├── README.md / README.zh-CN.md  # English / 简体中文
├── LICENSE                      # MIT
├── CHANGELOG.md
├── package.json                 # DSH 插件清单（dsh.bundle.patch）
├── cordis.patch.yml             # DSH Cordis 补丁（skill-filesystem provider）
├── lib/index.js                 # DSH 插件适配器
├── skills/blender-mentor/       # DSH 内置技能（自动生成）
├── .claude-plugin/marketplace.json
├── plugins/blender-mentor/      # Claude Code 插件包装（自动生成）
├── dsh/install.ps1 / install.sh # DSH 一键安装脚本
├── references/                  # 10 个参考文件（7 份人设文档 + 模块格式 + 写作说明 + 建模质量门）
├── scripts/                     # 22 个可执行工具
├── assets/                      # ESD 模板、加载清单、拒绝词示例
├── docs/                        # banner + 示例会话图
└── tools/build_skill.py         # 维护侧构建工具
```

</details>

## 常见问题

**这是 Blender 插件吗？**
不是。它是 Agent Skill：给 AI 客户端加载的指令 + 脚本；Blender 需要另外安装。有 shell/MCP 时它可自动执行无头脚本，但没有桥接时不能操作 Blender GUI。

**需要先装 Blender 吗？**
只做教学、点评和规划不需要；要打开 `.blend`、跑渲染探针和机器验收时需要 Blender 4.2 LTS / 5.x。

**它会控制 Blender 界面吗？**
不会。它编写并执行 bpy/无头脚本，审查你提供的产物；不会替你点鼠标建模。

**我的 `.blend` 会被上传吗？**
不会。验收脚本在本机运行，输出 JSON/文本，不上传文件。

**怎么保证标准/书籍是最新的？**
新模块，或声明了 `source_id` 的模块，通过 `source_id` 引用 `assets/source_registry.json`。`source_audit.py` 检查 TTL、`withdrawn`/`superseded`、缺 jurisdiction；`source_refresh.py` 查官方目录/Crossref，但只提议、不自动替换。现有模块的 data 已全部使用 `source_id`；内置 registry 将其登记为 `internal / metadata-only`，外部标准/书页码仍需另行核验。“最新出版版”不等于“当地 adopted edition”：规范必须绑定 jurisdiction 和生效版次。

**支持哪些客户端？**
DSH、Claude Code、Claude.ai、Cursor，以及任何支持标准 Agent Skills 布局（`SKILL.md` + 资源目录）的客户端。

**两个版本号是什么意思？**
人设套件为 **V5.9.2**；打包后的技能发布版本为 **v5.9.2**。

## 开发与验证

```bash
python -m compileall -q scripts tools
python scripts/persona_lint.py . --allow-no-deny   # 结构门
python scripts/selftest.py .                       # 27 pass + 1 skipped
```

Blender 侧检查：

```bash
blender -b file.blend --python scripts/asset_gate.py -- --json gate.json
blender -b scene.blend --python scripts/biomech_check.py -- --eccentric 1,4 --support 1-4
```

重建技能目录：

```bash
python tools/build_skill.py --source <V5.9.2 套件目录> --out <仓库父目录> --force
```

## 许可

MIT，见 [LICENSE](LICENSE)。课程文档中的第三方参考书目仅作引用，版权归原作者。

---

如果这个技能帮你省了时间，点个 ⭐ 能让更多人找到它 · [反馈问题](https://github.com/OWNER/REPO/issues) · [Release](https://github.com/OWNER/REPO/releases)
"""


CHANGELOG_MD =  r"""# Changelog

## V5.9.2 — 2026-10-20

> 通用建模/交付质量门；人设套件升 **V5.9.2**。

### Added
- `references/model-qa.md`：通用质量门（坐标/楼层、构件净空、mesh/UV、相机/出图、交付边界、来源治理、反模式、交付前 10 问）；
- `SKILL.md §0.4`：6 道建模/交付质量门 + 路由；
- `selftest`：新增 `model_qa_reference` 检查（27 项）。

### Changed
- README 参考文件数 9 → 10；selftest 计数 26 → 27；
- 模型层问题不再依赖“看图发现”，改为交付前检查表。

## V5.9.1 — 2026-10-20

> 模板补丁；人设套件升 **V5.9.1**。

### Fixed
- `assets/modules/_template.json`：data 示例增加 `source_id` + `verification`，新模块不再漏掉来源治理字段。

## V5.9.0 — 2026-10-20

> 模块来源治理落地；人设套件升 **V5.9.0**。

### Added
- `assets/source_registry.json`：15 条内部模块参考来源（internal / metadata-only）；
- ENG-001 / BIO-001 / ESD-001 每个 data 增加 `source_id`；
- 三个模块文档增加“来源注册”附录。

### Changed
- 模块版本：ENG-001 **1.1.0**、BIO-001 **1.1.0**、ESD-001 **1.1.9**；
- README/SKILL/module-format 改为“所有内置模块已接 source_id”，不再称现有模块为 legacy；
- `persona_lint` / `source_audit` 覆盖内置 registry：`source_audit` 状态为 `warn`（internal/metadata-only，外部标准未核）。

## V5.8.2 — 2026-10-20

> 来源治理 fail-closed 修复；人设套件升 **V5.8.2**。

### Fixed
- `preflight`：`source_audit` 返回 `error` 时也进入 `ask`，不再 fail-open；
- `source_audit`：有 `source_id` 但 registry 缺失/不可读 → `fail`，不再 `skipped`；
- `source_refresh`：无 registry → `skipped`（exit 0），不再报错；`--json` 也写 skipped；
- `source_refresh`：DOI 分支提前，不再依赖 `check_url`；
- `source_refresh`：重定向目标必须仍在 allowlist 内；
- `module_gap` Prompt 要求 `source_id` + `assets/source_registry.json`；
- `module.schema.json` / `module_lint` 支持 `source_id`；
- `module-format.md` 明确 source_id（新）与 source（legacy）；
- `source_selftest` 扩展到 **11** 项（缺 registry / DOI / 重定向 / source_id lint / preflight error）。

### Changed
- README/README.zh-CN 明确现有 ENG/BIO/ESD 为 legacy；README 工具分类改为 6 个 `.blend` 验收脚本。

## V5.8.1 — 2026-10-20

> 文档补丁；人设套件升 **V5.8.1**。

### Fixed
- README/README.zh-CN：技能包版本从 v5.6.1 修正为 v5.8.1；
- selftest 计数 24 → **26**；
- 工具说明加入 source governance（source_audit/source_refresh）；
- How it works 加入来源审计步骤；
- FAQ 新增“标准/书籍如何保持最新”，强调 latest published ≠ locally adopted。

## V5.8.0 — 2026-10-20

> 人设套件升 **V5.8.0**：来源治理层（Source Governance）。

### Added
- `scripts/source_audit.py`：TTL / withdrawn / superseded / pending / 法规缺 jurisdiction 检查；
- `scripts/source_refresh.py`：官方域名 + Crossref 查询，只输出 proposals，不自动替换；
- `scripts/source_selftest.py`：5 个来源审计回归；
- `assets/source_registry.template.json`：来源注册表模板；
- `SKILL.md §0.3`、`references/module-authoring.md §6.5`：来源时效规则；
- `preflight` 接入来源审计：fail → ask；
- `load_plan` 增加 source_audit/source_refresh。

### Changed
- 模块数据通过 `source_id` 引用来源注册表；`withdrawn/superseded` 或缺 jurisdiction 不得继续；
- `selftest` 扩展到 **26 项**；`source_selftest` 5 个场景。

## V5.7.0 — 2026-10-20

> 文档补丁；人设套件升 **V5.7.0**。

### Added
- `references/module-authoring.md`：模块写作格式、单层住宅知识拆解、
  可复制给任意 AI 的查资料/填表 Prompt、插入与验收流程；
- `SKILL.md` 路由新增“写新模块 / 让 AI 查资料填表 / 单层小房子模块”；
- `references/module-format.md` 增加写作说明入口。

### Changed
- 参考文件数 8 → 9；版本锚点升 V5.7.0。
- 无代码/模块数据变更，无需升模块版本。

## V5.6.1 — 2026-10-20

> 本地修复（未发布）；针对 V5.6.0 评审报告的两个 P0 与 P1/P2。

### Fixed
- **P0-1**：`preflight` 新增 `proceed_core`，普通教学/操作任务不再被 `block`；
  只有“需要参考数据但无模块覆盖”才 `block/ask`。
- **P0-2**：`audit_claims` 默认只审计 `proceed` 的模块支撑交付；
  `proceed_core` 自动 `skipped`；新增 `[PROJECT]`/`[MEASURED]`/`[EXAMPLE]` 标签。
- **P1**：ASCII 触发词改用词边界（COM 不再命中 compare）；
  ESD 排除 UV/拓扑；补英文触发词；焊接移出 ENG include（无数据不伪装覆盖）；
  `--json` 写盘失败不再 traceback；router 支持 `core_allowed`。
- **P2**：修正 `main.md` ENG-001 历史版本标签、module-format 场景数、README 参考文件数；
  文档补 `--warn-only`、审计同行规则、Python/Blender 降级说明。

### Changed
- `selftest` 扩展到 **24 项**；`module_selftest` 扩展到 **10 个场景**。

## V5.6.0 — 2026-10-20

> 人设套件升 **V5.6.0**：新增通用模块治理层（预审 → 路由 → 引用审计）。

### Added
- `references/module-format.md`：模块格式、证据要求、冲突协议、新增模块 SOP；
- `assets/module.schema.json` / `assets/module_registry.json` / `assets/modules/*.json`；
- `scripts/preflight.py`：`proceed / ask / block` 预审闸门；
- `scripts/module_lint.py` / `module_conflict.py` / `module_selftest.py`；
- `scripts/audit_claims.py`：输出数字必须带模块引用或 `[ASSUMPTION]`。

### Changed
- `load_router.py` 强制接预审：`modules_allowed=false` 时不加载任何模块；
- `SKILL.md` 新增 §0 预审、§0.1 输出审计、§1 预审后路由；
- `selftest` 扩展到 **21 项**。

## V5.5.1 — 2026-10-20

> 打包修复；人设套件仍为 **V5.5.0**。

### Fixed
- 安装包/技能 zip 未携带 `tests/engineering` 时，`selftest` 不再判 fail：
  `engineering_regression_assets` 改为 skip（回归测试仅随仓库分发）。

## V5.5.0 — 2026-10-20

> 人设套件升 **V5.5.0**：新增通用模块 **ENG-001 工业设计与可制造性**。

### Added
- `references/module-engineering.md`（ENG-001 v1.0.0）：力学/制造/人体工学/装配；
- `scripts/engineering_check.py`：稳定性、壁厚、分侧拔模、悬垂面积/支撑体积、干涉、间隙预检；
- `scripts/engineering_regression.py` + `tests/engineering/`：3 个固定场景回归；
- `assets/engineering_check.template.json`（eng-check/3 配置）；
- 路由/加载计划/`persona_lint`/`selftest` 接入 ENG-001。

### Changed
- 人设套件版本 V5.5.0；`SKILL.md` 描述增加可制造性触发词；
- `selftest` 扩展为 17 项（新增工程脚本编译与回归资产检查）。

## V5.4.5 — 2026-10-20

> 技能包发布版本；人设套件版本仍为 **V5.4.0**（六件套版本锚点不变）。

### Changed
- 新增 Last commit 徽章；
- 收掉重复：Blender 版本只在 Requirements 表声明，移除 Requirements 中的客户端行；
- 保持 Quick start 默认顺序：DSH → Claude Code → Cursor；
- 版本升至 `5.4.5`。

## V5.4.4 — 2026-10-20

> 技能包发布版本；人设套件版本仍为 **V5.4.0**（六件套版本锚点不变）。

### Changed
- 首屏新增纯文本示例会话（不依赖图片加载）；
- 新增“评分速览”：0 分一票否决 / 2 分达标 / 3 分生产级；
- 合并 Quick start 与安装章节，删除重复命令与重复的客户端/Blender 说明；
- 版本升至 `5.4.4`。

## V5.4.3 — 2026-10-20

> 技能包发布版本；人设套件版本仍为 **V5.4.0**（六件套版本锚点不变）。

### Changed
- README 重写为转化优先结构：首屏价值主张、Quick Start、示例输出、Requirements、FAQ、CTA；
- 新增 `docs/demo.svg` 示例会话图（问题 → 评分 → P0/P1/P2 → 机器验收）；
- 明确“不是 Blender 插件、验收需本机 Blender”，补充 Requirements 与 FAQ；
- 仓库结构与维护者命令收进 `<details>`，安装说明主路径化；
- `package.json` / 插件清单版本升至 `5.4.3`。

## V5.4.2 — 2026-10-19

> 技能包发布版本；人设套件版本仍为 **V5.4.0**（六件套版本锚点不变）。

### Added
- DSH 插件清单：根 `package.json`（`dsh.bundle.patch`）、`cordis.patch.yml`、
  `lib/index.js`、`skills/blender-mentor/`，满足 dsh.so 插件市场检查；
- DSH 一键安装：`dsh/install.ps1` / `dsh/install.sh`（自动 clone、备份旧版、安装后自检）；
- Claude Code 插件市场：`.claude-plugin/marketplace.json` + `plugins/blender-mentor/`，
  可用 `/plugin marketplace add` + `/plugin install` 一键安装；
- README banner 与社交预览图：`docs/banner.png`、`docs/social-preview.png`；
- GitHub topics：`dsh-plugin`、`agent-skills`、`claude-skill` 等。

### Changed
- Release 附件改为与 `main` 对齐的双包：完整仓库包 `blender-mentor-v5.4.2.zip` +
  技能包 `blender-mentor-skill-v5.4.2.zip`；
- `package.json` / 插件清单版本升至 `5.4.2`。

## V5.4.1 — 2026-10-19

> 技能包发布版本；人设套件版本仍为 **V5.4.0**（六件套版本锚点不变）。

### Changed
- 双语 README：English（`README.md`，默认）+ 简体中文（`README.zh-CN.md`），顶部互加语言跳转；
- Release 说明改为中英双语；
- 发布附件更新为含双语 README 的 `v5.4.1` 技能包；
- Claude Code 插件支持：`.claude-plugin/marketplace.json` + `plugins/blender-mentor/`，
  可用 `/plugin marketplace add` + `/plugin install` 一键安装；
- DSH 一键安装：`dsh/install.ps1` / `dsh/install.sh`（自动 clone、备份旧版、安装后自检）；
- DSH 插件清单：根 `package.json`（`dsh.bundle.patch`）、`cordis.patch.yml`、
  `lib/index.js`、`skills/blender-mentor/`，满足 dsh.so 插件市场检查；
- 仓库源码快照（tag `v5.4.1`）包含全部文档/工具更新。

### Fixed
- Release 附件与 `main` 分支内容不一致的问题（此前 `v5.4.0` 附件早于双语 README）。

## V5.4.0 — 2026-10-19

### Added
- 标准 Agent Skill 布局：`SKILL.md` + `references/` + `scripts/` + `assets/`；
- `scripts/curve_audit.py`、`scripts/render_probe.py`（从 toolbox §2.2/§2.6 提取）；
- `scripts/load_router.py`、`scripts/selftest.py`、`scripts/expand_esd_spec.py`、`scripts/sample_esd_from_blend.py`；
- `tools/build_skill.py`（仓库自包含的构建工具：从 V5.4.0 六件套重建本技能）；
- `assets/esd_spec.example.json`（从 toolbox 的 json 示例提取）；
- GitHub 仓库配套：README、LICENSE、CHANGELOG、`.gitignore`、CI（结构门 + 自检）；
- 双语 README：English（`README.md`）+ 简体中文（`README.zh-CN.md`）。

### Fixed
- 标准布局下的旧路径引用（`persona_tools/`）统一迁移到 `scripts/`；
- toolbox 剥离代码后产生的悬空标题与空用法段；
- `render_probe.py`：输出路径改为 `//probe.png`；无相机时结构化失败（不再 traceback）；
- `render_probe.py`：自动选择场景内相机；
- `selftest.py`：`lint_equivalence` 改为严格三态 skip（不计入 pass）；
- `SKILL.md`：`<SKILL>` 路径定义与 `load_router` 调用改为绝对路径形式。

### Removed
- toolbox 内嵌 python/json/bash 代码（保留文字说明与脚本指针）；
- `starter/` 课程二进制素材（按标准技能布局不随包分发）。
"""


GITIGNORE = """# Python
__pycache__/
*.py[cod]
.venv/
venv/

# Blender / 运行产物
*.blend1
*.blend2
probe.png
*_measured.json
jobs/
*.log

# 项目侧敏感数据（§12.4：不进入人设）
deny.txt

# OS
.DS_Store
Thumbs.db
"""

CI_YML = """name: validate-skill

on:
  push:
    branches: [main]
  pull_request:

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Compile scripts
        run: python -m compileall -q scripts tools

      - name: Persona structure gate
        run: python scripts/persona_lint.py . --allow-no-deny

      - name: Toolchain selftest
        run: python scripts/selftest.py .

      - name: Validate Claude Code plugin manifests
        run: |
          python - <<'PY'
          import json
          from pathlib import Path
          m = json.loads(Path(".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
          assert m.get("plugins"), "marketplace has no plugins"
          for entry in m["plugins"]:
              src = Path(entry["source"])
              pj = src / ".claude-plugin" / "plugin.json"
              assert pj.is_file(), f"missing {pj}"
              manifest = json.loads(pj.read_text(encoding="utf-8"))
              assert manifest["name"] == entry["name"], (manifest["name"], entry["name"])
              skill_md = src / "skills" / entry["name"] / "SKILL.md"
              assert skill_md.is_file(), f"missing {skill_md}"
          print("plugin manifests: ok")
          PY

      - name: Check DSH installers
        run: |
          test -f dsh/install.ps1
          bash -n dsh/install.sh
          echo "dsh installers: ok"

      - name: Validate DSH plugin manifest
        run: |
          python - <<'PY'
          import json
          from pathlib import Path
          pkg = json.loads(Path("package.json").read_text(encoding="utf-8"))
          assert pkg["license"] == "MIT", pkg.get("license")
          assert pkg["dsh"]["bundle"]["patch"] == "./cordis.patch.yml", pkg.get("dsh")
          for rel in ("cordis.patch.yml", "lib/index.js",
                      "skills/blender-mentor/SKILL.md",
                      "skills/blender-mentor/package.json"):
              assert Path(rel).is_file(), f"missing {rel}"
          print("dsh plugin manifest: ok")
          PY
          node --check lib/index.js

      - name: Layout check (no legacy paths in references)
        run: |
          python - <<'PY'
          import re, sys
          from pathlib import Path
          bad = []
          for p in Path("references").glob("*.md"):
              for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                  if re.match(r"\\s*-\\s*V\\d", line):
                      continue
                  if "persona_tools/" in line or re.search(r"blender-mentor-v5[\\w.-]*\\.md", line):
                      bad.append(f"{p}:{i}: {line.strip()[:80]}")
          if bad:
              print("legacy layout references found:")
              print("\\n".join(bad))
              sys.exit(1)
          print("layout check: ok")
          PY
"""

LICENSE_TEXT = """MIT License

Copyright (c) 2026 The blender-mentor contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


def die(msg):
    print("BUILD_SKILL {\"status\": \"fail\", \"error\": %s}" % json.dumps(msg, ensure_ascii=False))
    return 1


def read_text(path):
    with open(path, encoding="utf-8-sig") as fh:
        return fh.read()


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def find_suite(source):
    """在 source 下找含 blender-mentor-v5.md 的目录（最多向下 3 层）。"""
    direct = os.path.join(source, FILES["main"])
    if os.path.isfile(direct):
        return os.path.abspath(source)
    for root, dirs, files in os.walk(source):
        depth = os.path.relpath(root, source).count(os.sep)
        if depth >= 3:
            dirs[:] = []
            continue
        if FILES["main"] in files:
            return os.path.abspath(root)
    return None


def walk_fences(text):
    """返回代码块列表：{start, end, lang, code, heading}，start/end 为行下标（含围栏行）。"""
    lines = text.splitlines()
    blocks = []
    heading = ""
    in_fence = False
    lang = ""
    start = 0
    buf = []
    for i, ln in enumerate(lines):
        stripped = ln.strip()
        if not in_fence and stripped.startswith("```"):
            in_fence = True
            lang = stripped[3:].strip().split()[0] if stripped[3:].strip() else ""
            start = i
            buf = []
            continue
        if in_fence and stripped.startswith("```"):
            blocks.append({"start": start, "end": i, "lang": lang,
                           "code": "\n".join(buf), "heading": heading})
            in_fence = False
            continue
        if in_fence:
            buf.append(ln)
        elif stripped.startswith("#"):
            heading = stripped
    return lines, blocks


def extract_scripts(toolbox_text):
    """按标题提取完整脚本。找不到就报错，避免静默缺脚本。"""
    lines, blocks = walk_fences(toolbox_text)
    got = {}
    for b in blocks:
        if not b["lang"].startswith("python"):
            continue
        fname = match_script(b["heading"])
        if fname:
            if fname in got:
                raise RuntimeError("duplicate script block for %s" % fname)
            got[fname] = b["code"].rstrip() + "\n"
    expected = list(EXTRACTED) + [f for _, f in EXTRA_EXTRACTS]
    missing = [f for f in expected if f not in got]
    if missing:
        raise RuntimeError("missing script blocks in toolbox: %s" % ", ".join(missing))
    return got, blocks


def strip_toolbox(text, script_names):
    """删除 toolbox 的所有 python/json/bash 代码块；完整脚本块替换为一行指针。"""
    lines, blocks = walk_fences(text)
    raw = text.splitlines()

    # heading -> 脚本名（仅完整脚本块）
    script_heading = {}
    for b in blocks:
        if b["lang"].startswith("python"):
            fname = match_script(b["heading"])
            if fname:
                script_heading[(b["start"], b["end"])] = fname

    replacements = []
    for b in blocks:
        key = (b["start"], b["end"])
        if b["lang"].startswith("python"):
            fname = script_heading.get(key)
            if fname:
                repl = ["> 完整脚本：`scripts/%s`。" % fname]
            else:
                repl = ["> 示例代码已剥离（标准布局只保留文字说明；完整脚本见 `scripts/`）。"]
        elif b["lang"].startswith("json"):
            try:
                data = json.loads(b["code"])
            except ValueError:
                data = None
            if isinstance(data, dict) and "events" in data:
                repl = ["> 示例 spec 已提取到 `assets/esd_spec.example.json`。"]
            else:
                repl = ["> 数据块已剥离（见 `assets/`）。"]
        elif b["lang"].startswith(("bash", "sh", "shell")):
            # 用法命令转成纯文字（标准布局要求 toolbox_text 零代码围栏）
            code_lines = [x.strip() for x in b["code"].splitlines() if x.strip()]
            usage = code_lines[0] if code_lines else ""
            note = code_lines[1] if len(code_lines) > 1 else ""
            line = "> 用法：`" + usage + "`"
            if note:
                line += "（" + note + "）"
            repl = [line]
        else:
            continue  # text/csv/yaml 等文档块保留
        replacements.append((b["start"], b["end"], repl))

    for start, end, repl in sorted(replacements, reverse=True):
        raw[start:end + 1] = repl
    out = "\n".join(raw)
    # 顶部加一段说明
    marker = "> 配套主文档 `main.md`。"
    if marker in out:
        out = out.replace(marker, marker + "\n> 标准技能布局：本文件已剥离 python/json/bash 内嵌代码（用法改为纯文字）；完整脚本见 `scripts/`，数据模板见 `assets/`。", 1)
    return out


def rewrite_layout_refs(text):
    """把文档里旧套件布局的路径引用改成本标准布局的引用。

    只改操作型引用；变更记录里的历史事实保持原样（以 `- V` 开头的行跳过）。
    """
    # 1) 先做整句替换（避免被下面的通用替换拆掉）
    text = text.replace(
        "包内附带 `persona_tools/` 与 `starter/` 课程素材",
        "配套脚本在 `scripts/`、数据在 `assets/`；`starter/` 课程素材未随标准技能包分发",
    )
    text = text.replace(
        "包内附带 `persona_tools/`：`persona_lint.py`、`deny.example.txt`、`expand_esd_spec.py`、"
        "`esd_spec.template.json`、`selftest.py`、`test_biomech_nla.py`、`README.md`（项目侧工具）。",
        "配套工具：`scripts/`（`persona_lint.py`、`selftest.py`、`expand_esd_spec.py`、"
        "`load_router.py`、`sample_esd_from_blend.py` 等）；模板与拒绝词示例在 `assets/`。",
    )
    text = text.replace(
        "## 6. Starter 文件清单（教师准备，已随包生成）",
        "## 6. Starter 文件清单（教师准备；标准技能布局不随包分发）",
    )
    text = text.replace(
        "> 由 `starter/build_starter.py` 生成、`starter/verify_starter.py` 验收（28 项）；缺文件时重建。",
        "> 原 V5.4.0 套件包内含 `starter/` 课程素材；标准技能布局为控制体积未随包分发。"
        "需要时从原套件包获取（`starter/build_starter.py` 生成、`starter/verify_starter.py` 验收 28 项）。",
    )
    text = text.replace(
        "- `starter/curve_audit.py`、`starter/asset_gate.py`、`starter/render_probe.py`：来自 toolbox。",
        "- 标准布局已提供 `scripts/curve_audit.py` / `scripts/asset_gate.py` / `scripts/render_probe.py`；"
        "其余 starter 素材需从原套件包获取。",
    )
    # 剥离代码后，标题/描述与 token 粗估同步修正
    text = text.replace(
        "# Blender 导师 V5 · 工具箱（资产门 / bpy 片段 / 130 条误区库 / 修复对话）",
        "# Blender 导师 V5 · 工具箱（资产门 / 工具指针 / 130 条误区库 / 修复对话）",
    )
    text = text.replace(
        "工具箱（资产门脚本、bpy 片段、",
        "工具箱（资产门脚本入口、bpy 片段指针、",
    )
    text = text.replace(
        "全量六件套约 3.9 万 token（粗估）",
        "全量六件套约 3.1 万 token（标准布局剥离 toolbox 代码后的粗估）",
    )
    text = text.replace(
        "| 按任务 | `toolbox_text.md` | 脚本/验收/报错/误区等触发词 | ~16.5k |",
        "| 按任务 | `toolbox_text.md` | 脚本/验收/报错/误区等触发词 | ~6.3k |",
    )
    text = text.replace(
        "- `toolbox_python_blocks` 失败 → 脚本不可编译，不得交付；",
        "- `toolbox_python_blocks` 失败 → （标准布局下已无内嵌代码，该检查恒过；脚本编译由构建脚本负责）；",
    )

    # 2) 逐行通用替换；历史变更记录不动
    out_lines = []
    for line in text.splitlines():
        if re.match(r"\s*-\s*V\d", line):
            out_lines.append(line)
            continue
        line = line.replace("persona_tools/", "scripts/")
        line = line.replace("`blender-mentor-v5*.md`", "`references/*.md`")
        line = line.replace("`scripts/load_plan.json`", "`assets/load_plan.json`")
        # toolbox 里的用法示例同步到标准布局
        line = line.replace("--python asset_gate.py", "--python scripts/asset_gate.py")
        line = line.replace("python envelope_check.py", "python scripts/envelope_check.py")
        line = line.replace("python persona_lint.py", "python scripts/persona_lint.py")
        out_lines.append(line)
    return "\n".join(out_lines)


def find_stale_refs(skill_dir):
    """检查 references/ 里是否还有旧布局路径（变更记录的历史行豁免）。"""
    hits = []
    refs = os.path.join(skill_dir, "references")
    for fn in sorted(os.listdir(refs)):
        if not fn.endswith(".md"):
            continue
        path = os.path.join(refs, fn)
        for i, line in enumerate(read_text(path).splitlines(), 1):
            if re.match(r"\s*-\s*V\d", line):
                continue
            if "persona_tools/" in line or re.search(r"blender-mentor-v5[\w.-]*\.md", line):
                hits.append({"file": "references/" + fn, "line": i,
                             "text": line.strip()[:120]})
    return hits


def rewrite_doc_names(text):
    pairs = [
        ("blender-mentor-v5-module-biomechanics.md", "module-biomechanics.md"),
        ("blender-mentor-v5-module-esd.md", "module-esd.md"),
        ("blender-mentor-v5-curriculum.md", "curriculum.md"),
        ("blender-mentor-v5-toolbox.md", "toolbox_text.md"),
        ("blender-mentor-v5-rubric.md", "rubric.md"),
        ("blender-mentor-v5.md", "main.md"),
    ]
    for old, new in pairs:
        text = text.replace(old, new)
    return text


def replace_once(text, old, new, label):
    if old not in text:
        raise RuntimeError("patch point not found: %s" % label)
    return text.replace(old, new, 1)


def patch_render_probe(code):
    """标准布局补强：输出路径改为相对 blend，且无相机时不再抛 RuntimeError traceback。"""
    # 与 starter/build_starter.py 一致：raw toolbox 写死 C:\temp，改为相对输出
    code = replace_once(
        code,
        r'sc.render.filepath = r"C:\temp\probe.png"',
        'sc.render.filepath = bpy.path.abspath("//probe.png")',
        "render_probe.relative_path",
    )
    code = replace_once(code, "import bpy, os\n", "import bpy, os, json\n",
                        "render_probe.import_json")
    code = replace_once(
        code,
        "sc = bpy.context.scene\n",
        'sc = bpy.context.scene\n\n'
        '# 标准布局补强：没有相机时明确失败，而不是抛 RuntimeError traceback\n'
        'if sc.camera is None:\n'
        '    cam = next((o for o in bpy.data.objects if o.type == "CAMERA"), None)\n'
        '    if cam is not None:\n'
        '        sc.camera = cam\n'
        'if sc.camera is None:\n'
        '    print(\'RENDER_PROBE {"status": "fail", "error": "no camera in scene"}\')\n'
        '    raise SystemExit(1)\n',
        "render_probe.camera_guard",
    )
    code = replace_once(
        code,
        'bpy.ops.render.render(write_still=True)\n'
        'print("probe exists", os.path.exists(sc.render.filepath))',
        'try:\n'
        '    bpy.ops.render.render(write_still=True)\n'
        'except RuntimeError as exc:\n'
        '    print(\'RENDER_PROBE {"status": "fail", "error": %s}\' % json.dumps(str(exc), ensure_ascii=False))\n'
        '    raise SystemExit(1)\n'
        '\n'
        'exists = os.path.exists(sc.render.filepath)\n'
        'print("probe exists", exists)\n'
        'print(\'RENDER_PROBE {"status": "%s", "file": %s}\' % ("pass" if exists else "fail",\n'
        '                                                     json.dumps(sc.render.filepath, ensure_ascii=False)))\n'
        'raise SystemExit(0 if exists else 1)',
        "render_probe.result",
    )
    return code


def patch_persona_lint(code):
    old = '''FILES = [
    "blender-mentor-v5.md",
    "blender-mentor-v5-rubric.md",
    "blender-mentor-v5-curriculum.md",
    "blender-mentor-v5-toolbox.md",
    "blender-mentor-v5-module-esd.md",
    "blender-mentor-v5-module-biomechanics.md",
]'''
    new = '''FILES = [
    "references/main.md",
    "references/rubric.md",
    "references/curriculum.md",
    "references/toolbox_text.md",
    "references/module-esd.md",
    "references/module-biomechanics.md",
]'''
    code = replace_once(code, old, new, "persona_lint.FILES")
    code = code.replace("python persona_tools/persona_lint.py", "python scripts/persona_lint.py")
    code = code.replace(
        "    5. toolbox 内 python 代码块可编译\n",
        "    5. （标准布局）toolbox 已剥离代码；scripts/ 由构建脚本做编译检查\n",
    )
    return code


def patch_load_router(code):
    code = replace_once(
        code,
        'PLAN_PATH = os.path.join(HERE, "load_plan.json")',
        'PLAN_PATH = os.path.join(ROOT, "assets", "load_plan.json")',
        "load_router.PLAN_PATH",
    )
    # 预算裁剪顺序里写死了旧文件名，标准布局下必须同步，否则永远裁不到 toolbox
    code = replace_once(
        code,
        '"blender-mentor-v5-curriculum.md"',
        '"references/curriculum.md"',
        "load_router.trim_curriculum",
    )
    code = replace_once(
        code,
        '"blender-mentor-v5-toolbox.md"',
        '"references/toolbox_text.md"',
        "load_router.trim_toolbox",
    )
    code = code.replace("python persona_tools/load_router.py", "python scripts/load_router.py")
    return code


def patch_selftest(code):
    equivalence_old = '''    # 2.1) lint 与 toolbox §7 内嵌版行为等价（README 的"等价性检查"）
    try:
        toolbox_text = open(os.path.join(root, "blender-mentor-v5-toolbox.md"),
                            encoding="utf-8").read()
        m7 = re.search(r"## 7\\..*?```python\\n(.*?)```", toolbox_text, re.S)
        box = {"__name__": "lint_toolbox"}
        exec(compile(m7.group(1), "<toolbox-7>", "exec"), box)
        a = lint["lint"](root, deny_ok)
        b = box["lint"](root, deny_ok)
        same = (a["status"] == b["status"]
                and {c["check"]: c["pass"] for c in a["checks"]}
                == {c["check"]: c["pass"] for c in b["checks"]})
        _check(checks, "lint_equivalence", same,
               {"tools": a["status"], "toolbox": b["status"]})
    except Exception as exc:  # noqa: BLE001
        _check(checks, "lint_equivalence", False,
               type(exc).__name__ + ": " + str(exc))'''
    equivalence_new = '''    # 2.1) 标准布局下 toolbox 已剥离代码，内嵌版等价性检查无法执行：记为 skip，不计入 pass
    checks.append({"check": "lint_equivalence", "skip": True, "pass": None,
                   "detail": "disabled: toolbox_text.md has no embedded code (standard layout)"})'''
    code = replace_once(code, equivalence_old, equivalence_new, "selftest.equivalence")

    envelope_old = '''    toolbox = os.path.join(root, "blender-mentor-v5-toolbox.md")
    try:
        text = open(toolbox, encoding="utf-8").read()
        m = re.search(r"## 5\\..*?```python\\n(.*?)```", text, re.S)
        env = {"__name__": "env"}
        exec(compile(m.group(1), "<toolbox-5>", "exec"), env)
        env_result = env["check_spec"](spec)
        _check(checks, "expanded_spec_passes_envelope",
               env_result["status"] == "pass",
               {c["check"]: c["pass"] for c in env_result["checks"]})
    except Exception as exc:  # noqa: BLE001
        _check(checks, "expanded_spec_passes_envelope", False,
               type(exc).__name__ + ": " + str(exc))'''
    envelope_new = '''    try:
        env = _load("env", os.path.join(TOOLS, "envelope_check.py"))
        env_result = env["check_spec"](spec)
        _check(checks, "expanded_spec_passes_envelope",
               env_result["status"] == "pass",
               {c["check"]: c["pass"] for c in env_result["checks"]})
    except Exception as exc:  # noqa: BLE001
        _check(checks, "expanded_spec_passes_envelope", False,
               type(exc).__name__ + ": " + str(exc))'''
    code = replace_once(code, envelope_old, envelope_new, "selftest.envelope")

    code = replace_once(
        code,
        'os.path.join(TOOLS, "esd_spec.template.json")',
        'os.path.join(ROOT, "assets", "esd_spec.template.json")',
        "selftest.esd_template_path",
    )
    code = replace_once(
        code,
        'plan_path = os.path.join(TOOLS, "load_plan.json")',
        'plan_path = os.path.join(ROOT, "assets", "load_plan.json")',
        "selftest.load_plan_path",
    )
    code = replace_once(
        code,
        'os.path.join(TOOLS, "esd_sample_config.template.json")',
        'os.path.join(ROOT, "assets", "esd_sample_config.template.json")',
        "selftest.sample_config_path",
    )
    code = replace_once(
        code,
        'os.path.join(TOOLS, "deny.example.txt")',
        'os.path.join(ROOT, "assets", "deny.example.txt")',
        "selftest.deny_example_path",
    )
    code = code.replace("python persona_tools/selftest.py", "python scripts/selftest.py")
    code = code.replace("persona_tools 纯 Python 自检", "scripts 纯 Python 自检")
    code = code.replace("# 套件目录默认 persona_tools 的上一级", "# 技能目录默认 scripts 的上一级")

    # 严格三态：skip 不计入 pass / total
    result_old = '''    result = {"status": "pass" if all(c["pass"] for c in checks) else "fail",
              "passed": sum(1 for c in checks if c["pass"]),
              "total": len(checks), "checks": checks}'''
    result_new = '''    active = [c for c in checks if not c.get("skip")]
    result = {"status": "pass" if all(c["pass"] for c in active) else "fail",
              "passed": sum(1 for c in active if c["pass"]),
              "total": len(active),
              "skipped": [c["check"] for c in checks if c.get("skip")],
              "checks": checks}'''
    code = replace_once(code, result_old, result_new, "selftest.result_three_state")
    return code


def patch_load_plan(plan):
    mapping = {
        "blender-mentor-v5.md": "references/main.md",
        "blender-mentor-v5-rubric.md": "references/rubric.md",
        "blender-mentor-v5-curriculum.md": "references/curriculum.md",
        "blender-mentor-v5-toolbox.md": "references/toolbox_text.md",
        "blender-mentor-v5-module-esd.md": "references/module-esd.md",
        "blender-mentor-v5-module-biomechanics.md": "references/module-biomechanics.md",
        "persona_tools/persona_lint.py": "scripts/persona_lint.py",
        "persona_tools/selftest.py": "scripts/selftest.py",
        "persona_tools/expand_esd_spec.py": "scripts/expand_esd_spec.py",
        "persona_tools/load_router.py": "scripts/load_router.py",
        "persona_tools/sample_esd_from_blend.py": "scripts/sample_esd_from_blend.py",
    }

    def fix_item(item):
        if isinstance(item, dict) and "file" in item:
            item["file"] = mapping.get(item["file"], item["file"])
        return item

    for key in ("always", "on_demand", "modules", "tools"):
        if key in plan:
            plan[key] = [fix_item(i) for i in plan[key]]
    existing = {i.get("file") for i in plan.setdefault("tools", [])}
    for item in (
        {"file": "scripts/curve_audit.py", "when": "曲线审计（插值/手柄统计）"},
        {"file": "scripts/render_probe.py", "when": "渲染探针（输出 //probe.png）"},
    ):
        if item["file"] not in existing:
            plan["tools"].append(item)
    return plan


def write_claude_plugin(skill_dir, repo_slug):
    """生成 Claude Code 插件包装：marketplace + plugin + skills/<name>/ 副本。"""
    owner = repo_slug.split("/")[0]
    repo_url = "https://github.com/%s" % repo_slug
    plugin_root = os.path.join(skill_dir, "plugins", "blender-mentor")
    skill_copy = os.path.join(plugin_root, "skills", "blender-mentor")
    os.makedirs(skill_copy, exist_ok=True)

    # 根目录 Skill 是唯一正本；插件里放一份副本，保证 Claude Code 的 skills/ 约定成立
    shutil.copy2(os.path.join(skill_dir, "SKILL.md"), os.path.join(skill_copy, "SKILL.md"))
    for d in ("references", "scripts", "assets"):
        shutil.copytree(os.path.join(skill_dir, d), os.path.join(skill_copy, d), dirs_exist_ok=True)

    desc = ("Blender full-stack mentor skill: teaching, 0-3 rubric grading, "
            "asset/animation acceptance (ESD/BIO/ENG).")
    plugin = {
        "name": "blender-mentor",
        "displayName": "Blender Mentor",
        "description": desc,
        "version": "5.9.2",
        "author": {"name": owner},
        "homepage": repo_url,
        "repository": repo_url,
        "license": "MIT",
        "keywords": ["blender", "ai-skill", "agent-skills", "claude-skill",
                     "animation", "rigging", "biomechanics"],
    }
    write_text(os.path.join(plugin_root, ".claude-plugin", "plugin.json"),
               json.dumps(plugin, ensure_ascii=False, indent=2) + "\n")

    plugin_readme = (
        "# Blender Mentor - Claude Code plugin\n\n"
        "This plugin packages the `blender-mentor` Agent Skill.\n\n"
        "## Install\n\n"
        "```text\n"
        "/plugin marketplace add {slug}\n"
        "/plugin install blender-mentor@blender-mentor-marketplace\n"
        "```\n\n"
        "The skill lives at `skills/blender-mentor/SKILL.md`; its `references/`, "
        "`scripts/` and `assets/` are bundled next to it.\n\n"
        "## Links\n\n"
        "- Repository: {url}\n"
        "- Release notes: {url}/releases\n"
        "- License: MIT\n"
    ).replace("{slug}", repo_slug).replace("{url}", repo_url)
    write_text(os.path.join(plugin_root, "README.md"), plugin_readme)
    write_text(os.path.join(plugin_root, "LICENSE"), LICENSE_TEXT)

    marketplace = {
        "name": "blender-mentor-marketplace",
        "description": "Blender Mentor - AI Agent Skill for Blender teaching, grading and acceptance.",
        "owner": {"name": owner},
        "plugins": [{
            "name": "blender-mentor",
            "source": "./plugins/blender-mentor",
            "description": desc,
            "version": "5.9.2",
        }],
    }
    write_text(os.path.join(skill_dir, ".claude-plugin", "marketplace.json"),
               json.dumps(marketplace, ensure_ascii=False, indent=2) + "\n")
    return [
        ".claude-plugin/marketplace.json",
        "plugins/blender-mentor/.claude-plugin/plugin.json",
        "plugins/blender-mentor/README.md",
        "plugins/blender-mentor/skills/blender-mentor/SKILL.md",
    ]


def write_dsh_plugin(skill_dir, repo_slug):
    """生成 DSH 技能插件包：package.json(dsh 字段) + cordis.patch.yml + skills/。"""
    owner = repo_slug.split("/")[0]
    repo_url = "https://github.com/%s" % repo_slug
    pkg_name = "blender-mentor"
    version = "5.9.2"
    desc = ("Blender full-stack mentor AI Skill: teaching, 0-3 rubric grading, "
            "asset/animation acceptance (ESD/BIO/ENG).")

    package = {
        "name": pkg_name,
        "version": version,
        "description": desc,
        "type": "module",
        "main": "./lib/index.js",
        "exports": {".": "./lib/index.js", "./package.json": "./package.json"},
        "license": "MIT",
        "keywords": ["dsh-plugin", "deepseek-harness", "agent-skill", "blender",
                     "ai-skill", "animation", "rigging", "biomechanics"],
        "repository": {"type": "git", "url": "git+%s.git" % repo_url},
        "homepage": repo_url,
        "bugs": {"url": repo_url + "/issues"},
        "files": ["lib", "cordis.patch.yml", "skills", "README.md",
                  "README.zh-CN.md", "LICENSE", "CHANGELOG.md"],
        "dsh": {"bundle": {"patch": "./cordis.patch.yml"}},
        "engines": {"node": "^22.19.0 || >=24.0.0"},
    }
    write_text(os.path.join(skill_dir, "package.json"),
               json.dumps(package, ensure_ascii=False, indent=2) + "\n")

    patch = (
        "# Opt-in Blender Mentor filesystem Skill provider for DeepSeek Harness.\n"
        "# Resolves the packaged Skill root from the installed package identity.\n"
        "- insert:\n"
        "    - id: blender-mentor-skill-filesystem\n"
        "      name: '@deepseek-ai/dsh-skill-filesystem'\n"
        "      config:\n"
        "        providerName: blender-mentor-plugin\n"
        "        includeDefaultRoots: false\n"
        "        bundledSkillDir: !!js process.getBuiltinModule('node:path').join("
        "process.getBuiltinModule('node:path').dirname("
        "process.getBuiltinModule('node:module').createRequire(baseUrl)"
        ".resolve('blender-mentor/package.json')), 'skills')\n"
    )
    write_text(os.path.join(skill_dir, "cordis.patch.yml"), patch)

    adapter = (
        "import { createRequire } from 'node:module';\n"
        "import { dirname, join } from 'node:path';\n\n"
        "export const name = 'blender-mentor';\n"
        "export const PACKAGE_NAME = 'blender-mentor';\n\n"
        "export function resolveBlenderMentorSkillRoot(profileBaseUrl) {\n"
        "  if (!profileBaseUrl) {\n"
        "    throw new Error('blender-mentor: missing DSH profile baseUrl for package resolution');\n"
        "  }\n"
        "  const manifestPath = createRequire(profileBaseUrl).resolve(`${PACKAGE_NAME}/package.json`);\n"
        "  return join(dirname(manifestPath), 'skills');\n"
        "}\n"
    )
    write_text(os.path.join(skill_dir, "lib", "index.js"), adapter)

    skill_copy = os.path.join(skill_dir, "skills", "blender-mentor")
    os.makedirs(skill_copy, exist_ok=True)
    shutil.copy2(os.path.join(skill_dir, "SKILL.md"), os.path.join(skill_copy, "SKILL.md"))
    for d in ("references", "scripts", "assets"):
        shutil.copytree(os.path.join(skill_dir, d), os.path.join(skill_copy, d), dirs_exist_ok=True)

    write_text(os.path.join(skill_copy, "package.json"), json.dumps({
        "name": "blender-mentor-skill",
        "version": version,
        "private": True,
        "type": "module",
        "description": desc,
        "license": "MIT",
    }, ensure_ascii=False, indent=2) + "\n")
    write_text(os.path.join(skill_copy, "skill-release.json"), json.dumps({
        "schemaVersion": 1,
        "skillId": "blender-mentor",
        "channel": "stable",
        "version": version,
        "source": {"repository": repo_url},
    }, ensure_ascii=False, indent=2) + "\n")
    return [
        "package.json",
        "cordis.patch.yml",
        "lib/index.js",
        "skills/blender-mentor/SKILL.md",
        "skills/blender-mentor/package.json",
        "skills/blender-mentor/skill-release.json",
    ]


def run_built_selfchecks(out_dir):
    """直接 exec 生成的脚本做纯 Python 自检，返回 (ok, details)。"""
    import importlib.util

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    details = {}
    scripts = os.path.join(out_dir, "scripts")
    lint_mod = load("p_lint", os.path.join(scripts, "persona_lint.py"))
    lint_res = lint_mod.lint(out_dir, None, strict=False)
    details["lint"] = lint_res["status"]

    # 调用 selftest.main([out_dir])，捕获它打印的 JSON 结论
    import io
    import contextlib
    selftest_mod = load("p_selftest", os.path.join(scripts, "selftest.py"))
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = selftest_mod.main([out_dir])
    except SystemExit as exc:
        rc = exc.code if isinstance(exc.code, int) else 1
    text = buf.getvalue().strip()
    details["selftest_rc"] = rc
    details["selftest_last"] = text.splitlines()[-1][:400] if text else ""
    ok = details["lint"] == "pass" and rc == 0
    return ok, details


def build(source, out_root, force=False, repo_slug="OWNER/REPO"):
    suite = find_suite(source)
    if not suite:
        raise RuntimeError("six-file suite not found under %s (need blender-mentor-v5.md)" % source)

    # 先读自身源码：--force 会清空输出目录（保留 .git），之后 __file__ 可能已不存在
    self_source = None
    try:
        me = os.path.abspath(__file__)
        if os.path.isfile(me):
            self_source = read_text(me)
    except OSError:
        self_source = None

    skill_dir = os.path.join(out_root, "blender-mentor")
    if os.path.exists(skill_dir):
        if not force:
            raise RuntimeError("%s already exists; pass --force to overwrite" % skill_dir)
        # 保留 .git（仓库历史）、docs（图片资源）与 dsh（安装脚本），其余重新生成
        for entry in os.listdir(skill_dir):
            if entry in (".git", "docs", "dsh"):
                continue
            p = os.path.join(skill_dir, entry)
            if os.path.isdir(p):
                shutil.rmtree(p)
            else:
                os.remove(p)
    os.makedirs(skill_dir, exist_ok=True)

    refs = os.path.join(skill_dir, "references")
    scripts = os.path.join(skill_dir, "scripts")
    assets = os.path.join(skill_dir, "assets")
    for d in (refs, scripts, assets):
        os.makedirs(d)

    # 1) 读入六件套
    texts = {}
    for key, fname in FILES.items():
        path = os.path.join(suite, fname)
        if not os.path.isfile(path):
            raise RuntimeError("missing suite file: %s" % path)
        texts[key] = read_text(path)

    # 2) 从 toolbox 提取完整脚本（必须用原文：补丁点里含原始文件名）
    toolbox_raw = texts["toolbox"]
    extracted, _ = extract_scripts(toolbox_raw)
    for fname, code in extracted.items():
        if fname == "persona_lint.py":
            code = patch_persona_lint(code)
        elif fname == "render_probe.py":
            code = patch_render_probe(code)
        write_text(os.path.join(scripts, fname), code)

    # 3) 从 toolbox 提取 json 代码块 -> assets
    _, blocks = walk_fences(toolbox_raw)
    json_blocks = [b for b in blocks if b["lang"].startswith("json")]
    example_written = False
    for b in json_blocks:
        try:
            data = json.loads(b["code"])
        except ValueError:
            continue
        if isinstance(data, dict) and "events" in data:
            write_text(os.path.join(assets, "esd_spec.example.json"),
                       json.dumps(data, ensure_ascii=False, indent=2) + "\n")
            example_written = True

    # 4) toolbox_text：先重写文件名，再剥离代码块
    toolbox_text = strip_toolbox(rewrite_doc_names(toolbox_raw), list(extracted))
    write_text(os.path.join(refs, REF_NAMES["toolbox"]), rewrite_layout_refs(toolbox_text))

    # 5) 其余文档改名复制，并修正旧布局路径引用
    for key in ("main", "rubric", "curriculum", "esd", "bio"):
        write_text(os.path.join(refs, REF_NAMES[key]),
                   rewrite_layout_refs(rewrite_doc_names(texts[key])))

    # 5.1) 通用模块 ENG-001 + 治理规范
    for extra_ref in ("module-engineering.md", "module-format.md", "module-authoring.md", "model-qa.md"):
        module_src = os.path.join(suite, extra_ref)
        if not os.path.isfile(module_src):
            raise RuntimeError("missing module reference: %s" % module_src)
        shutil.copyfile(module_src, os.path.join(refs, extra_ref))

    # 6) 独立工具 + 资产文件
    tools_src = os.path.join(suite, "persona_tools")
    if not os.path.isdir(tools_src):
        raise RuntimeError("persona_tools/ not found next to suite: standard layout needs the 4 standalone tools")
    for tool in COPIED_TOOLS:
        src = os.path.join(tools_src, tool)
        if not os.path.isfile(src):
            raise RuntimeError("missing standalone tool: %s" % src)
        code = read_text(src)
        if tool == "load_router.py":
            code = patch_load_router(code)
        elif tool == "selftest.py":
            code = patch_selftest(code)
        write_text(os.path.join(scripts, tool), code)

    for asset in ASSET_FILES:
        src = os.path.join(tools_src, asset)
        if not os.path.isfile(src):
            raise RuntimeError("missing asset: %s" % src)
        if asset == "load_plan.json":
            plan = patch_load_plan(json.loads(read_text(src)))
            write_text(os.path.join(assets, asset), json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
        else:
            shutil.copyfile(src, os.path.join(assets, asset))

    # 6.1) 最终版 lint/selftest/router（含治理层校验）
    for rel, fname in (("scripts/persona_lint.py", "persona_lint.py"),
                       ("scripts/selftest.py", "selftest.py"),
                       ("scripts/load_router.py", "load_router.py")):
        src = os.path.join(tools_src, fname)
        if os.path.isfile(src):
            shutil.copyfile(src, os.path.join(skill_dir, rel))

    # 6.15) 模块 JSON 目录
    modules_src = os.path.join(tools_src, "modules")
    if not os.path.isdir(modules_src):
        raise RuntimeError("missing modules dir: %s" % modules_src)
    shutil.copytree(modules_src, os.path.join(assets, "modules"), dirs_exist_ok=True)

    # 6.2) 工程回归 fixture/config/expected
    tests_src = os.path.join(suite, "tests")
    if os.path.isdir(tests_src):
        shutil.copytree(tests_src, os.path.join(skill_dir, "tests"), dirs_exist_ok=True)

    # 7) SKILL.md
    write_text(os.path.join(skill_dir, "SKILL.md"), SKILL_MD)

    # 7.0) GitHub 仓库配套文件（重建时保留 .git，可直接继续提交）
    repo_files = {
        "README.md": README_EN_MD.replace("OWNER/REPO", repo_slug),
        "README.zh-CN.md": README_ZH_MD.replace("OWNER/REPO", repo_slug),
        "LICENSE": LICENSE_TEXT,
        "CHANGELOG.md": CHANGELOG_MD,
        ".gitignore": GITIGNORE,
        os.path.join(".github", "workflows", "validate.yml"): CI_YML,
    }
    for rel, content in repo_files.items():
        write_text(os.path.join(skill_dir, rel), content)

    # 构建工具随仓库分发（tools/build_skill.py），保证仓库自包含、可重建
    if self_source:
        write_text(os.path.join(skill_dir, "tools", "build_skill.py"), self_source)

    # 7.05) Claude Code 插件包装（marketplace + plugin + skills/ 副本）
    plugin_files = write_claude_plugin(skill_dir, repo_slug)

    # 7.06) DSH 技能插件包（package.json dsh 字段 + cordis patch + skills/ 副本）
    dsh_plugin_files = write_dsh_plugin(skill_dir, repo_slug)

    # 7.1) 旧布局引用检查：references/ 里不允许残留旧路径（历史变更记录豁免）
    stale = find_stale_refs(skill_dir)
    if stale:
        raise RuntimeError("stale layout references in references/: " + json.dumps(
            stale[:5], ensure_ascii=False))

    # 8) 自检：所有脚本可编译 + lint/selftest
    py_files = sorted(f for f in os.listdir(scripts) if f.endswith(".py"))
    for f in py_files:
        src = read_text(os.path.join(scripts, f))
        try:
            compile(src, f, "exec")
        except SyntaxError as exc:
            raise RuntimeError("generated script does not compile: %s (%s)" % (f, exc))
    ok, details = run_built_selfchecks(skill_dir)

    # 自检会 import 脚本，清掉 __pycache__，保证交付目录干净
    for root, dirs, files in os.walk(skill_dir):
        for d in list(dirs):
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                dirs.remove(d)

    report = {
        "status": "pass" if ok else "fail",
        "skill_dir": os.path.abspath(skill_dir),
        "suite_dir": suite,
        "references": sorted(os.listdir(refs)),
        "scripts": py_files,
        "assets": sorted(os.listdir(assets)),
        "repo_files": sorted(repo_files),
        "claude_plugin": plugin_files,
        "dsh_plugin": dsh_plugin_files,
        "tools": ["tools/build_skill.py"] if self_source else [],
        "extracted_from_toolbox": sorted(extracted),
        "json_example_extracted": example_written,
        "stale_refs": stale,
        "checks": details,
    }
    print("BUILD_SKILL " + json.dumps(report, ensure_ascii=False))
    return 0 if ok else 1


def main(argv=None):
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser(description="Build standard AI skill layout from Blender Mentor V5.4.0")
    ap.add_argument("--source", default=".", help="directory containing the six .md files (+ persona_tools/)")
    ap.add_argument("--out", default=".", help="output directory (creates ./blender-mentor)")
    ap.add_argument("--force", action="store_true", help="overwrite existing ./blender-mentor")
    ap.add_argument("--repo", default="OWNER/REPO",
                    help="GitHub repo slug used in README, e.g. Memory175/blender-mentor")
    args = ap.parse_args(argv)
    try:
        return build(args.source, args.out, args.force, args.repo)
    except Exception as exc:  # noqa: BLE001
        print("BUILD_SKILL " + json.dumps(
            {"status": "fail", "error": type(exc).__name__ + ": " + str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
