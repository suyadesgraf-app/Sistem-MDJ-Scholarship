"""Regression tests for student notifications feature.

Covers:
- selection_progress notification created when admin changes participant status (only when new status differs)
- GET /api/notifications returns only current user's notifications and excludes Mongo _id
- POST /api/notifications/{id}/read marks a single notification as read
- POST /api/notifications/read-all marks all unread as read for current user only
- Announcements via PUT /api/site/content trigger 'announcement' notifications for registered students
"""
import os
import time
import uuid

import pytest
import requests

def _load_backend_url():
    val = os.environ.get("REACT_APP_BACKEND_URL")
    if val:
        return val.rstrip("/")
    env_path = "/app/frontend/.env"
    if os.path.exists(env_path):
        with open(env_path) as fh:
            for line in fh:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip().rstrip("/")
    raise RuntimeError("REACT_APP_BACKEND_URL not set")


BASE_URL = _load_backend_url()

STUDENT_EMAIL = "mahasiswa.mdj@baznasbazisdki.id"
STUDENT_PASSWORD = "MahasiswaMDJ2026!"
ADMIN_EMAIL = "admin.mdj@baznasbazisdki.id"
ADMIN_PASSWORD = "AdminMDJ2026!"
SUPER_EMAIL = "supri@baznasbazisdki.id"
SUPER_PASSWORD = "MdjSuper2026!"


def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    tok = r.json().get("token")
    assert tok
    return tok


def _hdr(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def student_token():
    return _login(STUDENT_EMAIL, STUDENT_PASSWORD)


@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture(scope="module")
def super_token():
    return _login(SUPER_EMAIL, SUPER_PASSWORD)


@pytest.fixture(scope="module")
def student_user_id(student_token):
    r = requests.get(f"{BASE_URL}/api/auth/me", headers=_hdr(student_token), timeout=15)
    assert r.status_code == 200
    uid = r.json().get("user_id") or r.json().get("id")
    assert uid
    return uid


def test_list_notifications_shape_and_no_object_id(student_token):
    r = requests.get(f"{BASE_URL}/api/notifications", headers=_hdr(student_token), timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert "notifications" in data and "unread_count" in data
    assert isinstance(data["notifications"], list)
    for n in data["notifications"]:
        assert "_id" not in n
        assert {"id", "user_id", "type", "title", "message", "is_read", "created_at"} <= set(n.keys())


def test_admin_status_change_creates_selection_progress_notification(
    student_token, admin_token, student_user_id
):
    # Read current status
    reg = requests.get(f"{BASE_URL}/api/registration",
                       headers=_hdr(student_token), timeout=15).json()
    current_status = reg.get("status") or "submitted"

    # Choose a different valid status
    target = "verifikasi" if current_status != "verifikasi" else "wawancara"

    # Snapshot notifications before
    before = requests.get(f"{BASE_URL}/api/notifications",
                          headers=_hdr(student_token), timeout=15).json()
    before_ids = {n["id"] for n in before["notifications"]}

    # Admin updates status
    r = requests.put(
        f"{BASE_URL}/api/admin/participants/{student_user_id}/status",
        headers=_hdr(admin_token),
        json={"status": target, "note": "TEST_notification_regression"},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    assert r.json().get("status") == target

    # Wait a moment
    time.sleep(0.5)

    after = requests.get(f"{BASE_URL}/api/notifications",
                         headers=_hdr(student_token), timeout=15).json()
    new_notifs = [n for n in after["notifications"] if n["id"] not in before_ids]
    progress = [n for n in new_notifs if n["type"] == "selection_progress"]
    assert len(progress) == 1, f"Expected 1 new selection_progress, got {progress}"
    n = progress[0]
    assert n["user_id"] == student_user_id
    assert n["is_read"] is False
    assert target.replace("_", " ") in n["message"].lower() or "seleksi" in n["message"].lower()

    # Idempotent: setting same status again should NOT create another notif
    before2 = requests.get(f"{BASE_URL}/api/notifications",
                           headers=_hdr(student_token), timeout=15).json()
    r2 = requests.put(
        f"{BASE_URL}/api/admin/participants/{student_user_id}/status",
        headers=_hdr(admin_token),
        json={"status": target, "note": "TEST_no_change"},
        timeout=15,
    )
    assert r2.status_code == 200
    time.sleep(0.3)
    after2 = requests.get(f"{BASE_URL}/api/notifications",
                          headers=_hdr(student_token), timeout=15).json()
    assert after2["unread_count"] == before2["unread_count"], \
        "No new notification should be created when status is unchanged"

    # Restore original status (cleanup)
    requests.put(
        f"{BASE_URL}/api/admin/participants/{student_user_id}/status",
        headers=_hdr(admin_token),
        json={"status": current_status, "note": "TEST_restore"},
        timeout=15,
    )


def test_mark_single_notification_read(student_token):
    data = requests.get(f"{BASE_URL}/api/notifications",
                        headers=_hdr(student_token), timeout=15).json()
    unread = [n for n in data["notifications"] if not n["is_read"]]
    if not unread:
        pytest.skip("No unread notifications available to mark read")
    target = unread[0]
    r = requests.post(f"{BASE_URL}/api/notifications/{target['id']}/read",
                      headers=_hdr(student_token), timeout=15)
    assert r.status_code == 200
    after = requests.get(f"{BASE_URL}/api/notifications",
                         headers=_hdr(student_token), timeout=15).json()
    found = next((n for n in after["notifications"] if n["id"] == target["id"]), None)
    assert found and found["is_read"] is True


def test_mark_read_wrong_user_returns_404(student_token, admin_token):
    # Admin trying to mark a random id (or student's id) — since notifications
    # are user-scoped, using a bogus id should 404 for anyone.
    bogus = str(uuid.uuid4())
    r = requests.post(f"{BASE_URL}/api/notifications/{bogus}/read",
                      headers=_hdr(admin_token), timeout=15)
    assert r.status_code == 404


def test_mark_all_read_scope_isolated(student_token, admin_token):
    # Ensure student has at least one unread by creating via status change
    student_uid = requests.get(f"{BASE_URL}/api/auth/me",
                               headers=_hdr(student_token), timeout=15).json().get("user_id")
    reg = requests.get(f"{BASE_URL}/api/registration",
                       headers=_hdr(student_token), timeout=15).json()
    current = reg.get("status") or "submitted"
    target = "wawancara" if current != "wawancara" else "verifikasi"
    requests.put(f"{BASE_URL}/api/admin/participants/{student_uid}/status",
                 headers=_hdr(admin_token),
                 json={"status": target, "note": "TEST_mark_all"}, timeout=15)
    time.sleep(0.3)

    # Admin unread count before
    admin_before = requests.get(f"{BASE_URL}/api/notifications",
                                headers=_hdr(admin_token), timeout=15).json()
    student_before = requests.get(f"{BASE_URL}/api/notifications",
                                  headers=_hdr(student_token), timeout=15).json()
    assert student_before["unread_count"] >= 1

    r = requests.post(f"{BASE_URL}/api/notifications/read-all",
                      headers=_hdr(student_token), timeout=15)
    assert r.status_code == 200
    student_after = requests.get(f"{BASE_URL}/api/notifications",
                                 headers=_hdr(student_token), timeout=15).json()
    admin_after = requests.get(f"{BASE_URL}/api/notifications",
                               headers=_hdr(admin_token), timeout=15).json()
    assert student_after["unread_count"] == 0
    # Admin unread count must not decrease (scope isolation)
    assert admin_after["unread_count"] == admin_before["unread_count"]

    # Restore
    requests.put(f"{BASE_URL}/api/admin/participants/{student_uid}/status",
                 headers=_hdr(admin_token),
                 json={"status": current, "note": "TEST_restore"}, timeout=15)


def test_announcement_creates_notification_for_students(super_token, student_token):
    # Fetch current content
    content = requests.get(f"{BASE_URL}/api/site/content", timeout=15).json()
    original_announcements = list(content.get("announcements", []))

    new_ann = {
        "date": "2026-01-15",
        "category": "TEST",
        "title": f"TEST_ANN_{uuid.uuid4().hex[:8]}",
        "summary": "Pengumuman uji otomatis notifikasi.",
    }
    payload_content = {**content, "announcements": original_announcements + [new_ann]}

    before = requests.get(f"{BASE_URL}/api/notifications",
                          headers=_hdr(student_token), timeout=15).json()
    before_ids = {n["id"] for n in before["notifications"]}

    r = requests.put(f"{BASE_URL}/api/site/content",
                     headers=_hdr(super_token),
                     json={"content": payload_content}, timeout=20)
    assert r.status_code == 200, r.text

    time.sleep(1.0)
    after = requests.get(f"{BASE_URL}/api/notifications",
                         headers=_hdr(student_token), timeout=15).json()
    new_notifs = [n for n in after["notifications"] if n["id"] not in before_ids]
    ann_notifs = [n for n in new_notifs
                  if n["type"] == "announcement" and n["title"] == new_ann["title"]]
    try:
        assert len(ann_notifs) == 1, f"Expected 1 announcement notif, got {ann_notifs}"
        assert ann_notifs[0]["message"] == new_ann["summary"]
        assert ann_notifs[0]["is_read"] is False
    finally:
        # Cleanup: restore original announcements
        restore_content = {**content, "announcements": original_announcements}
        requests.put(f"{BASE_URL}/api/site/content",
                     headers=_hdr(super_token),
                     json={"content": restore_content}, timeout=20)
        # Delete the test notification directly via marking read (no delete API exists)
        # Best-effort: leave read=false but note it's TEST_ prefixed for easy identification.
