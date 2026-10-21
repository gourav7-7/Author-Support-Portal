$ErrorActionPreference = "Stop"
Push-Location "$PSScriptRoot\backend"
try { & "$PSScriptRoot\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 }
finally { Pop-Location }
