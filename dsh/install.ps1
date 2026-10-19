param(
    [string]$Dest = (Join-Path $env:USERPROFILE ".agents\skills\blender-mentor"),
    [switch]$Force
)

# Blender Mentor — DSH one-line installer
# Usage (internet): irm https://raw.githubusercontent.com/Memory175/blender-mentor/main/dsh/install.ps1 | iex
# Usage (clone):    powershell -NoProfile -ExecutionPolicy Bypass -File .\dsh\install.ps1
$ErrorActionPreference = "Stop"
$SkillName = "blender-mentor"
$RepoUrl = "https://github.com/Memory175/blender-mentor.git"
$TempClone = $null

function Resolve-Source {
    if ($PSScriptRoot) {
        $candidate = Split-Path -Parent $PSScriptRoot
        if (Test-Path (Join-Path $candidate "SKILL.md")) {
            Write-Host "Using local source: $candidate"
            return $candidate
        }
    }
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        throw "git not found. Install Git, or download the repository zip and copy it manually."
    }
    $tmp = Join-Path $env:TEMP ("blender-mentor-src-" + [guid]::NewGuid().ToString("N"))
    Write-Host "Cloning $RepoUrl ..."
    git clone --depth 1 $RepoUrl $tmp | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "git clone failed. Check your network/proxy, then retry."
    }
    $script:TempClone = $tmp
    return $tmp
}

$Source = Resolve-Source
try {
    if (Test-Path $Dest) {
        $backupRoot = Join-Path $env:USERPROFILE ".agents\skill-backups"
        New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null
        $backup = Join-Path $backupRoot ($SkillName + "-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
        Move-Item -LiteralPath $Dest -Destination $backup
        Write-Host "Backed up existing skill to $backup"
    }

    New-Item -ItemType Directory -Force -Path $Dest | Out-Null
    $items = @("SKILL.md", "references", "scripts", "assets",
               "README.md", "README.zh-CN.md", "LICENSE", "CHANGELOG.md")
    foreach ($item in $items) {
        $src = Join-Path $Source $item
        if (Test-Path -LiteralPath $src) {
            Copy-Item -LiteralPath $src -Destination $Dest -Recurse -Force
        }
    }

    if (-not (Test-Path (Join-Path $Dest "SKILL.md"))) {
        throw "Install failed: SKILL.md was not copied."
    }
    $count = (Get-ChildItem -LiteralPath $Dest -Recurse -File).Count
    Write-Host ""
    Write-Host "Blender Mentor installed: $Dest ($count files)"
    Write-Host "Open a new DSH session and ask, for example:"
    Write-Host "  用 blender-mentor 带我过 M1 建模与拓扑"
    Write-Host "  帮我审这个走路循环，按评分表打分并给修改清单"

    $py = Get-Command python -ErrorAction SilentlyContinue
    if ($py) {
        try {
            & $py.Source (Join-Path $Dest "scripts\selftest.py") $Dest | Select-Object -Last 1
        } catch {
            Write-Host "(selftest skipped: $($_.Exception.Message))"
        }
    }
} finally {
    if ($TempClone) {
        Remove-Item -LiteralPath $TempClone -Recurse -Force -ErrorAction SilentlyContinue
    }
}
