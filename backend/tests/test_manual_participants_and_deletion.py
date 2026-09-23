"""
Tests for Super Admin manual participant creation and permanent deletion flows.
IMPORTANT: This test suite avoids executing confirmed scope=all deletions to protect shared DB.
Cleans up all TEST_ prefixed data via Mongo directly.
"""
import os
import re
import uuid
import time
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://sistem-registrasi.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

SUPER_ADMIN = {"email": "supri@baznasbazisdki.id", "password": "MdjSuper2026!"}
DEMO_ADMIN = {"email": "admin.mdj@baznasbazisdki.id", "password": "AdminMDJ2026!"}
DEMO_STUDENT = {"email": "mahasiswa.mdj@baznasbazisdki.id", "password": "MahasiswaMDJ2026!"}

RUN_TAG = uuid.uuid4().hex[:6]
TEST_CAMPUS = f"TEST_KampusUji_{RUN_TAG}"
TEST_EMAIL_1 = f"test.manual.{RUN_TAG}.1@contoh.invalid"
TEST_EMAIL_2 = f"test.manual.{RUN_TAG}.2@contoh.invalid"


_nik_counter = {"n": 0}


def _nik():
    _nik_counter["n"] += 1
    base = uuid.uuid4().int
    s = str(base)[:11] + str(_nik_counter["n"]).zfill(1)
    s = (s + "0000000000000000")[:16]
    # Ensure exactly 16 digits, starting non-zero
    if s.startswith("0"):
        s = "3" + s[1:]
    return s


TEST_NIK_1 = _nik()
TEST_NIK_2 = _nik()


@pytest.fixture(scope="module")
def mongo_db():
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    yield db
    # Final teardown: aggressive cleanup by prefix
    try:
        emails = [TEST_EMAIL_1, TEST_EMAIL_2]
        niks = [TEST_NIK_1, TEST_NIK_2]
        users = list(db.users.find({"email": {"$in": emails}}, {"user_id": 1}))
        user_ids = [u.get("user_id") for u in users if u.get("user_id")]
        # Also find profiles/registrations that may have leaked
        prof_users = list(db.profiles.find(
            {"data.institusi": {"$regex": f"^{re.escape(TEST_CAMPUS)}$", "$options": "i"}},
            {"user_id": 1},
        ))
        user_ids += [p["user_id"] for p in prof_users if p.get("user_id")]
        user_ids = list(set(user_ids))
        if user_ids:
            db.documents.delete_many({"user_id": {"$in": user_ids}})
            db.profiles.delete_many({"user_id": {"$in": user_ids}})
            db.registrations.delete_many({"user_id": {"$in": user_ids}})
            db.notifications.delete_many({"user_id": {"$in": user_ids}})
            db.student_live_chat_messages.delete_many({"student_id": {"$in": user_ids}})
            db.active_letter_approvals.delete_many({"user_id": {"$in": user_ids}})
            db.stage_ii_eligibilities.delete_many({"user_id": {"$in": user_ids}})
            db.users.delete_many({"user_id": {"$in": user_ids}})
            db.campus_disbursements.update_many(
                {"recipient_user_ids": {"$in": user_ids}},
                {"$pull": {"recipient_user_ids": {"$in": user_ids}}},
            )
        db.registrations.delete_many({"email": {"$in": emails}})
        db.registrations.delete_many({"nik": {"$in": niks}})
        db.users.delete_many({"email": {"$in": emails}})
        db.campuses.delete_many({"name": TEST_CAMPUS})
    finally:
        client.close()


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    if r.status_code != 200:
        return None
    token = r.json().get("token")
    return token


@pytest.fixture(scope="module")
def super_token():
    tok = _login(**SUPER_ADMIN)
    assert tok, f"Super admin login failed"
    return tok


@pytest.fixture(scope="module")
def student_token():
    return _login(**DEMO_STUDENT)


@pytest.fixture(scope="module")
def admin_token():
    return _login(**DEMO_ADMIN)


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


# ---------------- Auth / RBAC ----------------
class TestRBAC:
    def test_manual_endpoint_requires_super_admin_student(self, student_token):
        if not student_token:
            pytest.skip("no student token")
        r = requests.post(f"{API}/admin/participants/manual",
                          json={"name": "X", "nik": "1" * 16, "email": "x@x.co", "phone": "0812345678", "campus": "K", "nim": "N"},
                          headers=_h(student_token), timeout=30)
        assert r.status_code == 403, r.text

    def test_delete_preview_forbidden_admin(self, admin_token):
        if not admin_token:
            pytest.skip("no admin token")
        r = requests.post(f"{API}/admin/participants/delete-preview",
                          json={"scope": "all"}, headers=_h(admin_token), timeout=30)
        assert r.status_code == 403, r.text

    def test_delete_forbidden_admin(self, admin_token):
        if not admin_token:
            pytest.skip("no admin token")
        r = requests.delete(f"{API}/admin/participants",
                            json={"scope": "all", "confirmed": True},
                            headers=_h(admin_token), timeout=30)
        assert r.status_code == 403, r.text


# ---------------- Manual create validation ----------------
class TestManualValidation:
    def test_reject_bad_nik(self, super_token):
        r = requests.post(f"{API}/admin/participants/manual",
                          json={"name": "TEST Bad NIK", "nik": "12345", "email": TEST_EMAIL_1,
                                "phone": "0812345678", "campus": TEST_CAMPUS, "nim": "N1"},
                          headers=_h(super_token), timeout=30)
        assert r.status_code == 400, r.text

    def test_reject_bad_email(self, super_token):
        r = requests.post(f"{API}/admin/participants/manual",
                          json={"name": "TEST Bad Email", "nik": TEST_NIK_1, "email": "not-an-email",
                                "phone": "0812345678", "campus": TEST_CAMPUS, "nim": "N1"},
                          headers=_h(super_token), timeout=30)
        assert r.status_code == 400, r.text

    def test_reject_bad_phone(self, super_token):
        r = requests.post(f"{API}/admin/participants/manual",
                          json={"name": "TEST Bad Phone", "nik": TEST_NIK_1, "email": TEST_EMAIL_1,
                                "phone": "12", "campus": TEST_CAMPUS, "nim": "N1"},
                          headers=_h(super_token), timeout=30)
        assert r.status_code == 400, r.text


# ---------------- Manual create + duplicate + campus autocreate ----------------
class TestManualCreate:
    def test_create_first_participant_creates_campus(self, super_token, mongo_db):
        # Ensure clean state
        mongo_db.campuses.delete_many({"name": TEST_CAMPUS})
        payload = {
            "name": f"TEST Peserta Satu {RUN_TAG}",
            "nik": TEST_NIK_1,
            "email": TEST_EMAIL_1,
            "phone": "081234567890",
            "campus": TEST_CAMPUS,
            "nim": f"NIM{RUN_TAG}1",
        }
        r = requests.post(f"{API}/admin/participants/manual", json=payload,
                          headers=_h(super_token), timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        participant = data.get("participant", {})
        assert participant.get("email") == TEST_EMAIL_1
        assert participant.get("status") == "submitted"

        # Verify persistence via GET participants list
        user = mongo_db.users.find_one({"email": TEST_EMAIL_1})
        assert user is not None, "user should be created"
        assert user.get("role") == "student"
        prof = mongo_db.profiles.find_one({"user_id": user["user_id"]})
        assert prof is not None
        reg = mongo_db.registrations.find_one({"user_id": user["user_id"]})
        assert reg is not None
        assert reg.get("status") == "submitted"
        # No documents
        doc_count = mongo_db.documents.count_documents({"user_id": user["user_id"]})
        assert doc_count == 0
        # Campus autocreated
        camp = mongo_db.campuses.find_one({"name": TEST_CAMPUS})
        assert camp is not None, "campus should be autocreated"

    def test_create_second_participant_same_campus(self, super_token, mongo_db):
        payload = {
            "name": f"TEST Peserta Dua {RUN_TAG}",
            "nik": TEST_NIK_2,
            "email": TEST_EMAIL_2,
            "phone": "081234567891",
            "campus": TEST_CAMPUS,
            "nim": f"NIM{RUN_TAG}2",
        }
        r = requests.post(f"{API}/admin/participants/manual", json=payload,
                          headers=_h(super_token), timeout=30)
        assert r.status_code == 200, r.text
        assert mongo_db.users.find_one({"email": TEST_EMAIL_2}) is not None

    def test_reject_duplicate_email(self, super_token):
        payload = {
            "name": "TEST Duplicate",
            "nik": _nik(),  # different nik
            "email": TEST_EMAIL_1,
            "phone": "081234567892",
            "campus": TEST_CAMPUS,
            "nim": f"NIMDUP{RUN_TAG}",
        }
        r = requests.post(f"{API}/admin/participants/manual", json=payload,
                          headers=_h(super_token), timeout=30)
        assert r.status_code == 409, r.text


# ---------------- Preview ----------------
class TestPreview:
    def test_preview_single(self, super_token, mongo_db):
        user = mongo_db.users.find_one({"email": TEST_EMAIL_1})
        assert user
        r = requests.post(f"{API}/admin/participants/delete-preview",
                          json={"scope": "single", "user_id": user["user_id"]},
                          headers=_h(super_token), timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["count"] == 1
        assert len(data["participants"]) == 1
        assert data["participants"][0]["email"] == TEST_EMAIL_1

    def test_preview_campus(self, super_token):
        r = requests.post(f"{API}/admin/participants/delete-preview",
                          json={"scope": "campus", "campus": TEST_CAMPUS},
                          headers=_h(super_token), timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["count"] == 2, data
        assert TEST_CAMPUS in data["label"]

    def test_preview_all_only_counts_no_delete(self, super_token, mongo_db):
        # preview only; must NOT delete anything
        pre_count = mongo_db.registrations.count_documents({})
        r = requests.post(f"{API}/admin/participants/delete-preview",
                          json={"scope": "all"}, headers=_h(super_token), timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["count"] >= 2
        demo_user = mongo_db.users.find_one({"email": DEMO_STUDENT["email"]})
        assert demo_user, "demo student should exist"
        expected_count = mongo_db.registrations.count_documents(
            {"user_id": {"$ne": demo_user["user_id"]}}
        )
        assert data["count"] == expected_count
        post_count = mongo_db.registrations.count_documents({})
        assert pre_count == post_count, "preview must not delete"


class TestDemoStudentProtection:
    def test_demo_account_is_excluded_from_delete_preview(self, super_token, mongo_db):
        demo_user = mongo_db.users.find_one({"email": DEMO_STUDENT["email"]})
        assert demo_user, "demo student should exist"
        r = requests.post(
            f"{API}/admin/participants/delete-preview",
            json={"scope": "single", "user_id": demo_user["user_id"]},
            headers=_h(super_token),
            timeout=30,
        )
        assert r.status_code == 200, r.text
        assert r.json()["count"] == 0

    def test_demo_account_cannot_be_deleted(self, super_token, mongo_db):
        demo_user = mongo_db.users.find_one({"email": DEMO_STUDENT["email"]})
        assert demo_user, "demo student should exist"
        r = requests.delete(
            f"{API}/admin/participants",
            json={"scope": "single", "user_id": demo_user["user_id"], "confirmed": True},
            headers=_h(super_token),
            timeout=30,
        )
        assert r.status_code == 404, r.text
        assert mongo_db.users.find_one({"user_id": demo_user["user_id"]}) is not None

    def test_demo_account_is_excluded_from_beneficiary_recaps(self, super_token, mongo_db):
        demo_user = mongo_db.users.find_one({"email": DEMO_STUDENT["email"]})
        assert demo_user, "demo student should exist"
        expected_beneficiaries = mongo_db.registrations.count_documents(
            {
                "status": "lolos",
                "user_id": {"$ne": demo_user["user_id"]},
            }
        )
        stats_response = requests.get(
            f"{API}/admin/stats",
            headers=_h(super_token),
            timeout=30,
        )
        assert stats_response.status_code == 200, stats_response.text
        assert stats_response.json()["verified"] == expected_beneficiaries

        beneficiaries_response = requests.get(
            f"{API}/admin/beneficiaries",
            headers=_h(super_token),
            timeout=30,
        )
        assert beneficiaries_response.status_code == 200, beneficiaries_response.text
        beneficiary_emails = {
            item.get("email", "").lower()
            for item in beneficiaries_response.json()
        }
        assert DEMO_STUDENT["email"] not in beneficiary_emails

    def test_demo_account_can_be_found_in_participant_list(self, super_token):
        response = requests.get(
            f"{API}/admin/participants",
            params={"search": DEMO_STUDENT["email"]},
            headers=_h(super_token),
            timeout=30,
        )
        assert response.status_code == 200, response.text
        participants = response.json()
        assert len(participants) == 1
        assert participants[0]["email"] == DEMO_STUDENT["email"]


# ---------------- Delete guard ----------------
class TestDeleteGuard:
    def test_delete_without_confirmed_rejected(self, super_token, mongo_db):
        user = mongo_db.users.find_one({"email": TEST_EMAIL_1})
        r = requests.delete(f"{API}/admin/participants",
                            json={"scope": "single", "user_id": user["user_id"], "confirmed": False},
                            headers=_h(super_token), timeout=30)
        assert r.status_code == 400, r.text


# ---------------- Actual deletes (single + campus) ----------------
class TestPermanentDelete:
    def test_delete_single_participant(self, super_token, mongo_db):
        user = mongo_db.users.find_one({"email": TEST_EMAIL_1})
        assert user
        uid = user["user_id"]
        # seed related data to verify cascade
        mongo_db.notifications.insert_one({"id": f"n_{uid}", "user_id": uid, "message": "t"})
        mongo_db.student_live_chat_messages.insert_one({"id": f"c_{uid}", "student_id": uid, "message": "t"})
        mongo_db.active_letter_approvals.insert_one({"id": f"a_{uid}", "user_id": uid})
        mongo_db.stage_ii_eligibilities.insert_one({"id": f"s_{uid}", "user_id": uid})
        mongo_db.campus_disbursements.insert_one({
            "id": f"cd_{uid}", "campus": TEST_CAMPUS, "recipient_user_ids": [uid, "other-keep"]
        })

        r = requests.delete(f"{API}/admin/participants",
                            json={"scope": "single", "user_id": uid, "confirmed": True},
                            headers=_h(super_token), timeout=30)
        assert r.status_code == 200, r.text
        assert r.json()["deleted_count"] == 1

        assert mongo_db.users.find_one({"user_id": uid}) is None
        assert mongo_db.profiles.find_one({"user_id": uid}) is None
        assert mongo_db.registrations.find_one({"user_id": uid}) is None
        assert mongo_db.notifications.find_one({"user_id": uid}) is None
        assert mongo_db.student_live_chat_messages.find_one({"student_id": uid}) is None
        assert mongo_db.active_letter_approvals.find_one({"user_id": uid}) is None
        assert mongo_db.stage_ii_eligibilities.find_one({"user_id": uid}) is None
        cd = mongo_db.campus_disbursements.find_one({"id": f"cd_{uid}"})
        assert cd is not None and uid not in cd.get("recipient_user_ids", [])
        # Campus master remains
        assert mongo_db.campuses.find_one({"name": TEST_CAMPUS}) is not None
        mongo_db.campus_disbursements.delete_one({"id": f"cd_{uid}"})

    def test_delete_by_campus_removes_remaining(self, super_token, mongo_db):
        user2 = mongo_db.users.find_one({"email": TEST_EMAIL_2})
        assert user2
        uid2 = user2["user_id"]
        r = requests.delete(f"{API}/admin/participants",
                            json={"scope": "campus", "campus": TEST_CAMPUS, "confirmed": True},
                            headers=_h(super_token), timeout=30)
        assert r.status_code == 200, r.text
        assert r.json()["deleted_count"] >= 1
        assert mongo_db.users.find_one({"user_id": uid2}) is None
        # Master campus is NOT deleted by participant deletion
        assert mongo_db.campuses.find_one({"name": TEST_CAMPUS}) is not None

    def test_delete_no_targets_returns_404(self, super_token):
        r = requests.delete(f"{API}/admin/participants",
                            json={"scope": "single", "user_id": f"nonexistent_{RUN_TAG}",
                                  "confirmed": True},
                            headers=_h(super_token), timeout=30)
        assert r.status_code == 404, r.text
