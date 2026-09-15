"""Test registration period gate (settings.registration_open).

Verifies:
- POST /api/registration returns 403 with exact Indonesian message when closed
- GET /api/registration remains accessible while closed
- Super admin can toggle registration_open via PUT /api/site/content
- Non super_admin (student, admin) cannot update site content
- After toggling open, POST /api/registration saves a draft
- After closing again, GET still returns the persisted draft, POST returns 403

The test ALWAYS restores initial site content and deletes temporary test users
in the teardown fixture to keep production state intact.
"""
import os
import uuid
import copy
import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
CLOSED_MSG = (
    "Masa pendaftaran belum dibuka. Silakan pantau pengumuman MDJ Scholarship secara berkala."
)

SUPER = ("supri@baznasbazisdki.id", "MdjSuper2026!")
ADMIN = ("admin.mdj@baznasbazisdki.id", "AdminMDJ2026!")
STUDENT = ("mahasiswa.mdj@baznasbazisdki.id", "MahasiswaMDJ2026!")


# ---- helpers ----
def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return r.json()["token"]


def _hdr(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def super_token():
    return _login(*SUPER)


@pytest.fixture(scope="module")
def admin_token():
    return _login(*ADMIN)


@pytest.fixture(scope="module")
def student_token():
    return _login(*STUDENT)


@pytest.fixture(scope="module")
def initial_content(super_token):
    """Snapshot initial site content and restore in teardown."""
    r = requests.get(f"{BASE_URL}/api/site/content", timeout=20)
    assert r.status_code == 200
    snapshot = copy.deepcopy(r.json())
    yield snapshot
    # Restore with strict registration_open=false + full content
    restored = copy.deepcopy(snapshot)
    settings = restored.get("settings") or {}
    settings["registration_open"] = False
    restored["settings"] = settings
    resp = requests.put(
        f"{BASE_URL}/api/site/content",
        json={"content": restored},
        headers=_hdr(super_token),
        timeout=30,
    )
    assert resp.status_code == 200, f"restore failed: {resp.text}"
    # Confirm
    verify = requests.get(f"{BASE_URL}/api/site/content", timeout=20).json()
    assert verify.get("settings", {}).get("registration_open") is False


def _set_registration_open(super_token, snapshot, is_open):
    body = copy.deepcopy(snapshot)
    settings = body.get("settings") or {}
    settings["registration_open"] = is_open
    body["settings"] = settings
    r = requests.put(
        f"{BASE_URL}/api/site/content",
        json={"content": body},
        headers=_hdr(super_token),
        timeout=30,
    )
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="module")
def temp_student(super_token):
    """Create a temporary student via /auth/register and delete after."""
    email = f"test.reggate.{uuid.uuid4().hex[:8]}@example.com"
    password = "TestPass123!"
    r = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"name": "TEST Regate Student", "email": email, "password": password},
        timeout=20,
    )
    assert r.status_code in (200, 201), r.text
    body = r.json()
    token = body.get("token") or _login(email, password)
    user_id = body.get("user", {}).get("id") or body.get("user_id")
    yield {"email": email, "password": password, "token": token, "user_id": user_id}
    # Cleanup: prefer admin delete endpoint if available; otherwise raw mongo
    # Try admin registrations cleanup by hitting mongo directly via a hook endpoint - if none, use pymongo
    try:
        from motor.motor_asyncio import AsyncIOMotorClient  # noqa
        import asyncio, os as _os
        from pymongo import MongoClient
        client = MongoClient(_os.environ["MONGO_URL"])
        db = client[_os.environ["DB_NAME"]]
        db.registrations.delete_many({"email": email})
        db.profiles.delete_many({"user_id": user_id})
        db.users.delete_many({"email": email})
        client.close()
    except Exception as exc:
        print(f"cleanup temp student warning: {exc}")


# ---- tests ----

# --- site content snapshot & initial state must be closed ---
def test_initial_state_is_closed(initial_content):
    assert initial_content.get("settings", {}).get("registration_open") is False, (
        "Initial state must be closed per spec"
    )


# --- POST /api/registration is 403 with exact message when closed ---
def test_post_registration_closed_returns_403(student_token, initial_content):
    r = requests.post(
        f"{BASE_URL}/api/registration",
        json={"category": "Mahasiswa Sarjana (S1)", "action": "save"},
        headers=_hdr(student_token),
        timeout=20,
    )
    assert r.status_code == 403, r.text
    body = r.json()
    assert body.get("detail") == CLOSED_MSG


# --- GET /api/registration remains accessible while closed ---
def test_get_registration_available_while_closed(student_token):
    r = requests.get(f"{BASE_URL}/api/registration", headers=_hdr(student_token), timeout=20)
    assert r.status_code == 200


# --- Non super_admin cannot PUT /api/site/content ---
def test_admin_cannot_update_site_content(admin_token, initial_content):
    r = requests.put(
        f"{BASE_URL}/api/site/content",
        json={"content": copy.deepcopy(initial_content)},
        headers=_hdr(admin_token),
        timeout=20,
    )
    assert r.status_code == 403, r.text


def test_student_cannot_update_site_content(student_token, initial_content):
    r = requests.put(
        f"{BASE_URL}/api/site/content",
        json={"content": copy.deepcopy(initial_content)},
        headers=_hdr(student_token),
        timeout=20,
    )
    assert r.status_code == 403, r.text


# --- Super admin opens period, temp student can POST /api/registration ---
def test_open_period_temp_student_can_save_draft(super_token, initial_content, temp_student):
    _set_registration_open(super_token, initial_content, True)
    try:
        # verify content reflects
        verify = requests.get(f"{BASE_URL}/api/site/content", timeout=20).json()
        assert verify["settings"]["registration_open"] is True

        r = requests.post(
            f"{BASE_URL}/api/registration",
            json={"category": "Mahasiswa Sarjana (S1)", "action": "save"},
            headers=_hdr(temp_student["token"]),
            timeout=20,
        )
        assert r.status_code == 200, r.text
        reg = r.json()
        assert reg.get("status") == "draft"
        assert reg.get("category") == "Mahasiswa Sarjana (S1)"
        assert reg.get("user_id") == temp_student["user_id"] or reg.get("email") == temp_student["email"]

        # GET returns the draft
        g = requests.get(
            f"{BASE_URL}/api/registration",
            headers=_hdr(temp_student["token"]),
            timeout=20,
        )
        assert g.status_code == 200
        assert g.json().get("status") == "draft"
    finally:
        _set_registration_open(super_token, initial_content, False)


# --- Once closed again, draft still retrievable, POST rejected ---
def test_after_close_draft_persists_post_blocked(super_token, initial_content, temp_student):
    # ensure closed
    _set_registration_open(super_token, initial_content, False)

    g = requests.get(
        f"{BASE_URL}/api/registration",
        headers=_hdr(temp_student["token"]),
        timeout=20,
    )
    assert g.status_code == 200
    reg = g.json()
    assert reg.get("status") == "draft", "existing draft must remain after closing period"

    # POST new change is rejected
    p = requests.post(
        f"{BASE_URL}/api/registration",
        json={"category": "Mahasiswa Vokasi", "action": "save"},
        headers=_hdr(temp_student["token"]),
        timeout=20,
    )
    assert p.status_code == 403
    assert p.json().get("detail") == CLOSED_MSG

    # Draft category unchanged
    g2 = requests.get(
        f"{BASE_URL}/api/registration",
        headers=_hdr(temp_student["token"]),
        timeout=20,
    )
    assert g2.json().get("category") == "Mahasiswa Sarjana (S1)"


# --- Final integrity: initial state restored to closed ---
def test_zzz_final_state_still_closed():
    r = requests.get(f"{BASE_URL}/api/site/content", timeout=20)
    assert r.status_code == 200
    assert r.json().get("settings", {}).get("registration_open") is False
