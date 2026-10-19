#!/usr/bin/env bash
# Blender Mentor — DSH installer (Linux / macOS / WSL)
# Usage: bash dsh/install.sh
#        SKILL_DEST="$HOME/.agents/skills/blender-mentor" bash dsh/install.sh
set -euo pipefail

SKILL_NAME="blender-mentor"
REPO_URL="https://github.com/Memory175/blender-mentor.git"
DEST="${SKILL_DEST:-$HOME/.agents/skills/$SKILL_NAME}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
SRC="$(dirname "$SCRIPT_DIR")"
TEMP_CLONE=""

cleanup() {
    if [ -n "$TEMP_CLONE" ] && [ -d "$TEMP_CLONE" ]; then
        rm -rf "$TEMP_CLONE"
    fi
}
trap cleanup EXIT

if [ ! -f "$SRC/SKILL.md" ]; then
    if ! command -v git >/dev/null 2>&1; then
        echo "error: git not found. Install Git, or download the repository zip manually." >&2
        exit 1
    fi
    TEMP_CLONE="$(mktemp -d "${TMPDIR:-/tmp}/blender-mentor-src-XXXXXX")"
    echo "Cloning $REPO_URL ..."
    git clone --depth 1 "$REPO_URL" "$TEMP_CLONE/blender-mentor"
    SRC="$TEMP_CLONE/blender-mentor"
else
    echo "Using local source: $SRC"
fi

if [ -d "$DEST" ]; then
    BACKUP_ROOT="$HOME/.agents/skill-backups"
    mkdir -p "$BACKUP_ROOT"
    BACKUP="$BACKUP_ROOT/$SKILL_NAME-$(date +%Y%m%d-%H%M%S)"
    mv "$DEST" "$BACKUP"
    echo "Backed up existing skill to $BACKUP"
fi

mkdir -p "$DEST"
for item in SKILL.md references scripts assets README.md README.zh-CN.md LICENSE CHANGELOG.md; do
    if [ -e "$SRC/$item" ]; then
        cp -R "$SRC/$item" "$DEST/"
    fi
done

if [ ! -f "$DEST/SKILL.md" ]; then
    echo "error: install failed, SKILL.md missing." >&2
    exit 1
fi

COUNT="$(find "$DEST" -type f | wc -l | tr -d ' ')"
echo ""
echo "Blender Mentor installed: $DEST ($COUNT files)"
echo "Open a new DSH session and ask, for example:"
echo "  用 blender-mentor 带我过 M1 建模与拓扑"
echo "  帮我审这个走路循环，按评分表打分并给修改清单"

if command -v python3 >/dev/null 2>&1; then
    python3 "$DEST/scripts/selftest.py" "$DEST" | tail -n 1 || true
elif command -v python >/dev/null 2>&1; then
    python "$DEST/scripts/selftest.py" "$DEST" | tail -n 1 || true
fi
