# Run from PowerShell: powershell -ExecutionPolicy Bypass -File .\setup.ps1
$ErrorActionPreference = "Stop"
function Invoke-Checked {
    param([string]$Executable, [string[]]$CommandArgs)
    & $Executable @CommandArgs
    if ($LASTEXITCODE -ne 0) { throw "Command failed: $Executable $CommandArgs" }
}
Push-Location $PSScriptRoot
try {
    if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw "Install Python 3.12 with the Windows Python launcher first." }
    if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) { throw "Install Node.js 22 LTS or newer, then open a new PowerShell terminal." }
    if (-not (Test-Path .env)) { Copy-Item .env.example .env }
    if (-not (Test-Path .venv\Scripts\python.exe)) { Invoke-Checked -Executable "py" -CommandArgs @("-3.12", "-m", "venv", ".venv") }
    $ProjectPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
    Invoke-Checked -Executable $ProjectPython -CommandArgs @("-m", "pip", "install", "-r", "backend\requirements-dev.txt")
    Push-Location frontend
    try {
        Invoke-Checked -Executable "npm.cmd" -CommandArgs @("ci")
        Invoke-Checked -Executable "npm.cmd" -CommandArgs @("run", "build")
    } finally { Pop-Location }
    Push-Location backend
    try { Invoke-Checked -Executable $ProjectPython -CommandArgs @("-m", "app.seed") }
    finally { Pop-Location }
    Write-Host "Setup complete. Put your OPENAI_API_KEY in .env, then run: powershell -ExecutionPolicy Bypass -File .\run.ps1"
} finally { Pop-Location }
