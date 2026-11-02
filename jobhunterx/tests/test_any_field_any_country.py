"""JobHunterX is for anyone — any field, any country. The AI instructions carry no examples from one field or one
country, and phone numbers, profile links, job boards and community sources work from the person's own data."""

import ast
import asyncio
import pathlib
import re

import jobhunterx
from jobhunterx.agents.browser_agent import home_country, profile_links, split_phone
from jobhunterx.utils import phone

PKG = pathlib.Path(jobhunterx.__file__).parent
# words that tie an instruction to software / AI work or to one country (a guard, not a filter used by the app)
FIELD_OR_COUNTRY = re.compile(r"(?i)\b(technical recruiter|software|developer|programm\w+|python|llms?|machine learning|"
                              r"data scien\w+|\bRAG\b|github|kaggle|leetcode|india\w*|naukri|hyderabad|bengaluru|\+91|"
                              r"10-digit|ctc|it-services)\b")
# the profile has LinkedIn / GitHub *fields* (schema names the reader fills and the apply agent reads); the office
# "sitcom" of the app's own agents is flavour text, not about the candidate
ALLOWED = {("agents/browser_agent.py", "github"), ("agents/extractor.py", "github"), ("services/office.py", "india")}


def _prompts():
    for f in PKG.rglob("*.py"):
        if "__pycache__" in str(f):
            continue
        src = f.read_text()
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                names = [t.id for t in node.targets if isinstance(t, ast.Name)]
                if any(re.search(r"SYS|PROMPT|RULES", n) for n in names) and len(node.value.value) > 150:
                    yield f.relative_to(PKG).as_posix(), names[0], node.value.value


def test_ai_instructions_carry_no_field_or_country_examples():
    bad = []
    for path, name, text in _prompts():
        for m in FIELD_OR_COUNTRY.finditer(text):
            word = m.group(0).lower()
            if not any(path == p and word.startswith(w) for p, w in ALLOWED):
                bad.append(f"{path}:{name}: {m.group(0)}")
    assert not bad, "\n".join(sorted(set(bad)))
    assert len(list(_prompts())) >= 12            # the guard really reads the prompts


def test_phone_numbers_work_for_every_country():
    assert split_phone("+91 80747 49058") == ("+91", "8074749058")
    assert split_phone("08074749058", "India") == ("+91", "8074749058")
    assert split_phone("+1 (415) 555-0100") == ("+1", "4155550100")
    assert split_phone("020 7946 0958", "United Kingdom") == ("+44", "2079460958")
    assert split_phone("11 91234-5678", "Brazil") == ("+55", "11912345678")
    assert phone.calling_code("Kenya") == "+254" and phone.country_for_code("+254") == "Kenya"
    assert home_country({"phone": "+971 50 123 4567"}) == "United Arab Emirates"
    assert home_country({"phone": "5551234"}) == ""                  # no country guessed
    assert home_country({"preferences": {"home_country": "Germany"}, "phone": "+91 1"}) == "Germany"


def test_profile_links_go_by_their_own_site_names():
    links = profile_links({"linkedin": "https://www.linkedin.com/in/a", "github": "https://example.com/not-github",
                           "portfolio": "https://my-work.art",
                           "links": [{"label": "Dribbble", "url": "https://dribbble.com/a"},
                                     {"label": "Research", "url": "https://www.researchgate.net/profile/A"}]})
    assert links["portfolio"] == "https://my-work.art"
    assert links["sites"] == {"linkedin": "https://www.linkedin.com/in/a", "dribbble": "https://dribbble.com/a",
                              "researchgate": "https://www.researchgate.net/profile/A"}   # a "github" link not on github: dropped


def test_job_boards_search_without_preset_job_words():
    from jobhunterx.discovery import ats
    for adapter in ats.ADAPTERS.values():
        assert getattr(adapter, "DEFAULT_QUERIES", ("",)) == ("",)


def test_reddit_communities_are_chosen_for_the_persons_field(monkeypatch):
    from jobhunterx.discovery import community
    from jobhunterx.intelligence import llm_structured
    seen = {}

    async def fake(**kw):
        seen["user"] = kw["user"]
        return kw["model"](subreddits=["r/nursing_jobs", "bad name!", "TeachersJobs"]), "fake"

    monkeypatch.setattr(llm_structured, "call_structured", fake)
    subs = asyncio.new_event_loop().run_until_complete(community.communities(["Staff Nurse", "ICU Nurse"], "Kenya"))
    assert subs == ["nursing_jobs", "TeachersJobs"]
    assert "Staff Nurse" in seen["user"] and "Kenya" in seen["user"]
    assert not hasattr(community, "REDDIT_SUBS")
