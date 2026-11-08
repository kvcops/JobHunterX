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

if [ "$ACTION" = "diagnose" ]; then
  say "Jobs (last 14 days)"
  DB=$(grep -E '^DATABASE_URL=' "$DIR/.env" 2>/dev/null | cut -d= -f2- | sed 's#^sqlite+aiosqlite:///##')
  [ -n "$DB" ] && [ -f "$DB" ] || DB="$DIR/creatoros.db"
  "$PY" - "$DB" <<'PYEOF'
import sqlite3, sys, re
con = sqlite3.connect(sys.argv[1])
rows = con.execute("SELECT job_type, status, COUNT(*) FROM jobs WHERE created_at > datetime('now','-14 days') GROUP BY 1,2 ORDER BY 1,2").fetchall()
for r in rows: print("  %-14s %-10s %d" % r)
print("\n  latest 25 jobs: created | updated | minutes | status | progress | error")
for r in con.execute("SELECT job_id, job_type, status, progress, created_at, updated_at, COALESCE(error,'') FROM jobs ORDER BY created_at DESC LIMIT 25"):
    jid, typ, st, pr, c, u, err = r
    mins = con.execute("SELECT (julianday(?)-julianday(?))*1440", (u, c)).fetchone()[0] or 0
    err = re.sub(r"(key|token|secret|password)=\S+", r"\1=***", err, flags=re.I)[:160]
    print(f"  {c[5:16]} | {u[11:16]} | {mins:6.1f} | {typ[:11]:11s} {st:9s} {pr or 0:4.2f} | {err}")
PYEOF
  say "Memory / OOM kills (14 days)"
  free -m | head -3; swapon --show 2>/dev/null | head -3
  journalctl -k --since "14 days ago" --no-pager -o short 2>/dev/null | grep -iE "out of memory|oom-kill|killed process" | tail -15
  say "Worker log: errors and stops (last 4000 lines)"
  L="$DIR/tmp/logs/worker.log"
  [ -f "$L" ] && tail -n 4000 "$L" | grep -E "ERROR|Traceback|Timeout|timed out|failed|Killed|MemoryError|cancel|paused|stopped responding|interrupted|resum" \
    | grep -vE "unusable answer|has no API key|rate-limited|switching to|primp|ddgs|research.search|research.entities|creatoros.research|INFO" | sed -E 's/(key|token)=[^ ]+/\1=***/Ig' | tail -60
  say "Stage timings of recent cuts (minutes from start of each project's run)"
  [ -f "$L" ] && tail -n 30000 "$L" | grep -E "proj_[0-9a-f]+ \| [a-z_.]+" | "$PY" -c '
import sys, re, datetime as dt
runs = {}
for line in sys.stdin:
    m = re.match(r"(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d),\d+ .*?(proj_[0-9a-f]+) \| ([a-z_.]+)", line)
    if not m: continue
    t = dt.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S"); runs.setdefault(m.group(2), []).append((t, m.group(3)))
for pid, ev in list(runs.items())[-4:]:
    t0 = ev[0][0]; seen = {}
    for t, st in ev: seen.setdefault(st, (t - t0).total_seconds() / 60)
    last = (ev[-1][0] - t0).total_seconds() / 60
    keys = [k for k in seen if k.split(".")[-1] in ("planned","researched","generated","synthesized","aligned","directing","acquired","rendering","encoding","mixed","completed","failed")]
    print(f"  {pid}: total {last:.1f} min | " + " ".join(f"{k}@{seen[k]:.1f}" for k in keys))
'
  say "Render speed (frames per second of browser captures)"
  [ -f "$L" ] && tail -n 30000 "$L" | grep -oE "frames piped in [0-9.]+s \([0-9.]+ fps\)" | tail -12
  say "Diagnose only — nothing changed"; exit 0
fi

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
