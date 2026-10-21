param([Parameter(Mandatory = $true)][string]$TargetPath)
$ErrorActionPreference = "Stop"
$TargetRoot = (Resolve-Path -LiteralPath $TargetPath).Path
if ($TargetRoot.TrimEnd('\') -eq $PSScriptRoot.TrimEnd('\')) {
    throw "Extract the new ZIP into a separate folder, then point -TargetPath at your existing project."
}
if (-not (Test-Path (Join-Path $TargetRoot "backend\app\main.py")) -or
    -not (Test-Path (Join-Path $TargetRoot "frontend\package.json"))) {
    throw "TargetPath must be the existing BookLeaf project root containing backend and frontend."
}
$Manifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot "update-files.json") -Raw | ConvertFrom-Json
# Validate every source before copying anything. Runtime configuration/data never appear in this manifest.
foreach ($Entry in $Manifest.files) {
    $Relative = [string]$Entry.path
    if ([IO.Path]::IsPathRooted($Relative) -or $Relative -match '(^|[\\/])\.\.([\\/]|$)' -or
        $Relative -match '(^|[\\/])(\.env|\.local-secret|\.git|\.venv|node_modules)([\\/]|$)' -or $Relative -match '\.db($|-)') {
        throw "Unsafe update path: $Relative"
    }
    $Source = Join-Path $PSScriptRoot $Relative
    if ((Get-FileHash -LiteralPath $Source -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Entry.sha256) {
        throw "Update file changed after packaging: $Relative"
    }
}
$BackupRoot = Join-Path $TargetRoot (".bookleaf-upgrade-backup\" + (Get-Date -Format "yyyyMMdd-HHmmss-fff"))
foreach ($Entry in $Manifest.files) {
    $Destination = Join-Path $TargetRoot $Entry.path
    if (Test-Path -LiteralPath $Destination) {
        $Backup = Join-Path $BackupRoot $Entry.path
        New-Item -ItemType Directory -Force -Path (Split-Path $Backup -Parent) | Out-Null
        Copy-Item -LiteralPath $Destination -Destination $Backup
    }
}
foreach ($Entry in $Manifest.files) {
    $Destination = Join-Path $TargetRoot $Entry.path
    New-Item -ItemType Directory -Force -Path (Split-Path $Destination -Parent) | Out-Null
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $Entry.path) -Destination $Destination -Force
}
Write-Host "Updated source copied. Your .env, keys, virtual environment and database files were preserved."
Write-Host "Previous source files were backed up under: $BackupRoot"
Write-Host "From your existing project folder, run setup.ps1 to rebuild and add the attachments table, then run.ps1."
