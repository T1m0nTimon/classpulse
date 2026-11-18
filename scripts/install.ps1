# One-time setup on Windows. Needs Python 3.11+ and Node.js 20+.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
python -m venv backend/.venv
backend/.venv/Scripts/python -m pip install --upgrade pip | Out-Null
backend/.venv/Scripts/python -m pip install -e "backend[postgres]"
Push-Location frontend; npm ci; npm run build; Pop-Location
if (-not (Test-Path .env)) {
  $secret = backend/.venv/Scripts/python -c "import secrets; print(secrets.token_urlsafe(48))"
  (Get-Content .env.example) -replace '^SECRET_KEY=.*', "SECRET_KEY=$secret" | Set-Content .env
  Write-Host "Created .env with a random SECRET_KEY."
}
Write-Host "Done. Start ClassPulse with: scripts\start.ps1"
