#!/usr/bin/env bash
# CreatorOS on the same VPS (run by .github/workflows/deploy-vps.yml with
# action=creatoros-inspect / creatoros-deploy). Prints NAMES of API keys and
# whether each is set — never a value.
#
#   bash creatoros-vps.sh inspect [dir]
#   bash creatoros-vps.sh deploy  [dir] [branch]
set -uo pipefail
ACTION="${1:-inspect}"; DIR="${2:-}"; BRANCH="${3:-}"
say() { printf '\n== %s\n' "$*"; }

if [ -z "$DIR" ]; then
  for d in /opt/creatoros /root/CreatorOS /root/creatoros /opt/CreatorOS; do
    [ -d "$d/.git" ] && { DIR="$d"; break; }
  done
fi
[ -n "$DIR" ] && [ -d "$DIR/.git" ] || { echo "CreatorOS checkout not found"; exit 1; }
cd "$DIR" || exit 1
PY="$DIR/.venv/bin/python"; [ -x "$PY" ] || PY="$(command -v python3)"
UNITS=$(systemctl list-units --all --type=service --no-legend 2>/dev/null | awk '{print $1}' | grep -Ei 'creat(or)?os' || true)

say "Checkout $DIR"
git -c safe.directory="$DIR" rev-parse --abbrev-ref HEAD
git -c safe.directory="$DIR" log --oneline -3
git -c safe.directory="$DIR" status --short | head -15

say "Services"
for u in $UNITS; do printf '%-34s %s\n' "$u" "$(systemctl is-active "$u")"; done

say "Machine"
echo "cpus: $(nproc)   $(free -g | awk '/Mem:/ {print "ram_gb: "$2"  free_gb: "$7}')"
"$PY" --version 2>&1

say "API keys in .env (names only)"
for f in "$DIR/.env" "$DIR/backend/.env" "$DIR/frontend/.env.local"; do
  [ -f "$f" ] || continue
  echo "$f:"
  grep -E '^[A-Za-z_][A-Za-z0-9_]*=' "$f" | while IFS='=' read -r k v; do
    case "$k" in *KEY*|*TOKEN*|*SECRET*|*PASSWORD*|*_ID) printf '  %-28s %s\n' "$k" "$([ -n "$v" ] && echo set || echo EMPTY)";;
                 *) printf '  %-28s (setting)\n' "$k";; esac
  done
done
for u in $UNITS; do
  envs=$(systemctl show "$u" -p Environment --value 2>/dev/null | tr ' ' '\n' | cut -d= -f1 | grep -v '^$' | tr '\n' ' ')
  [ -n "$envs" ] && echo "$u environment names: $envs"
done

say "Models the app will use (provider order per tier; key_configured = a key is set)"
"$PY" - <<'PYEOF' 2>&1 | head -60
import json, os, sys
sys.path.insert(0, os.getcwd())
try:
    from backend.app.core.config import settings  # loads .env
    from backend.app.core.llm import catalog
    d = catalog.describe()
    for p, info in d["providers"].items():
        print(f"  {p:7s} key_configured={info['key_configured']}")
    print(f"  keyless fallbacks enabled: {d['keyless_enabled']}")
    for tier, rows in d["tiers"].items():
        on = [r["id"] for r in rows if r["enabled"]]
        print(f"  {tier:6s}: " + " > ".join(on[:8]))
except Exception as e:
    print("could not read the model catalog:", e)
PYEOF

say "Models that actually answered (last 3 days of logs)"
for u in $UNITS; do journalctl -u "$u" --since "3 days ago" --no-pager -o cat 2>/dev/null; done \
  | grep -oE "llm '[a-z_]+': [a-z0-9]+/[^ ]+ (returned|has no|is rate|failed)|keyless [a-z0-9]+/[^ ]+ \(served by [^)]+\)|served by [a-z0-9/._:-]+" \
  | sed -E "s/^llm '[a-z_]+': //" | sort | uniq -c | sort -rn | head -25
for f in "$DIR"/tmp/logs/worker.log; do
  [ -f "$f" ] || continue
  echo "worker.log:"
  tail -n 20000 "$f" | grep -oE "keyless [a-z0-9]+/[^ ]+|llm '[a-z_]+': [a-z0-9]+/[^ ]+ returned an unusable answer|gemini/[a-z0-9.-]+|groq/[a-z0-9./-]+|nvidia/[a-z0-9./-]+" \
    | sort | uniq -c | sort -rn | head -25
done

[ "$ACTION" = "deploy" ] || { say "Inspect only — nothing changed"; exit 0; }

# ---------------------------------------------------------------- deploy
[ -n "$BRANCH" ] || { echo "deploy needs a branch"; exit 1; }
case "$BRANCH" in *[!A-Za-z0-9._/-]*) echo "Refusing odd branch name"; exit 1;; esac
say "Update to $BRANCH"
G="git -c safe.directory=$DIR"
$G stash push -u -m "before $BRANCH $(date +%F-%H%M)" >/dev/null 2>&1 && echo "local changes stashed" || true
$G fetch -q origin "$BRANCH" || { echo "fetch failed"; exit 1; }
OLD=$($G rev-parse HEAD)
$G checkout -q -B "$BRANCH" "origin/$BRANCH" || exit 1
echo "$($G rev-parse --short "$OLD") -> $($G rev-parse --short HEAD)"

say "Python packages"
if [ -x "$DIR/.venv/bin/pip" ]; then
  "$DIR/.venv/bin/pip" install -q -r requirements.txt 2>&1 | tail -3 || true
else
  echo "no venv at $DIR/.venv"
fi

say "Website"
if $G diff --quiet "$OLD" HEAD -- frontend; then echo "frontend unchanged"; else
  (cd frontend && (npm ci --no-audit --no-fund >/dev/null 2>&1 || npm install --no-audit --no-fund >/dev/null 2>&1) && npm run build 2>&1 | tail -4) || echo "frontend build failed"
fi

say "Restart"
for u in $UNITS; do
  case "$u" in *[!A-Za-z0-9@._-]*) continue;; esac
  systemctl restart "$u" && echo "restarted $u"
done
sleep 6
for u in $UNITS; do printf '%-34s %s\n' "$u" "$(systemctl is-active "$u")"; done
c=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 http://127.0.0.1:8000/auth/session || echo 000)
echo "api :8000 -> HTTP $c"
say "Deployed $($G rev-parse --short HEAD)"
