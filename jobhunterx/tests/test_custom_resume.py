"""Resume for a job the user brings (pasted JD / link), inline formatting, two columns and the strict one-page rule."""

import copy

from jobhunterx.generation import render, richtext
from jobhunterx.services.documents import _title_company_guess
from tests.test_api_v2 import _no_lifespan_db, _wait_snapshot, client  # noqa: F401  (fixtures)
from tests.test_doc_styles_chat import CONTENT
from tests.fixtures import scenario

JD = ("AI Engineer at Zeta Labs, Hyderabad. You will build retrieval-augmented generation assistants and LLM features "
      "in Python with LangChain, ship APIs with FastAPI and Docker and evaluate models. Requirements: Python, LangChain, "
      "RAG, FastAPI, Docker; 0-2 years of experience.")


# ---------------------------------------------------------------- inline formatting
def test_rich_text_formats_and_stays_safe():
    out = str(richtext.to_html("Built **RAG** in *Python*; see [demo](https://x.dev/a?b=1&c=2)"))
    assert "<b>RAG</b>" in out and "<i>Python</i>" in out and '<a href="https://x.dev/a?b=1&amp;c=2">demo</a>' in out
    hostile = str(richtext.to_html('<script>alert(1)</script> [x](javascript:alert(1)) **<img src=x onerror=1>**'))
    assert "<script" not in hostile and "<img" not in hostile and "javascript:" not in hostile.replace("javascript:alert(1)", "")
    assert 'href="javascript' not in hostile
    assert str(richtext.to_html(r"2 \* 3 = 6 and \[not a link\](https://x)")) == "2 * 3 = 6 and [not a link](https://x)"
    assert richtext.plain("**Built** a [bot](https://x.dev) in *Go*") == "Built a bot in Go"


def test_formatting_reaches_the_pdf_text():
    c = {**CONTENT, "summary": "AI engineer who built **production RAG** with [LangChain](https://langchain.com)."}
    html = render._render("resume.html", doc=c, s={"id": "classic", **render.styles.STYLES["classic"]}, **render.SHRINK_PROFILES[0])
    assert "<b>production RAG</b>" in html and '<a href="https://langchain.com">LangChain</a>' in html
    pdf, pages = render.render_resume(c)
    assert pdf.startswith(b"%PDF") and pages == 1
    import shutil, subprocess, tempfile
    if shutil.which("pdftotext"):
        with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
            f.write(pdf); f.flush()
            text = subprocess.run(["pdftotext", f.name, "-"], capture_output=True, text=True).stdout
        assert "production RAG" in text and "**" not in text and "](" not in text


# ---------------------------------------------------------------- layouts + one page, always
def _huge():
    big = copy.deepcopy(CONTENT)
    big["experience"] = [{**big["experience"][0], "bullets": [f"Built pipeline number {i} that served two million requests a day "
                                                              "using Python, FAISS and LangChain on AWS with full tests." for i in range(6)]}] * 7
    big["projects"] = [{**big["projects"][0], "title": f"Project {i}"} for i in range(10)]
    big["achievements"] = [f"Award {i} for building something useful" for i in range(8)]
    big["certifications"] = [f"Certificate {i}" for i in range(8)]
    return big


def test_resume_never_goes_past_one_page_in_any_layout():
    for layout in ("single", "two_column"):
        pdf, pages, fit = render.render_resume_fit({**_huge(), "layout": layout}, "classic")
        assert pages == 1, layout
        assert fit, layout                                    # the fitter says what it hid, for the editor
        assert set(fit) <= {"max_bullets_per_exp", "max_projects", "max_education", "max_achievements", "max_certs",
                            "max_extras", "max_skill_groups", "max_experience", "hide_summary"}


def test_two_column_layout_is_a_real_layout_and_short_resumes_hide_nothing():
    html = render._render("resume.html", doc={**CONTENT, "layout": "two_column"}, s={"id": "classic", **render.styles.STYLES["classic"]},
                          **render.SHRINK_PROFILES[0])
    assert "@frame side" in html and "<pdf:nextframe" in html
    pdf, pages, fit = render.render_resume_fit({**CONTENT, "layout": "two_column"}, "modern")
    assert pages == 1 and fit == {}


def test_unknown_layout_falls_back_to_single():
    from jobhunterx.generation.content import ResumeContent
    assert ResumeContent.model_validate({**CONTENT, "layout": "../../x"}).layout == "single"


def test_title_and_company_are_read_from_a_pasted_first_line():
    assert _title_company_guess(JD) == ("AI Engineer", "Zeta Labs")
    assert _title_company_guess("ML Intern @ Acme AI (Remote)\nAbout us") == ("ML Intern", "Acme AI")
    assert _title_company_guess("Backend Developer") == ("Backend Developer", "")


# ---------------------------------------------------------------- API
def test_custom_resume_from_pasted_description(client):  # noqa: F811
    client.put("/api/profile", json=scenario.PROFILE)
    _wait_snapshot(client)
    r = client.post("/api/documents/custom", json={"jd_text": JD, "layout": "two_column", "style": "modern"})
    assert r.status_code == 200, r.text
    doc = r.json()["document"]
    assert doc["kind"] == "resume" and doc["job_id"] is None and doc["page_count"] == 1
    assert doc["content"]["layout"] == "two_column" and doc["style"] == "modern"
    assert doc["target"]["title"] == "AI Engineer" and doc["target"]["company"] == "Zeta Labs"
    assert doc["title"] == "Resume — AI Engineer @ Zeta Labs"
    assert client.get(f"/api/documents/{doc['id']}/pdf").content.startswith(b"%PDF")

    # editing keeps formatting markers and the layout, and the PDF stays one page
    edited = {**doc["content"], "summary": "**AI engineer** building RAG in *Python*.", "layout": "single"}
    saved = client.patch(f"/api/documents/{doc['id']}", json={"content": edited}).json()["document"]
    assert saved["content"]["summary"] == edited["summary"] and saved["content"]["layout"] == "single" and saved["page_count"] == 1
    listed = {d["id"]: d for d in client.get("/api/documents").json()["documents"]}
    assert listed[doc["id"]]["target"]["company"] == "Zeta Labs"


def test_custom_resume_rejects_bad_input(client):  # noqa: F811
    client.put("/api/profile", json=scenario.PROFILE)
    assert client.post("/api/documents/custom", json={}).status_code == 422
    assert client.post("/api/documents/custom", json={"jd_text": "too short"}).status_code == 422
    r = client.post("/api/documents/custom", json={"url": "https://www.linkedin.com/jobs/view/123"})
    assert r.status_code == 422 and "LinkedIn" in r.text
    assert client.post("/api/documents/custom", json={"url": "ftp://example.com/job"}).status_code == 422
    assert client.post("/api/documents/custom", json={"jd_text": JD, "layout": "three_column"}).status_code == 422


# ---------------------------------------------------------------- skills: grouped, deduplicated, capped
def test_skills_are_grouped_even_without_a_model_and_repeats_dropped():
    from jobhunterx.generation.skills import _drop_bracketed_repeats, _fallback_groups, _is_heading
    names = ["Python Automation", "Terraform", "AWS CLI", "Slurm", "InfiniBand", "Lmod",
             "Environment Modules (Lmod, EasyBuild, Spack)", "Splunk", "Firewalls", "Operations & Reliability",
             "Cloud & Managed Services"]
    names = [n for n in names if not _is_heading(n)]
    assert "Operations & Reliability" not in names and "Cloud & Managed Services" not in names
    names = _drop_bracketed_repeats(names)
    assert "Lmod" not in names and "Environment Modules (Lmod, EasyBuild, Spack)" in names
    groups = {g.category: g.items for g in _fallback_groups(names)}
    assert len(groups) >= 3 and "Skills" not in groups
    assert "Slurm" in groups["HPC & Systems"] and "Terraform" in groups["Cloud & DevOps"]


def test_one_page_resume_lists_job_skills_first_and_caps_the_rest():
    from jobhunterx.generation.content import SkillGroup
    from jobhunterx.generation.resume import MAX_SKILLS, MAX_SKILLS_PER_GROUP, _cap_skills
    groups = [SkillGroup(category=f"G{g}", items=[f"s{g}-{i}" for i in range(20)]) for g in range(5)]
    wanted = {"s4-19", "s0-7"}
    out = _cap_skills(groups, lambda it: 0 if it in wanted else 1)
    kept = [it for g in out for it in g.items]
    assert len(kept) <= MAX_SKILLS and all(len(g.items) <= MAX_SKILLS_PER_GROUP for g in out)
    assert wanted <= set(kept)


def test_rows_keep_short_lines_on_one_line_and_dates_right_aligned():
    c = {**CONTENT, "education": [{"degree": "M.Tech", "institution": "JNTU Kakinada, India", "start": "2008", "end": "2010"},
                                  {"degree": "MCA", "institution": "Andhra University"}]}
    html = render._render("resume.html", doc=c, s={"id": "classic", **render.styles.STYLES["classic"]}, **render.SHRINK_PROFILES[0])
    assert 'width="80%"' in html and '<td class="right" width="20%">2008 – 2010</td>' in html
    assert '<td width="100%"><span class="row-title">MCA' in html          # no dates: no empty half-row
