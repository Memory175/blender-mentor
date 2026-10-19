# Blender Mentor — DSH one-line installer

This folder contains installers that copy the `blender-mentor` Agent Skill into
DeepSeek Harness's user skill directory (`~/.agents/skills/blender-mentor`).

> `raw.githubusercontent.com` may be blocked on some networks, so the one-line
> commands below use the latest Release asset instead.

## Windows (PowerShell)

```powershell
irm https://github.com/Memory175/blender-mentor/releases/latest/download/dsh-install.ps1 -OutFile "$env:TEMP\dsh-install.ps1"; powershell -NoProfile -ExecutionPolicy Bypass -File "$env:TEMP\dsh-install.ps1"
```

From a clone:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\dsh\install.ps1
```

Options: `-Dest <path>` to install elsewhere.

## Linux / macOS / WSL

```bash
curl -fsSL https://github.com/Memory175/blender-mentor/releases/latest/download/dsh-install.sh | bash
```

Or from a clone:

```bash
bash dsh/install.sh
```

Custom destination:

```bash
SKILL_DEST="$HOME/.agents/skills/blender-mentor" bash dsh/install.sh
```

The installer:

1. uses the local clone when one is available, otherwise `git clone --depth 1`;
2. backs up an existing `blender-mentor` skill under `~/.agents/skill-backups/`;
3. copies `SKILL.md`, `references/`, `scripts/`, `assets/`, README/LICENSE/CHANGELOG;
4. verifies `SKILL.md` exists and runs `scripts/selftest.py` when Python is available.

After installing, open a new DSH session and ask e.g. `用 blender-mentor 带我过 M1`.
