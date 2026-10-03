#!/usr/bin/env bash
# JobHunterX — one command to set up and start (macOS / Linux).
#
#   bash start.sh
#
# First time: installs uv, makes the venv, installs packages, creates .env, starts the app.
# Next times: skips what is already done and just starts the app.
# Add --no-start to only set up.

set -euo pipefail
cd "$(dirname "$0")"

say() { printf '\033[36m==> %s\033[0m\n' "$1"; }
fail() { printf '\033[31mERROR: %s\033[0m\n' "$1"; exit 1; }

# 1. uv (fast installer)
if ! command -v uv >/dev/null 2>&1; then
  say "Installing uv (fast Python installer)..."
  curl -LsSf https://astral.sh/uv/install.sh | sh || python3 -m pip install --user uv
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
  command -v uv >/dev/null 2>&1 || fail "uv was installed but this terminal can't see it yet. Open a new terminal and run: bash start.sh"
fi

# 2. Virtual environment (uv downloads Python 3.11 if it is missing)
venv_python() {   # bin/ on macOS/Linux, Scripts/ when run from Git Bash on Windows
  for p in .venv/bin/python .venv/Scripts/python.exe; do [ -x "$p" ] && { echo "$(pwd)/$p"; return 0; }; done
  return 1
}
if ! venv_python >/dev/null; then
  say "Creating the virtual environment (.venv)..."
  uv venv --python 3.11 .venv || fail "Could not create the virtual environment."
fi
PY="$(venv_python)"

# 3. Packages — reinstalled only when requirements.txt changes
HASH="$( (sha256sum requirements.txt 2>/dev/null || shasum -a 256 requirements.txt) | cut -d' ' -f1)"
STAMP=.venv/.requirements.sha256
if [ ! -f "$STAMP" ] || [ "$(cat "$STAMP")" != "$HASH" ]; then
  say "Installing packages (about 30 seconds)..."
  uv pip install --python "$PY" -r requirements.txt || fail "Package install failed. Check your internet connection and run the command again."
  echo "$HASH" > "$STAMP"
else
  say "Packages already installed."
fi

# 4. Settings file
if [ ! -f jobhunterx/.env ]; then
  cp jobhunterx/.env.example jobhunterx/.env
  say "Created jobhunterx/.env  (the app will ask for your free AI key on the first screen)"
fi

if [ "${1:-}" = "--no-start" ]; then say "Setup done. Run 'bash start.sh' to start the app."; exit 0; fi

# 5. Start the app and open the browser
PORT="$(grep -E '^\s*PORT\s*=\s*[0-9]+' jobhunterx/.env | head -1 | sed -E 's/.*=\s*([0-9]+).*/\1/' || true)"
URL="http://127.0.0.1:${PORT:-8000}"
if (exec 3<>"/dev/tcp/127.0.0.1/${PORT:-8000}") 2>/dev/null; then
  say "Something is already running on port ${PORT:-8000} - probably JobHunterX in another terminal. Opening $URL"
  say "If it is another program, set PORT=8001 in jobhunterx/.env and run this again."
  (command -v open >/dev/null && open "$URL") || (command -v xdg-open >/dev/null && xdg-open "$URL") || true
  exit 0
fi
say "Starting JobHunterX at $URL  (press Ctrl + C to stop)"
( sleep 6; (command -v open >/dev/null && open "$URL") || (command -v xdg-open >/dev/null && xdg-open "$URL") || true ) >/dev/null 2>&1 &
cd jobhunterx
exec "$PY" -m jobhunterx.api.main
