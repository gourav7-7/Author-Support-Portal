# Serves the compiled frontend and API together at http://127.0.0.1:8000
$ErrorActionPreference = "Stop"
if (-not (Test-Path "$PSScriptRoot\.venv\Scripts\python.exe")) { throw "Run setup.ps1 first." }
if (-not (Test-Path "$PSScriptRoot\frontend\dist\index.html")) { throw "Run npm.cmd run build inside frontend first." }
Push-Location "$PSScriptRoot\backend"
try { & "$PSScriptRoot\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 }
finally { Pop-Location }
