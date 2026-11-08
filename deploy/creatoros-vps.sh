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

if [ "$ACTION" = "bench" ]; then
  say "Benchmark (temporary files only; skipped while a cut is running)"
  DB=$(grep -E '^DATABASE_URL=' "$DIR/.env" 2>/dev/null | cut -d= -f2- | sed 's#^sqlite+aiosqlite:///##')
  [ -n "$DB" ] && [ -f "$DB" ] || DB="$DIR/creatoros.db"
  busy=$("$PY" -c "import sqlite3,sys;print(sqlite3.connect(sys.argv[1]).execute(\"SELECT COUNT(*) FROM jobs WHERE status='running'\").fetchone()[0])" "$DB" 2>/dev/null || echo 0)
  [ "$busy" = "0" ] || { echo "a cut is running — not benchmarking now"; exit 0; }
  T=$(mktemp -d)
  "$PY" - "$T" <<'PYEOF' 2>&1 | grep -vE "^INFO|DeprecationWarning" | tail -12
import sys, time, os
sys.path.insert(0, os.getcwd())
t = sys.argv[1]
from backend.app.core.config import settings  # noqa: F401  (.env)
from render.browser.template_scene import render_template_clip
s = time.time()
render_template_clip("kt_slam", {"statement": "Three hearts keep one octopus alive", "emphasis": ["Three"]},
                     {"kicker": "Bench"}, 1080, 1920, 6.0, f"{t}/kt.mp4", look="orbit")
print(f"animated scene 6 s: {time.time() - s:.1f} s")
from PIL import Image
Image.new("RGB", (1600, 1000), (40, 80, 120)).save(f"{t}/p.jpg")
from render.ffmpeg.scene_composer import compose_shots_scene
s = time.time()
compose_shots_scene(shots=[{"path": f"{t}/p.jpg", "kind": "image", "duration": 6.0, "src_size": (1600, 1000),
                            "motion": "in", "amount": 0.08}],
                    caption_segments=[{"start_sec": 0, "end_sec": 6, "text": "one two three four five six"}],
                    duration_sec=6.0, width=1080, height=1920, output_path=f"{t}/photo.mp4")
print(f"photo scene 6 s (zoom + captions + grade): {time.time() - s:.1f} s")
from backend.app.audio.tts_kokoro import synthesize_speech
from pathlib import Path
s = time.time()
d, _, _ = synthesize_speech("An octopus has three hearts. One of them stops when it swims.", voice_id="am_michael",
                            output_path=Path(f"{t}/v.wav"))
print(f"Kokoro: {d:.1f} s of speech in {time.time() - s:.1f} s")
PYEOF
  rm -rf "$T"
  say "Bench done — nothing changed"; exit 0
fi

if [ "$ACTION" = "heygen" ]; then
  # Read-only probe of the HeyGen voice API with the key in .env (never printed).
  "$PY" - "$DIR" <<'PYEOF'
import json, os, sys, time, urllib.request, urllib.error
d = sys.argv[1]
key = ""
for f in (os.path.join(d, ".env"), os.path.join(d, "backend", ".env")):
    if os.path.isfile(f):
        for line in open(f):
            if line.startswith("HEYGEN_API_KEY="):
                key = line.split("=", 1)[1].strip()
print("HEYGEN_API_KEY:", "set" if key else "MISSING")
if not key:
    sys.exit()
H = {"X-Api-Key": key, "Content-Type": "application/json", "Accept": "application/json"}
def call(method, url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, headers=H, method=method)
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, json.loads(r.read().decode() or "{}"), time.time() - t
    except urllib.error.HTTPError as e:
        return e.code, (e.read().decode()[:600]), time.time() - t
def shape(o, depth=0):
    if isinstance(o, dict):
        return {k: shape(v, depth + 1) if depth < 2 else type(v).__name__ for k, v in list(o.items())[:25]}
    if isinstance(o, list):
        return [shape(o[0], depth + 1)] if o else []
    return type(o).__name__
import re
allv, token = [], ""
for page in range(30):
    q = "?type=public&limit=100" + (f"&next_token={token}" if token else "")
    st, body, dt = call("GET", "https://api.heygen.com/v3/models/audio/voices" + q)
    if st != 200:
        print("page", page, st, str(body)[:200]); break
    allv += body.get("data") or []
    token = body.get("next_token") or ""
    if not body.get("has_more") or not token:
        break
print("public voices:", len(allv), "english:", sum(1 for v in allv if v.get("language") == "en"))
kw = re.compile(r"narrat|documentar|story|educat|teacher|deep|warm|energ|news|author|calm|friendly|british|american|confident|clear|dramatic|epic|movie|trailer|podcast|radio|host|announcer|young|old|wise|cheer|excit|kid|child|grand|whisper|soft|bold|hype|creator|youtube|explainer|professional|smooth|rich", re.I)
picks = [v for v in allv if v.get("language") == "en" and kw.search(v.get("name", ""))]
print("descriptive english voices:", len(picks))
for v in picks[:150]:
    print("  ", v["voice_id"], "|", v["name"])
st, body, dt = call("GET", "https://api.heygen.com/v3/models/audio/voices?type=private")
print("\nprivate ->", st, str(body)[:400])
# do tags get performed or read out? transcribe the take
try:
    from faster_whisper import WhisperModel
    wm = WhisperModel("tiny.en", device="cpu", compute_type="int8")
except Exception as e:
    wm = None; print("no whisper:", e)
vid = next((v["voice_id"] for v in picks if "Deep Authority" in v["name"]), picks[0]["voice_id"] if picks else "")
for text in ("Octopuses have three hearts.", "[excited] Octopuses have three hearts.",
             "[whispers] Octopuses have three hearts.", "[dramatic] Octopuses have three hearts.",
             "Octopuses have three hearts. [laughs] Really!"):
    st, body, dt = call("POST", "https://api.heygen.com/v3/models/audio/tts",
                        {"model": "heygen-voice-1-turbo-free", "voice_id": vid, "text": text})
    if st != 200:
        print(text, "->", st, str(body)[:200]); continue
    url = body["data"]["audio_url"]; dur = body["data"].get("duration")
    said = ""
    if wm:
        import tempfile
        f = tempfile.mktemp(suffix=".wav"); urllib.request.urlretrieve(url, f)
        segs, _ = wm.transcribe(f); said = " ".join(s.text for s in segs).strip(); os.remove(f)
    print(f"{text!r} -> {dur:.2f}s heard: {said!r} ({dt:.1f}s)")
PYEOF
  say "HeyGen probe done — nothing changed"; exit 0
fi

if [ "$ACTION" = "frames" ]; then
  # Contact sheets of the newest finished videos, base64 in the log (read-only).
  PD=$(cd "$DIR" && "$PY" -c "from backend.app.core.config import settings; print(settings.projects_dir)" 2>/dev/null </dev/null | tail -1)
  [ -d "$PD" ] || PD="$DIR/projects"
  echo "projects: $PD ($(ls -d "$PD"/proj_* 2>/dev/null | wc -l) folders, $(find "$PD" -maxdepth 2 -name '*.mp4' 2>/dev/null | wc -l) finished videos)"
  FF=$(command -v ffmpeg || echo "$DIR/.venv/bin/ffmpeg")
  VIDS=$(find "$PD" -maxdepth 2 -name '*.mp4' 2>/dev/null)
  for v in $([ -n "$VIDS" ] && ls -t $VIDS | head -3); do
    d=$(dirname "$v"); dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$v" 2>/dev/null </dev/null)
    say "VIDEO $(basename "$d") $(basename "$v") ${dur}s"
    "$PY" - "$d/manifest.json" <<'PYEOF'
import json, sys, collections
try:
    m = json.load(open(sys.argv[1]))
except Exception as e:
    print("no manifest", e); sys.exit()
print("topic:", m.get("topic"), "| look:", (m.get("look") or {}).get("id") if isinstance(m.get("look"), dict) else m.get("look"))
c = collections.Counter(); t = collections.Counter()
for s in m.get("scenes") or []:
    t[str(s.get("template") or s.get("visual_type"))] += 1
    for x in s.get("shots") or s.get("media") or []:
        c[str(x.get("provider"))] += 1
print("scenes:", dict(t)); print("media providers:", dict(c))
PYEOF
    n=18; fps=$(awk -v d="$dur" -v n=$n 'BEGIN{printf "%.4f", n/(d>1?d:1)}')
    T=$(mktemp --suffix=.jpg)
    "$FF" -nostdin -v error -y -i "$v" -vf "fps=$fps,scale=300:-2,tile=6x3" -frames:v 1 -q:v 6 "$T"
    echo "SHEET-BEGIN"; base64 -w0 "$T"; echo; echo "SHEET-END"; rm -f "$T"
  done
  say "Frames done — nothing changed"; exit 0
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
  # Keep the working build: a failed build on a small server must never take the site down.
  (cd frontend && rm -rf .next.bak && { [ -d .next ] && cp -a .next .next.bak || true; }
   (npm ci --no-audit --no-fund >/dev/null 2>&1 || npm install --no-audit --no-fund >/dev/null 2>&1)
   if NODE_OPTIONS=--max-old-space-size=1536 npm run build > /tmp/creatoros-build.log 2>&1; then
     tail -4 /tmp/creatoros-build.log; rm -rf .next.bak
   else
     echo "frontend build FAILED — restoring the previous build"; tail -15 /tmp/creatoros-build.log
     [ -d .next.bak ] && { rm -rf .next; mv .next.bak .next; }
   fi)
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
