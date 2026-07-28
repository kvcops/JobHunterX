import re

c = open(r"C:\Users\vamsi\OneDrive\Desktop\Job agent\vellum-os\vellum\tools\ats_api.py", encoding="utf-8").read()

for city in ["chennai", "mumbai", "ncr", "pune", "kolkata", "bengaluru", "hyderabad", "ahmedabad"]:
    m = re.search(r'    "' + city + r'": \[\n(.*?)\n    \],', c, re.DOTALL)
    if m:
        text = m.group(1).replace("\n", ",")
        entries = [x.strip().strip('"') for x in text.split(",") if x.strip().strip('"')]
        print(f"{city}: {len(entries)} companies")
