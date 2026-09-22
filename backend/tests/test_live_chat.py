"""Tests for /api/admin/live-chat/messages RBAC + create + list flow (iter 37)."""
import os
import uuid
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fallback read from frontend .env
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

CREATED_IDS = []


def login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    data = r.json()
    return data.get("token") or data.get("access_token")


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def admin_token():
    return login(*ADMIN)


@pytest.fixture(scope="module")
def super_token():
    return login(*SUPER_ADMIN)


@pytest.fixture(scope="module")
def student_token():
    return login(*STUDENT)


@pytest.fixture(scope="module", autouse=True)
def cleanup_at_end():
    yield
    client = MongoClient(MONGO_URL)
    if CREATED_IDS:
        res = client[DB_NAME].admin_live_chat_messages.delete_many({"id": {"$in": CREATED_IDS}})
        print(f"[cleanup] deleted {res.deleted_count} test messages: {CREATED_IDS}")
    client.close()


# ---------- RBAC ----------
def test_get_unauth_401():
    r = requests.get(f"{BASE_URL}/api/admin/live-chat/messages")
    assert r.status_code in (401, 403), r.text


def test_post_unauth_401():
    r = requests.post(f"{BASE_URL}/api/admin/live-chat/messages", json={"session_id": "admin-team", "message": "x"})
    assert r.status_code in (401, 403), r.text


def test_get_student_forbidden(student_token):
    r = requests.get(f"{BASE_URL}/api/admin/live-chat/messages", headers=auth_headers(student_token))
    assert r.status_code == 403, r.text


def test_post_student_forbidden(student_token):
    r = requests.post(
        f"{BASE_URL}/api/admin/live-chat/messages",
        headers=auth_headers(student_token),
        json={"session_id": "admin-team", "message": "student-should-fail"},
    )
    assert r.status_code == 403, r.text


# ---------- session validation ----------
def test_get_wrong_session_404(admin_token):
    r = requests.get(
        f"{BASE_URL}/api/admin/live-chat/messages?session_id=other-room",
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 404


def test_post_wrong_session_404(admin_token):
    r = requests.post(
        f"{BASE_URL}/api/admin/live-chat/messages",
        headers=auth_headers(admin_token),
        json={"session_id": "other-room", "message": "hi"},
    )
    assert r.status_code == 404


# ---------- empty payload ----------
def test_post_empty_message_rejected(admin_token):
    r = requests.post(
        f"{BASE_URL}/api/admin/live-chat/messages",
        headers=auth_headers(admin_token),
        json={"session_id": "admin-team", "message": ""},
    )
    assert r.status_code in (400, 422)


def test_post_whitespace_message_rejected(admin_token):
    r = requests.post(
        f"{BASE_URL}/api/admin/live-chat/messages",
        headers=auth_headers(admin_token),
        json={"session_id": "admin-team", "message": "     "},
    )
    # spaces pass Field min_length=1 but should fail server strip check with 400
    assert r.status_code in (400, 422)


# ---------- Happy path: admin creates, super_admin sees ----------
def test_admin_creates_and_super_reads(admin_token, super_token):
    tag = f"TEST_iter37_{uuid.uuid4().hex[:8]}"
    payload = {"session_id": "admin-team", "message": f"{tag} from admin"}
    r = requests.post(f"{BASE_URL}/api/admin/live-chat/messages", headers=auth_headers(admin_token), json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    msg = body["message"]
    assert msg["message"] == payload["message"]
    assert msg["session_id"] == "admin-team"
    assert msg["sender_role"] == "admin"
    assert "id" in msg and isinstance(msg["id"], str)
    assert "_id" not in msg
    CREATED_IDS.append(msg["id"])

    # Super admin GET
    r2 = requests.get(f"{BASE_URL}/api/admin/live-chat/messages", headers=auth_headers(super_token))
    assert r2.status_code == 200
    data = r2.json()
    assert data["session_id"] == "admin-team"
    ids = [m["id"] for m in data["messages"]]
    assert msg["id"] in ids, "super_admin should see the admin message"
    fetched = [m for m in data["messages"] if m["id"] == msg["id"]][0]
    assert fetched["message"] == payload["message"]
    assert "_id" not in fetched


def test_super_admin_can_post(super_token, admin_token):
    tag = f"TEST_iter37_{uuid.uuid4().hex[:8]}"
    r = requests.post(
        f"{BASE_URL}/api/admin/live-chat/messages",
        headers=auth_headers(super_token),
        json={"session_id": "admin-team", "message": f"{tag} from super"},
    )
    assert r.status_code == 200
    mid = r.json()["message"]["id"]
    CREATED_IDS.append(mid)

    # Admin should see it
    r2 = requests.get(f"{BASE_URL}/api/admin/live-chat/messages", headers=auth_headers(admin_token))
    assert r2.status_code == 200
    assert mid in [m["id"] for m in r2.json()["messages"]]
