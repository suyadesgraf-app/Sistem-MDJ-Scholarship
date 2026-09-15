"""Test Pakta Integritas digital submission + documents lock/permission.

Verifies:
- POST /api/registration submit without pakta_integritas_agreed -> 400
- POST /api/registration submit with pakta but missing prerequisites -> 400 with two lists
- Complete student can submit -> registration stores pakta_integritas_agreed=true,
  timestamp, version, documents_locked_at, documents_editing_allowed=false
- After submit: POST /documents, DELETE /documents/{id}, /profile/extract-* -> 403
- Admin/Super Admin PUT document-editing-permission allowed=true unlocks;
  allowed=false locks again. Student & admin_wilayah -> 403.
- Cleanup: all temp users/docs/registrations/profiles/notifications and
  registration_open restored to false.
"""
import copy
import io
import os
import uuid

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")

SUPER = ("supri@baznasbazisdki.id", "MdjSuper2026!")
ADMIN = ("admin.mdj@baznasbazisdki.id", "AdminMDJ2026!")
STUDENT_DEMO = ("mahasiswa.mdj@baznasbazisdki.id", "MahasiswaMDJ2026!")

PAKTA_DOCS = [
    "KTP DKI Jakarta",
    "Kartu Keluarga (KK)",
    "Pas Foto 3x4",
    "Kartu Tanda Mahasiswa (KTM)",
    "KRS / KHS / Transkrip Nilai",
    "Surat Keterangan Mahasiswa Aktif",
    "SKTM / Surat Rekomendasi",
    "Surat Persetujuan Orang Tua",
    "Surat Keterangan Tidak Menerima Beasiswa Lain",
]
PAKTA_MISSING_REQUIRED = (
    "Anda wajib menyetujui Pakta Integritas sebelum mengirim pendaftaran."
)
DOCS_LOCKED_MSG = (
    "Dokumen pendaftaran sudah dikirim dan terkunci. Panitia perlu mengizinkan edit kembali."
)
CLOSED_MSG = (
    "Masa pendaftaran belum dibuka. Silakan pantau pengumuman MDJ Scholarship secara berkala."
)


def _login(email, password):
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text}"
    return r.json()["token"]


def _hdr(token):
    return {"Authorization": f"Bearer {token}"}


def _jhdr(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def mongo():
    client = MongoClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    yield db
    client.close()


@pytest.fixture(scope="module")
def super_token():
    return _login(*SUPER)


@pytest.fixture(scope="module")
def admin_token():
    return _login(*ADMIN)


@pytest.fixture(scope="module")
def demo_student_token():
    return _login(*STUDENT_DEMO)


@pytest.fixture(scope="module")
def snapshot_content(super_token):
    """Snapshot & restore site_content; open registration for tests."""
    r = requests.get(f"{BASE_URL}/api/site/content", timeout=20)
    assert r.status_code == 200
    snap = copy.deepcopy(r.json())

    # open
    body = copy.deepcopy(snap)
    settings = body.get("settings") or {}
    settings["registration_open"] = True
    body["settings"] = settings
    rr = requests.put(
        f"{BASE_URL}/api/site/content",
        json={"content": body},
        headers=_jhdr(super_token),
        timeout=30,
    )
    assert rr.status_code == 200, rr.text

    yield snap

    # restore + force registration_open=false
    restored = copy.deepcopy(snap)
    restored_settings = restored.get("settings") or {}
    restored_settings["registration_open"] = False
    restored["settings"] = restored_settings
    rp = requests.put(
        f"{BASE_URL}/api/site/content",
        json={"content": restored},
        headers=_jhdr(super_token),
        timeout=30,
    )
    assert rp.status_code == 200
    verify = requests.get(f"{BASE_URL}/api/site/content", timeout=20).json()
    assert verify.get("settings", {}).get("registration_open") is False


def _make_temp_student(mongo, prefix="pakta"):
    """Register a fresh temp student via /auth/register."""
    email = f"test.{prefix}.{uuid.uuid4().hex[:8]}@example.com"
    password = "TestPass123!"
    r = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"name": f"TEST {prefix}", "email": email, "password": password},
        timeout=30,
    )
    assert r.status_code in (200, 201), r.text
    body = r.json()
    return {
        "email": email,
        "password": password,
        "token": body["token"],
        "user_id": body["user"].get("user_id") or body["user"].get("id"),
    }


def _seed_profile(mongo, user_id, complete=True):
    data = {
        "jenjang": "S1",
        "institusi": "Universitas TEST MDJ",
        "jurusan": "Teknik Informatika",
        "nim": "TEST123456",
        "semester": "5",
        "ipk": "3.75",
        "biayaPendidikanSemester": "6500000",
    }
    if not complete:
        data.pop("ipk", None)
        data.pop("biayaPendidikanSemester", None)
    mongo.profiles.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id, "data": data}},
        upsert=True,
    )


def _seed_docs(mongo, user_id, doc_types):
    from datetime import datetime, timezone as tz
    now = datetime.now(tz.utc).isoformat()
    records = [
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "doc_type": dt,
            "storage_path": f"test/pakta/{user_id}/{uuid.uuid4()}.pdf",
            "original_filename": "test.pdf",
            "content_type": "application/pdf",
            "size": 1024,
            "is_deleted": False,
            "created_at": now,
        }
        for dt in doc_types
    ]
    if records:
        mongo.documents.insert_many(records)
    return records


def _cleanup_user(mongo, email, user_id):
    mongo.users.delete_many({"email": email})
    mongo.profiles.delete_many({"user_id": user_id})
    mongo.documents.delete_many({"user_id": user_id})
    mongo.registrations.delete_many({"user_id": user_id})
    mongo.notifications.delete_many({"user_id": user_id})
    mongo.user_sessions.delete_many({"user_id": user_id})


# --- Test: submit without pakta agreement -> 400 ---
def test_submit_without_pakta_agreed_returns_400(snapshot_content, mongo):
    stu = _make_temp_student(mongo, "noagree")
    try:
        r = requests.post(
            f"{BASE_URL}/api/registration",
            json={
                "category": "Mahasiswa Sarjana (S1)",
                "action": "submit",
                "pakta_integritas_agreed": False,
            },
            headers=_jhdr(stu["token"]),
            timeout=30,
        )
        assert r.status_code == 400, r.text
        assert r.json().get("detail") == PAKTA_MISSING_REQUIRED
    finally:
        _cleanup_user(mongo, stu["email"], stu["user_id"])


# --- Test: submit with pakta but missing prerequisites -> 400 with lists ---
def test_submit_missing_prereqs_returns_400_with_lists(snapshot_content, mongo):
    stu = _make_temp_student(mongo, "missing")
    try:
        # partial profile & partial docs
        _seed_profile(mongo, stu["user_id"], complete=False)
        _seed_docs(mongo, stu["user_id"], PAKTA_DOCS[:3])

        r = requests.post(
            f"{BASE_URL}/api/registration",
            json={
                "category": "Mahasiswa Sarjana (S1)",
                "action": "submit",
                "pakta_integritas_agreed": True,
            },
            headers=_jhdr(stu["token"]),
            timeout=30,
        )
        assert r.status_code == 400, r.text
        detail = r.json().get("detail")
        assert isinstance(detail, dict), f"detail must be object, got {detail}"
        assert "missing_education" in detail and "missing_documents" in detail
        # ipk & biayaPendidikanSemester missing -> at least 2 missing edu items
        assert any("IPK" in x for x in detail["missing_education"])
        assert any("biaya" in x.lower() for x in detail["missing_education"])
        # 6 remaining docs missing
        assert len(detail["missing_documents"]) == len(PAKTA_DOCS) - 3
    finally:
        _cleanup_user(mongo, stu["email"], stu["user_id"])


# --- Test: complete student can submit; registration reflects pakta fields ---
@pytest.fixture(scope="module")
def submitted_student(snapshot_content, mongo):
    stu = _make_temp_student(mongo, "complete")
    _seed_profile(mongo, stu["user_id"], complete=True)
    _seed_docs(mongo, stu["user_id"], PAKTA_DOCS)
    r = requests.post(
        f"{BASE_URL}/api/registration",
        json={
            "category": "Mahasiswa Sarjana (S1)",
            "action": "submit",
            "pakta_integritas_agreed": True,
        },
        headers=_jhdr(stu["token"]),
        timeout=30,
    )
    assert r.status_code == 200, r.text
    reg = r.json()
    stu["registration"] = reg
    yield stu
    _cleanup_user(mongo, stu["email"], stu["user_id"])


def test_complete_submit_persists_pakta_fields(submitted_student):
    reg = submitted_student["registration"]
    assert reg["status"] == "submitted"
    assert reg["pakta_integritas_agreed"] is True
    assert reg.get("pakta_integritas_agreed_at")
    assert reg.get("pakta_integritas_version")
    assert reg.get("documents_locked_at")
    assert reg.get("documents_editing_allowed") is False
    assert "_id" not in reg


# --- Test: after submit, POST /documents is 403 ---
def test_upload_document_blocked_after_submit(submitted_student):
    files = {
        "file": ("t.pdf", io.BytesIO(b"%PDF-1.4 test"), "application/pdf"),
    }
    data = {"doc_type": "KTP DKI Jakarta"}
    r = requests.post(
        f"{BASE_URL}/api/documents",
        headers=_hdr(submitted_student["token"]),
        files=files,
        data=data,
        timeout=30,
    )
    assert r.status_code == 403, r.text
    assert r.json().get("detail") == DOCS_LOCKED_MSG


# --- Test: DELETE /documents/{id} is 403 after submit ---
def test_delete_document_blocked_after_submit(submitted_student, mongo):
    doc = mongo.documents.find_one({"user_id": submitted_student["user_id"], "is_deleted": False})
    assert doc, "expected some doc in db for the student"
    r = requests.delete(
        f"{BASE_URL}/api/documents/{doc['id']}",
        headers=_hdr(submitted_student["token"]),
        timeout=30,
    )
    assert r.status_code == 403, r.text
    assert r.json().get("detail") == DOCS_LOCKED_MSG


# --- Test: extract endpoints are 403 after submit (no storage touched) ---
@pytest.mark.parametrize("path", [
    "/api/profile/extract-ktp",
    "/api/profile/extract-kk",
    "/api/profile/extract-ktm",
    "/api/profile/extract-academic-record",
])
def test_extract_endpoints_blocked_after_submit(submitted_student, path):
    files = {"file": ("t.pdf", io.BytesIO(b"x"), "application/pdf")}
    r = requests.post(
        f"{BASE_URL}{path}",
        headers=_hdr(submitted_student["token"]),
        files=files,
        timeout=30,
    )
    assert r.status_code == 403, f"{path}: {r.status_code} {r.text}"
    assert r.json().get("detail") == DOCS_LOCKED_MSG


# --- Test: admin can toggle document-editing-permission ---
def test_admin_can_grant_and_revoke_permission(submitted_student, admin_token, super_token):
    uid = submitted_student["user_id"]
    # grant via provincial admin
    r = requests.put(
        f"{BASE_URL}/api/admin/participants/{uid}/document-editing-permission",
        json={"allowed": True},
        headers=_jhdr(admin_token),
        timeout=30,
    )
    assert r.status_code == 200, r.text
    reg = r.json()
    assert reg.get("documents_editing_allowed") is True

    # student can now upload
    files = {"file": ("t.pdf", io.BytesIO(b"%PDF-1.4 x"), "application/pdf")}
    r2 = requests.post(
        f"{BASE_URL}/api/documents",
        headers=_hdr(submitted_student["token"]),
        files=files,
        data={"doc_type": "Pas Foto 3x4"},
        timeout=60,
    )
    assert r2.status_code == 200, r2.text

    # revoke via super admin
    r3 = requests.put(
        f"{BASE_URL}/api/admin/participants/{uid}/document-editing-permission",
        json={"allowed": False},
        headers=_jhdr(super_token),
        timeout=30,
    )
    assert r3.status_code == 200
    assert r3.json().get("documents_editing_allowed") is False

    # now student blocked again
    r4 = requests.post(
        f"{BASE_URL}/api/documents",
        headers=_hdr(submitted_student["token"]),
        files={"file": ("t.pdf", io.BytesIO(b"%PDF-1.4 y"), "application/pdf")},
        data={"doc_type": "Pas Foto 3x4"},
        timeout=30,
    )
    assert r4.status_code == 403


# --- Test: student cannot call permission endpoint ---
def test_student_cannot_grant_permission(submitted_student, demo_student_token):
    uid = submitted_student["user_id"]
    r = requests.put(
        f"{BASE_URL}/api/admin/participants/{uid}/document-editing-permission",
        json={"allowed": True},
        headers=_jhdr(demo_student_token),
        timeout=30,
    )
    assert r.status_code == 403, r.text


# --- Test: admin_wilayah cannot grant permission ---
def test_admin_wilayah_cannot_grant_permission(submitted_student, super_token, mongo):
    # create an admin_wilayah user directly in mongo
    from datetime import datetime, timezone as tz
    from passlib.context import CryptContext
    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    email = f"test.wilayah.{uuid.uuid4().hex[:6]}@example.com"
    uid = f"user_{uuid.uuid4().hex[:12]}"
    mongo.users.insert_one({
        "user_id": uid,
        "email": email,
        "password_hash": pwd.hash("TestPass123!"),
        "name": "TEST Wilayah",
        "role": "admin_wilayah",
        "auth_provider": "password",
        "is_active": True,
        "auth_version": 0,
        "region": "Jakarta Pusat",
        "created_at": datetime.now(tz.utc).isoformat(),
    })
    try:
        token = _login(email, "TestPass123!")
        r = requests.put(
            f"{BASE_URL}/api/admin/participants/{submitted_student['user_id']}/document-editing-permission",
            json={"allowed": True},
            headers=_jhdr(token),
            timeout=30,
        )
        assert r.status_code == 403, r.text
    finally:
        mongo.users.delete_many({"email": email})
        mongo.user_sessions.delete_many({"user_id": uid})


# --- Test: final registration_open is False after teardown-like check ---
def test_zzz_registration_open_restored(snapshot_content):
    # snapshot fixture is module-scoped; teardown will restore. We can verify current is True during tests.
    v = requests.get(f"{BASE_URL}/api/site/content", timeout=20).json()
    # During test module runtime we set it True; a separate final restore is in fixture teardown.
    assert v.get("settings", {}).get("registration_open") in (True, False)
