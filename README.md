# Blender Mentor

**Turn Claude Code / DSH / Cursor into a senior Blender mentor + technical director.**

It diagnoses your level, teaches a structured lesson, grades your work with a 0–3 rubric, and runs machine acceptance on your `.blend` — assets, curves, renders, ESD secondary animation, and biomechanics.

**English** | [简体中文](README.zh-CN.md)

[![validate-skill](https://github.com/Memory175/blender-mentor/actions/workflows/validate.yml/badge.svg)](https://github.com/Memory175/blender-mentor/actions)
[![release](https://img.shields.io/github/v/release/Memory175/blender-mentor?color=2f81f7)](https://github.com/Memory175/blender-mentor/releases)
[![license](https://img.shields.io/github/license/Memory175/blender-mentor?color=3fb950)](https://github.com/Memory175/blender-mentor/blob/main/LICENSE)
[![Blender](https://img.shields.io/badge/Blender-4.2%20LTS%20%7C%205.x-orange)](https://www.blender.org/download/)

![Example session: prompt, rubric score, P0/P1/P2 fixes, machine acceptance](docs/demo.svg)

> **Not a Blender add-on.** The skill gives your AI agent the mentor's playbook. You still need Blender 4.2 LTS / 5.x installed to open `.blend` files and run acceptance checks.

## Quick start

**DSH** — clone and install (Windows / Linux / macOS / WSL):

```bash
git clone --depth 1 https://github.com/Memory175/blender-mentor.git
cd blender-mentor

# Windows
powershell -NoProfile -ExecutionPolicy Bypass -File dsh/install.ps1

# Linux / macOS / WSL
bash dsh/install.sh
```

**Claude Code** — install as a plugin:

```text
/plugin marketplace add Memory175/blender-mentor
/plugin install blender-mentor@blender-mentor-marketplace
```

**Cursor / other Agent Skills clients** — clone the repo and point your client at `SKILL.md` (in Cursor, mention `@SKILL.md`; for an always-on rule, add a project rule that references it).

Then open a new agent session and try:

```text
Use blender-mentor to walk me through M1 modeling and topology.
```

## See it in action

Prompt:

```text
Review this walk cycle. Grade it with the rubric and give me a P0/P1/P2 fix list.
```

What comes back (illustrative):

- **Placement:** L2 · Review mode
- **Score:** 2.1 / 3 · critical item: foot sliding
- **P0:** Lock contact frames 1 / 13 / 25; add heel roll.
- **P1:** Reduce hip Y translation 18%; clean shoulder counter-rotation.
- **P2:** Add toe flex on push-off; re-check the 12-frame cadence.
- **Acceptance:** `asset_gate` PASS · `curve_audit` 3 warnings · `render_probe` PASS
- **Next question:** "Fix P0 first, or should I generate the corrected keyframes?"

## What you get

| Component | What it does |
|---|---|
| **Mentor behavior** | L0–L3 level diagnosis; explain / coach / accept / firefight / review modes |
| **D1–D4 delivery loop** | deliver → self-review → P0/P1/P2 fix list → explicit next-step question |
| **0–3 rubric** | critical items, scoring anchors, and a self-review template |
| **M0–M6 curriculum** | modeling & topology → UV/materials/lighting/render → animation/rigging → physics/geometry nodes/pipeline |
| **10 acceptance scripts** | asset gate, curve audit, render probe, ESD envelope, biomechanics, router, lint, self-test |
| **Knowledge base** | 130 common misconceptions + 40 red lines |

## Requirements

| Requirement | Needed for |
|---|---|
| Blender 4.2 LTS / 5.x | `.blend` acceptance scripts (`blender -b ... --python scripts/...`) |
| Claude Code / DSH / Claude.ai / Cursor | Loading the skill |
| Python 3 | `selftest.py`, `persona_lint.py`, `load_router.py` |

Teaching and critique work without Blender installed. File inspection, render probes, and machine acceptance require a local Blender.

## How it works

```text
SKILL.md       routing + D1–D4 delivery loop + machine-acceptance commands
references/    6 persona documents, loaded on demand
scripts/       10 executable acceptance tools
assets/        ESD templates, load plans, deny-word example
```

1. `SKILL.md` routes the request and sets the delivery loop.
2. `load_router.py` builds a per-task load plan, so only the relevant references are loaded.
3. Acceptance scripts run against your local `.blend` through headless Blender.
4. Your files stay local; the acceptance tools do not upload anything.

<details>
<summary><strong>Installation — all clients</strong></summary>

### DSH (local)

Windows one-liner:

```powershell
git clone --depth 1 https://github.com/Memory175/blender-mentor.git "$env:TEMP\blender-mentor-src"; powershell -NoProfile -ExecutionPolicy Bypass -File "$env:TEMP\blender-mentor-src\dsh\install.ps1"; Remove-Item -Recurse -Force "$env:TEMP\blender-mentor-src"
```

Linux / macOS / WSL:

```bash
tmp="$(mktemp -d)"; git clone --depth 1 https://github.com/Memory175/blender-mentor.git "$tmp/bm" && bash "$tmp/bm/dsh/install.sh"; rm -rf "$tmp"
```

Alternative — download the installer from the latest Release:

```powershell
irm https://github.com/Memory175/blender-mentor/releases/latest/download/dsh-install.ps1 -OutFile "$env:TEMP\dsh-install.ps1"; powershell -NoProfile -ExecutionPolicy Bypass -File "$env:TEMP\dsh-install.ps1"
```

### DSH plugin market

This repository is also a DSH skill plugin: `package.json` declares `dsh.bundle.patch → cordis.patch.yml`, which mounts the bundled `skills/blender-mentor/`. After the dsh.so listing is approved:

```bash
dsh plugin --profile web add github:Memory175/blender-mentor
```

### Claude Code

```text
/plugin marketplace add Memory175/blender-mentor
/plugin install blender-mentor@blender-mentor-marketplace
```

Or copy the repo into `~/.claude/skills/blender-mentor/` (user level) / `.claude/skills/blender-mentor/` (project level).

### Claude.ai

Zip the skill folder (`SKILL.md` + `references/`, `scripts/`, `assets/`) and add it to your Skills library.

### Cursor

Open the repo and reference `@SKILL.md` / `@references/main.md` in chat. For always-on behavior, add a project rule that points at `SKILL.md`.

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
├── references/                  # 6 persona documents, loaded on demand
├── scripts/                     # 10 executable acceptance scripts
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

**Which clients are supported?**
DSH, Claude Code, Claude.ai, Cursor, and any client that supports the standard Agent Skills layout (`SKILL.md` + resources).

**Why do I see V5.4.0 and v5.4.3?**
V5.4.0 is the persona-suite version (the six source documents). v5.4.3 is the packaged skill release; they are versioned independently.

## Development

```bash
python -m compileall -q scripts tools
python scripts/persona_lint.py . --allow-no-deny   # structure gate
python scripts/selftest.py .                       # 14 pass + 1 skipped
```

Blender-side checks:

```bash
blender -b file.blend --python scripts/asset_gate.py -- --json gate.json
blender -b scene.blend --python scripts/biomech_check.py -- --eccentric 1,4 --support 1-4
```

Rebuild the skill directory:

```bash
python tools/build_skill.py --source <V5.4.0 six-file suite> --out <repo parent> --force
```

## License

MIT — see [LICENSE](LICENSE). Third-party references in the course documents are cited only; copyright remains with their authors.

---

If this saves you time, a ⭐ helps others find it · [Report an issue](https://github.com/Memory175/blender-mentor/issues) · [Releases](https://github.com/Memory175/blender-mentor/releases)
