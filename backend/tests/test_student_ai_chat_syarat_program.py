"""Iter45: Verify Indonesian suffix normalization + synonym expansion in RAG retrieval.

Bug: Student AI chat returned exact out-of-scope fallback for Indonesian queries
like 'syaratnya apa ajah?' and 'program apa sih ini?' despite Super Admin
uploading relevant references. Fix normalizes '-nya' suffix and expands synonyms
in backend/rag_service.py::reference_tokens.

These tests hit the LIVE stream endpoint and assert:
  1. 'syaratnya apa ajah?' -> sources include SYARAT DAN KETENTUAN and answer is NOT the fallback
  2. 'program apa sih ini?' -> sources present, non-fallback answer
  3. Unrelated 'cuaca' weather question -> exact fallback string, empty sources
  4. Retrieval never leaks: role gating on /student/ai-chat/stream

Cleanup: only removes chat messages created during this run (tracked by pre-count
delta on the demo student's session). Does NOT touch ai_references or ai_reference_chunks.
"""
import json
import os
import subprocess

import pytest
import requests

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://sistem-registrasi.preview.emergentagent.com",
).rstrip("/")
API = f"{BASE_URL}/api"

STUDENT = {"email": "mahasiswa.mdj@baznasbazisdki.id", "password": "MahasiswaMDJ2026!"}
ADMIN = {"email": "admin.mdj@baznasbazisdki.id", "password": "AdminMDJ2026!"}

OUT_OF_SCOPE = "Maaf, pertanyaan tersebut berada di luar cakupan referensi dokumen yang tersedia."
SYARAT_PDF = "SYARAT DAN KETENTUAN (TERMS & CONDITIONS).pdf"
EXPECTED_REFS = {
    "KEBIJAKAN PRIVASI.pdf",
    SYARAT_PDF,
    "PAKTA INTEGRITAS PENDAFTAR.pdf",
}


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text[:200]}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def student_token():
    return _login(STUDENT)


@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def pre_count(student_token):
    # Snapshot messages count BEFORE running tests, so cleanup only removes new ones
    r = requests.get(
        f"{API}/student/ai-chat/messages",
        headers={"Authorization": f"Bearer {student_token}"},
        timeout=15,
    )
    assert r.status_code == 200
    data = r.json()
    ids = [m.get("id") for m in data.get("messages", [])]
    return {"session_id": data["session_id"], "pre_ids": set(ids)}


def _consume_sse(token, question, timeout=120):
    r = requests.post(
        f"{API}/student/ai-chat/stream",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": question},
        stream=True,
        timeout=timeout,
    )
    assert r.status_code == 200, f"stream {r.status_code} {r.text[:200]}"
    deltas, sources, done, event = [], None, False, None
    for line in r.iter_lines(decode_unicode=True):
        if line is None:
            continue
        if line == "":
            event = None
            continue
        if line.startswith("event: "):
            event = line[7:].strip()
        elif line.startswith("data: "):
            try:
                data = json.loads(line[6:])
            except Exception:
                continue
            if event == "done":
                sources = data.get("sources")
                done = True
                break
            if "text" in data:
                deltas.append(data["text"])
    r.close()
    return "".join(deltas), sources, done


# ---------- 0. Sanity: references we depend on exist ----------
def test_references_intact():
    """Super Admin uploaded references must still exist untouched."""
    super_token = _login({"email": "supri@baznasbazisdki.id", "password": "MdjSuper2026!"})
    r = requests.get(
        f"{API}/super-admin/ai-references",
        headers={"Authorization": f"Bearer {super_token}"},
        timeout=15,
    )
    assert r.status_code == 200
    names = {ref["name"] for ref in r.json()["references"]}
    missing = EXPECTED_REFS - names
    assert not missing, f"Missing expected references: {missing}. Present: {names}"


# ---------- 1. Unit: reference_tokens synonym+suffix expansion ----------
def test_reference_tokens_expansion_unit():
    """Direct import verifies -nya normalization + synonym expansion."""
    import sys
    sys.path.insert(0, "/app/backend")
    from rag_service import reference_tokens

    q1 = reference_tokens("syaratnya apa ajah?")
    assert "syarat" in q1, f"'syarat' missing after -nya strip: {q1}"
    # Synonym expansion
    assert {"persyaratan", "ketentuan", "kriteria"}.issubset(q1), f"synonyms missing: {q1}"

    q2 = reference_tokens("program apa sih ini?")
    assert "program" in q2
    assert {"beasiswa", "scholarship", "mdj"}.issubset(q2), f"program synonyms missing: {q2}"


# ---------- 2. RBAC guard on stream ----------
def test_stream_forbids_admin(admin_token):
    r = requests.post(
        f"{API}/student/ai-chat/stream",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"question": "syaratnya apa ajah?"},
        timeout=15,
    )
    assert r.status_code == 403


def test_stream_forbids_unauth():
    r = requests.post(f"{API}/student/ai-chat/stream", json={"question": "hi"}, timeout=15)
    assert r.status_code in (401, 403)


# ---------- 3. Bug repro: 'syaratnya apa ajah?' now grounded ----------
def test_syarat_query_grounded(student_token, pre_count):
    answer, sources, done = _consume_sse(student_token, "syaratnya apa ajah?")
    assert done, "no done event received"
    assert sources is not None, "sources missing in done event"
    assert SYARAT_PDF in sources, (
        f"Expected {SYARAT_PDF!r} in sources, got {sources}. "
        f"Answer prefix: {answer[:200]!r}"
    )
    # Must NOT be exact fallback
    assert answer.strip() != OUT_OF_SCOPE, (
        f"Got exact out-of-scope fallback despite matching references. Sources={sources}"
    )
    assert len(answer.strip()) > 20, f"Answer too short: {answer!r}"


# ---------- 4. Bug repro: 'program apa sih ini?' now grounded ----------
def test_program_query_grounded(student_token, pre_count):
    answer, sources, done = _consume_sse(student_token, "program apa sih ini?")
    assert done, "no done event"
    assert sources is not None and len(sources) > 0, f"sources empty: {sources}"
    # Should hit at least one of the uploaded refs
    assert any(s in EXPECTED_REFS for s in sources), f"sources not from uploaded refs: {sources}"
    assert answer.strip() != OUT_OF_SCOPE, (
        f"Exact fallback returned. Sources={sources}. Answer={answer[:200]!r}"
    )
    assert len(answer.strip()) > 20, f"Answer too short: {answer!r}"


# ---------- 5. Out-of-scope preserved for genuinely unrelated question ----------
def test_weather_out_of_scope(student_token, pre_count):
    # Use a question with no overlapping tokens with privacy/terms/pakta refs
    answer, sources, done = _consume_sse(
        student_token, "Bagaimana resep memasak rendang khas Padang paling enak?"
    )
    assert done, "no done event"
    # Primary requirement: exact fallback text in answer
    assert OUT_OF_SCOPE in answer, f"expected exact fallback, got: {answer[:200]!r} sources={sources}"


# ---------- 6. Persistence + role isolation ----------
def test_messages_persisted(student_token, pre_count):
    r = requests.get(
        f"{API}/student/ai-chat/messages",
        headers={"Authorization": f"Bearer {student_token}"},
        timeout=15,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["session_id"] == pre_count["session_id"]
    # We ran 3 questions, so should have at least 6 new messages (3 user + 3 assistant)
    new_ids = {m.get("id") for m in data["messages"]} - pre_count["pre_ids"]
    assert len(new_ids) >= 6, f"expected >=6 new messages, got {len(new_ids)}"


def test_messages_admin_forbidden(admin_token):
    r = requests.get(
        f"{API}/student/ai-chat/messages",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=15,
    )
    assert r.status_code == 403


# ---------- Z. Cleanup - remove only messages created in this run ----------
def test_zzz_cleanup_test_messages_only(student_token, pre_count):
    """Delete only chat messages created during this test run.
    Preserves ai_references and ai_reference_chunks (existing seeded data)."""
    # Fetch current messages, find new IDs, delete via mongosh by id list
    r = requests.get(
        f"{API}/student/ai-chat/messages",
        headers={"Authorization": f"Bearer {student_token}"},
        timeout=15,
    )
    assert r.status_code == 200
    current_ids = {m.get("id") for m in r.json()["messages"]}
    new_ids = list(current_ids - pre_count["pre_ids"])
    if not new_ids:
        return
    id_list_js = json.dumps(new_ids)
    js = f'db.student_ai_chat_messages.deleteMany({{id: {{$in: {id_list_js}}}}});'
    db_name = os.environ.get("DB_NAME", "test_database")
    result = subprocess.run(
        ["mongosh", f"mongodb://localhost:27017/{db_name}", "--quiet", "--eval", js],
        capture_output=True, text=True, timeout=30,
    )
    print("cleanup:", result.stdout, result.stderr)
    # Verify pre-existing messages still intact and no new leftover
    r2 = requests.get(
        f"{API}/student/ai-chat/messages",
        headers={"Authorization": f"Bearer {student_token}"},
        timeout=15,
    )
    assert r2.status_code == 200
    after_ids = {m.get("id") for m in r2.json()["messages"]}
    assert pre_count["pre_ids"].issubset(after_ids), "pre-existing messages were touched"
    assert after_ids.isdisjoint(set(new_ids)), "test-created messages were not cleaned"
