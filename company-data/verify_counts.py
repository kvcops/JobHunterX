from pathlib import Path
import re

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
API_PATH = PROJECT_ROOT / "vellum-os" / "vellum" / "tools" / "ats_client.py"

if API_PATH.exists():
    content = API_PATH.read_text(encoding="utf-8")
    for city in ["chennai", "mumbai", "ncr", "pune", "kolkata", "bengaluru", "hyderabad", "ahmedabad"]:
        m = re.search(r'    "' + city + r'": \[\n(.*?)\n    \],', content, re.DOTALL)
        if m:
            text = m.group(1).replace("\n", ",")
            entries = [x.strip().strip('"') for x in text.split(",") if x.strip().strip('"')]
            print(f"{city}: {len(entries)} companies")
else:
    print(f"ATS client file not found at {API_PATH}")
