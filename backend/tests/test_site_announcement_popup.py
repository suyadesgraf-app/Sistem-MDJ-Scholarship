"""Tests for site-announcement popup flow (iter35).

Covers:
- PUT /api/site/content requires super_admin (non-super forbidden)
- Adding a new announcement creates notifications for each registered user
  with type=announcement, is_popup_seen=false, and no duplicates on re-save.
- GET /api/student/site-announcements/pending returns pending announcement
  for the owning student only, without Mongo _id.
- POST /api/student/site-announcements/{id}/seen sets is_read/is_popup_seen
  and subsequent GET returns null.
- Data safety: original site content is restored in fixture teardown and
  test-only notifications are purged.
"""
import os
import uuid
import requests
import pytest

# Direct DB access (sync) to seed minimal registration for test users
# so notify_new_announcements includes them without opening registration.
from pymongo import MongoClient

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")
_sync_client = MongoClient(MONGO_URL)
_db = _sync_client[DB_NAME]


def _run(op):
    # Compat shim so we can keep the same call sites; pymongo is synchronous.
    return op

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://sistem-registrasi.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

SUPER_EMAIL = os.environ.get("ADMIN_EMAIL", "supri@baznasbazisdki.id")
SUPER_PASS = os.environ.get("ADMIN_PASSWORD", "MdjSuper2026!")

TEST_TITLE = f"TEST_ONLY_ANNOUNCEMENT_{uuid.uuid4().hex[:8]}"
TEST_SUMMARY = "TEST_ONLY summary do not act on this"
TEST_DATE = "2099-01-01"
TEST_CATEGORY = "Umum"


def _login(email: str, password: str) -> str:
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return r.json()["token"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def super_token():
    return _login(SUPER_EMAIL, SUPER_PASS)


@pytest.fixture(scope="module")
def original_site_content(super_token):
    r = requests.get(f"{API}/site/content", timeout=30)
    assert r.status_code == 200
    content = r.json()
    # Strip server-managed fields not accepted by SiteContentInput
    content.pop("updated_at", None)
    yield content
    # Teardown: restore original content (refresh token in case module-scoped one expired)
    fresh = _login(SUPER_EMAIL, SUPER_PASS)
    restore_payload = {"content": content}
    r = requests.put(f"{API}/site/content", json=restore_payload, headers=_headers(fresh), timeout=30)
    assert r.status_code == 200, f"failed to restore site content: {r.text}"
    # Purge any TEST_ONLY announcement notifications
    _db.notifications.delete_many({"type": "announcement", "title": {"$regex": "^TEST_ONLY"}})


@pytest.fixture(scope="module")
def test_student():
    """Create an ephemeral student and yield their credentials/token."""
    email = f"test_popup_{uuid.uuid4().hex[:8]}@example.com"
    password = "TestPopup2026!"
    payload = {
        "name": "TEST_ONLY Popup Student",
        "email": email,
        "password": password,
    }
    r = requests.post(f"{API}/auth/register", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
    token = r.json().get("token") or _login(email, password)
    user_id = r.json().get("user", {}).get("user_id") or r.json().get("user_id")
    assert user_id, f"could not resolve user_id from register response: {r.json()}"
    # Seed a minimal registration so notify_new_announcements includes this user.
    reg_id = str(uuid.uuid4())
    _run(_db.registrations.insert_one({
        "id": reg_id,
        "user_id": user_id,
        "name": "TEST_ONLY Popup Student",
        "email": email,
        "category": "Umum",
        "status": "draft",
        "test_tag": "TEST_ONLY_iter35_popup",
    }))
    yield {"email": email, "password": password, "token": token, "user_id": user_id}
    # Cleanup: delete seeded registration + notifications + user
    _run(_db.registrations.delete_many({"user_id": user_id}))
    _run(_db.notifications.delete_many({"user_id": user_id}))
    _run(_db.users.delete_many({"id": user_id}))
    _run(_db.profiles.delete_many({"user_id": user_id}))


def _put_content_with_new_announcement(super_token: str, original: dict, new_ann: dict):
    payload_content = dict(original)
    anns = list(payload_content.get("announcements") or [])
    anns.append(new_ann)
    payload_content["announcements"] = anns
    r = requests.put(
        f"{API}/site/content",
        json={"content": payload_content},
        headers=_headers(super_token),
        timeout=30,
    )
    return r


# --- Auth ---


def test_put_site_content_forbidden_for_student(test_student, original_site_content):
    r = requests.put(
        f"{API}/site/content",
        json={"content": original_site_content},
        headers=_headers(test_student["token"]),
        timeout=30,
    )
    assert r.status_code == 403


# --- Add announcement + notification behaviour ---


def test_add_announcement_creates_notification_and_no_duplicate(super_token, original_site_content, test_student):
    new_ann = {
        "date": TEST_DATE,
        "category": TEST_CATEGORY,
        "title": TEST_TITLE,
        "summary": TEST_SUMMARY,
    }

    # First save: should add exactly one notif for the test student
    r = _put_content_with_new_announcement(super_token, original_site_content, new_ann)
    assert r.status_code == 200, r.text

    # Fetch pending for the test student
    r = requests.get(f"{API}/student/site-announcements/pending", headers=_headers(test_student["token"]), timeout=30)
    assert r.status_code == 200
    body = r.json()
    ann = body.get("announcement")
    assert ann is not None, f"pending announcement not returned: {body}"
    assert ann["title"] == TEST_TITLE
    assert ann["message"] == TEST_SUMMARY
    assert ann["type"] == "announcement"
    assert ann.get("is_popup_seen") is False
    # No mongo _id leak
    assert "_id" not in ann
    notif_id = ann["id"]

    # Second save with same announcement should NOT create a duplicate notif
    r2 = _put_content_with_new_announcement(super_token, original_site_content, new_ann)
    assert r2.status_code == 200
    # Poll pending again — should still return the same notif (or same title)
    r3 = requests.get(f"{API}/student/site-announcements/pending", headers=_headers(test_student["token"]), timeout=30)
    assert r3.status_code == 200
    ann2 = r3.json().get("announcement")
    assert ann2 is not None
    assert ann2["id"] == notif_id, "duplicate notification created on re-save (signature dedup broken)"

    # Save it to be used by the /seen test
    pytest.notif_id = notif_id


def test_mark_seen_updates_and_pending_becomes_null(test_student):
    notif_id = getattr(pytest, "notif_id", None)
    assert notif_id, "prev test did not set notif_id"

    r = requests.post(
        f"{API}/student/site-announcements/{notif_id}/seen",
        headers=_headers(test_student["token"]),
        timeout=30,
    )
    assert r.status_code == 200, r.text

    r2 = requests.get(f"{API}/student/site-announcements/pending", headers=_headers(test_student["token"]), timeout=30)
    assert r2.status_code == 200
    assert r2.json().get("announcement") is None


def test_mark_seen_wrong_id_returns_404(test_student):
    r = requests.post(
        f"{API}/student/site-announcements/nonexistent-id-xyz/seen",
        headers=_headers(test_student["token"]),
        timeout=30,
    )
    assert r.status_code == 404


def test_pending_isolation_across_users(super_token, original_site_content):
    """Another temp student should independently see the announcement pending."""
    email = f"test_popup2_{uuid.uuid4().hex[:8]}@example.com"
    password = "TestPopup2026!"
    reg = requests.post(f"{API}/auth/register", json={"name": "TEST_ONLY 2", "email": email, "password": password}, timeout=30)
    assert reg.status_code in (200, 201)
    tok = reg.json().get("token") or _login(email, password)
    user_id2 = reg.json().get("user", {}).get("user_id") or reg.json().get("user_id")
    assert user_id2
    _run(_db.registrations.insert_one({
        "id": str(uuid.uuid4()), "user_id": user_id2, "name": "TEST_ONLY 2",
        "email": email, "category": "Umum", "status": "draft",
        "test_tag": "TEST_ONLY_iter35_popup",
    }))
    try:
        fresh_ann = {
            "date": TEST_DATE,
            "category": TEST_CATEGORY,
            "title": TEST_TITLE + "_2",
            "summary": TEST_SUMMARY + " (v2)",
        }
        r = _put_content_with_new_announcement(super_token, original_site_content, fresh_ann)
        assert r.status_code == 200

        r2 = requests.get(f"{API}/student/site-announcements/pending", headers=_headers(tok), timeout=30)
        assert r2.status_code == 200
        ann = r2.json().get("announcement")
        assert ann is not None, "second user should have pending after PUT with new signature"
        assert ann["title"] == TEST_TITLE + "_2"
        assert "_id" not in ann
        assert ann.get("is_popup_seen") is False
    finally:
        _run(_db.registrations.delete_many({"user_id": user_id2}))
        _run(_db.notifications.delete_many({"user_id": user_id2}))
        _run(_db.users.delete_many({"id": user_id2}))
        _run(_db.profiles.delete_many({"user_id": user_id2}))


# --- Teardown: clean up TEST_ONLY notifications by asking super admin to touch a benign endpoint
# The site_content restore is handled by fixture teardown. Notification cleanup is best-effort via mongo.
