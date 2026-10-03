# JobHunterX — one command to set up and start (Windows).
#
#   powershell -ExecutionPolicy Bypass -File start.ps1
#
# First time: installs uv, makes the venv, installs packages, creates .env, starts the app.
# Next times: skips what is already done and just starts the app.
# Add -NoStart to only set up.

param([switch]$NoStart)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

function Say($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Fail($msg) { Write-Host "ERROR: $msg" -ForegroundColor Red; exit 1 }

# 1. uv (fast installer)
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Say "Installing uv (fast Python installer)..."
    try {
        Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    } catch {
        Say "uv installer failed, trying pip instead..."
        python -m pip install --user uv
    }
    $env:Path = "$env:USERPROFILE\.local\bin;$env:USERPROFILE\.cargo\bin;$env:Path"
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Fail "uv was installed but this window can't see it yet. Close this window, open a new one and run the same command again."
    }
}

# 2. Virtual environment (uv downloads Python 3.11 if it is missing)
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Say "Creating the virtual environment (.venv)..."
    uv venv --python 3.11 .venv
    if ($LASTEXITCODE -ne 0) { Fail "Could not create the virtual environment." }
}
$py = (Resolve-Path ".venv\Scripts\python.exe").Path

# 3. Packages — reinstalled only when requirements.txt changes
$hash = (Get-FileHash requirements.txt -Algorithm SHA256).Hash.ToLower()
$stamp = ".venv\.requirements.sha256"
if (-not (Test-Path $stamp) -or (Get-Content $stamp -Raw).Trim() -ne $hash) {
    Say "Installing packages (about 30 seconds)..."
    uv pip install --python $py -r requirements.txt
    if ($LASTEXITCODE -ne 0) { Fail "Package install failed. Check your internet connection and run the command again." }
    Set-Content -Path $stamp -Value $hash
} else {
    Say "Packages already installed."
}

# 4. Settings file
if (-not (Test-Path "jobhunterx\.env")) {
    Copy-Item "jobhunterx\.env.example" "jobhunterx\.env"
    Say "Created jobhunterx\.env  (the app will ask for your free AI key on the first screen)"
}

if ($NoStart) { Say "Setup done. Run this command again (without -NoStart) to start the app."; exit 0 }

# 5. Start the app and open the browser
$port = 8000
$line = Select-String -Path "jobhunterx\.env" -Pattern '^\s*PORT\s*=\s*(\d+)' | Select-Object -First 1
if ($line) { $port = $line.Matches[0].Groups[1].Value }
$url = "http://127.0.0.1:$port"
if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
    Say "Something is already running on port $port - probably JobHunterX in another window. Opening $url"
    Say "If it is another program, set PORT=8001 in jobhunterx\.env and run this again."
    Start-Process $url
    exit 0
}
Say "Starting JobHunterX at $url  (press Ctrl + C to stop)"
Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoProfile", "-Command", "Start-Sleep 6; Start-Process '$url'"
Set-Location jobhunterx
& $py -m jobhunterx.api.main
