"""Validation tests for user-requested TEST batch PDF-JB-TAHAP1-2026.

Verifies imported Jakarta Barat Stage-I Sudah Dicairkan test data:
  * users/profiles/registrations count & fields
  * campus_disbursements per campus (stage 1 sudah_dicairkan, no stage 2)
  * API /admin/disbursements/campuses filtered by region=Jakarta Barat
  * NIM remains blank on every profile
  * Test-batch marker (test_batch_id, is_test_data) present everywhere
  * Demo/other-region data not altered
  * Admin Wilayah scope returns only Jakarta Barat
"""
import os
import uuid
import hashlib
import bcrypt
import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
BATCH_ID = "PDF-JB-TAHAP1-2026"
REGION = "Jakarta Barat"


# ---------------------------------------------------------------- fixtures
@pytest.fixture(scope="module")
def db():
    return MongoClient(MONGO_URL)[DB_NAME]


@pytest.fixture(scope="module")
def super_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "supri@baznasbazisdki.id",
        "password": "MdjSuper2026!",
    })
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_wilayah_token(db):
    """Seed a temporary admin_wilayah for Jakarta Barat then delete afterwards."""
    email = f"test_aw_jb_{uuid.uuid4().hex[:6]}@example.invalid"
    password = "AdminWilayahJB2026!"
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user_id = f"test_aw_{uuid.uuid4().hex[:12]}"
    db.users.insert_one({
        "user_id": user_id,
        "email": email,
        "name": "TEST Admin Wilayah JB",
        "role": "admin_wilayah",
        "region": REGION,
        "password_hash": hashed,
        "auth_provider": "password",
        "is_active": True,
        "auth_version": 0,
    })
    try:
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": email, "password": password,
        })
        assert r.status_code == 200, r.text
        yield r.json()["token"]
    finally:
        db.users.delete_one({"user_id": user_id})


# ---------------------------------------------------------------- DB truths
class TestBatchPersistence:
    def test_users_count_and_fields(self, db):
        users = list(db.users.find({"test_batch_id": BATCH_ID}))
        assert len(users) == 459
        for u in users:
            assert u["role"] == "student"
            assert u.get("is_test_data") is True
            assert u["email"].startswith("test_jb_")
            assert u.get("is_active") is False  # test accounts inactive

    def test_registrations_count_and_status(self, db):
        regs = list(db.registrations.find({"test_batch_id": BATCH_ID}))
        assert len(regs) == 459
        for r in regs:
            assert r["status"] == "lolos"
            assert r.get("is_test_data") is True
            assert r["user_id"].startswith("test_jb_")

    def test_profiles_all_jakarta_barat_and_blank_nim(self, db):
        profs = list(db.profiles.find({"data.test_batch_id": BATCH_ID}))
        assert len(profs) == 459
        for p in profs:
            data = p.get("data", {})
            assert data.get("kota") == REGION, f"non-JB profile: {data.get('kota')}"
            assert data.get("nim", "") == "", f"NIM should be blank, got {data.get('nim')!r}"
            assert data.get("institusi"), "campus (institusi) must be present"

    def test_campus_disbursements_stage_and_status(self, db):
        rows = list(db.campus_disbursements.find({"test_batch_id": BATCH_ID}))
        assert len(rows) == 84
        for cd in rows:
            assert cd["region"] == REGION
            assert cd["stage"] == 1
            assert cd["status"] == "sudah_dicairkan"

    def test_no_stage_two_for_batch(self, db):
        assert db.campus_disbursements.count_documents(
            {"test_batch_id": BATCH_ID, "stage": 2}
        ) == 0

    def test_no_other_region_touched(self, db):
        assert db.profiles.count_documents(
            {"data.test_batch_id": BATCH_ID, "data.kota": {"$ne": REGION}}
        ) == 0

    def test_demo_accounts_intact(self, db):
        for email, role in [
            ("supri@baznasbazisdki.id", "super_admin"),
            ("admin.mdj@baznasbazisdki.id", "admin"),
            ("mahasiswa.mdj@baznasbazisdki.id", "student"),
        ]:
            u = db.users.find_one({"email": email})
            assert u is not None, f"demo account {email} missing"
            assert u["role"] == role
            assert u.get("test_batch_id") != BATCH_ID


# ------------------------------------------------------------ super admin API
class TestSuperAdminAPI:
    def test_list_campuses_jakarta_barat(self, super_token):
        r = requests.get(
            f"{BASE_URL}/api/admin/disbursements/campuses?region={REGION}",
            headers={"Authorization": f"Bearer {super_token}"},
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 84, f"expected 84 campuses, got {len(data)}"
        total = sum(c["recipient_count"] for c in data)
        assert total == 459, f"expected 459 recipients, got {total}"
        # every campus purely Jakarta Barat
        for c in data:
            assert c["regions"] == [REGION]

    def test_every_stage_one_is_sudah_dicairkan(self, super_token):
        """User requested ALL Stage-I marked Sudah Dicairkan."""
        r = requests.get(
            f"{BASE_URL}/api/admin/disbursements/campuses?region={REGION}",
            headers={"Authorization": f"Bearer {super_token}"},
        )
        data = r.json()
        not_paid = [
            (c["campus"], c["recipient_count"],
             c.get("stage_one", {}).get("status"))
            for c in data
            if c.get("stage_one", {}).get("status") != "sudah_dicairkan"
        ]
        assert not not_paid, (
            f"{len(not_paid)} campuses NOT marked sudah_dicairkan "
            f"(user requested ALL): {not_paid[:5]}"
        )

    def test_stage_two_belum_diproses_for_all(self, super_token):
        r = requests.get(
            f"{BASE_URL}/api/admin/disbursements/campuses?region={REGION}",
            headers={"Authorization": f"Bearer {super_token}"},
        )
        for c in r.json():
            assert c["stage_two"]["status"] in {"belum_diproses", None}, \
                f"unexpected stage2 status for {c['campus']}: {c['stage_two']}"

    def test_students_have_blank_nim_via_campus_detail(self, super_token):
        # take campus_keys from the list API so we know they resolve
        r = requests.get(
            f"{BASE_URL}/api/admin/disbursements/campuses?region={REGION}",
            headers={"Authorization": f"Bearer {super_token}"},
        )
        for c in r.json()[:5]:
            resp = requests.get(
                f"{BASE_URL}/api/admin/disbursements/campuses/{c['campus_key']}",
                headers={"Authorization": f"Bearer {super_token}"},
            )
            assert resp.status_code == 200, resp.text
            detail = resp.json()
            for reg in detail.get("regions", []):
                assert reg["region"] == REGION
                for s in reg.get("recipients", []):
                    nim = s.get("nim", "")
                    assert nim in ("", "-", None), \
                        f"expected blank NIM, got {nim!r}"


# ---------------------------------------------------------- admin wilayah
class TestAdminWilayahScope:
    def test_admin_wilayah_sees_only_jakarta_barat(self, admin_wilayah_token):
        r = requests.get(
            f"{BASE_URL}/api/admin/disbursements/campuses",
            headers={"Authorization": f"Bearer {admin_wilayah_token}"},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert len(data) >= 1
        for c in data:
            assert c["regions"] == [REGION], f"leak: {c['regions']}"
        total = sum(c["recipient_count"] for c in data)
        assert total == 459

    def test_admin_wilayah_cannot_update_stage(self, admin_wilayah_token, super_token):
        # take a resolvable campus_key from the list API
        r = requests.get(
            f"{BASE_URL}/api/admin/disbursements/campuses?region={REGION}",
            headers={"Authorization": f"Bearer {super_token}"},
        )
        campus_key = r.json()[0]["campus_key"]
        url = (f"{BASE_URL}/api/admin/disbursements/campuses/"
               f"{campus_key}/regions/{REGION}/stages/1")
        r2 = requests.put(
            url,
            headers={"Authorization": f"Bearer {admin_wilayah_token}"},
            json={"status": "belum_diproses"},
        )
        # read-only expectation
        assert r2.status_code in (401, 403), \
            f"admin_wilayah should not update stage, got {r2.status_code}"
