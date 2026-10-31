"""What the person clicks (a resume, a cover letter, auto-apply, the AI editor) runs on its own while a search is
running: no shared lock, and AI calls someone is waiting on go ahead of the search's queued calls."""

import asyncio

from jobhunterx.config import models as M


def test_clicked_work_jumps_ahead_of_queued_search_calls(monkeypatch):
    monkeypatch.setattr(M, "limits", lambda m: {"rpm": 600, "rph": None, "rpd": None, "tpm": None, "tpd": None})  # 0.1 s apart
    b = M._ModelBudget("test/model")
    order = []

    async def call(name, background):
        tok = M.BACKGROUND.set(background)
        try:
            await b.acquire(10)
            order.append(name)
        finally:
            M.BACKGROUND.reset(tok)

    async def main():
        tasks = [asyncio.create_task(call(f"search{i}", True)) for i in range(5)]
        await asyncio.sleep(0.02)                         # the search's calls are queued first
        tasks.append(asyncio.create_task(call("resume", False)))
        await asyncio.gather(*tasks)

    asyncio.new_event_loop().run_until_complete(main())
    # the next free slot: only search calls that had already started their slot (at most two here) go before it
    assert order.index("resume") <= 2, order
    assert order[-1].startswith("search") and order.index("resume") < order.index("search3"), order
    assert sorted(order) == sorted(["resume", *[f"search{i}" for i in range(5)]])


def test_background_flag_stays_inside_the_search_task():
    async def main():
        async def search_like():
            M.BACKGROUND.set(True)
            await asyncio.sleep(0)
            return M.BACKGROUND.get()

        inside = await asyncio.create_task(search_like())
        return inside, M.BACKGROUND.get()

    inside, outside = asyncio.new_event_loop().run_until_complete(main())
    assert inside is True and outside is False            # a resume request started meanwhile is not background


def test_resume_and_cover_letter_finish_while_a_search_runs(monkeypatch):
    from jobhunterx import storage
    from jobhunterx.domain.candidate import CandidateProfile
    from jobhunterx.intelligence import llm_structured
    from jobhunterx.services import documents as docs_svc
    from jobhunterx.services import profile as profile_svc
    from jobhunterx.services.search import Run, execute, new_run
    from tests.fixtures import scenario
    from tests.test_custom_resume import JD

    scenario.install(monkeypatch)
    fast = llm_structured.call_llm_with_fallback

    async def slow(chain, messages, **kw):
        # the search's calls are very slow (busy free tiers); a resume must not wait for them to finish
        await asyncio.sleep(0.6 if M.BACKGROUND.get() else 0.02)
        return await fast(chain, messages, **kw)

    monkeypatch.setattr(llm_structured, "call_llm_with_fallback", slow)

    async def noop(e):
        return None

    async def main():
        profile = CandidateProfile.model_validate(scenario.PROFILE)
        await profile_svc.save_profile(profile)
        snap = await profile_svc.get_snapshot(profile)
        run = Run(new_run(profile.content_hash()), noop)
        search = asyncio.create_task(execute(run, profile, {}))
        await asyncio.sleep(0.3)                          # the search is under way
        assert not search.done()
        doc = await docs_svc.generate_custom(profile, snap, jd_text=JD, url="", title="", company="", layout="single",
                                             style="classic", emit=noop)
        resume_done_first = not search.done()
        await search
        rows = await storage.list_rows(order="fit_score DESC")
        job_id = rows[0]["id"]
        letter = await docs_svc.generate_for_job(job_id, "cover_letter", profile, snap, noop)
        return doc, resume_done_first, run.data["status"], letter

    doc, resume_done_first, status, letter = asyncio.new_event_loop().run_until_complete(main())
    assert doc.page_count == 1 and doc.kind == "resume"
    assert resume_done_first, "the resume waited for the search to finish"
    assert status == "completed" and letter.kind == "cover_letter"
