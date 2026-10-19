# blender-mentor

> Blender 全栈导师 V5.4.0 · AI Agent Skill（标准布局）
> 把这个仓库放进支持 Agent Skills 的客户端（DSH / Claude Code / Claude.ai / Cursor 等），
> 让 Agent 以「资深 Blender 导师 + 技术总监」的方式教学、评分、验收与排错。

[English](README.md) | **简体中文**

[![validate-skill](https://github.com/Memory175/blender-mentor/actions/workflows/validate.yml/badge.svg)](https://github.com/Memory175/blender-mentor/actions)

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
├── .claude-plugin/
│   └── marketplace.json     # Claude Code 插件市场
├── .github/workflows/validate.yml
├── tools/
│   └── build_skill.py       # 维护侧构建工具（从 V5.4.0 六件套重建技能）
├── plugins/
│   └── blender-mentor/      # Claude Code 插件包装（自动生成）
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
git clone https://github.com/Memory175/blender-mentor.git blender-mentor
cp -r blender-mentor ~/.agents/skills/blender-mentor
# Windows PowerShell:
# Copy-Item -Recurse blender-mentor "$env:USERPROFILE\.agents\skills\blender-mentor"
```

### Claude Code

放到用户级 `~/.claude/skills/blender-mentor/`，或项目级 `.claude/skills/blender-mentor/`。

也可以用本仓库的插件市场一键安装：

```text
/plugin marketplace add Memory175/blender-mentor
/plugin install blender-mentor@blender-mentor-marketplace
```

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
