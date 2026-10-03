#!/usr/bin/env bash
# JobHunterX - one command to set up and start (macOS / Linux, also Git Bash on Windows).
#
#   bash start.sh
#
# First time: installs uv, makes the venv, installs packages, creates .env, starts the app.
# Next times: checks everything is still fine, then starts the app.
# The browser opens only after the app is really up and answering.
# Add --no-start to only set up and check.

set -uo pipefail          # every step checks its own result
cd "$(dirname "$0")"
ROOT="$(pwd)"

say()  { printf '\033[36m==> %s\033[0m\n' "$1"; }
ok()   { printf '\033[32m    OK  %s\033[0m\n' "$1"; }
fail() { printf '\n\033[31mERROR: %s\033[0m\n' "$1"; exit 1; }
open_url() { (command -v open >/dev/null && open "$1") || (command -v xdg-open >/dev/null && xdg-open "$1") \
             || (command -v cmd.exe >/dev/null && cmd.exe /c start "" "$1") || true; }

# ---------------------------------------------------------------- 1. uv
if ! command -v uv >/dev/null 2>&1; then
  say "Installing uv (fast Python installer)..."
  curl -LsSf https://astral.sh/uv/install.sh | sh || python3 -m pip install --user uv
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi
UV_VERSION="$(uv --version 2>/dev/null)" || fail "uv is installed but this terminal can't use it yet. Open a new terminal and run: bash start.sh"
ok "$UV_VERSION"

# ---------------------------------------------------------------- 2. venv (rebuilt if broken)
venv_python() {   # bin/ on macOS/Linux, Scripts/ in Git Bash on Windows
  for p in .venv/bin/python .venv/Scripts/python.exe; do [ -x "$p" ] && { echo "$ROOT/$p"; return 0; }; done
  return 1
}
venv_ok() { local p; p="$(venv_python)" && "$p" -c "import sys; assert sys.version_info >= (3, 11)" 2>/dev/null; }
if ! venv_ok; then
  if [ -d .venv ]; then say "The virtual environment looks broken - rebuilding it..."; else say "Creating the virtual environment (.venv)..."; fi
  uv venv --clear --python 3.11 .venv && venv_ok || fail "Could not create the virtual environment. Check your internet connection and try again."
  rm -f .venv/.requirements.sha256
fi
PY="$(venv_python)"
ok "virtual environment: $("$PY" --version)"

# ---------------------------------------------------------------- 3. packages (installed, then verified)
HASH="$( (sha256sum requirements.txt 2>/dev/null || shasum -a 256 requirements.txt) | cut -d' ' -f1)"
STAMP=.venv/.requirements.sha256
install_packages() {
  say "Installing packages (about 30 seconds the first time)..."
  uv pip install --python "$PY" -r requirements.txt || fail "Package install failed. Check your internet connection and run the command again."
  echo "$HASH" > "$STAMP"
}
app_loads() { (cd jobhunterx && "$PY" -c "import jobhunterx.api.main" >/dev/null 2>&1); }
if [ ! -f "$STAMP" ] || [ "$(tr -d '[:space:]' < "$STAMP")" != "$HASH" ]; then install_packages; fi
say "Checking that everything is installed correctly..."
if ! app_loads; then
  say "Something is missing - repairing the install..."
  install_packages
  if ! app_loads; then
    (cd jobhunterx && "$PY" -c "import jobhunterx.api.main")
    fail "The app still can't load (see the message above). Delete the .venv folder and run this command again."
  fi
fi
ok "all packages load"

# ---------------------------------------------------------------- 4. settings file
if [ ! -f jobhunterx/.env ]; then
  cp jobhunterx/.env.example jobhunterx/.env
  ok "created jobhunterx/.env (the app will ask for your free AI key on the first screen)"
else
  ok "settings file jobhunterx/.env"
fi

if [ "${1:-}" = "--no-start" ]; then say "Setup done and checked. Run 'bash start.sh' to start the app."; exit 0; fi

# ---------------------------------------------------------------- 5. start, then open the browser once it answers
PORT="$(grep -E '^[[:space:]]*PORT[[:space:]]*=[[:space:]]*[0-9]+' jobhunterx/.env | head -1 | sed -E 's/[^0-9]*([0-9]+).*/\1/')"
PORT="${PORT:-8000}"
URL="http://127.0.0.1:$PORT"
if (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null; then
  say "Something is already running on port $PORT - probably JobHunterX in another terminal. Opening $URL"
  say "If it is another program, set PORT=8001 in jobhunterx/.env and run this again."
  open_url "$URL"; exit 0
fi

say "Starting JobHunterX..."
(cd jobhunterx && exec "$PY" -m jobhunterx.api.main) &
SERVER=$!
cleanup() { kill "$SERVER" 2>/dev/null; wait "$SERVER" 2>/dev/null; }
trap 'cleanup; exit 0' INT TERM

answers() { "$PY" -c "import sys, urllib.request; urllib.request.urlopen(sys.argv[1], timeout=2)" "$URL/api/setup" >/dev/null 2>&1; }
ready=0
for _ in $(seq 1 120); do
  kill -0 "$SERVER" 2>/dev/null || break
  if answers; then ready=1; break; fi
  sleep 0.5
done
if [ "$ready" != 1 ]; then
  cleanup
  fail "The app did not start (see the messages above). Fix the problem shown there, then run this command again."
fi

printf '\n\033[32m  JobHunterX is running:  %s\n  Keep this terminal open. Press Ctrl + C to stop.\033[0m\n\n' "$URL"
open_url "$URL"
wait "$SERVER"
