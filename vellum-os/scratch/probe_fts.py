"""Quick probe: does FTS cleanup work on delete?"""
import asyncio
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, ".")
from vellum.config import database as db


async def main():
    tmp = Path(tempfile.mkdtemp()) / "test.db"
    db.set_db_path(str(tmp))
    await db.init_db()

    jid = await db.insert_job({
        "company": "Acme", "role": "Engineer",
        "apply_url": "https://acme.com/job/1",
        "jd_text": "hello world python",
    })

    conn = await db.get_connection()
    cur = await conn.execute("SELECT count(*) c FROM jobs_fts")
    print("fts rows after insert:", (await cur.fetchone())["c"])

    await db.delete_job(jid)

    cur = await conn.execute("SELECT count(*) c FROM jobs_fts")
    print("fts rows after delete_job:", (await cur.fetchone())["c"])

    cur = await conn.execute("SELECT name FROM sqlite_master WHERE name LIKE 'jobs_fts%'")
    print("fts tables:", [r["name"] for r in await cur.fetchall()])

    # Now clear_jobs (all)
    jid2 = await db.insert_job({
        "company": "Beta", "role": "Engineer",
        "apply_url": "https://beta.com/job/2",
        "jd_text": "another job post",
    })
    await db.clear_jobs()
    cur = await conn.execute("SELECT count(*) c FROM jobs_fts")
    print("fts rows after clear_jobs:", (await cur.fetchone())["c"])
    await conn.close()


asyncio.run(main())
