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
    "load_router.py",
    "selftest.py",
]

ASSET_FILES = [
    "load_plan.json",
    "esd_sample_config.template.json",
    "esd_spec.template.json",
    "deny.example.txt",
]

SKILL_MD = """---
name: blender-mentor
description: Blender 全栈导师（V5.4.0：建模/拓扑/UV/材质/灯光/渲染/动画/绑定/物理/几何节点/bpy/管线）。凡是 Blender 教学、作业批改、工程评审、资产验收、次级动画（ESD）或生物力学（BIO），以及用户要求「像导师一样带我 / 审我的工程 / 给我打分」时必须使用本技能。English triggers include teach me Blender, review my .blend, grade my animation, Blender mentor, critique my render or rig.
---

# Blender 全栈导师（V5.4.0 · 标准技能布局）

角色一句话：把 Blender 任务当**可交付工程**来带——先诊断，再给原理/步骤/验证；交付必须自评 + 修改清单 + 明确询问。

> `<SKILL>` = 本技能目录的绝对路径（下文命令同）；路径含空格时给命令加引号。

## 1. 路由规则（先读对文件，不要全读）

| 用户意图 | 读这个 |
|---|---|
| 身份、边界、六段回答模板、提示分级 L1–L3、纠错/救火、40 条红线 | `references/main.md`（评审/交付前至少读 §1、§2.8、§8） |
| 评分、批改、评审、自评表、关键项与通过线 | `references/rubric.md` |
| 备课、课程、作业、前测后测、Capstone | `references/curriculum.md` |
| 报错排查、bpy、资产门、验收口径、130 条误区库 | `references/toolbox_text.md` |
| 次级动画/形变/包络/弹跳/粒子/镜头震动 | `references/module-esd.md` |
| 人体/类人/走路/跑跳/受击/动力链/肌肉体积 | `references/module-biomechanics.md` |

加载规则：模块最多同时 2 个；`main.md` 与 `rubric.md` 不裁剪；超预算裁剪顺序
curriculum → toolbox_text → 非当前任务模块。
需要机器清单时：`python "<SKILL>/scripts/load_router.py" --task "人体走路循环，需要验收脚本"`。
`load_router.py` 输出的是套件官方上限（含 main+rubric 常驻），按上表取用即可，不必全读。
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
| 套件结构门 | `python <SKILL>/scripts/persona_lint.py <SKILL> --allow-no-deny` |
| 工具链自检 | `python <SKILL>/scripts/selftest.py <SKILL>` |

数据与模板：`assets/esd_spec.template.json`（模板）、`assets/esd_spec.example.json`
（虚构示例）、`assets/esd_sample_config.template.json`（采样配置）、
`assets/load_plan.json`（加载规则）、`assets/deny.example.txt`（拒绝词模板）。

`persona_lint.py` 默认 strict：发布验收用 `--deny <项目侧 deny.txt>`（先把
`assets/deny.example.txt` 复制成项目侧 `deny.txt` 并填真实正则）；只做结构检查用
`--allow-no-deny`。路径含空格时给命令加引号。

## 4. 版本与治理

- 套件 **V5.4.0**；改动 `references/` 后必须重跑 `persona_lint.py`。
- 项目日志、帧号、实测值只写项目目录，不写入人设文件；只有用户明确说“写入人设”才允许修改。
- `references/toolbox_text.md` 已剥离内嵌代码：脚本统一在 `scripts/`，数据在 `assets/`。
"""


README_EN_MD = """# blender-mentor

> **Blender Full-Stack Mentor V5.4.0 · AI Agent Skill (standard layout)**
> Drop this repo into any Agent Skills–capable client (DSH / Claude Code / Claude.ai / Cursor) and let the agent teach, grade, review, and verify Blender work like a senior mentor + technical director.

**English** | [简体中文](README.zh-CN.md)

[![validate-skill](https://github.com/OWNER/REPO/actions/workflows/validate.yml/badge.svg)](https://github.com/OWNER/REPO/actions)

## What it is

`SKILL.md` is the resident operating manual (routing + D1–D4 delivery loop + machine-acceptance commands); `references/` holds six on-demand persona documents; `scripts/` ships executable acceptance tools; `assets/` holds templates and rule data.

Core behavior:

- **Diagnose before acting** — place the learner at an L0–L3 candidate level via the rubric, then choose explain / coach / accept / firefight / review mode.
- **Delivery loop D1→D4** — deliver → self-evaluate by sampling the artifact → P0/P1/P2 fix list → an explicit, option-based question.
- **Machine acceptance** — asset gate, curve audit, render probe, ESD envelope checks, biomechanics checks.
- **No fabrication, no unauthorized actions, no sign-off substitution** — acceptance evidence must be sampled from the artifact.

## Repository layout

```text
.
├── SKILL.md                 # Agent Skill entry point (required)
├── README.md                # English (this file)
├── README.zh-CN.md          # 简体中文
├── LICENSE                  # MIT
├── CHANGELOG.md
├── .gitignore
├── .github/workflows/validate.yml
├── tools/
│   └── build_skill.py       # maintainer build tool (rebuild from the V5.4.0 six-file suite)
├── references/              # persona documents, loaded on demand
│   ├── main.md              # identity / boundaries / six-part template / 40 red lines
│   ├── rubric.md            # 0–3 scoring rubric / critical items / self-review template
│   ├── curriculum.md        # M0–M6 course package
│   ├── toolbox_text.md      # 130-misconception library (code stripped)
│   ├── module-esd.md        # ESD-001 energy-scaled secondary animation
│   └── module-biomechanics.md # BIO-001 biomechanics
├── scripts/                 # 10 executable scripts
│   ├── asset_gate.py        # asset gate (headless Blender)
│   ├── curve_audit.py       # curve audit
│   ├── render_probe.py      # render probe (//probe.png)
│   ├── envelope_check.py    # ESD envelope assertions
│   ├── expand_esd_spec.py   # expand ESD template to executable spec
│   ├── sample_esd_from_blend.py # sample a measured spec from a .blend
│   ├── biomech_check.py     # BIO-001 biomechanics acceptance
│   ├── persona_lint.py      # persona structure gate + deny-word scan
│   ├── load_router.py       # generate the load plan for a task
│   └── selftest.py          # toolchain self-test (strict three-state)
└── assets/
    ├── load_plan.json
    ├── esd_spec.template.json
    ├── esd_spec.example.json
    ├── esd_sample_config.template.json
    └── deny.example.txt
```

## Installation

### DSH (local)

```bash
git clone https://github.com/OWNER/REPO.git blender-mentor
cp -r blender-mentor ~/.agents/skills/blender-mentor
# Windows PowerShell:
# Copy-Item -Recurse blender-mentor "$env:USERPROFILE\\.agents\\skills\\blender-mentor"
```

### Claude Code

Place it in `~/.claude/skills/blender-mentor/` (user level) or `.claude/skills/blender-mentor/` (project level).

### Claude.ai (Skills-enabled plans)

Zip the repo (or upload `SKILL.md` together with its directories) and add it to your Skills library.

### Cursor

Open this repo in Cursor and reference it in chat with `@SKILL.md` / `@references/main.md`. To keep it always on, put `SKILL.md` under `.cursor/rules/`.

## Verify

```bash
python -m compileall -q scripts tools
python scripts/persona_lint.py . --allow-no-deny   # structure gate
python scripts/selftest.py .                       # toolchain self-test (14 pass + 1 skipped)
```

Blender-side checks (requires Blender 4.2 LTS / 5.x):

```bash
blender -b file.blend --python scripts/asset_gate.py -- --json gate.json
blender -b scene.blend --python scripts/biomech_check.py -- --eccentric 1,4 --support 1-4
```

## Usage examples

```text
Use blender-mentor to walk me through M1 modeling and topology
Review this walk cycle: grade it with the rubric and give a P0/P1/P2 fix list
Turn this bounce animation's deformation envelope into an acceptance-testable spec
Why is Blender throwing this error? Start with an L2 hint
```

## Versioning & updates

- Suite version: **V5.4.0**; skill package release: **v5.4.1** (see `CHANGELOG.md`);
- After editing anything in `references/`, re-run `persona_lint.py`;
- Rebuild the skill directory: `python tools/build_skill.py --source <V5.4.0 six-file suite> --out <repo parent> --force` (keeps `.git`).

## License

MIT — see [LICENSE](LICENSE). Third-party references in the course documents are cited only; copyright remains with their authors.
"""


README_ZH_MD = """# blender-mentor

> Blender 全栈导师 V5.4.0 · AI Agent Skill（标准布局）
> 把这个仓库放进支持 Agent Skills 的客户端（DSH / Claude Code / Claude.ai / Cursor 等），
> 让 Agent 以「资深 Blender 导师 + 技术总监」的方式教学、评分、验收与排错。

[English](README.md) | **简体中文**

[![validate-skill](https://github.com/OWNER/REPO/actions/workflows/validate.yml/badge.svg)](https://github.com/OWNER/REPO/actions)

## 这是什么

`SKILL.md` 是常驻操作手册（路由 + D1–D4 交付闭环 + 机器验收命令）；`references/` 是六份可按需加载的人设文档；`scripts/` 是可执行的验收工具；`assets/` 是模板与规则数据。

核心行为：

- **先诊断再动手**：按 rubric 判断 L0–L3 candidate，再决定讲解 / 陪练 / 验收 / 救火 / 评审模式；
- **交付闭环 D1→D4**：交付 → 对产物采样自评 → P0/P1/P2 修改清单 → 明确选项询问；
- **机器验收**：资产门、曲线审计、渲染探针、ESD 包络断言、生物力学检查；
- **不伪造、不越权、不替用户签核**；验收数据必须来自产物。

## 仓库结构

```text
.
├── SKILL.md                 # Agent Skill 入口（必须）
├── README.md                # English
├── README.zh-CN.md          # 简体中文
├── LICENSE                  # MIT
├── CHANGELOG.md
├── .gitignore
├── .github/workflows/validate.yml
├── tools/
│   └── build_skill.py       # 维护侧构建工具（从 V5.4.0 六件套重建技能）
├── references/              # 人设文档（按需加载）
│   ├── main.md              # 身份/边界/六段模板/40 条红线
│   ├── rubric.md            # 0–3 分评分表/关键项/自评模板
│   ├── curriculum.md        # M0–M6 课程包
│   ├── toolbox_text.md      # 130 条误区库（已剥离代码）
│   ├── module-esd.md        # ESD-001 能量驱动次级动画
│   └── module-biomechanics.md # BIO-001 生物力学
├── scripts/                 # 10 个可执行脚本
│   ├── asset_gate.py        # 资产门（Blender 无头）
│   ├── curve_audit.py       # 曲线审计
│   ├── render_probe.py      # 渲染探针（//probe.png）
│   ├── envelope_check.py    # ESD 包络断言
│   ├── expand_esd_spec.py   # ESD 模板展开
│   ├── sample_esd_from_blend.py # 从 .blend 采样 measured spec
│   ├── biomech_check.py     # BIO-001 生物力学验收
│   ├── persona_lint.py      # 人设结构门 + 拒绝词扫描
│   ├── load_router.py       # 按任务生成加载清单
│   └── selftest.py          # 工具链自检（严格三态）
└── assets/
    ├── load_plan.json
    ├── esd_spec.template.json
    ├── esd_spec.example.json
    ├── esd_sample_config.template.json
    └── deny.example.txt
```

## 安装

### DSH（本机）

```bash
git clone https://github.com/OWNER/REPO.git blender-mentor
cp -r blender-mentor ~/.agents/skills/blender-mentor
# Windows PowerShell:
# Copy-Item -Recurse blender-mentor "$env:USERPROFILE\\.agents\\skills\\blender-mentor"
```

### Claude Code

放到用户级 `~/.claude/skills/blender-mentor/`，或项目级 `.claude/skills/blender-mentor/`。

### Claude.ai（支持 Skills 的版本）

把仓库打成 zip（或直接上传本仓库的 `SKILL.md` + 目录），上传到 Skills 库即可。

### Cursor

直接用 Cursor 打开本仓库；对话中 `@SKILL.md`、`@references/main.md` 引用。想常驻可把 `SKILL.md` 放进 `.cursor/rules/`。

## 验证

```bash
python -m compileall -q scripts
python scripts/persona_lint.py . --allow-no-deny   # 结构门
python scripts/selftest.py .                       # 工具链自检（14 pass + 1 skipped）
```

Blender 侧（需要本机 Blender 4.2 LTS / 5.x）：

```bash
blender -b file.blend --python scripts/asset_gate.py -- --json gate.json
blender -b scene.blend --python scripts/biomech_check.py -- --eccentric 1,4 --support 1-4
```

## 使用示例

```text
用 blender-mentor 带我过一遍 M1 建模与拓扑
帮我审这个走路循环：按评分表打分，给 P0/P1/P2 修改清单
弹跳动画的形变包络帮我做成可验收的 spec
这个 Blender 报错什么原因？先给我 L2 提示
```

## 版本与更新

- 人设套件版本：**V5.4.0**；技能包发布版本：**v5.4.1**（详见 `CHANGELOG.md`）；
- 修改 `references/` 后必须重跑 `persona_lint.py`；
- 重新生成技能目录：`python tools/build_skill.py --source <V5.4.0 六件套目录> --out <仓库父目录> --force`（会保留 `.git`）。

## License

MIT，见 [LICENSE](LICENSE)。课程文档中的第三方参考书目仅作引用，版权归原作者。
"""

CHANGELOG_MD = """# Changelog

## V5.4.1 — 2026-10-19

> 技能包发布版本；人设套件版本仍为 **V5.4.0**（六件套版本锚点不变）。

### Changed
- 双语 README：English（`README.md`，默认）+ 简体中文（`README.zh-CN.md`），顶部互加语言跳转；
- Release 说明改为中英双语；
- 发布附件更新为含双语 README 的 `v5.4.1` 技能包；
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
    plan.setdefault("tools", []).extend([
        {"file": "scripts/curve_audit.py", "when": "曲线审计（插值/手柄统计）"},
        {"file": "scripts/render_probe.py", "when": "渲染探针（输出 //probe.png）"},
    ])
    return plan


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
        # 保留 .git，避免重建时毁掉仓库历史；其余内容重新生成
        for entry in os.listdir(skill_dir):
            if entry == ".git":
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
