param([int]$Port = 8000)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Unable to create the Python virtual environment.' }
}
& $pythonPath -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& $pythonPath scripts\configure_local.py
if ($LASTEXITCODE -ne 0) { throw 'Local configuration failed.' }
Write-Host "Opening CivicSathi at http://127.0.0.1:$Port (Ctrl+C to stop)."
Write-Host 'Staff access is granted to email addresses listed in STAFF_EMAILS in .env.'
& $pythonPath -m uvicorn app.main:app --host 127.0.0.1 --port $Port --reload
