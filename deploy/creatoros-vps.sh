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
first = None
for pname in ("token", "next_token", "cursor", "page_token"):
    allv, token = [], ""
    for page in range(40):
        q = "?type=public&limit=100" + (f"&{pname}={token}" if token else "")
        st, body, dt = call("GET", "https://api.heygen.com/v3/models/audio/voices" + q)
        if st != 200:
            print("page", page, st, str(body)[:200]); break
        got = body.get("data") or []
        if page == 1 and got and allv and got[0].get("voice_id") == allv[0].get("voice_id"):
            print(pname, ": same page again"); break
        allv += got
        token = body.get("next_token") or ""
        if not body.get("has_more") or not token:
            break
    print(f"pagination via {pname}: {len(allv)} voices")
    if len(allv) > 100:
        break
print("public voices:", len(allv), "english:", sum(1 for v in allv if v.get("language") == "en"))
off = [v for v in allv if str(v.get("voice_id", "")).startswith("public_")]
print("official (public_*) voices:", len(off))
for v in off[:200]:
    print("  OFF", v["voice_id"], "|", v.get("language"), "|", v["name"])
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
vid = next((v["voice_id"] for v in off if "Narrator" in v["name"]), off[0]["voice_id"] if off else (picks[0]["voice_id"] if picks else ""))
print("tag test voice:", vid)
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
        import soundfile as sf, numpy as np
        a, sr = sf.read(f, dtype="float32", always_2d=True); a = a.mean(axis=1)
        if sr != 16000:
            a = np.interp(np.linspace(0, len(a), int(len(a) * 16000 / sr), endpoint=False), np.arange(len(a)), a).astype("float32")
        segs, _ = wm.transcribe(a); said = " ".join(s.text for s in segs).strip(); os.remove(f)
    print(f"{text!r} -> {dur:.2f}s heard: {said!r} ({dt:.1f}s)")
PYEOF
  say "App code: HeyGen narrator end to end"
  ( cd "$DIR" && set -a && . ./.env 2>/dev/null; set +a; "$PY" - <<'PYEOF'
import time, tempfile
from pathlib import Path
from backend.app.audio import heygen_tts
from backend.app.audio.tts_kokoro import synthesize_speech
print("enabled:", heygen_tts.enabled(), "| model:", heygen_tts.model())
pool = heygen_tts.cast_pool()
print("cast pool:", {k: len(v) for k, v in pool.items()})
for k, v in pool.items():
    print(" ", k, ":", ", ".join(x.get("name", "") for x in v[:8]))
for look, ct in (("noir", "documentary"), ("pop", "viral"), ("keynote", "explainer"), ("studio", "story")):
    vid = heygen_tts.cast("proj_test1234", look, ct)
    print(f"cast {look}/{ct}: {heygen_tts.voice_name(vid)}")
vid = heygen_tts.cast("proj_test1234", "keynote", "explainer")
out = Path(tempfile.mkdtemp()) / "s.wav"
t = time.time()
d, sr, _ = synthesize_speech("Octopus blood runs blue, not red. Why did evolution pick copper?",
                             voice_id="heygen:" + vid, output_path=out, mood="curious", energy=0.6)
print(f"synthesize_speech via HeyGen: {d:.2f}s audio at {sr} Hz in {time.time()-t:.1f}s")
PYEOF
  )
  say "HeyGen probe done — nothing changed"; exit 0
fi

if [ "$ACTION" = "tone" ]; then
  # App-level tone check: the tone director's labels for sample scenes (real
  # LLM), the HeyGen line it builds, and pitch/loudness per sentence of the
  # take. Read-only; the key in .env is never printed.
  ( cd "$DIR" && set -a && . ./.env 2>/dev/null; set +a; "$PY" - <<'PYEOF'
import asyncio, numpy as np
from backend.app.audio import tone, heygen_tts as h
scenes = [
  {"scene_id": "s1", "text": "Over 2,000 people died when the dam burst at night! It was the deadliest flood in a century."},
  {"scene_id": "s2", "text": "But within a year, the town had rebuilt every single home. Volunteers came from forty countries."},
  {"scene_id": "s3", "text": "Then investigators found that officials stole the relief money. Nobody was ever punished."},
  {"scene_id": "s4", "text": "Octopuses have three hearts and blue blood! Why would evolution build an animal like that?"},
  {"scene_id": "s5", "text": "India just won the World Cup in a last-ball thriller! The whole country partied all night."},
]
print("story tone (flood topic):", tone.story_tone("The night the dam burst", scenes[:3]))
plan = asyncio.run(tone.plan("The night the dam burst", scenes[:3]))
plan.update(asyncio.run(tone.plan("Weird animals and sports", scenes[3:])))
for sc in scenes:
    sents = tone.split_sentences(sc["text"])
    for s_, t_ in zip(sents, plan[sc["scene_id"]]):
        print(f"  {t_:9s} {h.TONE_TAGS.get(t_, ''):12s} | {s_}")
def f0(a, sr):
    fr, hop, out = int(sr * .04), int(sr * .01), []
    lo, hi = int(sr / 400), int(sr / 70)
    for i in range(0, len(a) - fr, hop):
        x = a[i:i + fr]; x = x - x.mean()
        if float((x * x).sum()) < 1e-4 * fr: continue
        c = np.correlate(x, x, "full")[fr - 1:]; k = lo + int(np.argmax(c[lo:hi]))
        if c[k] > .45 * c[0]: out.append(sr / k)
    return float(np.median(out)) if out else 0
vid = h.cast_pool()["authority"][0]["voice_id"]
for sid in ("s1", "s2", "s5"):
    sc = next(x for x in scenes if x["scene_id"] == sid)
    sents = tone.split_sentences(sc["text"]); line = h.tagged_sentences(sents, plan[sid])
    a, sr = h.synthesize(line, vid, attempts=3); m = len(a) // 2
    print(f"{sid}: {line!r}\n    {len(a)/sr:.2f}s  first half f0 {f0(a[:m], sr):.0f}Hz, second half f0 {f0(a[m:], sr):.0f}Hz, "
          f"loud {20*np.log10(np.sqrt((a**2).mean())+1e-9):.1f}dB")
PYEOF
  )
  say "Tone check done — nothing changed"; exit 0
fi

if [ "$ACTION" = "sync" ]; then
  # Caption/voice sync check on the newest finished videos (read-only):
  # transcribe the final video's audio, match spoken words to the caption
  # words on screen, report the gap every 10 s; per-scene audio vs clip.
  PD=$(cd "$DIR" && "$PY" -c "from backend.app.core.config import settings; print(settings.projects_dir)" 2>/dev/null </dev/null | tail -1)
  [ -d "$PD" ] || PD="$DIR/projects"
  ( cd "$DIR" && "$PY" - "$PD" <<'PYEOF'
import sys, json, glob, os, subprocess, difflib, re
import numpy as np, soundfile as sf
pd = sys.argv[1]
def dur(path, sel="format"):
    q = ["ffprobe", "-v", "error"] + (["-select_streams", sel[0]] if sel != "format" else []) + \
        ["-show_entries", ("stream" if sel != "format" else "format") + "=duration", "-of", "csv=p=0", path]
    try: return float(subprocess.run(q, capture_output=True, text=True).stdout.strip().split("\n")[0])
    except Exception: return -1
from faster_whisper import WhisperModel
wm = WhisperModel("base.en", device="cpu", compute_type="int8")
mans = sorted(glob.glob(os.path.join(pd, "proj_*", "manifest.json")), key=os.path.getmtime, reverse=True)
done = 0
for mp in mans:
    m = json.load(open(mp)); d = os.path.dirname(mp)
    fv = m.get("final_video") or ""
    fv = fv if os.path.isabs(fv) else os.path.join(d, os.path.basename(fv))
    if not os.path.isfile(fv): continue
    done += 1
    if done > 6: break
    import time as _t
    print(f"\n== {os.path.basename(d)} | {m.get('topic')!r} | {m.get('format')} | made {_t.strftime('%m-%d %H:%M', _t.gmtime(os.path.getmtime(fv)))} UTC")
    print(f"final: video {dur(fv,'v'):.2f}s audio {dur(fv,'a'):.2f}s")
    t0 = 0.0; cap = []
    for sc in m.get("scenes") or []:
        sid = sc["scene_id"]; wav = os.path.join(d, "audio", sid + ".wav"); clip = os.path.join(d, "scenes", sid + ".mp4")
        info = sf.info(wav) if os.path.isfile(wav) else None
        cd = dur(clip, "v") if os.path.isfile(clip) else -1
        spans = os.path.join(d, "audio", sid + ".spans.json")
        ns = len(json.load(open(spans))) if os.path.isfile(spans) else 0
        caps = sc.get("captions") or []
        last = max([c["end_sec"] for c in caps] or [0])
        print(f"  {sid}: wav {info.samplerate if info else '-'}Hz {info.duration if info else -1:.2f}s | clip {cd:.2f}s | manifest {sc.get('duration_sec')} | spans {ns} | captions end {last:.2f} | words {len(sc.get('text','').split())}")
        # the captions burned into the picture: the .ass the clip was made
        # with; each event's start is when its highlighted word lights up
        ass = os.path.join(d, "scenes", sid + ".ass"); evs = 0
        if os.path.isfile(ass):
            for ln in open(ass, encoding="utf-8", errors="ignore"):
                if not ln.startswith("Dialogue:"): continue
                f = ln.split(",", 9); h, mi, se = f[1].split(":"); st = int(h) * 3600 + int(mi) * 60 + float(se)
                body = f[9]
                hit = re.search(r"\\c&H(?!FFFFFF)[0-9A-Fa-f]{6}&\}([^{\s]+)", body)
                if hit:
                    cap.append((re.sub(r"[^a-z0-9]", "", hit.group(1).lower()), t0 + st)); evs += 1
                else:
                    plain = re.sub(r"\{[^}]*\}", "", body).split()
                    if plain: cap.append((re.sub(r"[^a-z0-9]", "", plain[0].lower()), t0 + st)); evs += 1
        print(f"      .ass events {evs}")
        t0 += cd if cd > 0 else float(sc.get("duration_sec") or 0)
    a = subprocess.run(["ffmpeg", "-v", "error", "-i", fv, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True).stdout
    audio = np.frombuffer(a, dtype=np.float32)
    segs, _ = wm.transcribe(audio, word_timestamps=True, language="en", beam_size=1, condition_on_previous_text=False)
    spoken = [(re.sub(r"[^a-z0-9]", "", w.word.lower()), w.start) for s in segs for w in (s.words or [])]
    sm = difflib.SequenceMatcher(a=[x[0] for x in spoken], b=[x[0] for x in cap], autojunk=False)
    pairs = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            pairs += [(spoken[i1 + k][1], cap[j1 + k][1]) for k in range(i2 - i1)]
    print(f"  matched {len(pairs)} of {len(cap)} caption words / {len(spoken)} spoken")
    for b in range(0, int(t0) + 10, 10):
        g = [c - s for s, c in pairs if b <= s < b + 10]
        if g: print(f"   t={b:3d}-{b+10:3d}s  caption minus voice: median {np.median(g):+.2f}s  (n={len(g)}, min {min(g):+.2f}, max {max(g):+.2f})")
PYEOF
  )
  say "Sync check done — nothing changed"; exit 0
fi

if [ "$ACTION" = "frames" ]; then
  # Contact sheets of the newest finished videos, base64 in the log (read-only).
  PD=$(cd "$DIR" && "$PY" -c "from backend.app.core.config import settings; print(settings.projects_dir)" 2>/dev/null </dev/null | tail -1)
  [ -d "$PD" ] || PD="$DIR/projects"
  echo "projects: $PD ($(ls -d "$PD"/proj_* 2>/dev/null | wc -l) folders, $(find "$PD" -maxdepth 2 -name '*.mp4' 2>/dev/null | wc -l) finished videos)"
  FF=$(command -v ffmpeg || echo "$DIR/.venv/bin/ffmpeg")
  VIDS=$(find "$PD" -maxdepth 2 -name '*.mp4' 2>/dev/null)
  # the 2 newest landscape and the 2 newest portrait videos
  PICK=""; NL=0; NP=0
  for v in $([ -n "$VIDS" ] && ls -t $VIDS); do
    wh=$(ffprobe -v error -select_streams v -show_entries stream=width,height -of csv=p=0 "$v" 2>/dev/null </dev/null)
    w=${wh%,*}; h=${wh#*,}
    if [ "${w:-0}" -gt "${h:-0}" ]; then [ $NL -lt 2 ] && { PICK="$PICK $v"; NL=$((NL+1)); }
    else [ $NP -lt 2 ] && { PICK="$PICK $v"; NP=$((NP+1)); }; fi
    [ $NL -ge 2 ] && [ $NP -ge 2 ] && break
  done
  for v in $PICK; do
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
    wh=$(ffprobe -v error -select_streams v -show_entries stream=width,height -of csv=p=0 "$v" 2>/dev/null </dev/null)
    if [ "${wh%,*}" -gt "${wh#*,}" ]; then n=16; TILE="scale=480:-2,tile=4x4"; else n=18; TILE="scale=300:-2,tile=6x3"; fi
    fps=$(awk -v d="$dur" -v n=$n 'BEGIN{printf "%.4f", n/(d>1?d:1)}')
    T=$(mktemp --suffix=.jpg)
    "$FF" -nostdin -v error -y -i "$v" -vf "fps=$fps,$TILE" -frames:v 1 -q:v 5 "$T"
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
