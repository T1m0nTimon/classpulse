# Starts ClassPulse on port 8000 (reachable from other devices in the same network).
Set-Location (Join-Path $PSScriptRoot "..")
$port = if ($env:PORT) { $env:PORT } else { "8000" }
Write-Host "ClassPulse is starting on port $port - open http://localhost:$port and follow the hint on screen."
backend/.venv/Scripts/uvicorn classpulse.main:app --app-dir backend --host 0.0.0.0 --port $port --no-access-log
