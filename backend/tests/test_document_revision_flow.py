"""Test document revision (Kembalikan untuk Dilengkapi) flow.

Coverage:
1. Admin/Super Admin POST /admin/participants/{uid}/return-documents:
   - uses one common reason without a request body
   - submitted registration -> 200 with status=perlu_perbaikan,
     revision_requested=True, documents_editing_allowed=True, revision_note stored,
     history/audit push, notification document_revision_requested with revision_note.
2. Student GET /api/student/document-revisions/pending returns that notification
   (only unseen). POST /seen marks is_read + is_popup_seen. Second GET returns null.
3. During active revision: POST /documents and DELETE /documents/{id} succeed (200).
4. Student POST /api/registration action=submit while registration_open=False for a
   student with revision_requested=True -> 200 (resubmission bypass). Reg becomes
   status=submitted, documents_editing_allowed=False, revision_requested=False,
   revision_resubmitted_at set. Follow-up POST /documents -> 403.
5. Admin who requested revision receives document_revision_resubmitted notification.
6. Student and admin_wilayah receive 403 for return-documents. Legacy
   document-editing-permission allowed=True is rejected (>=400) to guarantee the
   common return flow cannot be bypassed.
7. Cleanup: all temp users/docs/registrations/profiles/notifications; restore
   registration_open=False.
"""
import copy
import io
import os
import time
import uuid
from datetime import datetime, timezone as tz

import pytest
import requests
from dotenv import load_dotenv
from passlib.context import CryptContext
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


def _hdr(t):
    return {"Authorization": f"Bearer {t}"}


def _jhdr(t):
    return {"Authorization": f"Bearer {t}", "Content-Type": "application/json"}


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


def _set_registration_open(super_token, value: bool):
    r = requests.get(f"{BASE_URL}/api/site/content", timeout=20)
    assert r.status_code == 200
    body = copy.deepcopy(r.json())
    settings = body.get("settings") or {}
    settings["registration_open"] = value
    body["settings"] = settings
    rr = requests.put(
        f"{BASE_URL}/api/site/content",
        json={"content": body},
        headers=_jhdr(super_token),
        timeout=30,
    )
    assert rr.status_code == 200, rr.text


@pytest.fixture(scope="module")
def registration_open_snapshot(super_token):
    """Open registration during tests; force close on teardown."""
    r = requests.get(f"{BASE_URL}/api/site/content", timeout=20)
    assert r.status_code == 200
    snap = copy.deepcopy(r.json())
    _set_registration_open(super_token, True)
    yield snap
    _set_registration_open(super_token, False)
    verify = requests.get(f"{BASE_URL}/api/site/content", timeout=20).json()
    assert verify.get("settings", {}).get("registration_open") is False


def _make_temp_student(prefix="rev"):
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


def _seed_profile(mongo, user_id):
    mongo.profiles.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id, "data": {
            "jenjang": "S1",
            "institusi": "Universitas TEST MDJ",
            "jurusan": "Teknik Informatika",
            "nim": "TEST123456",
            "semester": "5",
            "ipk": "3.75",
            "biayaPendidikanSemester": "6500000",
        }}},
        upsert=True,
    )


def _seed_docs(mongo, user_id, doc_types):
    now = datetime.now(tz.utc).isoformat()
    records = [
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "doc_type": dt,
            "storage_path": f"test/rev/{user_id}/{uuid.uuid4()}.pdf",
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


def _cleanup_user(mongo, email, user_id):
    mongo.users.delete_many({"email": email})
    mongo.profiles.delete_many({"user_id": user_id})
    mongo.documents.delete_many({"user_id": user_id})
    mongo.registrations.delete_many({"user_id": user_id})
    mongo.notifications.delete_many({"user_id": user_id})
    mongo.user_sessions.delete_many({"user_id": user_id})


# Shared module-level submitted student
@pytest.fixture(scope="module")
def submitted_stu(registration_open_snapshot, mongo):
    stu = _make_temp_student("submit")
    _seed_profile(mongo, stu["user_id"])
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
    stu["registration"] = r.json()
    yield stu
    _cleanup_user(mongo, stu["email"], stu["user_id"])


# --- 1. return-documents by admin uses common reason and notifies student ---
def test_return_documents_success_persists_and_notifies(submitted_stu, admin_token, mongo):
    uid = submitted_stu["user_id"]
    note = "Mohon lengkapi dan perbaiki data serta dokumen pendaftaran Anda dengan benar."
    r = requests.post(
        f"{BASE_URL}/api/admin/participants/{uid}/return-documents",
        headers=_jhdr(admin_token),
        timeout=30,
    )
    assert r.status_code == 200, r.text
    reg = r.json()
    assert "_id" not in reg
    assert reg["status"] == "perlu_perbaikan"
    assert reg.get("revision_requested") is True
    assert reg.get("documents_editing_allowed") is True
    assert reg.get("revision_note") == note
    assert reg.get("revision_requested_by_user_id")
    # history contains audit entry
    assert any(h.get("status") == "perlu_perbaikan" and h.get("note") == note
               for h in reg.get("history", []))

    # notification created (no _id)
    notif = mongo.notifications.find_one(
        {"user_id": uid, "type": "document_revision_requested"},
        sort=[("created_at", -1)],
    )
    assert notif is not None
    # metadata dict is merged at top-level in create_notification (see server.py)
    assert notif.get("revision_note") == note
    assert note in notif.get("message", "")


# --- 2. Student pending revision GET + seen POST ---
def test_pending_revision_visible_and_seen(submitted_stu, mongo):
    r = requests.get(
        f"{BASE_URL}/api/student/document-revisions/pending",
        headers=_hdr(submitted_stu["token"]),
        timeout=20,
    )
    assert r.status_code == 200, r.text
    payload = r.json()
    revision = payload.get("revision")
    assert revision is not None, "expected pending revision"
    assert "_id" not in revision
    notif_id = revision["id"]
    assert revision.get("revision_note")

    # mark seen
    s = requests.post(
        f"{BASE_URL}/api/student/document-revisions/{notif_id}/seen",
        headers=_hdr(submitted_stu["token"]),
        timeout=20,
    )
    assert s.status_code == 200, s.text

    # second GET should now be null
    r2 = requests.get(
        f"{BASE_URL}/api/student/document-revisions/pending",
        headers=_hdr(submitted_stu["token"]),
        timeout=20,
    )
    assert r2.status_code == 200
    assert r2.json().get("revision") is None

    # notification in Mongo has is_popup_seen & is_read
    doc = mongo.notifications.find_one({"id": notif_id})
    assert doc.get("is_popup_seen") is True
    assert doc.get("is_read") is True


# --- 3. During revision student can upload & delete document ---
def test_documents_editable_during_revision(submitted_stu, mongo):
    files = {"file": ("t.pdf", io.BytesIO(b"%PDF-1.4 revision"), "application/pdf")}
    r = requests.post(
        f"{BASE_URL}/api/documents",
        headers=_hdr(submitted_stu["token"]),
        files=files,
        data={"doc_type": "KTP DKI Jakarta"},
        timeout=60,
    )
    assert r.status_code == 200, r.text
    new_doc = r.json()
    assert new_doc.get("id")

    # delete it
    d = requests.delete(
        f"{BASE_URL}/api/documents/{new_doc['id']}",
        headers=_hdr(submitted_stu["token"]),
        timeout=20,
    )
    assert d.status_code == 200, d.text


# --- 4. Resubmission works even when registration_open=False ---
def test_resubmission_bypasses_closed_registration_and_relocks(
    submitted_stu, admin_token, super_token, mongo
):
    uid = submitted_stu["user_id"]
    # Close registration explicitly
    _set_registration_open(super_token, False)
    try:
        # sanity: another fresh student cannot submit while closed
        stranger = _make_temp_student("stranger")
        try:
            _seed_profile(mongo, stranger["user_id"])
            _seed_docs(mongo, stranger["user_id"], PAKTA_DOCS)
            r_closed = requests.post(
                f"{BASE_URL}/api/registration",
                json={
                    "category": "Mahasiswa Sarjana (S1)",
                    "action": "submit",
                    "pakta_integritas_agreed": True,
                },
                headers=_jhdr(stranger["token"]),
                timeout=30,
            )
            assert r_closed.status_code == 403, r_closed.text
            assert r_closed.json().get("detail") == CLOSED_MSG
        finally:
            _cleanup_user(mongo, stranger["email"], stranger["user_id"])

        # Ensure the revising student is still in revision_requested state
        cur = mongo.registrations.find_one({"user_id": uid})
        assert cur.get("revision_requested") is True

        # Previous test soft-deleted the KTP doc; re-seed before resubmit so gaps pass.
        existing_types = set(
            mongo.documents.distinct(
                "doc_type", {"user_id": uid, "is_deleted": False}
            )
        )
        missing_types = [d for d in PAKTA_DOCS if d not in existing_types]
        if missing_types:
            _seed_docs(mongo, uid, missing_types)

        # Resubmit WITHOUT ceklis pakta ulang
        r = requests.post(
            f"{BASE_URL}/api/registration",
            json={
                "category": "Mahasiswa Sarjana (S1)",
                "action": "submit",
                "pakta_integritas_agreed": False,
            },
            headers=_jhdr(submitted_stu["token"]),
            timeout=30,
        )
        assert r.status_code == 200, r.text
        reg = r.json()
        assert "_id" not in reg
        assert reg["status"] == "submitted"
        assert reg.get("documents_editing_allowed") is False
        assert reg.get("revision_requested") is False
        assert reg.get("revision_resubmitted_at")

        # Uploads locked again
        rup = requests.post(
            f"{BASE_URL}/api/documents",
            headers=_hdr(submitted_stu["token"]),
            files={"file": ("x.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
            data={"doc_type": "Pas Foto 3x4"},
            timeout=30,
        )
        assert rup.status_code == 403, rup.text
        assert rup.json().get("detail") == DOCS_LOCKED_MSG

        # DELETE also locked
        doc = mongo.documents.find_one({"user_id": uid, "is_deleted": False})
        if doc:
            rdel = requests.delete(
                f"{BASE_URL}/api/documents/{doc['id']}",
                headers=_hdr(submitted_stu["token"]),
                timeout=20,
            )
            assert rdel.status_code == 403

        # --- 5. Admin (who requested revision) got document_revision_resubmitted notif
        # admin_token belongs to admin.mdj account; get its user_id
        me = requests.get(f"{BASE_URL}/api/auth/me", headers=_hdr(admin_token), timeout=20).json()
        admin_uid = me.get("user_id") or me.get("id")
        assert admin_uid, me
        # wait briefly for notification create
        time.sleep(0.5)
        n = mongo.notifications.find_one(
            {"user_id": admin_uid, "type": "document_revision_resubmitted", "source_id": uid}
        )
        assert n is not None, "expected document_revision_resubmitted notif for requesting admin"
        # cleanup this specific admin notification (per instructions: don't leave test notifs on owner)
        mongo.notifications.delete_many(
            {"user_id": admin_uid, "type": "document_revision_resubmitted", "source_id": uid}
        )
    finally:
        # Re-open so remaining tests (if any) can rely on open state; teardown closes anyway.
        _set_registration_open(super_token, True)


# --- 6a. Student & admin_wilayah are 403 on return-documents ---
def test_return_documents_forbidden_for_student_and_wilayah(
    submitted_stu, demo_student_token, mongo
):
    uid = submitted_stu["user_id"]
    # student
    r = requests.post(
        f"{BASE_URL}/api/admin/participants/{uid}/return-documents",
        json={"note": "malicious"},
        headers=_jhdr(demo_student_token),
        timeout=20,
    )
    assert r.status_code == 403, r.text

    # admin_wilayah (create temp)
    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    email = f"test.wilayah.{uuid.uuid4().hex[:6]}@example.com"
    uid_w = f"user_{uuid.uuid4().hex[:12]}"
    mongo.users.insert_one({
        "user_id": uid_w,
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
        tok = _login(email, "TestPass123!")
        r2 = requests.post(
            f"{BASE_URL}/api/admin/participants/{uid}/return-documents",
            json={"note": "coba wilayah"},
            headers=_jhdr(tok),
            timeout=20,
        )
        assert r2.status_code == 403, r2.text
    finally:
        mongo.users.delete_many({"email": email})
        mongo.user_sessions.delete_many({"user_id": uid_w})


# --- 6b. Legacy document-editing-permission allowed=True is rejected ---
def test_legacy_permission_allowed_true_rejected(submitted_stu, admin_token, super_token):
    uid = submitted_stu["user_id"]
    for tok in (admin_token, super_token):
        r = requests.put(
            f"{BASE_URL}/api/admin/participants/{uid}/document-editing-permission",
            json={"allowed": True},
            headers=_jhdr(tok),
            timeout=20,
        )
        # spec: rejected to ensure catatan wajib cannot be bypassed. Backend returns 400.
        assert r.status_code in (400, 403), r.text
