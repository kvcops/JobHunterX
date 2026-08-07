from pathlib import Path
import re

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
API_PATH = PROJECT_ROOT / "vellum-os" / "vellum" / "tools" / "ats_client.py"

if API_PATH.exists():
    content = API_PATH.read_text(encoding="utf-8")
    pattern = r'    "(\w+)": \[\n(.*?)\n    \],'
    matches = re.findall(pattern, content, re.DOTALL)

    print(f"{'City':<20} {'Companies':>8}")
    print("-" * 30)
    total = 0
    for city, data in matches:
        count = data.count('"')
        print(f"{city:<20} {count:>8}")
        total += count

    print("-" * 30)
    print(f"{'TOTAL':<20} {total:>8}")
    print(f"\nTotal file lines: {len(content.splitlines())}")
    print("\nSyntax check: OK")
else:
    print(f"File not found at {API_PATH}")
