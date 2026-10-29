"""Document styles (real PDF renders), the chat editor's safety checks and the new document endpoints."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from jobhunterx.domain.candidate import CandidateProfile
from jobhunterx.domain.documents import GeneratedDocument
from jobhunterx.generation import chat_edit, render, styles
from tests.fixtures import scenario

CONTENT = {
    "header": {"name": "Asha Rao", "email": "asha@example.com", "phone": "+91 9000000000", "location": "Hyderabad",
               "links": [{"label": "GitHub", "url": "https://github.com/asha", "text": "github.com/asha"}]},
    "headline": "AI Engineer", "summary": "AI engineer with 1.5 years building LLM and RAG applications in Python.",
    "skills": [{"category": "AI", "items": ["Python", "LangChain", "FAISS"]}],
    "experience": [{"role": "AI Engineer", "company": "Acme", "location": "Hyderabad", "start": "2024", "end": "Present",
                    "bullets": ["Built a RAG assistant in Python that answers support questions.",
                                "Deployed LangChain pipelines with FAISS retrieval."]}],
    "projects": [{"title": "Doc QA", "description": "Question answering over PDFs using FAISS and Python.", "technologies": ["Python"],
                  "url": "", "links": []}],
    "education": [{"degree": "B.Tech", "institution": "CVR College", "university": "JNTU", "start": "2020", "end": "2024", "grade": "", "details": ""}],
    "certifications": ["Cloud Basics"], "achievements": ["Won an internal hackathon"], "competitions": [], "languages": ["English"], "item_links": {},
}
PROFILE = CandidateProfile.model_validate(scenario.PROFILE)


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------- styles
def test_every_style_renders_every_document_kind():
    for sid in styles.STYLES:
        for kind in ("resume", "cv"):
            pdf, pages = render.render_document(kind, CONTENT, {}, sid)
            assert pdf.startswith(b"%PDF") and pages >= 1, (sid, kind)
        pdf, _ = render.render_document("cover_letter", {"greeting": "Dear team,", "paragraphs": ["Hello there."], "closing": "Regards,", "signature": "Asha"},
                                        {"name": "Asha Rao", "email": "a@b.co", "phone": "", "location": ""}, sid)
        assert pdf.startswith(b"%PDF")


def test_unknown_style_falls_back_and_cannot_pick_a_path():
    assert styles.get("../../etc/passwd")["id"] == styles.DEFAULT_STYLE
    assert styles.get(None)["id"] == styles.DEFAULT_STYLE
    assert not styles.valid("nope") and styles.valid("modern")
    pdf, _ = render.render_resume(CONTENT, "{{7*7}}")
    assert pdf.startswith(b"%PDF")


def test_styles_change_the_look_not_the_content():
    a, _ = render.render_resume(CONTENT, "classic")
    b, _ = render.render_resume(CONTENT, "bold")
    assert a != b


# ---------------------------------------------------------------- chat editor
def _fake(monkeypatch, ops, reply="Done."):
    async def fake(**kw):
        return chat_edit.ChatEdit(reply=reply, ops=[chat_edit.EditOp(**o) for o in ops]), "fake-model"
    monkeypatch.setattr(chat_edit, "call_structured", fake)


def _chat(instruction="shorten it", content=None, kind="resume"):
    return _run(chat_edit.chat_edit(kind, content or CONTENT, instruction, PROFILE))


def test_chat_applies_a_safe_rewrite(monkeypatch):
    _fake(monkeypatch, [{"op": "rewrite_bullet", "index": 0, "sub": 0, "text": "Built a Python RAG assistant that answers support questions."}])
    out = _chat()
    assert out.changes[0].accepted and out.content["experience"][0]["bullets"][0].startswith("Built a Python RAG")
    assert CONTENT["experience"][0]["bullets"][0].startswith("Built a RAG assistant")        # the input is never mutated


def test_chat_rejects_invented_facts_and_keeps_the_original(monkeypatch):
    _fake(monkeypatch, [{"op": "rewrite_bullet", "index": 0, "sub": 0, "text": "Cut support costs by 70% using Kubernetes and Terraform at scale."},
                        {"op": "set_summary", "text": "Principal engineer with 12 years of experience leading teams at Google."}])
    out = _chat()
    assert [c.accepted for c in out.changes] == [False, False]
    assert out.content == CONTENT and "70" in out.changes[0].reason or "Kubernetes" in out.changes[0].reason


def test_chat_allows_facts_the_user_typed(monkeypatch):
    _fake(monkeypatch, [{"op": "rewrite_bullet", "index": 0, "sub": 0, "text": "Built a Python RAG assistant that cut support tickets by 30%."}])
    assert not _chat("mention it cut tickets by 30%").changes[0].accepted is False


def test_chat_cannot_touch_links_or_add_urls_or_bad_indexes(monkeypatch):
    _fake(monkeypatch, [{"op": "rewrite_project", "index": 0, "text": "Question answering over PDFs, see https://evil.example/x for the demo."},
                        {"op": "rewrite_bullet", "index": 5, "sub": 0, "text": "Built a Python RAG assistant for support."},
                        {"op": "remove_item", "list_name": "header", "index": 0},
                        {"op": "reorder_skills", "index": 0, "items": ["Python", "Rust"]}])
    out = _chat()
    assert not any(c.accepted for c in out.changes)
    assert out.content["header"] == CONTENT["header"]


def test_chat_reorders_and_removes(monkeypatch):
    _fake(monkeypatch, [{"op": "reorder_skills", "index": 0, "items": ["FAISS", "Python"]},
                        {"op": "remove_item", "list_name": "achievements", "index": 0},
                        {"op": "remove_bullet", "index": 0, "sub": 1}])
    out = _chat()
    assert all(c.accepted for c in out.changes)
    assert out.content["skills"][0]["items"] == ["FAISS", "Python"] and out.content["achievements"] == []
    assert len(out.content["experience"][0]["bullets"]) == 1


def test_chat_input_hygiene(monkeypatch):
    _fake(monkeypatch, [])
    with pytest.raises(chat_edit.ChatEditError):
        _chat("  ")
    with pytest.raises(chat_edit.ChatEditError):
        _chat("make it shorter", content={"header": "not-a-header"})
    assert chat_edit.clean_text("a\x00b <script>x</script>\n\n y", 50) == "a b script x /script y"


def test_chat_cover_letter(monkeypatch):
    letter = {"greeting": "Dear team,", "paragraphs": ["I build Python and LLM applications with FAISS retrieval."], "closing": "Regards,", "signature": "Asha Rao"}
    _fake(monkeypatch, [{"op": "rewrite_paragraph", "index": 0, "text": "I build LLM applications in Python with FAISS retrieval for support teams."},
                        {"op": "remove_paragraph", "index": 0}])
    out = _chat(content=letter, kind="cover_letter")
    assert out.changes[0].accepted and not out.changes[1].accepted          # the last paragraph can't be removed


# ---------------------------------------------------------------- endpoints
@pytest.fixture
def client(monkeypatch):
    from jobhunterx.api import main
    from jobhunterx.config import database as db
    path = db._db_path
    monkeypatch.setattr(main, "set_db_path", lambda p: db.set_db_path(path))
    with TestClient(main.app, raise_server_exceptions=False) as c:
        yield c


def _seed_doc(client):
    from jobhunterx import storage
    from jobhunterx.services import profile as profile_svc
    _run(profile_svc.save_profile(PROFILE))
    doc = GeneratedDocument(id="doc1", kind="resume", title="Resume", content=CONTENT)
    pdf, pages = render.render_resume(CONTENT)
    doc.page_count = pages
    _run(storage.save_document(doc, pdf))
    return doc


def test_styles_endpoint_and_style_switch_and_styled_download(client):
    r = client.get("/api/document-styles")
    assert r.status_code == 200 and {s["id"] for s in r.json()["styles"]} == set(styles.STYLES)
    _seed_doc(client)
    assert client.patch("/api/documents/doc1/style", json={"style": "bogus"}).status_code == 422
    r = client.patch("/api/documents/doc1/style", json={"style": "modern"})
    assert r.status_code == 200 and r.json()["document"]["style"] == "modern"
    plain = client.get("/api/documents/doc1/pdf")
    bold = client.get("/api/documents/doc1/pdf", params={"style": "bold"})
    assert plain.content.startswith(b"%PDF") and bold.content.startswith(b"%PDF") and plain.content != bold.content
    assert client.get("/api/documents/doc1/pdf", params={"style": "../x"}).status_code == 422


def test_chat_endpoint_validation_size_and_rate_limit(client, monkeypatch):
    _seed_doc(client)
    _fake(monkeypatch, [{"op": "set_headline", "text": "Applied AI Engineer"}])
    assert client.post("/api/documents/doc1/chat", json={"instruction": "x"}).status_code == 422             # too short
    assert client.post("/api/documents/doc1/chat", json={"instruction": "y" * 601}).status_code == 422       # too long
    big = {**CONTENT, "summary": "z" * 400_000}
    assert client.post("/api/documents/doc1/chat", json={"instruction": "shorten", "content": big}).status_code == 422
    assert client.post("/api/documents/missing/chat", json={"instruction": "shorten it"}).status_code == 404
    r = client.post("/api/documents/doc1/chat", json={"instruction": "new headline please"})
    assert r.status_code == 200 and r.json()["content"]["headline"] == "Applied AI Engineer"
    stored = _run(__import__("jobhunterx.storage", fromlist=["x"]).get_document("doc1"))
    assert stored.content["headline"] == "AI Engineer"                       # a chat proposal is never saved by itself
    codes = [client.post("/api/documents/doc1/chat", json={"instruction": "again please"}).status_code for _ in range(12)]
    assert 429 in codes
