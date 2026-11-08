"""Write sealed environment values into CreatorOS's .env on the VPS.

Reads base64 of a JSON object {"NAME": "value"} from stdin (never from the
command line, so values never appear in a process list). Prints NAMES only.
Then restarts the CreatorOS services so they read the new values.

    printf '%s' "$ENV_B64" | python3 creatoros-setenv.py [dir]
"""
import base64
import json
import os
import re
import subprocess
import sys

d = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else ""
if not d:
    for c in ("/opt/creatoros", "/root/CreatorOS", "/root/creatoros", "/opt/CreatorOS"):
        if os.path.isdir(os.path.join(c, ".git")):
            d = c
            break
if not d:
    sys.exit("CreatorOS checkout not found")
data = json.loads(base64.b64decode(sys.stdin.read().strip() or "e30="))
env_path = os.path.join(d, ".env")
lines = open(env_path).read().splitlines() if os.path.isfile(env_path) else []
for name, value in data.items():
    if not re.fullmatch(r"[A-Z][A-Z0-9_]{2,60}", name) or "\n" in str(value):
        print(f"skipped bad name {name!r}")
        continue
    lines = [l for l in lines if not l.startswith(name + "=")]
    lines.append(f"{name}={value}")
    print(f"set {name}")
old = os.umask(0o077)
with open(env_path + ".tmp", "w") as f:
    f.write("\n".join(lines) + "\n")
os.umask(old)
os.replace(env_path + ".tmp", env_path)
os.chmod(env_path, 0o600)
units = subprocess.run("systemctl list-units --all --type=service --no-legend | awk '{print $1}' | grep -Ei 'creat(or)?os'",
                       shell=True, capture_output=True, text=True).stdout.split()
for u in units:
    subprocess.run(["systemctl", "restart", u])
    print("restarted", u)
