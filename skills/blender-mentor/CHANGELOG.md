# Changelog

## V5.16.1 — 2026-10-20

> 验收 Profile 适用性修复 + 发布链修复；套件升 **V5.16.1**。

### Fixed
- `check.applies_if` / `optional` / `missing_context` 与 `--context`：浴室、厨房、楼梯、注塑、3D 打印、人体等条件检查不再无条件误报；必需上下文缺失返回 ask，optional 缺上下文 skip。
- `CHAR-RIG` 增加 human-only `biomech` 检查。
- `tools/build_skill.py` 支持当前标准布局，`--source .` 可重建并通过内置 selftest。
- `layout_check.py` 等外部检查标记 `tool_scope: project`，router 输出 `external_tools`。
- `persona_lint.py` 增加 acceptance profile schema/重复 ID/工具存在性校验。
- `selftest.py` 与 GitHub Actions 纳入 acceptance router 自检和标准布局构建。
- `INT-INTERIOR` 补 `support_contact`、`vertical_clearance`、`naming_duplicates`。
- `--list` 显示 `GENERIC`；`--context`/`--preflight` 读取失败返回明确错误。

### Tests
- `acceptance_router.py --selftest`：15/15；
- `selftest.py`：28/28；
- `persona_lint.py`：EXIT 0；
- `tools/build_skill.py --source . --out <tmp> --force`：PASS。

## V5.16.0 — 2026-10-20

> 验收分项 Profile 入人设；套件升 **V5.16.0**。

### Added
- `assets/acceptance_profiles.json`：INT-INTERIOR / ARCH-EXTERIOR / PROD-HARD / CHAR-RIG / ANIM-FX / ENV-SCENE / REALTIME-ASSET / GENERIC + LOOKDEV/DELIVERY overlay；
- `references/acceptance-profiles.md`：触发优先级、报告格式、不适用项、与流程/模型 QA 的接口；
- `scripts/acceptance_router.py`：显式 profile / preflight 模块映射 / 关键词触发 / 平局 ask / GENERIC；含 `--selftest`；
- `SKILL.md §0.8`、`main.md §2.12`：验收分项路由硬规则；
- `load_plan` 增加 acceptance-profiles 按需加载与 router 工具。

### Changed
- 套件/README/版本锚点 V5.15.0 → **V5.16.0**；
- `main.md` 文件数 10 → 11；README 参考文件 13 → 14，工具 23 → 24；
- 室内验收不再要求拔模/重量绘制；产品验收不再要求门洞/家具；角色验收不再要求房间面积。

### Tests
- `acceptance_router.py --selftest`：建筑内饰/产品/角色/实时资产/GENERIC/冲突 ask/显式覆盖/LOOKDEV overlay；
- `persona_lint.py`、`selftest.py`、`preflight.py` 回归。

## V5.15.0 — 2026-10-20

> 通用生产流程入人设；套件升 **V5.15.0**。

### Added
- `references/production-pipeline.md`：G0–G6 阶段/门禁、标准目录、数据契约、摆放 helper、QA L0–L5、冻结/变更、角色、反模式、DoD；
- `SKILL.md §0.7`：生产流程门禁（先冻结平面、禁止绝对坐标、覆盖率、禁止静默 allowlist、表现层不改几何）；
- `main.md §2.11`：生产流程协议与 G0–G6 门禁；
- `model-qa.md §3.1`：L1 AABB → L2 BVH → L3 门扇扫掠 + 覆盖率规则。

### Changed
- 套件/README/版本锚点 V5.14.0 → **V5.15.0**；
- `main.md` 文件数 9 → 10；
- 接触例外表替代静默 allowlist：reason + owner + 过期时间；
- `load_plan.json` 增加 production-pipeline 按需加载触发词。

### Tests
- `persona_lint.py`、`selftest.py`、`preflight.py` 回归。

## V5.14.0 — 2026-10-20

> 新增 INT-002 现代轻奢大平层变体；套件升 **V5.14.0**。

### Added
- `assets/modules/INT-002.json`：现代轻奢大平层/电梯平层变体（styles=`modern`+`luxury`，layouts=`apartment`；experimental）；
- `references/module-int-002.md`：人读版，含房间程序、分区/动线、风格基线、布局校验与 assumptions；
- `module_selftest` 增加 `int002_proceed`；
- README/中文 README 增加 INT-002 说明。

### Changed
- 人设文件数 8 → 9（模块 4 → 5）；references 11 → 12；
- 版本锚点 V5.13.0 → **V5.14.0**（SKILL / main / README / toolbox / rubric / curriculum / load_plan / registry）；
- INT-001 版本 **0.1.2 → 0.1.3**（仅 `intent.exclude` 排除现代轻奢/大平层，避免与 INT-002 同时命中）；INT-002 初始 **0.1.0**；
- 来源：INT-002 全部数据为 `assumption: true`，jurisdiction pending，不能当当地规范。

### Tests
- `module_lint.py`、`module_conflict.py`、`module_selftest.py`、`persona_lint.py`、`selftest.py`；
- 预期 INT-002 命中 `现代轻奢大平层`，INT-001 仍只命中中式两室两厅。

## V5.13.0 — 2026-10-20

> INT 空间布局校验入人设；套件升 **V5.13.0**。

### Added
- `SKILL.md §0.5`：INT 强制空间布局校验（门洞 keep-out、门洞断面、家具 AABB、支撑、垂直净空、命名）；
- `SKILL.md §3`：项目侧 `layout_check.py --strict` 验收入口；
- `references/main.md §2.10`：室内空间布局校验协议；
- `references/module-int-001.md §7`：INT 布局校验必查项/执行方式/实现约束；
- `references/model-qa.md §3.1`：通用建模 QA 增加室内空间校验。

### Changed
- 版本锚点 V5.12.0 → **V5.13.0**（SKILL / main / README / toolbox / rubric / curriculum / load_plan / registry）；
- INT-001 模块版本保持 **0.1.2**（data 不变，仅人设/工作流文档更新）；
- `source_audit` 仍为 **warn**，不改变来源状态。

### Tests
- 重跑 `persona_lint.py` 与套件 `selftest.py`；
- 校验示例：`layout_report.md` 0 FAIL / 1 WARN（`.001` 命名）。

## V5.12.0 — 2026-10-20

> 自审查索引 + 发布授权；套件升 **V5.12.0**。

### Added
- `scripts/self_audit.py`：自动扫描 `assets/modules/*.json` + `references/module-*.md`，写 `assets/self_audit_index.json`；
- `--sync` 自动补 `module_registry.json` 与 `load_plan.json`，新增模块不再手写索引；
- `persona_lint` 增加 `self_audit` 检查；
- `build_skill` 构建时自动跑 self_audit（write/sync），失败则构建失败；
- `SKILL.md §0.6` / `main.md §11.4`：默认不打包、不上传；只有用户明确说“发布/上传”才执行。

### Changed
- README 工具数 22 → 23；参考文件 11；
- `module_selftest` 24 项，`selftest` 27 项；
- 现有模块版本不变（INT-001 0.1.2）。

## V5.11.3 — 2026-10-20

> 人设 bug 修复；套件升 **V5.11.3**。

### Fixed
- `persona_lint` 未索引 `INT-001`：现校验 `module-int-001.md` 版本与 main 注册表一致；
- `preflight` 强制 `INT-001` 缺口会误拦截已命中的 `INT-002` 等风格/布局变体；
- `module_gap` 对“已有 INT 模块但缺 style/layout”误返回 `resolve_existing`，现返回 `missing_style_layout`；
- `main.md` 仍写“七个文件”且缺 INT-001 模块表/加载表，现补为八个文件；
- `SKILL.md` 描述缺 INT/室内触发词，现补 interior design / Chinese-style interior / two-bedroom apartment。

### Tests
- `module_selftest` 扩到 24 项（INT 变体、missing style/layout）；
- `selftest` 27 项、干净安装 24 项不变。

## V5.11.2 — 2026-10-20

> INT-001 收编 open questions；人设套件升 **V5.11.2**。

### Added
- INT-001 `open_questions`：OQ-001..007，含 priority / why / default_if_unanswered；
- `references/module-int-001.md §7` 改为项目输入清单表；
- 模块版本 0.1.1 → **0.1.2**（仅文档/问题清单，data 不变）。

### Changed
- 模块 registry hash 更新；
- 其它模块版本不变；`source_audit` 仍 warn。

## V5.11.1 — 2026-10-20

> INT-001 来源表补全；人设套件升 **V5.11.1**。

### Changed
- INT-001 版本 0.1.0 → **0.1.1**；
- 来源表补 URL/出版方/edition/reliability；新增 `SRC-CODE-HB-HEIGHT`；
- 层高数据改引湖北文件；`source_registry` 29 条；
- 来源仍为 pending/metadata-only，`source_audit` 仍为 **warn**；
- 模块 registry hash 更新；其它模块版本不变。

## V5.11.0 — 2026-10-20

> 新增 INT-001 内饰模块；人设套件升 **V5.11.0**。

### Added
- `assets/modules/INT-001.json`：中式风格两室两厅公寓内饰模块（experimental，styles=`chinese`，layouts=`apartment`，13 个 data key）；
- `references/module-int-001.md`：人读版，含风格/布局数据、硬规则、来源状态；
- 13 条 `SRC-*` 来源登记（全部 pending / 未提供 URL、版次、条款，来源审计预期 warn）；
- `load_plan` / `module_registry` 注册 INT-001；
- `module_lint` 校验 INT-* 的 styles/layouts 与 confidence；
- `module_selftest` 扩到 22 项（INT-001 proceed / style mismatch / layout mismatch / gap prompt）。

### Changed
- 人设文件数 7 → 8；references 10 → 11；
- 模块自检 22 项；全局 selftest 仍 27 项；
- 版本 V5.11.0；现有模块版本不变。

## V5.10.0 — 2026-10-20

> 内饰/室内建模硬规则；人设套件升 **V5.10.0**。

### Added
- `assets/style_taxonomy.json`：12 种建筑风格 + 7 种空间布局的稳定 ID/别名；
- `assets/module_gap_hints.json`：新增 `INT-001`（force），内饰不再按普通建模放行；
- `preflight`：内饰命中强制 block；已有 INT 模块时核对 `styles`/`layouts`，不匹配返回 ask；
- `module_gap`：INT 提示 Prompt 包含推断风格/布局，要求模块声明 styles/layouts；
- `module.schema` / `_template`：增加 `styles`、`layouts`；
- `module_lint`：INT-* 必须有非空 styles/layouts；
- `SKILL.md §0.5`、`module-format`、`module-authoring §6.6`：内饰模块规则。

### Changed
- `module_selftest` 扩到 18 项（内饰 block / prompt / style/layout proceed / mismatch ask）；
- 版本 V5.10.0；模块版本不变（ENG 1.1.0 / BIO 1.1.0 / ESD 1.1.9）。

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
