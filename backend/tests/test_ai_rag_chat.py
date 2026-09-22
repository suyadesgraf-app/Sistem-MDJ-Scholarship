"""Iter39: AI RAG references + Student AI chat backend tests"""
import io
import json
import os
import time
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://sistem-registrasi.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

SUPER = {"email": "supri@baznasbazisdki.id", "password": "MdjSuper2026!"}
ADMIN = {"email": "admin.mdj@baznasbazisdki.id", "password": "AdminMDJ2026!"}
STUDENT = {"email": "mahasiswa.mdj@baznasbazisdki.id", "password": "MahasiswaMDJ2026!"}

UNIQUE_MARK = f"BAJUKAWANRUBIKON{uuid.uuid4().hex[:8].upper()}"
OUT_OF_SCOPE = "Maaf, pertanyaan tersebut berada di luar cakupan referensi dokumen yang tersedia."


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"Login failed for {creds['email']}: {r.status_code} {r.text[:200]}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def super_token():
    return _login(SUPER)


@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def student_token():
    return _login(STUDENT)


@pytest.fixture(scope="module")
def second_student_token():
    # Register throwaway student
    email = f"test_iter39_{uuid.uuid4().hex[:8]}@example.com"
    password = "TestPass2026!"
    r = requests.post(f"{API}/auth/register", json={
        "name": "Iter39 Test Student",
        "email": email,
        "password": password,
    }, timeout=30)
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text[:200]}"
    token = _login({"email": email, "password": password})
    yield {"token": token, "email": email}


def _make_docx_bytes(text: str) -> bytes:
    from docx import Document
    doc = Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ---------- 1. Reference RBAC ----------
def test_list_references_forbids_admin(admin_token):
    r = requests.get(f"{API}/super-admin/ai-references", headers={"Authorization": f"Bearer {admin_token}"}, timeout=15)
    assert r.status_code == 403


def test_list_references_forbids_student(student_token):
    r = requests.get(f"{API}/super-admin/ai-references", headers={"Authorization": f"Bearer {student_token}"}, timeout=15)
    assert r.status_code == 403


def test_list_references_forbids_unauth():
    r = requests.get(f"{API}/super-admin/ai-references", timeout=15)
    assert r.status_code in (401, 403)


def test_upload_reference_forbids_admin(admin_token):
    files = {"file": ("t.docx", _make_docx_bytes("hi"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    r = requests.post(f"{API}/super-admin/ai-references", headers={"Authorization": f"Bearer {admin_token}"}, files=files, timeout=30)
    assert r.status_code == 403


# ---------- 2. Upload validation ----------
def test_upload_unsupported_extension(super_token):
    files = {"file": ("bad.exe", b"MZ\x00\x00binarydata", "application/octet-stream")}
    r = requests.post(f"{API}/super-admin/ai-references", headers={"Authorization": f"Bearer {super_token}"}, files=files, timeout=30)
    assert r.status_code == 400
    assert "belum didukung" in r.text.lower() or "format" in r.text.lower()


def test_upload_empty_file(super_token):
    files = {"file": ("empty.docx", b"", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    r = requests.post(f"{API}/super-admin/ai-references", headers={"Authorization": f"Bearer {super_token}"}, files=files, timeout=30)
    assert r.status_code == 400


# ---------- 3. Upload, list, RAG, cleanup ----------
_uploaded_id = {"id": None, "name": None}


def test_upload_valid_docx(super_token):
    filename = f"TEST_iter39_{uuid.uuid4().hex[:6]}.docx"
    content = f"Program beasiswa MDJ memiliki tanda pengenal khusus {UNIQUE_MARK} untuk pengujian sistem RAG."
    files = {"file": (filename, _make_docx_bytes(content), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    r = requests.post(f"{API}/super-admin/ai-references", headers={"Authorization": f"Bearer {super_token}"}, files=files, timeout=90)
    assert r.status_code == 200, f"upload failed: {r.status_code} {r.text[:300]}"
    body = r.json()
    ref = body["reference"]
    assert ref["name"] == filename
    assert ref["chunk_count"] >= 1
    # No storage_path leak
    assert "storage_path" not in ref
    _uploaded_id["id"] = ref["id"]
    _uploaded_id["name"] = filename


def test_list_references_hides_storage_path(super_token):
    r = requests.get(f"{API}/super-admin/ai-references", headers={"Authorization": f"Bearer {super_token}"}, timeout=15)
    assert r.status_code == 200
    refs = r.json()["references"]
    assert _uploaded_id["id"] in {ref["id"] for ref in refs}
    for ref in refs:
        assert "storage_path" not in ref


# ---------- 4. Student AI chat security ----------
def test_student_messages_unauth():
    r = requests.get(f"{API}/student/ai-chat/messages", timeout=15)
    assert r.status_code in (401, 403)


def test_student_messages_admin_forbidden(admin_token):
    r = requests.get(f"{API}/student/ai-chat/messages", headers={"Authorization": f"Bearer {admin_token}"}, timeout=15)
    assert r.status_code == 403


def test_student_stream_admin_forbidden(admin_token):
    r = requests.post(f"{API}/student/ai-chat/stream", headers={"Authorization": f"Bearer {admin_token}"}, json={"question": "hi"}, timeout=15)
    assert r.status_code == 403


def test_student_stream_unauth():
    r = requests.post(f"{API}/student/ai-chat/stream", json={"question": "hi"}, timeout=15)
    assert r.status_code in (401, 403)


# ---------- 5. RAG grounded answer ----------
def _consume_sse(token, question, timeout=90):
    r = requests.post(
        f"{API}/student/ai-chat/stream",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": question},
        stream=True,
        timeout=timeout,
    )
    assert r.status_code == 200, f"stream failed {r.status_code} {r.text[:200]}"
    deltas = []
    sources = None
    done_seen = False
    event_name = None
    for raw_line in r.iter_lines(decode_unicode=True):
        if raw_line is None:
            continue
        if raw_line == "":
            event_name = None
            continue
        if raw_line.startswith("event: "):
            event_name = raw_line[len("event: "):].strip()
        elif raw_line.startswith("data: "):
            payload = raw_line[len("data: "):]
            try:
                data = json.loads(payload)
            except Exception:
                continue
            if event_name == "done" or "sources" in data and "text" not in data:
                sources = data.get("sources")
                done_seen = True
                break
            elif "text" in data:
                deltas.append(data["text"])
    r.close()
    return "".join(deltas), sources, done_seen


def test_rag_grounded_answer(student_token):
    # Give backend a moment to persist chunks
    time.sleep(1)
    answer, sources, done = _consume_sse(student_token, f"Apa tanda pengenal khusus program beasiswa MDJ untuk pengujian sistem RAG?")
    assert done, "no done event"
    assert sources is not None, "sources missing"
    assert _uploaded_id["name"] in sources, f"expected source name in {sources}"
    # Answer should not be exact fallback since chunks matched
    assert OUT_OF_SCOPE not in answer or UNIQUE_MARK in answer.upper()


def test_rag_out_of_scope(student_token):
    answer, sources, done = _consume_sse(student_token, "Bagaimana cara memasak rendang khas Padang paling enak?")
    assert done, "no done event"
    assert sources == [] or sources is None or sources == []
    assert OUT_OF_SCOPE in answer


def test_student_messages_persisted(student_token):
    r = requests.get(f"{API}/student/ai-chat/messages", headers={"Authorization": f"Bearer {student_token}"}, timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert "messages" in data
    assert data["session_id"].startswith("student-rag-")
    # We should have at least user+assistant from RAG tests
    assert len(data["messages"]) >= 2


def test_second_student_cannot_see_first_history(second_student_token, student_token):
    # Second student's session_id derived from their own user_id -> should be empty or none of first student's
    r1 = requests.get(f"{API}/student/ai-chat/messages", headers={"Authorization": f"Bearer {student_token}"}, timeout=15)
    r2 = requests.get(f"{API}/student/ai-chat/messages", headers={"Authorization": f"Bearer {second_student_token['token']}"}, timeout=15)
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["session_id"] != r2.json()["session_id"]
    # Second student session must not include any of first student's messages
    ids1 = {m.get("id") for m in r1.json()["messages"]}
    ids2 = {m.get("id") for m in r2.json()["messages"]}
    assert ids1.isdisjoint(ids2)


# ---------- 6. Delete reference ----------
def test_delete_reference_forbids_admin(admin_token):
    r = requests.delete(f"{API}/super-admin/ai-references/{_uploaded_id['id']}", headers={"Authorization": f"Bearer {admin_token}"}, timeout=15)
    assert r.status_code == 403


def test_delete_reference(super_token):
    assert _uploaded_id["id"]
    r = requests.delete(f"{API}/super-admin/ai-references/{_uploaded_id['id']}", headers={"Authorization": f"Bearer {super_token}"}, timeout=15)
    assert r.status_code == 200
    # Second delete -> 404
    r2 = requests.delete(f"{API}/super-admin/ai-references/{_uploaded_id['id']}", headers={"Authorization": f"Bearer {super_token}"}, timeout=15)
    assert r2.status_code == 404


def test_zzz_cleanup(super_token, second_student_token):
    """Final cleanup - remove test data via direct mongo."""
    import subprocess
    email = second_student_token["email"]
    # Clean chat messages for demo student session + test student
    js = f"""
    db.ai_references.deleteMany({{name: /^TEST_iter39_/}});
    db.ai_reference_chunks.deleteMany({{reference_name: /^TEST_iter39_/}});
    var u = db.users.findOne({{email: "{email}"}});
    if (u) {{ db.student_ai_chat_messages.deleteMany({{session_id: "student-rag-" + u.user_id}}); db.users.deleteOne({{email: "{email}"}}); }}
    var s = db.users.findOne({{email: "{STUDENT['email']}"}});
    if (s) {{ db.student_ai_chat_messages.deleteMany({{session_id: "student-rag-" + s.user_id}}); }}
    """
    db_name = os.environ.get("DB_NAME", "test_database")
    result = subprocess.run(
        ["mongosh", f"mongodb://localhost:27017/{db_name}", "--quiet", "--eval", js],
        capture_output=True, text=True, timeout=30,
    )
    print("cleanup:", result.stdout, result.stderr)
    # Verify
    r = requests.get(f"{API}/super-admin/ai-references", headers={"Authorization": f"Bearer {super_token}"}, timeout=15)
    for ref in r.json()["references"]:
        assert not ref["name"].startswith("TEST_iter39_")
