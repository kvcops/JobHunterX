#!/usr/bin/env bash
# Update JobHunterX on a server: run it ON the server (web console, SSH, or GitHub's "Deploy to VPS" workflow).
#
#   curl -fsSL https://raw.githubusercontent.com/kvcops/JobHunterX/main/deploy/vps-update.sh | bash -s inspect
#   curl -fsSL https://raw.githubusercontent.com/kvcops/JobHunterX/main/deploy/vps-update.sh | bash -s deploy
#   ... | bash -s deploy /path/to/checkout      (when more than one checkout is found)
#
# inspect — read-only: finds the JobHunterX checkout, its branch, how it runs, listening ports
# deploy  — fast-forwards that checkout's branch (never over local edits), installs Python packages if requirements
#           changed, restarts the app the way it already runs (systemd / pm2 / docker compose / same process), checks it
set -u
ACTION="${1:-inspect}"; REPO_DIR="${2:-}"
export LC_ALL=C   # systemctl marks failed units with "*" in some locales; never let that reach a command as a pattern
say() { printf '\n== %s\n' "$*"; }

say "Server"
uname -sr; uptime -p 2>/dev/null || true

say "JobHunterX checkouts"
mapfile -t REPOS < <(for g in $(find / -xdev -maxdepth 5 -type d -name .git -not -path '*/node_modules/*' 2>/dev/null); do
  d=$(dirname "$g"); u=$(git -C "$d" remote get-url origin 2>/dev/null || true)
  case "${u,,}" in *jobhunterx*) echo "$d";; esac; done)
for d in "${REPOS[@]}"; do
  echo "$d  branch=$(git -C "$d" rev-parse --abbrev-ref HEAD)  at=$(git -C "$d" log -1 --format='%h %cs %s' | cut -c1-90)"
done
[ -n "$REPO_DIR" ] || { [ "${#REPOS[@]}" -eq 1 ] && REPO_DIR="${REPOS[0]}"; }

say "How it runs"
systemctl list-units --type=service --all --no-legend --plain 2>/dev/null | awk '{print $1, $3, $4}' | grep -Ei 'job|hunter|uvicorn|creat|app|api|web' || echo "(no matching systemd services)"
command -v pm2 >/dev/null && pm2 jlist 2>/dev/null | python3 -c "import sys,json; [print('pm2:', p['name'], p['pm2_env'].get('status'), p['pm2_env'].get('pm_cwd')) for p in json.load(sys.stdin)]" 2>/dev/null || true
command -v docker >/dev/null && docker ps --format 'docker: {{.Names}}  {{.Image}}  {{.Status}}  {{.Ports}}' 2>/dev/null || true
ps -eo pid,args --no-headers | grep -Ei 'uvicorn|jobhunterx|gunicorn' | grep -v grep | cut -c1-160 || true
say "Listening ports"
ss -ltnp 2>/dev/null | awk 'NR>1 {print $4, $6}' | sed 's/users:((//; s/,fd=[0-9]*//g' | sort -u | head -25

if [ "$ACTION" = "repair" ]; then
  say "Repair: services that are failed right now"
  FAILED=$(systemctl list-units --type=service --state=failed --no-legend --plain 2>/dev/null | awk '{print $1}' | grep -E '^[A-Za-z0-9@._-]+\.service$' || true)
  echo "${FAILED:-(none)}"
  systemctl reset-failed
  for u in $FAILED; do
    case "$u" in logrotate.service|apport-autoreport.service|*-autoreport.service) echo "skip (one-shot job): $u"; continue;; esac
    if systemctl restart "$u" 2>&1; then echo "restarted: $u -> $(systemctl is-active "$u")"; else echo "STILL FAILING: $u"; systemctl status "$u" --no-pager -n 8 2>&1 | tail -10; fi
  done
  say "After repair"
  systemctl list-units --type=service --state=failed --no-legend --plain 2>/dev/null | awk '{print "failed:", $1}' || true
  for u in ssh.service sshd.service systemd-resolved.service dbus.service caddy-duck.service creatoros-backend.service creatoros-frontend.service jobhunterx.service tailscaled.service polkit.service xrdp.service cron.service; do
    systemctl cat "$u" >/dev/null 2>&1 && echo "$u: $(systemctl is-active "$u")"
  done
  say "DNS"; getent hosts github.com >/dev/null && echo "DNS ok (github.com resolves)" || echo "DNS FAILING"
  for p in 9000 8000 3000; do echo "port $p -> HTTP $(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://127.0.0.1:$p/" || true)"; done
  exit 0
fi
if [ "$ACTION" != "deploy" ]; then say "Inspect only — nothing changed"; exit 0; fi
[ -n "$REPO_DIR" ] && [ -d "$REPO_DIR/.git" ] || { echo "Could not pick the checkout (found ${#REPOS[@]}). Run again with repo_dir set."; exit 1; }

say "Pull in $REPO_DIR"
cd "$REPO_DIR"
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "The server has local edits to tracked files — not pulling over them:"; git status --short --untracked-files=no; exit 1
fi
BRANCH=$(git rev-parse --abbrev-ref HEAD); BEFORE=$(git rev-parse HEAD)
git fetch --quiet origin "$BRANCH" && git merge --ff-only "origin/$BRANCH" || { echo "Fast-forward of $BRANCH failed"; exit 1; }
AFTER=$(git rev-parse HEAD)
echo "$BRANCH: ${BEFORE:0:7} -> ${AFTER:0:7}"; git log --oneline "$BEFORE..$AFTER" | head -20

# the Python that runs the app: from the running process, else a venv in the checkout
PID=$(pgrep -f "uvicorn.*jobhunterx|jobhunterx.api.main|python.*jobhunterx" | head -1 || true)
PY=""; [ -n "$PID" ] && PY=$(readlink -f "/proc/$PID/exe" 2>/dev/null || true)
for v in .venv venv jobhunterx/.venv jobhunterx/venv; do [ -z "$PY" ] && [ -x "$REPO_DIR/$v/bin/python" ] && PY="$REPO_DIR/$v/bin/python"; done
REQ=$(git ls-files | grep -E '(^|/)requirements\.txt$' | head -1)
if [ -n "$REQ" ] && [ -n "$PY" ] && ! git diff --quiet "$BEFORE" "$AFTER" -- "$REQ"; then
  say "requirements changed: installing with $PY"; "$PY" -m pip install -q -r "$REQ" || { echo "pip install failed"; exit 1; }
fi

say "Restart"
# exactly one plain service name (no "*" or other pattern characters: systemctl would expand them to many units)
UNIT=""
if systemctl cat jobhunterx.service >/dev/null 2>&1; then
  UNIT=jobhunterx.service
else
  for u in $(systemctl list-units --type=service --all --no-legend --plain 2>/dev/null | awk '{print $1}' | grep -E '^[A-Za-z0-9@._-]+\.service$'); do
    if systemctl cat "$u" 2>/dev/null | grep -qE "^(ExecStart|WorkingDirectory)=.*($REPO_DIR|jobhunterx)"; then UNIT="$u"; break; fi
  done
fi
case "$UNIT" in *[!A-Za-z0-9@._-]*) echo "Refusing odd unit name: $UNIT"; exit 1;; esac
if [ -n "$UNIT" ]; then
  systemctl restart "$UNIT" && echo "restarted systemd service $UNIT"; sleep 4; systemctl is-active "$UNIT"
elif command -v pm2 >/dev/null && pm2 jlist 2>/dev/null | grep -q "$REPO_DIR"; then
  NAME=$(pm2 jlist | python3 -c "import sys,json; print(next(p['name'] for p in json.load(sys.stdin) if p['pm2_env'].get('pm_cwd','').startswith('$REPO_DIR')))")
  pm2 restart "$NAME" --update-env && echo "restarted pm2 app $NAME"
elif ls "$REPO_DIR"/docker-compose.y*ml "$REPO_DIR"/compose.y*ml >/dev/null 2>&1; then
  docker compose up -d --build && echo "rebuilt docker compose services"
elif [ -n "$PID" ]; then
  # same command, same working folder, same environment (copied byte for byte before stopping it)
  CWD=$(readlink -f "/proc/$PID/cwd")
  mapfile -d '' CMD < "/proc/$PID/cmdline"; mapfile -d '' ENVS < "/proc/$PID/environ"
  kill "$PID"; for i in $(seq 1 20); do kill -0 "$PID" 2>/dev/null || break; sleep 0.5; done
  (cd "$CWD" && setsid nohup env -i "${ENVS[@]}" "${CMD[@]}" >> "$CWD/jobhunterx-server.log" 2>&1 < /dev/null &)
  echo "restarted the process in $CWD (log: $CWD/jobhunterx-server.log)"
else
  echo "Found no running JobHunterX to restart"; exit 1
fi

say "Health"
sleep 6
PORT=$(ss -ltnp 2>/dev/null | grep "pid=$(systemctl show -p MainPID --value "$UNIT" 2>/dev/null)," | awk '{print $4}' | sed 's/.*://' | head -1)
c=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "http://127.0.0.1:${PORT:-9000}/" || true)
echo "port ${PORT:-9000} -> HTTP $c"
case "$c" in 2*|3*|401) ;; *) echo "The app did not answer"; exit 1;; esac   # a login redirect is a live app
say "Deployed ${AFTER:0:7}"
