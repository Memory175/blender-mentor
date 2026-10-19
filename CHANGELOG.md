# Changelog

## V5.4.1 — 2026-10-19

> 技能包发布版本；人设套件版本仍为 **V5.4.0**（六件套版本锚点不变）。

### Changed
- 双语 README：English（`README.md`，默认）+ 简体中文（`README.zh-CN.md`），顶部互加语言跳转；
- Release 说明改为中英双语；
- 发布附件更新为含双语 README 的 `v5.4.1` 技能包；
- Claude Code 插件支持：`.claude-plugin/marketplace.json` + `plugins/blender-mentor/`，
  可用 `/plugin marketplace add` + `/plugin install` 一键安装；
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
