# Blender Mentor — DSH one-line installer

This folder contains installers that copy the `blender-mentor` Agent Skill into
DeepSeek Harness's user skill directory (`~/.agents/skills/blender-mentor`).

> Some networks block `raw.githubusercontent.com` and can be slow on release
> assets, so the primary one-liners below use `git clone`.

## Windows (PowerShell)

```powershell
git clone --depth 1 https://github.com/Memory175/blender-mentor.git "$env:TEMP\blender-mentor-src"; powershell -NoProfile -ExecutionPolicy Bypass -File "$env:TEMP\blender-mentor-src\dsh\install.ps1"; Remove-Item -Recurse -Force "$env:TEMP\blender-mentor-src"
```

## Linux / macOS / WSL

```bash
tmp="$(mktemp -d)"; git clone --depth 1 https://github.com/Memory175/blender-mentor.git "$tmp/bm" && bash "$tmp/bm/dsh/install.sh"; rm -rf "$tmp"
```

## From a clone

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\dsh\install.ps1
```

```bash
bash dsh/install.sh
```

Options: `-Dest <path>` (PowerShell) or `SKILL_DEST=<path>` (bash) to install elsewhere.

## What it does

1. uses the local clone when one is available, otherwise `git clone --depth 1`;
2. backs up an existing `blender-mentor` skill under `~/.agents/skill-backups/`;
3. copies `SKILL.md`, `references/`, `scripts/`, `assets/`, README/LICENSE/CHANGELOG;
4. verifies `SKILL.md` exists and runs `scripts/selftest.py` when Python is available.

After installing, open a new DSH session and ask e.g. `用 blender-mentor 带我过 M1`.
