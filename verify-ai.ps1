# Run explicitly to send two small live requests using your own OpenAI API key.
$ErrorActionPreference = "Stop"
$ProjectPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $ProjectPython)) { throw "Run setup.ps1 first." }
Push-Location (Join-Path $PSScriptRoot "backend")
try {
    & $ProjectPython -m app.verify_ai --run
    if ($LASTEXITCODE -ne 0) { throw "Live AI verification did not pass. Review the output above." }
} finally { Pop-Location }
