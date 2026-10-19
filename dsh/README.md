# Blender Mentor — DSH one-line installer

This folder contains installers that copy the `blender-mentor` Agent Skill into
DeepSeek Harness's user skill directory (`~/.agents/skills/blender-mentor`).

## Windows (PowerShell)

From the internet:

```powershell
irm https://raw.githubusercontent.com/Memory175/blender-mentor/main/dsh/install.ps1 | iex
```

From a clone:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\dsh\install.ps1
```

Optional: `-Dest <path>` to install elsewhere, `-Force` to skip using the
existing local source check.

## Linux / macOS / WSL

```bash
bash dsh/install.sh
```

Or with a custom destination:

```bash
SKILL_DEST="$HOME/.agents/skills/blender-mentor" bash dsh/install.sh
```

The installer:

1. uses the local clone when one is available, otherwise `git clone --depth 1`;
2. backs up an existing `blender-mentor` skill under `~/.agents/skill-backups/`;
3. copies `SKILL.md`, `references/`, `scripts/`, `assets/`, README/LICENSE/CHANGELOG;
4. verifies `SKILL.md` exists and runs `scripts/selftest.py` when Python is available.

After installing, open a new DSH session and ask e.g. `用 blender-mentor 带我过 M1`.
