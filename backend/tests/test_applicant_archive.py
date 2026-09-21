"""
Iter36 — Arsip Pendaftar (Applicant Archive) safety-oriented tests.

Safety: We DO NOT call POST /api/super-admin/applicant-archive against real data.
Archived-user state is simulated by direct pymongo insert of an isolated fixture
student. Restore endpoint IS exercised, but only against the fixture batch.
"""
import os
import uuid
import time
import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else None
if not BASE_URL:
    # fallback: read from frontend/.env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL"):
                BASE_URL = line.split("=", 1)[1].strip().strip('"').rstrip("/")
                break

API = f"{BASE_URL}/api"

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

SUPER = {"email": "supri@baznasbazisdki.id", "password": "MdjSuper2026!"}
ADMIN_PROV = {"email": "admin.mdj@baznasbazisdki.id", "password": "AdminMDJ2026!"}
STUDENT_DEMO = {"email": "mahasiswa.mdj@baznasbazisdki.id", "password": "MahasiswaMDJ2026!"}


@pytest.fixture(scope="module")
def db():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=30)
    return r


@pytest.fixture(scope="module")
def super_token():
    r = _login(SUPER)
    assert r.status_code == 200, f"super login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_prov_token():
    r = _login(ADMIN_PROV)
    if r.status_code != 200:
        pytest.skip(f"admin_prov login failed: {r.status_code}")
    return r.json()["token"]


@pytest.fixture(scope="module")
def student_demo_token():
    r = _login(STUDENT_DEMO)
    if r.status_code != 200:
        pytest.skip("student demo login failed")
    return r.json()["token"]


# ---------------------------------------------------------------------------
# 1) RBAC: only super_admin can access archive endpoints
# ---------------------------------------------------------------------------

def _auth(h):
    return {"Authorization": f"Bearer {h}"}


def test_summary_forbidden_admin_prov(admin_prov_token):
    r = requests.get(f"{API}/super-admin/applicant-archive/summary", headers=_auth(admin_prov_token), timeout=30)
    assert r.status_code == 403, f"expected 403 for admin got {r.status_code}"


def test_summary_forbidden_student(student_demo_token):
    r = requests.get(f"{API}/super-admin/applicant-archive/summary", headers=_auth(student_demo_token), timeout=30)
    assert r.status_code == 403


def test_summary_unauth():
    r = requests.get(f"{API}/super-admin/applicant-archive/summary", timeout=30)
    assert r.status_code == 401


def test_archive_all_forbidden_admin_prov(admin_prov_token):
    # Read-only auth check; admin must be blocked BEFORE any mutation.
    r = requests.post(f"{API}/super-admin/applicant-archive", headers=_auth(admin_prov_token), timeout=30)
    assert r.status_code == 403, f"admin must be blocked from archive-all, got {r.status_code}"


def test_archive_all_forbidden_student(student_demo_token):
    r = requests.post(f"{API}/super-admin/applicant-archive", headers=_auth(student_demo_token), timeout=30)
    assert r.status_code == 403


def test_restore_forbidden_admin_prov(admin_prov_token):
    r = requests.post(f"{API}/super-admin/applicant-archive/nonexistent-batch/restore",
                     headers=_auth(admin_prov_token), timeout=30)
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# 2) Summary returns clean structure (no Mongo _id) for super admin
# ---------------------------------------------------------------------------

def test_summary_success_super(super_token):
    r = requests.get(f"{API}/super-admin/applicant-archive/summary", headers=_auth(super_token), timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "active_applicant_count" in data
    assert "archived_applicant_count" in data
    assert "restorable_batch" in data
    assert isinstance(data["active_applicant_count"], int)
    assert isinstance(data["archived_applicant_count"], int)
    # If restorable_batch present, must not contain _id
    if data["restorable_batch"]:
        assert "_id" not in data["restorable_batch"]


# ---------------------------------------------------------------------------
# 3) Fixture archived student cannot login / /auth/me blocked;
#    restore reactivates and login works again.
# ---------------------------------------------------------------------------

@pytest.fixture
def archived_fixture(db):
    """Insert an isolated archived batch containing 1 student with all sub-records."""
    from passlib.hash import bcrypt
    batch_id = f"test-iter36-{uuid.uuid4().hex[:8]}"
    user_id = f"user_test_arch_{uuid.uuid4().hex[:8]}"
    email = f"test_arch_{uuid.uuid4().hex[:8]}@example.invalid"
    plain = "ArchTest2026!"
    pwd_hash = bcrypt.hash(plain)
    now = "2026-01-01T00:00:00+00:00"

    archived_fields = {
        "is_archived": True,
        "archive_batch_id": batch_id,
        "archived_at": now,
        "archived_by": "test_super",
    }

    db.users.insert_one({
        "user_id": user_id,
        "email": email,
        "password_hash": pwd_hash,
        "name": "TEST_ARCH Iter36",
        "role": "student",
        "auth_version": 1,
        "is_active": True,
        "created_at": now,
        **archived_fields,
    })
    db.registrations.insert_one({
        "user_id": user_id, "status": "draft", "created_at": now, **archived_fields,
    })
    db.profiles.insert_one({
        "user_id": user_id, "data": {"institusi": "TEST_ARCH"}, **archived_fields,
    })
    db.documents.insert_one({
        "user_id": user_id, "is_deleted": False, **archived_fields,
    })
    db.notifications.insert_one({
        "user_id": user_id, "title": "TEST_ARCH", "message": "x", **archived_fields,
    })
    batch_doc = {
        "id": batch_id,
        "status": "archived",
        "applicant_count": 1,
        "registration_count": 1,
        "profile_count": 1,
        "document_count": 1,
        "notification_count": 1,
        "archived_at": now,
        "archived_by": "test_super",
        "archived_by_name": "TEST Super",
    }
    db.applicant_archive_batches.insert_one(dict(batch_doc))

    yield {"batch_id": batch_id, "user_id": user_id, "email": email, "password": plain}

    # cleanup — remove any residue regardless of test path
    db.users.delete_many({"user_id": user_id})
    for coll in [db.registrations, db.profiles, db.documents, db.notifications]:
        coll.delete_many({"user_id": user_id})
    db.applicant_archive_batches.delete_many({"id": batch_id})


def test_archived_user_cannot_login(archived_fixture):
    r = _login({"email": archived_fixture["email"], "password": archived_fixture["password"]})
    assert r.status_code == 403, f"archived user must not login, got {r.status_code} {r.text}"
    assert "arsipkan" in r.text.lower() or "diarsipkan" in r.text.lower()


def test_archived_user_auth_me_blocked(archived_fixture, db):
    # simulate a stale token by directly minting one? Instead: since login is blocked,
    # verify get_current_user path rejects an archived user even if token were valid.
    # We insert a session cookie-like row and hit /auth/me with a Bearer token that
    # resolves through resolve_user_from_token — we don't have JWT signing key here,
    # so use user_sessions path via session_token.
    session_token = f"tok_{uuid.uuid4().hex}"
    db.user_sessions.insert_one({
        "user_id": archived_fixture["user_id"],
        "session_token": session_token,
        "expires_at": "2099-01-01T00:00:00+00:00",
        "created_at": "2026-01-01T00:00:00+00:00",
    })
    try:
        r = requests.get(f"{API}/auth/me",
                         headers={"Authorization": f"Bearer {session_token}"},
                         timeout=30)
        assert r.status_code in (401, 403), f"/auth/me must block archived user, got {r.status_code}"
    finally:
        db.user_sessions.delete_many({"session_token": session_token})


def test_restore_batch_super_admin(super_token, archived_fixture, db):
    batch_id = archived_fixture["batch_id"]
    r = requests.post(f"{API}/super-admin/applicant-archive/{batch_id}/restore",
                     headers=_auth(super_token), timeout=30)
    assert r.status_code == 200, f"restore failed: {r.status_code} {r.text}"
    body = r.json()
    assert body.get("batch_id") == batch_id

    # verify DB state
    u = db.users.find_one({"user_id": archived_fixture["user_id"]})
    assert u is not None
    assert u.get("is_archived") is False
    assert "archive_batch_id" not in u
    for coll_name in ["registrations", "profiles", "documents", "notifications"]:
        doc = db[coll_name].find_one({"user_id": archived_fixture["user_id"]})
        assert doc is not None, f"{coll_name} record missing after restore"
        assert doc.get("is_archived") is False
        assert "archive_batch_id" not in doc

    batch = db.applicant_archive_batches.find_one({"id": batch_id})
    assert batch["status"] == "restored"

    # Now login should succeed
    r2 = _login({"email": archived_fixture["email"], "password": archived_fixture["password"]})
    assert r2.status_code == 200, f"login after restore failed: {r2.status_code} {r2.text}"


def test_restore_invalid_batch(super_token):
    r = requests.post(f"{API}/super-admin/applicant-archive/does-not-exist/restore",
                     headers=_auth(super_token), timeout=30)
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# 4) Admin participants listing excludes archived students
# ---------------------------------------------------------------------------

def test_admin_participants_excludes_archived(super_token, archived_fixture):
    r = requests.get(f"{API}/admin/participants", headers=_auth(super_token), timeout=30)
    assert r.status_code == 200
    items = r.json()
    for it in items:
        assert it.get("user_id") != archived_fixture["user_id"], \
            "admin/participants must exclude archived students"


# ---------------------------------------------------------------------------
# 5) Static verification: batch-scoped mutation only touches archive_batch_id docs
#    We assert by comparing DB counts before/after fixture insert — done implicitly
#    by fixture cleanup. Here we assert that summary counts reflect the archived
#    fixture batch while active.
# ---------------------------------------------------------------------------

def test_summary_reflects_archived_fixture(super_token, archived_fixture):
    r = requests.get(f"{API}/super-admin/applicant-archive/summary",
                    headers=_auth(super_token), timeout=30)
    assert r.status_code == 200
    data = r.json()
    # archived_applicant_count includes our fixture (>=1)
    assert data["archived_applicant_count"] >= 1
    rb = data["restorable_batch"]
    # There might be another batch too, but restorable_batch is the latest;
    # simply assert schema.
    if rb:
        for k in ("id", "status", "applicant_count"):
            assert k in rb
        assert "_id" not in rb
