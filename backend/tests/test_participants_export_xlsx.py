"""Backend tests for GET /api/admin/participants/export.xlsx"""
import io
import os
import pytest
import requests
from openpyxl import load_workbook

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fallback to frontend/.env
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
    except Exception:
        pass

ADMIN = {"email": "admin.mdj@baznasbazisdki.id", "password": "AdminMDJ2026!"}
STUDENT = {"email": "mahasiswa.mdj@baznasbazisdki.id", "password": "MahasiswaMDJ2026!"}

EXPECTED_HEADERS = [
    "No.", "Nama", "Email", "ID CPM", "Kampus", "NIM", "Jenjang", "Jurusan",
    "Semester", "IPK", "Biaya Pendidikan / Semester (Rp)", "Wilayah", "Provinsi",
    "Nomor Telepon", "Dokumen Diunggah", "Status Pendaftaran", "Tanggal Daftar",
]


def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_token():
    return _login(**ADMIN)


@pytest.fixture(scope="module")
def student_token():
    return _login(**STUDENT)


def _download(token, params=None):
    r = requests.get(
        f"{BASE_URL}/api/admin/participants/export.xlsx",
        headers={"Authorization": f"Bearer {token}"},
        params=params or {},
        timeout=60,
    )
    return r


def test_export_all(admin_token):
    r = _download(admin_token)
    assert r.status_code == 200
    assert "spreadsheetml" in r.headers.get("content-type", "")
    assert "attachment" in r.headers.get("content-disposition", "")
    wb = load_workbook(io.BytesIO(r.content))
    ws = wb.active
    headers = [c.value for c in ws[1]]
    assert headers == EXPECTED_HEADERS
    # header formatting present (bold + fill)
    first = ws.cell(row=1, column=1)
    assert first.font.bold is True
    assert first.fill.fgColor.rgb.endswith("0B6B3A")


def test_export_filter_jakarta_pusat(admin_token):
    r = _download(admin_token, {"region": "Jakarta Pusat"})
    assert r.status_code == 200
    wb = load_workbook(io.BytesIO(r.content))
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    assert len(rows) == 9, f"expected 9 rows, got {len(rows)}"
    wilayah_idx = EXPECTED_HEADERS.index("Wilayah")
    for row in rows:
        assert row[wilayah_idx] == "Jakarta Pusat"


def test_export_filter_status_lolos(admin_token):
    r = _download(admin_token, {"status": "lolos"})
    assert r.status_code == 200
    wb = load_workbook(io.BytesIO(r.content))
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    assert len(rows) > 0
    status_idx = EXPECTED_HEADERS.index("Status Pendaftaran")
    for row in rows:
        # STATUS_LABELS[lolos] should be display label; ensure not empty and not raw 'submitted'
        assert row[status_idx] not in (None, "-", "")
        # All rows should share the same displayed status
    unique_statuses = {row[status_idx] for row in rows}
    assert len(unique_statuses) == 1, f"expected one status label, got {unique_statuses}"


def test_export_forbidden_for_student(student_token):
    r = _download(student_token)
    assert r.status_code == 403


def test_export_requires_auth():
    r = requests.get(f"{BASE_URL}/api/admin/participants/export.xlsx", timeout=30)
    assert r.status_code in (401, 403)
