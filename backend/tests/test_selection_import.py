"""Tests for Admin Selection Import (Wawancara & Kelulusan Akhir).

Covers: upload validation, matching (cpm_id), review items (mismatch / new / invalid),
status updates, notifications, history & audit download, and RBAC (student -> 403).
"""
import io
import os
import time
import uuid
from typing import Optional

import pytest
import requests
from openpyxl import Workbook, load_workbook
from pymongo import MongoClient

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin.mdj@baznasbazisdki.id"
ADMIN_PASSWORD = "AdminMDJ2026!"
STUDENT_EMAIL = "mahasiswa.mdj@baznasbazisdki.id"
STUDENT_PASSWORD = "MahasiswaMDJ2026!"

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

STATUS_RANK = {
    "draft": 0, "submitted": 1, "verifikasi": 2, "lolos_administrasi": 3,
    "wawancara": 4, "verifikasi_faktual": 5, "lolos": 6,
}


# ---- fixtures ----------------------------------------------------------------

@pytest.fixture(scope="module")
def db():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture(scope="module")
def student_token():
    return _login(STUDENT_EMAIL, STUDENT_PASSWORD)


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def picked_participants(admin_headers, db):
    """Pick two seeded participants for match testing.
    A -> status < verifikasi_faktual (upgradable via wawancara_lolos)
    B -> any seeded (used for mismatch, status unchanged)
    """
    r = requests.get(f"{API}/admin/participants", headers=admin_headers, timeout=30)
    assert r.status_code == 200
    participants = r.json()
    seeded = [p for p in participants if str(p.get("user_id", "")).startswith("student_uji_mdj_")]
    assert len(seeded) >= 5, f"Need >=5 seeded participants, got {len(seeded)}"

    a = next((p for p in seeded if STATUS_RANK.get(p.get("status"), 0) < STATUS_RANK["verifikasi_faktual"]), None)
    b = next((p for p in seeded if p["user_id"] != (a or {}).get("user_id")), None)
    c = next(
        (p for p in seeded
         if p["user_id"] not in {(a or {}).get("user_id"), (b or {}).get("user_id")}
         and STATUS_RANK.get(p.get("status"), 0) < STATUS_RANK["lolos"]),
        None,
    )
    assert a and b and c, "Could not pick 3 seeded participants for the test"
    return {"A": a, "B": b, "C": c}


# ---- helpers -----------------------------------------------------------------

def make_xlsx(rows, headers=None):
    headers = headers or [
        "ID CPM", "NIK", "Email Mahasiswa", "Nama Lengkap",
        "Nama Kampus", "Kota / Kabupaten",
    ]
    wb = Workbook()
    ws = wb.active
    ws.title = "Hasil"
    ws.append(["Laporan Hasil Seleksi", "", "", "", "", ""])
    ws.append(headers)
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


def upload(admin_headers, stage, xlsx_bytes, filename):
    files = {"file": (filename, xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    data = {"stage": stage}
    return requests.post(f"{API}/admin/selection-imports", headers=admin_headers, data=data, files=files, timeout=180)


# ---- tests -------------------------------------------------------------------

def test_upload_validation_rejects_non_xlsx(admin_headers):
    files = {"file": ("notes.txt", b"hello", "text/plain")}
    r = requests.post(f"{API}/admin/selection-imports", headers=admin_headers, data={"stage": "wawancara_lolos"}, files=files, timeout=30)
    assert r.status_code == 400
    assert "XLSX" in r.json().get("detail", "")


def test_upload_validation_invalid_stage(admin_headers):
    xlsx = make_xlsx([["", "", "", "", "", ""]])
    r = upload(admin_headers, "bogus_stage", xlsx, "test-selection-import-bogus.xlsx")
    assert r.status_code == 400


def test_wawancara_lolos_end_to_end(admin_headers, picked_participants, db):
    A = picked_participants["A"]
    B = picked_participants["B"]

    a_status_before = A["status"]
    b_status_before = B["status"]

    rows = [
        # Row 1 matched (cpm_id + same identity) -> should update to verifikasi_faktual
        [A["cpm_id"], "", A.get("email"), A.get("name"), A.get("institusi"), A.get("wilayah")],
        # Row 2 same cpm as B but campus/region mismatched -> mismatch review, status unchanged
        [B["cpm_id"], "", B.get("email"), B.get("name"), "Kampus Palsu XYZ", "Kota Antah Berantah"],
        # Row 3 brand new participant (not seeded)
        ["", f"{int(time.time())}0001234567", f"TEST_new_{uuid.uuid4().hex[:6]}@example.com",
         "Peserta Baru Uji", "Universitas Baru MDJ", "Jakarta Selatan"],
        # Row 4 all blanks -> invalid
        ["", "", "", "", "", ""],
    ]
    xlsx = make_xlsx(rows)
    filename = f"test-selection-import-wawancara-{uuid.uuid4().hex[:6]}.xlsx"
    r = upload(admin_headers, "wawancara_lolos", xlsx, filename)
    assert r.status_code == 200, r.text
    body = r.json()
    summary = body["summary"]
    assert summary["updated"] >= 1, f"Expected at least 1 updated, got {summary}"
    assert summary["review"] >= 1, f"Expected at least 1 review, got {summary}"
    assert summary["new"] >= 1, f"Expected at least 1 new, got {summary}"

    # Verify status of A moved to verifikasi_faktual
    r_a = requests.get(f"{API}/admin/participants/{A['user_id']}", headers=admin_headers, timeout=30)
    assert r_a.status_code == 200
    assert r_a.json()["registration"]["status"] == "verifikasi_faktual"

    # Verify status of B unchanged (mismatch)
    r_b = requests.get(f"{API}/admin/participants/{B['user_id']}", headers=admin_headers, timeout=30)
    assert r_b.status_code == 200
    assert r_b.json()["registration"]["status"] == b_status_before, \
        f"B status should be unchanged. before={b_status_before} after={r_b.json()['registration']['status']}"

    # Verify review endpoint returns items
    r_rev = requests.get(f"{API}/admin/selection-import-review", headers=admin_headers, params={"kind": "review"}, timeout=30)
    assert r_rev.status_code == 200
    review_items = [i for i in r_rev.json() if i["import_id"] == body["import_id"]]
    assert any(i["kind"] == "mismatch" for i in review_items), "Expected mismatch review item"

    r_new = requests.get(f"{API}/admin/selection-import-review", headers=admin_headers, params={"kind": "new"}, timeout=30)
    assert r_new.status_code == 200
    new_items = [i for i in r_new.json() if i["import_id"] == body["import_id"]]
    assert any(i["kind"] == "new_participant" for i in new_items), "Expected new_participant item"

    # Persist for later assertions
    pytest.wawancara_import_id = body["import_id"]
    pytest.wawancara_a_before = a_status_before


def test_history_and_audit_download(admin_headers):
    r = requests.get(f"{API}/admin/selection-imports", headers=admin_headers, timeout=30)
    assert r.status_code == 200
    records = r.json()
    assert any(rec["id"] == pytest.wawancara_import_id for rec in records)
    rec = next(rec for rec in records if rec["id"] == pytest.wawancara_import_id)
    assert rec.get("original_filename", "").startswith("test-selection-import-")
    assert isinstance(rec.get("summary"), dict)

    # Download audit file
    r_dl = requests.get(f"{API}/admin/selection-imports/{pytest.wawancara_import_id}/file", headers=admin_headers, timeout=30)
    assert r_dl.status_code == 200
    assert "spreadsheetml" in r_dl.headers.get("content-type", "") or r_dl.headers.get("content-type", "").endswith("xlsx")
    # Ensure downloaded bytes are a valid workbook
    wb = load_workbook(io.BytesIO(r_dl.content), read_only=True)
    assert wb.active.max_row >= 2
    wb.close()


def test_kelulusan_akhir_matches_and_notifies(admin_headers, picked_participants, db):
    C = picked_participants["C"]
    c_user_id = C["user_id"]
    notif_before = db.notifications.count_documents({"user_id": c_user_id, "type": "selection_progress"})

    rows = [[C["cpm_id"], "", C.get("email"), C.get("name"), C.get("institusi"), C.get("wilayah")]]
    xlsx = make_xlsx(rows)
    filename = f"test-selection-import-kelulusan-{uuid.uuid4().hex[:6]}.xlsx"
    r = upload(admin_headers, "kelulusan_akhir", xlsx, filename)
    assert r.status_code == 200, r.text
    summary = r.json()["summary"]
    assert summary["updated"] == 1, f"Expected exactly 1 update, got {summary}"

    r_c = requests.get(f"{API}/admin/participants/{c_user_id}", headers=admin_headers, timeout=30)
    assert r_c.status_code == 200
    assert r_c.json()["registration"]["status"] == "lolos"

    notif_after = db.notifications.count_documents({"user_id": c_user_id, "type": "selection_progress"})
    assert notif_after == notif_before + 1, f"Expected +1 notification, got before={notif_before} after={notif_after}"

    pytest.kelulusan_import_id = r.json()["import_id"]


def test_dismiss_review_item(admin_headers):
    r_rev = requests.get(f"{API}/admin/selection-import-review", headers=admin_headers, timeout=30)
    assert r_rev.status_code == 200
    items = [i for i in r_rev.json() if i.get("import_id") == pytest.wawancara_import_id]
    assert items, "Expected some review items from wawancara import"
    target = items[0]
    r_del = requests.delete(f"{API}/admin/selection-import-review/{target['id']}", headers=admin_headers, timeout=30)
    assert r_del.status_code == 200

    # Idempotent: 404 on second delete
    r_del2 = requests.delete(f"{API}/admin/selection-import-review/{target['id']}", headers=admin_headers, timeout=30)
    assert r_del2.status_code == 404


def test_student_forbidden_for_import_endpoints(student_token):
    headers = {"Authorization": f"Bearer {student_token}"}
    endpoints = [
        ("GET", f"{API}/admin/selection-imports"),
        ("GET", f"{API}/admin/selection-import-review"),
        ("GET", f"{API}/admin/selection-imports/{uuid.uuid4()}/file"),
        ("DELETE", f"{API}/admin/selection-import-review/{uuid.uuid4()}"),
    ]
    for method, url in endpoints:
        r = requests.request(method, url, headers=headers, timeout=30)
        assert r.status_code == 403, f"{method} {url} expected 403 got {r.status_code}"

    # POST upload also forbidden
    xlsx = make_xlsx([["", "", "", "", "", ""]])
    files = {"file": ("test-selection-import-student.xlsx", xlsx)}
    r = requests.post(f"{API}/admin/selection-imports", headers=headers, data={"stage": "wawancara_lolos"}, files=files, timeout=30)
    assert r.status_code == 403


# ---- cleanup ------------------------------------------------------------------

def test_zzz_cleanup(admin_headers, picked_participants, db):
    """Delete test-created import records and rollback status changes on seed participants."""
    # Delete all review items and imports whose filename starts with test-selection-import-
    test_imports = list(db.selection_imports.find({"original_filename": {"$regex": "^test-selection-import-"}}, {"id": 1}))
    ids = [imp["id"] for imp in test_imports]
    if ids:
        db.selection_import_review.delete_many({"import_id": {"$in": ids}})
        db.selection_imports.delete_many({"id": {"$in": ids}})

    # Restore seed participants A and C statuses if we changed them
    for key in ("A", "C"):
        p = picked_participants[key]
        db.registrations.update_one(
            {"user_id": p["user_id"]},
            {"$set": {"status": p["status"]}},
        )
    print(f"Cleanup done. Removed {len(ids)} test import records and their reviews.")
