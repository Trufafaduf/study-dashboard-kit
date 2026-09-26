<#
.SYNOPSIS
    Link this kit's .claude/commands and .claude/skills into a brain's
    .claude folder (Windows), so Claude Code discovers them from the outer
    repo.

.DESCRIPTION
    Run from anywhere; pass -BrainRoot to point at your brain. It defaults to
    this kit's parent directory, i.e. the layout where the kit sits at
    <brain>/<kit-folder> (as a submodule or a plain clone).

    For each command file under .claude/commands and each skill folder under
    .claude/skills in this kit, creates a link at
    <BrainRoot>/.claude/<commands|skills>/<name> pointing back into the kit.
    Skill folders (directories) are linked with an NTFS junction; command
    files are linked with a hard link (junctions can't target files).

    Idempotent: an existing link to the same target, or a file whose content
    already matches the kit's copy, is left alone and reported as already
    linked. A real file or folder that differs is never overwritten - the
    script warns and skips it.

.PARAMETER BrainRoot
    The root of your brain (the folder with wiki/, raw/, specs/, etc). Not
    required to exist in advance for path resolution to fail loudly if it's
    wrong.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\link-kit.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\link-kit.ps1 -BrainRoot D:\code\my-brain
#>
param(
    [string]$BrainRoot
)

$KitRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $BrainRoot) { $BrainRoot = Join-Path $KitRoot ".." }
$BrainRoot = (Resolve-Path $BrainRoot).Path

function Link-One {
    param([string]$Rel, [bool]$IsDir)
    $target = Join-Path $KitRoot $Rel
    if (-not (Test-Path $target)) { return }
    $dest = Join-Path $BrainRoot $Rel
    $destDir = Split-Path $dest -Parent
    if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }

    if (Test-Path $dest) {
        $item = Get-Item $dest -Force
        if ($item.LinkType -eq "Junction" -or $item.LinkType -eq "SymbolicLink") {
            if ($item.Target -contains $target -or $item.Target -eq $target) {
                Write-Host "ok (already linked): $Rel"
            } else {
                Write-Warning "skip: $dest links elsewhere (leaving it alone)"
            }
            return
        }
        if (-not $IsDir) {
            $a = (Get-FileHash $dest -ErrorAction SilentlyContinue).Hash
            $b = (Get-FileHash $target -ErrorAction SilentlyContinue).Hash
            if ($a -and $a -eq $b) {
                Write-Host "ok (already linked): $Rel"
                return
            }
        }
        Write-Warning "skip: $dest exists and is not a link to this kit (leaving it alone)"
        return
    }

    if ($IsDir) {
        New-Item -ItemType Junction -Path $dest -Target $target | Out-Null
    } else {
        New-Item -ItemType HardLink -Path $dest -Target $target | Out-Null
    }
    Write-Host "linked: $Rel -> $target"
}

$cmdSrc = Join-Path $KitRoot ".claude\commands"
if (Test-Path $cmdSrc) {
    Get-ChildItem $cmdSrc -Filter *.md | ForEach-Object {
        Link-One ".claude\commands\$($_.Name)" $false
    }
}

$skillSrc = Join-Path $KitRoot ".claude\skills"
if (Test-Path $skillSrc) {
    Get-ChildItem $skillSrc -Directory | ForEach-Object {
        Link-One ".claude\skills\$($_.Name)" $true
    }
}
