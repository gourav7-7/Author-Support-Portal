$ErrorActionPreference = "Stop"
Push-Location "$PSScriptRoot\frontend"
try { & npm.cmd run dev }
finally { Pop-Location }
