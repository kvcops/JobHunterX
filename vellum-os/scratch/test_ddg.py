"""Quick test for the new DuckDuckGo job discovery engine."""
import asyncio
from vellum.tools.job_discovery import discover_jobs

profile = {
    "suggested_role": "Software Engineer",
    "skills": ["Python", "React", "Node.js", "JavaScript", "SQL", "AWS"],
    "location": "Hyderabad",
    "relevant_experience": "Fresher",
}

plan = {
    "target_roles": ["software engineer", "python developer", "full stack developer"],
    "seniority_max": "entry",
    "years_experience": 0,
    "locations": ["Hyderabad", "Bangalore", "Remote"],
    "must_have": ["python", "react"],
    "reject_terms": ["senior", "lead", "manager", "sales", "marketing"],
}


async def run():
    async def event_cb(event):
        msg = event.get("message", "")
        print(f"  >> {msg}")

    jobs = await discover_jobs(
        profile, plan,
        max_queries=4,
        results_per_query=8,
        max_scrape=10,
        inter_query_delay=2.0,
        event_cb=event_cb,
    )
    print(f"\nFound {len(jobs)} valid jobs:")
    for j in jobs[:15]:
        company = j.get("company", "?")[:25]
        title = j.get("title", "?")[:45]
        location = j.get("location", "?")[:20]
        url = j.get("apply_url", "?")[:60]
        print(f"  {company:25s} | {title:45s} | {location:20s}")
        print(f"    URL: {url}")


asyncio.run(run())
