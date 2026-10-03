# JobHunterX - one command to set up and start (Windows).
#
#   powershell -ExecutionPolicy Bypass -File start.ps1      (or double-click start.bat)
#
# First time: installs uv, makes the venv, installs packages, creates .env, starts the app.
# Next times: checks everything is still fine, then starts the app.
# The browser opens only after the app is really up and answering.
# Add -NoStart to only set up and check.

param([switch]$NoStart)

$ErrorActionPreference = "Continue"   # every step checks its own result; stderr warnings must not abort
Set-Location -Path $PSScriptRoot

function Say($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Ok($msg) { Write-Host "    OK  $msg" -ForegroundColor Green }
function Fail($msg) { Write-Host ""; Write-Host "ERROR: $msg" -ForegroundColor Red; exit 1 }

# ---------------------------------------------------------------- 1. uv
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Say "Installing uv (fast Python installer)..."
    try {
        Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    } catch {
        Say "uv installer failed, trying pip instead..."
        python -m pip install --user uv
    }
    $env:Path = "$env:USERPROFILE\.local\bin;$env:USERPROFILE\.cargo\bin;$env:Path"
}
$uvVersion = (& uv --version 2>$null)
if ($LASTEXITCODE -ne 0 -or -not $uvVersion) {
    Fail "uv is installed but this window can't use it yet. Close this window, open a new one and run the same command again."
}
Ok $uvVersion

# ---------------------------------------------------------------- 2. venv (rebuilt if broken)
$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
function Test-Venv { if (-not (Test-Path $py)) { return $false }; & $py -c "import sys; assert sys.version_info >= (3, 11)" 2>$null; return ($LASTEXITCODE -eq 0) }
if (-not (Test-Venv)) {
    if (Test-Path ".venv") { Say "The virtual environment looks broken - rebuilding it..." } else { Say "Creating the virtual environment (.venv)..." }
    uv venv --clear --python 3.11 .venv
    if ($LASTEXITCODE -ne 0 -or -not (Test-Venv)) { Fail "Could not create the virtual environment. Check your internet connection and try again." }
    Remove-Item ".venv\.requirements.sha256" -ErrorAction SilentlyContinue
}
Ok ("virtual environment: " + (& $py --version))

# ---------------------------------------------------------------- 3. packages (installed, then verified)
function Install-Packages {
    Say "Installing packages (about 30 seconds the first time)..."
    uv pip install --python $py -r requirements.txt
    if ($LASTEXITCODE -ne 0) { Fail "Package install failed. Check your internet connection and run the command again." }
    Set-Content -Path ".venv\.requirements.sha256" -Value $hash
}
function Test-App {
    Push-Location jobhunterx
    try { & $py -c "import jobhunterx.api.main" 2>$null; return ($LASTEXITCODE -eq 0) } finally { Pop-Location }
}
$hash = (Get-FileHash requirements.txt -Algorithm SHA256).Hash.ToLower()
$stamp = ".venv\.requirements.sha256"
if (-not (Test-Path $stamp) -or (Get-Content $stamp -Raw).Trim() -ne $hash) { Install-Packages }
Say "Checking that everything is installed correctly..."
if (-not (Test-App)) {
    Say "Something is missing - repairing the install..."
    Install-Packages
    if (-not (Test-App)) {
        Push-Location jobhunterx; & $py -c "import jobhunterx.api.main"; Pop-Location
        Fail "The app still can't load (see the message above). Delete the .venv folder and run this command again."
    }
}
Ok "all packages load"

# ---------------------------------------------------------------- 4. settings file
if (-not (Test-Path "jobhunterx\.env")) {
    Copy-Item "jobhunterx\.env.example" "jobhunterx\.env"
    Ok "created jobhunterx\.env (the app will ask for your free AI key on the first screen)"
} else {
    Ok "settings file jobhunterx\.env"
}

if ($NoStart) { Say "Setup done and checked. Run this command again (without -NoStart) to start the app."; exit 0 }

# ---------------------------------------------------------------- 5. start, then open the browser once it answers
$port = 8000
$line = Select-String -Path "jobhunterx\.env" -Pattern '^\s*PORT\s*=\s*(\d+)' | Select-Object -First 1
if ($line) { $port = [int]$line.Matches[0].Groups[1].Value }
$url = "http://127.0.0.1:$port"
if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
    Say "Something is already running on port $port - probably JobHunterX in another window. Opening $url"
    Say "If it is another program, set PORT=8001 in jobhunterx\.env and run this again."
    Start-Process $url
    exit 0
}

Say "Starting JobHunterX..."
Push-Location jobhunterx
$server = Start-Process -FilePath $py -ArgumentList "-m", "jobhunterx.api.main" -NoNewWindow -PassThru
Pop-Location
$ready = $false
for ($i = 0; $i -lt 120; $i++) {
    if ($server.HasExited) { break }
    try {
        $r = Invoke-WebRequest "$url/api/setup" -UseBasicParsing -TimeoutSec 2
        if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch { }
    Start-Sleep -Milliseconds 500
}
if (-not $ready) {
    if (-not $server.HasExited) { Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue }
    Fail "The app did not start (see the messages above). Fix the problem shown there, then run this command again."
}

Write-Host ""
Write-Host "  JobHunterX is running:  $url" -ForegroundColor Green
Write-Host "  Keep this window open. Press Ctrl + C to stop." -ForegroundColor Green
Write-Host ""
Start-Process $url
try {
    Wait-Process -Id $server.Id
} finally {
    # Ctrl + C or closing: make sure the app stops with this window
    if (-not $server.HasExited) { Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue }
    Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}
