$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

$PythonLauncher = Get-Command py -ErrorAction SilentlyContinue
if (-not $PythonLauncher) {
    throw "Install Python 3.12 and enable the Windows py launcher, then rerun setup.ps1."
}

if (Test-Path ".venv") {
    Remove-Item -Recurse -Force .venv
}

& py -3.12 -m venv .venv
if ($LASTEXITCODE -ne 0) {
    throw "Could not create the Python 3.12 virtual environment."
}

$VenvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "Could not upgrade pip."
}

& $VenvPython -m pip install torch --index-url https://download.pytorch.org/whl/cpu
if ($LASTEXITCODE -ne 0) {
    throw "Could not install CPU-only PyTorch. Check your internet connection and Python 3.12 installation."
}

& $VenvPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    throw "Could not install backend requirements."
}

if (-not (Test-Path ".env")) {
    Copy-Item .env.example .env
    Write-Host "Created .env. Open it and set IBM_API_KEY and IBM_PROJECT_ID."
}

Write-Host "`nSetup complete. Next: .\.venv\Scripts\Activate.ps1; python -m app.check_granite"
