"""Tests for /api/admin/live-chat/messages/attachment and GET /api/admin/live-chat/attachments/{id} (iter 40).

Covers:
- POST attachment (PDF + audio/webm) by admin, super_admin, admin_wilayah.
- Response never leaks storage_path.
- GET download authenticated as each management role; denied for student/unauth.
- Cleanup: remove all test-created message docs at the end (Mongo).
"""
import io
import os
import uuid
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                break

MONGO_URL = os.environ.get("MONGO_URL") or "mongodb://localhost:27017"
DB_NAME = os.environ.get("DB_NAME") or "test_database"

SUPER_ADMIN = ("supri@baznasbazisdki.id", "MdjSuper2026!")
ADMIN = ("admin.mdj@baznasbazisdki.id", "AdminMDJ2026!")
STUDENT = ("mahasiswa.mdj@baznasbazisdki.id", "MahasiswaMDJ2026!")

WILAYAH_EMAIL = f"test_iter40_wilayah_{uuid.uuid4().hex[:8]}@example.com"
WILAYAH_PASS = "WilayahIter40!"
WILAYAH_REGION = "Jakarta Pusat"

CREATED_MESSAGE_IDS = []
CREATED_ATTACHMENT_IDS = []
CREATED_WILAYAH_USER_ID = None


def login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"login failed {email}: {r.status_code} {r.text}"
    return r.json().get("token") or r.json().get("access_token")


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# Minimal valid PDF bytes
PDF_BYTES = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 100 100]>>endobj\n"
    b"xref\n0 4\n0000000000 65535 f \n"
    b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n0\n%%EOF"
)
# Fake but plausible webm audio bytes (EBML header). The endpoint validates by extension, not magic.
WEBM_BYTES = b"\x1a\x45\xdf\xa3" + os.urandom(2048)


@pytest.fixture(scope="module")
def super_token():
    return login(*SUPER_ADMIN)


@pytest.fixture(scope="module")
def admin_token():
    return login(*ADMIN)


@pytest.fixture(scope="module")
def student_token():
    return login(*STUDENT)


@pytest.fixture(scope="module")
def wilayah_token(super_token):
    """Create a temporary admin_wilayah via /api/admin/users then login."""
    global CREATED_WILAYAH_USER_ID
    payload = {
        "name": "Test Iter40 Wilayah",
        "email": WILAYAH_EMAIL,
        "password": WILAYAH_PASS,
        "role": "admin_wilayah",
        "region": WILAYAH_REGION,
    }
    r = requests.post(
        f"{BASE_URL}/api/admin/users",
        headers=auth_headers(super_token),
        json=payload,
    )
    assert r.status_code == 200, f"create wilayah admin failed: {r.status_code} {r.text}"
    body = r.json()
    CREATED_WILAYAH_USER_ID = body.get("user_id") or body.get("id")
    return login(WILAYAH_EMAIL, WILAYAH_PASS)


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    client = MongoClient(MONGO_URL)
    if CREATED_MESSAGE_IDS:
        res = client[DB_NAME].admin_live_chat_messages.delete_many({"id": {"$in": CREATED_MESSAGE_IDS}})
        print(f"[cleanup] deleted {res.deleted_count} attachment messages: {CREATED_MESSAGE_IDS}")
    if CREATED_WILAYAH_USER_ID:
        res2 = client[DB_NAME].users.delete_one({"user_id": CREATED_WILAYAH_USER_ID})
        print(f"[cleanup] deleted wilayah admin user: {res2.deleted_count}")
    else:
        # fallback by email
        client[DB_NAME].users.delete_one({"email": WILAYAH_EMAIL})
    client.close()


def _upload(token, filename, content, mime, message="TEST_iter40 attach"):
    files = {"attachment": (filename, io.BytesIO(content), mime)}
    data = {"message": message}
    return requests.post(
        f"{BASE_URL}/api/admin/live-chat/messages/attachment",
        headers=auth_headers(token),
        files=files,
        data=data,
    )


# ---------- RBAC on POST attachment ----------
def test_attachment_unauth_denied():
    r = _upload("", "x.pdf", PDF_BYTES, "application/pdf")
    assert r.status_code in (401, 403)


def test_attachment_student_forbidden(student_token):
    r = _upload(student_token, "x.pdf", PDF_BYTES, "application/pdf")
    assert r.status_code == 403


# ---------- Validation ----------
def test_attachment_unsupported_extension(admin_token):
    r = _upload(admin_token, "malicious.exe", b"MZ" + os.urandom(100), "application/octet-stream")
    assert r.status_code == 400


def test_attachment_empty_rejected(admin_token):
    r = _upload(admin_token, "empty.pdf", b"", "application/pdf")
    assert r.status_code == 400


# ---------- Happy path: each management role uploads + downloads ----------
@pytest.mark.parametrize(
    "role_name",
    ["admin", "super_admin", "admin_wilayah"],
)
def test_pdf_upload_and_download(role_name, admin_token, super_token, wilayah_token, student_token):
    token_map = {"admin": admin_token, "super_admin": super_token, "admin_wilayah": wilayah_token}
    token = token_map[role_name]
    marker = f"TEST_iter40_{role_name}_{uuid.uuid4().hex[:6]}"
    fname = f"{marker}.pdf"

    r = _upload(token, fname, PDF_BYTES, "application/pdf", message=marker)
    assert r.status_code == 200, r.text
    body = r.json()
    msg = body["message"]
    assert msg["sender_role"] == role_name
    assert msg["message"] == marker
    assert "attachment" in msg
    att = msg["attachment"]
    # storage_path must NOT leak
    assert "storage_path" not in att, f"storage_path leaked for {role_name}: {att}"
    assert att["original_filename"] == fname
    assert att["content_type"] == "application/pdf"
    assert att["size"] >= 100
    assert "id" in att
    assert "_id" not in msg

    CREATED_MESSAGE_IDS.append(msg["id"])
    CREATED_ATTACHMENT_IDS.append(att["id"])
    attachment_id = att["id"]

    # Download via same role -> 200
    d = requests.get(
        f"{BASE_URL}/api/admin/live-chat/attachments/{attachment_id}",
        headers=auth_headers(token),
    )
    assert d.status_code == 200, d.text
    assert d.headers.get("content-type", "").startswith("application/pdf")
    assert len(d.content) > 0

    # Download via ?auth=<token> (browser link pattern in UI)
    d2 = requests.get(
        f"{BASE_URL}/api/admin/live-chat/attachments/{attachment_id}?auth={token}"
    )
    assert d2.status_code == 200

    # Student cannot download
    ds = requests.get(
        f"{BASE_URL}/api/admin/live-chat/attachments/{attachment_id}",
        headers=auth_headers(student_token),
    )
    assert ds.status_code in (401, 403)

    # Unauthenticated cannot download
    du = requests.get(f"{BASE_URL}/api/admin/live-chat/attachments/{attachment_id}")
    assert du.status_code in (401, 403)


def test_webm_audio_upload_and_listing(admin_token, super_token, wilayah_token):
    fname = f"TEST_iter40_voice_{uuid.uuid4().hex[:6]}.webm"
    r = _upload(admin_token, fname, WEBM_BYTES, "audio/webm", message="TEST_iter40 voice note")
    assert r.status_code == 200, r.text
    msg = r.json()["message"]
    att = msg["attachment"]
    assert "storage_path" not in att
    assert att["content_type"] == "audio/webm"
    assert att["original_filename"] == fname
    CREATED_MESSAGE_IDS.append(msg["id"])
    aid = att["id"]

    # Super admin can list & see this attachment; ensure list also hides storage_path.
    lst = requests.get(
        f"{BASE_URL}/api/admin/live-chat/messages",
        headers=auth_headers(super_token),
    )
    assert lst.status_code == 200
    found = [m for m in lst.json()["messages"] if m.get("id") == msg["id"]]
    assert found, "super_admin should see admin's audio message"
    fmsg = found[0]
    assert "attachment" in fmsg
    assert "storage_path" not in fmsg["attachment"]
    assert fmsg["attachment"]["id"] == aid

    # Admin wilayah can also download it (management role parity)
    d = requests.get(
        f"{BASE_URL}/api/admin/live-chat/attachments/{aid}",
        headers=auth_headers(wilayah_token),
    )
    assert d.status_code == 200
    assert d.headers.get("content-type", "").startswith("audio/webm")


def test_attachment_id_not_found(admin_token):
    r = requests.get(
        f"{BASE_URL}/api/admin/live-chat/attachments/{uuid.uuid4()}",
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 404
