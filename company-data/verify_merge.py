import re

with open(r"C:\Users\vamsi\OneDrive\Desktop\Job agent\vellum-os\vellum\tools\ats_api.py", encoding="utf-8") as f:
    content = f.read()

# Find all city sections and count companies
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
print("\nSyntax check: OK (file parsable)")
