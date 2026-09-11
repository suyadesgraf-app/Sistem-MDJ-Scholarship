"""Tests for education document scanning (KTM + Academic record) via Gemini OCR."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://sistem-registrasi.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

STUDENT_EMAIL = "mahasiswa.mdj@baznasbazisdki.id"
STUDENT_PASSWORD = "MahasiswaMDJ2026!"

KTM_PATH = "/tmp/mdj-ktm-uji.png"
KHS_PATH = "/tmp/mdj-khs-uji.png"


@pytest.fixture(scope="module")
def student_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": STUDENT_EMAIL, "password": STUDENT_PASSWORD})
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return s


def test_login_ok(student_session):
    r = student_session.get(f"{API}/auth/me")
    assert r.status_code == 200


def test_extract_ktm(student_session):
    with open(KTM_PATH, "rb") as f:
        r = student_session.post(
            f"{API}/profile/extract-ktm",
            files={"file": ("ktm.png", f, "image/png")},
            timeout=120,
        )
    assert r.status_code == 200, f"{r.status_code} {r.text}"
    body = r.json()
    data = body.get("data", {})
    doc = body.get("document")
    print("KTM extracted fields:", data)
    assert data, f"No fields extracted: {body}"
    assert doc and doc.get("doc_type") == "Kartu Tanda Mahasiswa (KTM)"
    docs = student_session.get(f"{API}/documents").json()
    assert any(d.get("doc_type") == "Kartu Tanda Mahasiswa (KTM)" for d in docs)


def test_extract_academic(student_session):
    with open(KHS_PATH, "rb") as f:
        r = student_session.post(
            f"{API}/profile/extract-academic-record",
            files={"file": ("khs.png", f, "image/png")},
            timeout=120,
        )
    assert r.status_code == 200, f"{r.status_code} {r.text}"
    body = r.json()
    data = body.get("data", {})
    print("Academic extracted fields:", data)
    assert data, f"No fields extracted: {body}"
    assert any(k in data for k in ("ipk", "semester", "nim", "institusi", "jurusan"))
    doc = body.get("document")
    assert doc and doc.get("doc_type") == "KRS / KHS / Transkrip Nilai"


def test_reject_bad_format(student_session):
    # backend rejects non-allowed extensions
    r = student_session.post(
        f"{API}/profile/extract-ktm",
        files={"file": ("bad.txt", b"hello world", "text/plain")},
        timeout=30,
    )
    assert r.status_code == 400


def test_save_education_persists(student_session):
    # Preserve existing profile data, add education fields via PUT /profile
    current = student_session.get(f"{API}/profile").json()
    data = dict(current.get("data", {}))
    data.update({
        "institusi": "Universitas Test MDJ",
        "nim": "1234567890",
        "jurusan": "Teknik Informatika",
        "jenjang": "S1",
        "semester": "5",
        "ipk": "3.75",
    })
    r = student_session.put(f"{API}/profile", json={"data": data})
    assert r.status_code == 200, f"{r.status_code} {r.text}"
    got = student_session.get(f"{API}/profile").json().get("data", {})
    for k in ("institusi", "nim", "jurusan", "jenjang", "semester", "ipk"):
        assert got.get(k) == data[k], f"{k}: expected {data[k]}, got {got.get(k)}"
