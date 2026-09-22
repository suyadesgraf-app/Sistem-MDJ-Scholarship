"""Iter47: Selection announcement stage-aware publish + no auto broadcast on status update.

Verifies review requirements:
  - Publishing with stage=administration / beneficiary stores stage on announcement + notifications
  - Title is 'Pengumuman Hasil Seleksi'
  - Invalid stage rejected
  - PUT /api/admin/participants/{user_id}/status does NOT create selection_result
    notification nor set is_announcement_published (only selection_progress)
"""
import os
import uuid
import requests
import pytest
import bcrypt
from pymongo import MongoClient

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ.get("DB_NAME", "test_database")

SUPER = {"email": "supri@baznasbazisdki.id", "password": "MdjSuper2026!"}
ADMIN_PROV = {"email": "admin.mdj@baznasbazisdki.id", "password": "AdminMDJ2026!"}

TAG = "TEST_iter47_stage"

pytestmark = pytest.mark.xdist_group(name="selection_announcement_stage")


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _hdr(t):
    return {"Authorization": f"Bearer {t}"}


@pytest.fixture(scope="module")
def mongo():
    c = MongoClient(MONGO_URL)
    yield c[DB_NAME]
    c.close()


@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN_PROV)


def _seed_users(mongo, category, spec):
    """spec: list of (outcome_label, status)."""
    users, regs = [], []
    hp = bcrypt.hashpw(b"TestPass123!", bcrypt.gensalt()).decode()
    now = "2026-01-15T00:00:00+00:00"
    for label, status in spec:
        uid = str(uuid.uuid4())
        email = f"test_iter47_{label}_{uuid.uuid4().hex[:6]}@contoh.invalid"
        users.append({
            "id": uid, "user_id": uid, "email": email,
            "name": f"TEST Iter47 {label}", "role": "student",
            "is_active": True, "password_hash": hp, "created_at": now,
            "test_tag": TAG,
        })
        regs.append({
            "id": str(uuid.uuid4()), "user_id": uid, "email": email,
            "name": f"TEST Iter47 {label}", "category": category,
            "status": status, "created_at": now, "test_tag": TAG,
        })
    mongo.users.insert_many(users)
    mongo.registrations.insert_many(regs)
    return users


def _cleanup(mongo, users, category):
    uids = [u["user_id"] for u in users]
    mongo.users.delete_many({"user_id": {"$in": uids}})
    mongo.registrations.delete_many({"user_id": {"$in": uids}})
    mongo.notifications.delete_many({"user_id": {"$in": uids}})
    mongo.sessions.delete_many({"user_id": {"$in": uids}})
    mongo.selection_announcements.delete_many({"category": category})


class TestPublishAdministrationStage:
    def test_publish_administration_stage(self, mongo, admin_token):
        category = f"TEST_ITER47_ADM_{uuid.uuid4().hex[:8]}"
        users = _seed_users(mongo, category, [
            ("passed", "lolos_administrasi"),
            ("failed", "ditolak"),
        ])
        try:
            r = requests.post(
                f"{API}/admin/selection-announcements/publish",
                headers=_hdr(admin_token),
                json={"category": category, "stage": "administration"},
                timeout=30,
            )
            assert r.status_code == 200, r.text
            data = r.json()
            ann_id = data["announcement_id"]

            ann = mongo.selection_announcements.find_one({"id": ann_id})
            assert ann is not None
            assert ann["stage"] == "administration"
            assert ann["title"] == "Pengumuman Hasil Seleksi"
            assert ann["status_publikasi"] == "Published"

            uids = [u["user_id"] for u in users]
            notifs = list(mongo.notifications.find(
                {"user_id": {"$in": uids}, "type": "selection_result"}))
            assert len(notifs) == 2
            for n in notifs:
                assert n["stage"] == "administration"
                assert n["title"] == "Pengumuman Hasil Seleksi"
                assert n["announcement_id"] == ann_id
                assert n["is_popup_seen"] is False
        finally:
            _cleanup(mongo, users, category)

    def test_publish_beneficiary_stage(self, mongo, admin_token):
        category = f"TEST_ITER47_BEN_{uuid.uuid4().hex[:8]}"
        users = _seed_users(mongo, category, [
            ("pm", "penerima_manfaat"),
        ])
        try:
            r = requests.post(
                f"{API}/admin/selection-announcements/publish",
                headers=_hdr(admin_token),
                json={"category": category, "stage": "beneficiary"},
                timeout=30,
            )
            assert r.status_code == 200, r.text
            ann_id = r.json()["announcement_id"]

            ann = mongo.selection_announcements.find_one({"id": ann_id})
            assert ann["stage"] == "beneficiary"

            uid = users[0]["user_id"]
            notif = mongo.notifications.find_one(
                {"user_id": uid, "type": "selection_result"})
            assert notif is not None
            assert notif["stage"] == "beneficiary"
            assert notif["result"] == "passed"
        finally:
            _cleanup(mongo, users, category)

    def test_publish_invalid_stage_rejected(self, mongo, admin_token):
        category = f"TEST_ITER47_BAD_{uuid.uuid4().hex[:8]}"
        users = _seed_users(mongo, category, [("passed", "lolos_administrasi")])
        try:
            r = requests.post(
                f"{API}/admin/selection-announcements/publish",
                headers=_hdr(admin_token),
                json={"category": category, "stage": "wawancara"},
                timeout=30,
            )
            assert r.status_code == 400
            assert "Tahapan" in r.json().get("detail", "")
        finally:
            _cleanup(mongo, users, category)


class TestStatusUpdateDoesNotBroadcast:
    def test_status_change_creates_progress_not_result(self, mongo, admin_token):
        """PUT /admin/participants/{uid}/status must NOT create selection_result
        notification, must NOT set is_announcement_published."""
        category = f"TEST_ITER47_NOAUTO_{uuid.uuid4().hex[:8]}"
        users = _seed_users(mongo, category, [("pending", "submitted")])
        uid = users[0]["user_id"]
        try:
            r = requests.put(
                f"{API}/admin/participants/{uid}/status",
                headers=_hdr(admin_token),
                json={"status": "lolos_administrasi", "note": "tes iter47"},
                timeout=30,
            )
            assert r.status_code == 200, r.text
            updated = r.json()
            assert updated["status"] == "lolos_administrasi"
            # is_announcement_published must NOT be true
            assert not updated.get("is_announcement_published"), \
                "Status update must NOT mark announcement as published"
            assert "selection_announcement_id" not in updated or \
                not updated.get("selection_announcement_id")

            # No selection_result notification created
            sel_notifs = list(mongo.notifications.find(
                {"user_id": uid, "type": "selection_result"}))
            assert len(sel_notifs) == 0, \
                f"Status update wrongly created selection_result notif: {sel_notifs}"

            # selection_progress notification IS created (informational only)
            prog = list(mongo.notifications.find(
                {"user_id": uid, "type": "selection_progress"}))
            assert len(prog) == 1

            # Mongo state
            reg = mongo.registrations.find_one({"user_id": uid})
            assert not reg.get("is_announcement_published"), \
                "registration flagged even though publish never called"
        finally:
            _cleanup(mongo, users, category)

    def test_pending_popup_none_before_publish(self, mongo, admin_token):
        """Student should NOT see selection popup just because status was flipped."""
        category = f"TEST_ITER47_POPUP_{uuid.uuid4().hex[:8]}"
        users = _seed_users(mongo, category, [("pending", "submitted")])
        uid = users[0]["user_id"]
        email = users[0]["email"]
        try:
            # Admin flips status to lolos_administrasi
            requests.put(
                f"{API}/admin/participants/{uid}/status",
                headers=_hdr(admin_token),
                json={"status": "lolos_administrasi", "note": "flip"},
                timeout=30,
            )
            # Student logs in and asks for pending selection announcement
            stok = _login({"email": email, "password": "TestPass123!"})
            r = requests.get(
                f"{API}/student/selection-announcements/pending",
                headers=_hdr(stok), timeout=30,
            )
            assert r.status_code == 200
            ann = r.json()["announcement"]
            # Because there is NO published announcement in this unique category,
            # the auto-claim branch should not fire and no popup should be pending.
            assert ann is None, \
                f"Popup pending before Publikasikan was clicked: {ann}"
        finally:
            _cleanup(mongo, users, category)
