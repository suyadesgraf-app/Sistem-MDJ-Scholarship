"""Iter28: Selection Announcement broadcast + student popup lifecycle.

Creates 2 temporary students with a unique category (one passed_administrasi, one ditolak),
publishes the announcement, verifies API contracts + role guards + notification lifecycle,
then FULLY cleans up all TEST_ data (users, registrations, notifications, sessions,
selection_announcements, profiles).
"""
import os
import uuid
import time
import requests
import pytest
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://sistem-registrasi.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

SUPER = {"email": "supri@baznasbazisdki.id", "password": "MdjSuper2026!"}
ADMIN_PROV = {"email": "admin.mdj@baznasbazisdki.id", "password": "AdminMDJ2026!"}
STUDENT_DEMO = {"email": "mahasiswa.mdj@baznasbazisdki.id", "password": "MahasiswaMDJ2026!"}

UNIQUE_CATEGORY = f"TEST_ITER28_KAT_{uuid.uuid4().hex[:8]}"
TAG = "TEST_iter28_selection_broadcast"

# Keep all tests on the same xdist worker so module-scoped seeded fixture is shared.
pytestmark = pytest.mark.xdist_group(name="selection_announcement_broadcast")


# ---------- helpers ----------
def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login failed for {creds['email']}: {r.status_code} {r.text}"
    return r.json()["token"]


def _hdr(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def mongo():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


@pytest.fixture(scope="module")
def tokens():
    return {
        "super": _login(SUPER),
        "admin": _login(ADMIN_PROV),
        "student_demo": _login(STUDENT_DEMO),
    }


@pytest.fixture(scope="module")
def seeded(mongo, tokens):
    """Seed 2 users + 2 registrations under unique category. yields dict + cleans up."""
    import bcrypt

    now = "2026-01-15T00:00:00+00:00"
    users = []
    regs = []
    passwd_hash = bcrypt.hashpw(b"TestPass123!", bcrypt.gensalt()).decode()
    for outcome, status in [("passed", "lolos_administrasi"), ("failed", "ditolak")]:
        uid = str(uuid.uuid4())
        email = f"test_iter28_{outcome}_{uuid.uuid4().hex[:6]}@contoh.invalid"
        users.append({
            "id": uid, "user_id": uid, "email": email, "name": f"TEST Iter28 {outcome}",
            "role": "student", "is_active": True, "password_hash": passwd_hash,
            "created_at": now, "test_tag": TAG,
        })
        regs.append({
            "id": str(uuid.uuid4()), "user_id": uid, "email": email,
            "name": f"TEST Iter28 {outcome}",
            "category": UNIQUE_CATEGORY, "status": status,
            "created_at": now, "test_tag": TAG,
        })
    mongo.users.insert_many(users)
    mongo.registrations.insert_many(regs)

    yield {"users": users, "regs": regs, "category": UNIQUE_CATEGORY}

    # ---- cleanup ----
    uids = [u["user_id"] for u in users]
    emails = [u["email"] for u in users]
    mongo.users.delete_many({"user_id": {"$in": uids}})
    mongo.registrations.delete_many({"user_id": {"$in": uids}})
    mongo.notifications.delete_many({"user_id": {"$in": uids}})
    mongo.notifications.delete_many({"category": UNIQUE_CATEGORY})
    mongo.sessions.delete_many({"user_id": {"$in": uids}})
    mongo.profiles.delete_many({"user_id": {"$in": uids}})
    mongo.selection_announcements.delete_many({"category": UNIQUE_CATEGORY})
    mongo.users.delete_many({"email": {"$in": emails}})
    mongo.registrations.delete_many({"test_tag": TAG})
    mongo.users.delete_many({"test_tag": TAG})


# ---------- 1. role guards on summary/publish ----------
class TestRoleGuards:
    def test_summary_admin_ok(self, tokens):
        r = requests.get(f"{API}/admin/selection-announcements/summary",
                         headers=_hdr(tokens["admin"]), timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "passed_count" in data and "failed_count" in data
        assert "categories" in data

    def test_summary_super_ok(self, tokens):
        r = requests.get(f"{API}/admin/selection-announcements/summary",
                         headers=_hdr(tokens["super"]), timeout=30)
        assert r.status_code == 200

    def test_summary_student_forbidden(self, tokens):
        r = requests.get(f"{API}/admin/selection-announcements/summary",
                         headers=_hdr(tokens["student_demo"]), timeout=30)
        assert r.status_code == 403

    def test_publish_student_forbidden(self, tokens):
        r = requests.post(f"{API}/admin/selection-announcements/publish",
                          headers=_hdr(tokens["student_demo"]),
                          json={"category": "all"}, timeout=30)
        assert r.status_code == 403

    def test_admin_wilayah_forbidden(self, tokens, mongo):
        # create temp admin_wilayah, login, then delete
        import bcrypt
        uid = str(uuid.uuid4())
        email = f"test_iter28_aw_{uuid.uuid4().hex[:6]}@contoh.invalid"
        hp = bcrypt.hashpw(b"TestPass123!", bcrypt.gensalt()).decode()
        mongo.users.insert_one({
            "id": uid, "user_id": uid, "email": email, "name": "TEST AW",
            "role": "admin_wilayah", "region": "Jakarta Pusat", "is_active": True,
            "password_hash": hp, "created_at": "2026-01-15T00:00:00+00:00",
            "test_tag": TAG,
        })
        try:
            tok = _login({"email": email, "password": "TestPass123!"})
            r1 = requests.get(f"{API}/admin/selection-announcements/summary",
                              headers=_hdr(tok), timeout=30)
            r2 = requests.post(f"{API}/admin/selection-announcements/publish",
                               headers=_hdr(tok), json={"category": "all"}, timeout=30)
            assert r1.status_code == 403, r1.text
            assert r2.status_code == 403, r2.text
        finally:
            mongo.users.delete_many({"user_id": uid})
            mongo.sessions.delete_many({"user_id": uid})


# ---------- 2. summary counts + publish flow ----------
class TestBroadcastLifecycle:
    def test_summary_for_unique_category(self, tokens, seeded):
        r = requests.get(f"{API}/admin/selection-announcements/summary",
                         headers=_hdr(tokens["admin"]),
                         params={"category": seeded["category"]}, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["category"] == seeded["category"]
        assert data["passed_count"] == 1
        assert data["failed_count"] == 1
        assert data["recipient_count"] == 2
        assert data["latest_publication"] in (None, {})

    def test_publish_returns_published(self, tokens, seeded, mongo):
        r = requests.post(f"{API}/admin/selection-announcements/publish",
                          headers=_hdr(tokens["admin"]),
                          json={"category": seeded["category"]}, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["status_publikasi"] == "Published"
        assert data["passed_count"] == 1
        assert data["failed_count"] == 1
        assert data["recipient_count"] == 2
        ann_id = data["announcement_id"]

        # Data assertion in Mongo: 2 selection_result notifications tied to test users
        uids = [u["user_id"] for u in seeded["users"]]
        notifs = list(mongo.notifications.find(
            {"user_id": {"$in": uids}, "type": "selection_result"}))
        assert len(notifs) == 2
        results = sorted(n.get("result") for n in notifs)
        assert results == ["failed", "passed"]
        for n in notifs:
            assert n["announcement_id"] == ann_id
            assert n["is_popup_seen"] is False
            assert n["is_read"] is False

        # registrations flagged
        regs = list(mongo.registrations.find({"user_id": {"$in": uids}}))
        assert all(r.get("is_announcement_published") is True for r in regs)
        assert all(r.get("selection_announcement_id") == ann_id for r in regs)

        # selection_announcements row
        ann = mongo.selection_announcements.find_one({"id": ann_id})
        assert ann is not None
        assert ann["status_publikasi"] == "Published"
        assert ann["category"] == seeded["category"]

    def test_republish_same_category_returns_400(self, tokens, seeded):
        # after publish, all recipients flagged, no new recipients -> 400
        r = requests.post(f"{API}/admin/selection-announcements/publish",
                          headers=_hdr(tokens["admin"]),
                          json={"category": seeded["category"]}, timeout=30)
        assert r.status_code == 400

    def test_summary_after_publish_shows_latest(self, tokens, seeded):
        r = requests.get(f"{API}/admin/selection-announcements/summary",
                         headers=_hdr(tokens["admin"]),
                         params={"category": seeded["category"]}, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert data["latest_publication"] is not None
        assert data["latest_publication"]["status_publikasi"] == "Published"
        # counts should be 0 now (all published)
        assert data["passed_count"] == 0
        assert data["failed_count"] == 0


# ---------- 3. student pending/seen endpoints ----------
class TestStudentPopupEndpoints:
    def test_pending_returns_only_own(self, seeded, mongo):
        # login as one test student
        passed_user = seeded["users"][0]  # outcome=passed
        failed_user = seeded["users"][1]  # outcome=failed
        tok_pass = _login({"email": passed_user["email"], "password": "TestPass123!"})
        tok_fail = _login({"email": failed_user["email"], "password": "TestPass123!"})

        r = requests.get(f"{API}/student/selection-announcements/pending",
                         headers=_hdr(tok_pass), timeout=30)
        assert r.status_code == 200
        ann = r.json()["announcement"]
        assert ann is not None
        assert ann["result"] == "passed"
        assert ann["is_popup_seen"] is False
        notif_id_pass = ann["id"]

        r2 = requests.get(f"{API}/student/selection-announcements/pending",
                          headers=_hdr(tok_fail), timeout=30)
        ann2 = r2.json()["announcement"]
        assert ann2 is not None
        assert ann2["result"] == "failed"
        notif_id_fail = ann2["id"]

        # demo student should NOT see anything from unique category (isolation)
        # (may see other, but ID must not match test notifs)
        tok_demo = _login(STUDENT_DEMO)
        r3 = requests.get(f"{API}/student/selection-announcements/pending",
                          headers=_hdr(tok_demo), timeout=30)
        assert r3.status_code == 200
        demo_ann = r3.json()["announcement"]
        if demo_ann is not None:
            assert demo_ann["id"] not in (notif_id_pass, notif_id_fail)

        # mark seen for pass user
        s = requests.post(f"{API}/student/selection-announcements/{notif_id_pass}/seen",
                         headers=_hdr(tok_pass), timeout=30)
        assert s.status_code == 200

        # pending now null
        r4 = requests.get(f"{API}/student/selection-announcements/pending",
                          headers=_hdr(tok_pass), timeout=30)
        assert r4.status_code == 200
        assert r4.json()["announcement"] is None

        # Mongo assertions
        doc = mongo.notifications.find_one({"id": notif_id_pass})
        assert doc["is_read"] is True
        assert doc["is_popup_seen"] is True
        assert "popup_seen_at" in doc

    def test_seen_wrong_user_returns_404(self, seeded):
        # login as passed user, try to seen failed user's notif
        passed_user = seeded["users"][0]
        failed_user = seeded["users"][1]
        tok_pass = _login({"email": passed_user["email"], "password": "TestPass123!"})
        tok_fail = _login({"email": failed_user["email"], "password": "TestPass123!"})
        r = requests.get(f"{API}/student/selection-announcements/pending",
                         headers=_hdr(tok_fail), timeout=30)
        fail_notif_id = r.json()["announcement"]["id"]
        # try to mark it seen as pass user
        s = requests.post(f"{API}/student/selection-announcements/{fail_notif_id}/seen",
                         headers=_hdr(tok_pass), timeout=30)
        assert s.status_code == 404
