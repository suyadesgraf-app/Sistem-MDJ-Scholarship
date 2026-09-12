"""
Backend tests for AI Administrative Verification.
Tests: generate, list, approve endpoints + RBAC + candidate scoring.

Uses direct pymongo seeding to create controlled test candidates (TEST_ prefix)
and cleans up all test-created data after the module runs.
"""
import os
import uuid
import time
from datetime import datetime, timezone

import pytest
import requests
from pymongo import MongoClient

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://sistem-registrasi.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

ADMIN_EMAIL = "admin.mdj@baznasbazisdki.id"
ADMIN_PASS = "AdminMDJ2026!"
SUPER_EMAIL = "supri@baznasbazisdki.id"
SUPER_PASS = "MdjSuper2026!"
STUDENT_EMAIL = "mahasiswa.mdj@baznasbazisdki.id"
STUDENT_PASS = "MahasiswaMDJ2026!"

REQUIRED_DOCS = [
    "KTP DKI Jakarta",
    "Kartu Keluarga (KK)",
    "Pas Foto 3x4",
    "Kartu Tanda Mahasiswa (KTM)",
    "KRS / KHS / Transkrip Nilai",
    "Surat Keterangan Mahasiswa Aktif",
    "SKTM / Surat Rekomendasi",
    "Surat Persetujuan Orang Tua",
    "Surat Keterangan Tidak Menerima Beasiswa Lain",
    "Pakta Integritas",
]

CAMPUS_NAME = "Universitas TEST AI Verifikasi"

_client = MongoClient(MONGO_URL)
_db = _client[DB_NAME]

TEST_TAG = "TEST_ai_verif"
_test_user_ids = []
_test_campus_id = None
_test_recommendation_ids = []


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    return r.json()["token"]


def _hdr(token):
    return {"Authorization": f"Bearer {token}"}


def _full_profile(email, nim):
    return {
        "namaLengkap": "TEST_ai_verif Peserta Lengkap",
        "email": email,
        "nik": "3171234567890123",
        "noTelp": "081234567890",
        "alamatLengkap": "Jl. Test AI Verifikasi No. 1",
        "kota": "Jakarta Selatan",
        "provinsi": "DKI Jakarta",
        "institusi": CAMPUS_NAME,
        "nim": nim,
        "jenjang": "S1",
        "jurusan": "Teknik Informatika",
        "semester": "5",
        "ipk": "3.75",
        "biayaPendidikanSemester": "6000000",
    }


def _seed_candidate(*, complete: bool, index: int):
    """Insert a user + profile + docs + registration for AI verification tests."""
    user_id = f"user_TESTaiv_{uuid.uuid4().hex[:10]}"
    email = f"TEST_aiv_{index}_{uuid.uuid4().hex[:6]}@contoh.invalid"
    now = datetime.now(timezone.utc).isoformat()

    _db.users.insert_one({
        "user_id": user_id,
        "email": email,
        "name": f"TEST_ai_verif Peserta {index}",
        "role": "student",
        "auth_provider": "password",
        "password_hash": "$2b$12$0000000000000000000000000000000000000000000000000000",
        "is_active": True,
        "created_at": now,
        "test_tag": TEST_TAG,
    })

    if complete:
        data = _full_profile(email, f"NIM{index:08d}")
    else:
        data = _full_profile(email, f"NIM{index:08d}")
        data["nik"] = "123"  # invalid NIK
        data["ipk"] = ""     # missing IPK
        data["biayaPendidikanSemester"] = ""

    _db.profiles.insert_one({
        "user_id": user_id,
        "data": data,
        "updated_at": now,
        "test_tag": TEST_TAG,
    })

    doc_types = REQUIRED_DOCS if complete else REQUIRED_DOCS[:6]
    for dt in doc_types:
        _db.documents.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "doc_type": dt,
            "file_path": f"test/{user_id}/{dt}.pdf",
            "uploaded_at": now,
            "is_deleted": False,
            "test_tag": TEST_TAG,
        })

    cpm_id = f"CPM-MDJ/2026/{9000 + index:06d}"
    _db.registrations.insert_one({
        "user_id": user_id,
        "name": data["namaLengkap"],
        "email": email,
        "cpm_id": cpm_id,
        "status": "submitted",
        "created_at": now,
        "updated_at": now,
        "history": [{"status": "submitted", "at": now}],
        "test_tag": TEST_TAG,
    })

    _test_user_ids.append(user_id)
    return user_id, cpm_id


@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown():
    global _test_campus_id
    # Ensure campus master has entry with our test campus name
    existing = _db.campuses.find_one({"name": CAMPUS_NAME})
    if not existing:
        _test_campus_id = str(uuid.uuid4())
        _db.campuses.insert_one({
            "id": _test_campus_id,
            "name": CAMPUS_NAME,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "test_tag": TEST_TAG,
        })

    # Seed two candidates: one complete, one incomplete
    u1, cpm1 = _seed_candidate(complete=True, index=1)
    u2, cpm2 = _seed_candidate(complete=False, index=2)
    u3, cpm3 = _seed_candidate(complete=True, index=3)

    pytest.candidate_complete_1 = u1
    pytest.candidate_complete_1_cpm = cpm1
    pytest.candidate_incomplete = u2
    pytest.candidate_complete_2 = u3
    pytest.candidate_complete_2_cpm = cpm3

    yield

    # Cleanup
    _db.users.delete_many({"user_id": {"$in": _test_user_ids}})
    _db.profiles.delete_many({"user_id": {"$in": _test_user_ids}})
    _db.documents.delete_many({"user_id": {"$in": _test_user_ids}})
    _db.registrations.delete_many({"user_id": {"$in": _test_user_ids}})
    _db.verification_recommendations.delete_many({"user_id": {"$in": _test_user_ids}})
    _db.notifications.delete_many({"user_id": {"$in": _test_user_ids}})
    if _test_campus_id:
        _db.campuses.delete_one({"id": _test_campus_id})


# ---------------- Tests ----------------

def test_student_rbac_forbidden():
    token = _login(STUDENT_EMAIL, STUDENT_PASS)
    r1 = requests.get(f"{API}/admin/verification-recommendations", headers=_hdr(token), timeout=30)
    r2 = requests.post(f"{API}/admin/verification-recommendations/generate", headers=_hdr(token), timeout=30)
    r3 = requests.post(
        f"{API}/admin/verification-recommendations/approve",
        headers=_hdr(token),
        json={"approve_all": True},
        timeout=30,
    )
    assert r1.status_code == 403
    assert r2.status_code == 403
    assert r3.status_code == 403


def test_admin_generate_lists_recommendations():
    token = _login(ADMIN_EMAIL, ADMIN_PASS)
    r = requests.post(
        f"{API}/admin/verification-recommendations/generate",
        headers=_hdr(token),
        timeout=180,  # AI may be slow
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] >= 3
    # Recommended count must be >= 2 (our two complete candidates)
    assert body["recommended"] >= 2
    assert body["review"] >= 1

    lst = requests.get(f"{API}/admin/verification-recommendations", headers=_hdr(token), timeout=30)
    assert lst.status_code == 200
    items = lst.json()
    by_user = {i["user_id"]: i for i in items}

    c1 = by_user.get(pytest.candidate_complete_1)
    assert c1 is not None, "Complete candidate 1 not present in list"
    assert c1["recommendation"] == "recommended"
    assert c1["approval_status"] == "pending"
    assert c1["document_count"] == 10
    assert c1["cpm_id"] == pytest.candidate_complete_1_cpm

    inc = by_user.get(pytest.candidate_incomplete)
    assert inc is not None
    assert inc["recommendation"] == "review"
    assert inc["approval_status"] == "pending"
    assert isinstance(inc["issues"], list) and len(inc["issues"]) > 0

    # Confirm registration statuses did not change
    reg_inc = _db.registrations.find_one({"user_id": pytest.candidate_incomplete})
    assert reg_inc["status"] == "submitted"


def test_approve_selected_only_changes_chosen():
    token = _login(ADMIN_EMAIL, ADMIN_PASS)
    rec = _db.verification_recommendations.find_one({"user_id": pytest.candidate_complete_1})
    assert rec and rec["recommendation"] == "recommended"

    r = requests.post(
        f"{API}/admin/verification-recommendations/approve",
        headers=_hdr(token),
        json={"recommendation_ids": [rec["id"]], "approve_all": False},
        timeout=60,
    )
    assert r.status_code == 200, r.text
    assert r.json()["approved"] == 1

    # Chosen candidate registration should be updated
    reg1 = _db.registrations.find_one({"user_id": pytest.candidate_complete_1})
    assert reg1["status"] == "lolos_administrasi"

    # Recommendation approved status
    rec1 = _db.verification_recommendations.find_one({"user_id": pytest.candidate_complete_1})
    assert rec1["approval_status"] == "approved"

    # Other candidate 2 must remain untouched
    reg2 = _db.registrations.find_one({"user_id": pytest.candidate_complete_2})
    assert reg2["status"] == "submitted"

    # Notification created
    notif = _db.notifications.find_one({
        "user_id": pytest.candidate_complete_1,
        "type": "selection_progress",
    })
    assert notif is not None


def test_approve_all_updates_remaining_recommended():
    token = _login(ADMIN_EMAIL, ADMIN_PASS)
    r = requests.post(
        f"{API}/admin/verification-recommendations/approve",
        headers=_hdr(token),
        json={"approve_all": True},
        timeout=120,
    )
    assert r.status_code == 200, r.text
    # Candidate 2 should now be approved
    reg2 = _db.registrations.find_one({"user_id": pytest.candidate_complete_2})
    assert reg2["status"] == "lolos_administrasi"

    # Incomplete candidate must NOT change
    reg_inc = _db.registrations.find_one({"user_id": pytest.candidate_incomplete})
    assert reg_inc["status"] == "submitted"


def test_approve_requires_selection():
    token = _login(ADMIN_EMAIL, ADMIN_PASS)
    r = requests.post(
        f"{API}/admin/verification-recommendations/approve",
        headers=_hdr(token),
        json={"recommendation_ids": [], "approve_all": False},
        timeout=30,
    )
    assert r.status_code == 400


def test_super_admin_can_list():
    token = _login(SUPER_EMAIL, SUPER_PASS)
    r = requests.get(f"{API}/admin/verification-recommendations", headers=_hdr(token), timeout=30)
    assert r.status_code == 200
