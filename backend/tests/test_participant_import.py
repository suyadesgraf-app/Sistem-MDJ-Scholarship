"""Backend tests for Super Admin participant Excel import (no-documents flow).

Covers:
- Role gating (super_admin only for preview & import)
- XLSX preview: header detection, suggested mapping, samples, row_count
- Validation: non-xlsx, empty xlsx, invalid mapping JSON, missing required "name" mapping
- Import creates users/profiles/registrations with status=lolos + imported_without_documents=true; no documents
- Duplicate detection via NIK / email / cpm_id updates same participant
- Identifier conflict pointing to different participants fails per row
- Cleanup of all TEST_ data after tests
"""
import io
import json
import os
import uuid

import pytest
import requests
from openpyxl import Workbook
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

SUPER_ADMIN = {"email": "supri@baznasbazisdki.id", "password": "MdjSuper2026!"}
STUDENT = {"email": "mahasiswa.mdj@baznasbazisdki.id", "password": "MahasiswaMDJ2026!"}

TEST_PREFIX = "TEST_IMPORT_"
TEST_NIK_PREFIX = "9999911"  # 16 digits total when combined
TEST_EMAIL_DOMAIN = "@test-import.invalid"

mongo_client = MongoClient(MONGO_URL)
db = mongo_client[DB_NAME]


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    token = r.json().get("token")
    assert token
    return token


@pytest.fixture(scope="module")
def super_token():
    return _login(SUPER_ADMIN)


@pytest.fixture(scope="module")
def student_token():
    return _login(STUDENT)


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def build_xlsx(header_row, data_rows):
    wb = Workbook()
    ws = wb.active
    ws.append(header_row)
    for r in data_rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


def cleanup_test_data():
    """Delete all TEST_ prefixed rows across collections."""
    email_re = {"$regex": TEST_EMAIL_DOMAIN + "$", "$options": "i"}
    nik_re = {"$regex": f"^{TEST_NIK_PREFIX}"}
    # find user_ids
    user_ids = set()
    for u in db.users.find({"$or": [{"email": email_re}, {"name": {"$regex": f"^{TEST_PREFIX}"}}]}, {"user_id": 1}):
        user_ids.add(u["user_id"])
    for p in db.profiles.find({"$or": [{"data.email": email_re}, {"data.nik": nik_re}, {"data.namaLengkap": {"$regex": f"^{TEST_PREFIX}"}}]}, {"user_id": 1}):
        user_ids.add(p["user_id"])
    for r in db.registrations.find({"$or": [{"email": email_re}, {"name": {"$regex": f"^{TEST_PREFIX}"}}]}, {"user_id": 1}):
        user_ids.add(r["user_id"])
    if user_ids:
        q = {"user_id": {"$in": list(user_ids)}}
        db.users.delete_many(q)
        db.profiles.delete_many(q)
        db.registrations.delete_many(q)
        db.documents.delete_many(q)
    # import records referencing test files
    db.participant_imports.delete_many({"original_filename": {"$regex": f"^{TEST_PREFIX}"}})


@pytest.fixture(scope="module", autouse=True)
def _module_cleanup():
    cleanup_test_data()
    yield
    cleanup_test_data()


# ---------- Role gating ----------

class TestRoleGating:
    def test_preview_forbidden_for_student(self, student_token):
        xlsx = build_xlsx(["Nama Lengkap"], [["Foo"]])
        r = requests.post(
            f"{API}/admin/participants/import/preview",
            headers=_headers(student_token),
            files={"file": (f"{TEST_PREFIX}gate.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            timeout=30,
        )
        assert r.status_code == 403, r.text

    def test_import_forbidden_for_student(self, student_token):
        xlsx = build_xlsx(["Nama Lengkap"], [["Foo"]])
        r = requests.post(
            f"{API}/admin/participants/import",
            headers=_headers(student_token),
            data={"mapping_json": json.dumps({"name": "Nama Lengkap"})},
            files={"file": (f"{TEST_PREFIX}gate.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            timeout=30,
        )
        assert r.status_code == 403, r.text

    def test_preview_requires_auth(self):
        xlsx = build_xlsx(["Nama Lengkap"], [["Foo"]])
        r = requests.post(
            f"{API}/admin/participants/import/preview",
            files={"file": (f"{TEST_PREFIX}gate.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            timeout=30,
        )
        assert r.status_code in (401, 403)


# ---------- Preview ----------

class TestPreview:
    def test_preview_suggests_mapping(self, super_token):
        headers = [
            "Nama Mahasiswa", "NIK", "Email Mahasiswa", "No HP",
            "Perguruan Tinggi", "NIM", "Program Studi", "Wilayah", "ID CPM",
        ]
        rows = [[
            f"{TEST_PREFIX}Alice", f"{TEST_NIK_PREFIX}000001", f"{TEST_PREFIX.lower()}alice{TEST_EMAIL_DOMAIN}",
            "08123", "Universitas Test", "1234", "Informatika", "Jakarta Selatan", "",
        ]]
        xlsx = build_xlsx(headers, rows)
        r = requests.post(
            f"{API}/admin/participants/import/preview",
            headers=_headers(super_token),
            files={"file": (f"{TEST_PREFIX}suggest.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["row_count"] == 1
        m = data["mapping"]
        assert m["name"] == "Nama Mahasiswa"
        assert m["nik"] == "NIK"
        assert m["email"] == "Email Mahasiswa"
        assert m["campus"] == "Perguruan Tinggi"
        assert m["nim"] == "NIM"
        assert m["major"] == "Program Studi"
        assert m["region"] == "Wilayah"
        assert m["cpm_id"] == "ID CPM"
        assert data["has_identity_column"] is True
        assert len(data["samples"]) == 1
        assert data["samples"][0]["NIK"] == f"{TEST_NIK_PREFIX}000001"
        # fields include gender etc
        keys = {f["key"] for f in data["fields"]}
        assert {"name", "nik", "email", "cpm_id", "gender"}.issubset(keys)

    def test_preview_rejects_non_xlsx(self, super_token):
        r = requests.post(
            f"{API}/admin/participants/import/preview",
            headers=_headers(super_token),
            files={"file": (f"{TEST_PREFIX}bad.csv", b"a,b\n1,2", "text/csv")},
            timeout=30,
        )
        assert r.status_code == 400

    def test_preview_rejects_empty_xlsx(self, super_token):
        wb = Workbook(); ws = wb.active; ws.append(["Nama Lengkap"])  # only header, no data
        buf = io.BytesIO(); wb.save(buf); buf.seek(0)
        r = requests.post(
            f"{API}/admin/participants/import/preview",
            headers=_headers(super_token),
            files={"file": (f"{TEST_PREFIX}empty.xlsx", buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            timeout=30,
        )
        assert r.status_code == 400

    def test_preview_without_identity_columns_still_works(self, super_token):
        xlsx = build_xlsx(["Nama Peserta", "Kolom Bebas"], [[f"{TEST_PREFIX}NoID", "x"]])
        r = requests.post(
            f"{API}/admin/participants/import/preview",
            headers=_headers(super_token),
            files={"file": (f"{TEST_PREFIX}noid.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            timeout=30,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["has_identity_column"] is False
        assert data["mapping"]["name"] in ("Nama Peserta", "")


# ---------- Import ----------

class TestImport:
    def test_import_creates_participants_no_documents(self, super_token):
        headers = ["Nama Lengkap", "NIK", "Email", "No HP", "Kampus", "NIM", "Program Studi", "Jenjang", "Semester", "IPK", "Kota", "Provinsi", "Alamat", "Jenis Kelamin"]
        rows = [
            [f"{TEST_PREFIX}Budi", f"{TEST_NIK_PREFIX}100001", f"{TEST_PREFIX.lower()}budi{TEST_EMAIL_DOMAIN}", "0811", "Univ A", "N001", "TI", "S1", "3", "3.5", "Jakarta Selatan", "DKI Jakarta", "Jl. Test 1", "Laki-laki"],
            [f"{TEST_PREFIX}Citra", f"{TEST_NIK_PREFIX}100002", f"{TEST_PREFIX.lower()}citra{TEST_EMAIL_DOMAIN}", "0822", "Univ B", "N002", "Akuntansi", "S1", "5", "3.8", "Jakarta Timur", "DKI Jakarta", "Jl. Test 2", "Perempuan"],
        ]
        xlsx = build_xlsx(headers, rows)
        mapping = {h_key: h for h_key, h in {
            "name": "Nama Lengkap", "nik": "NIK", "email": "Email", "phone": "No HP",
            "campus": "Kampus", "nim": "NIM", "major": "Program Studi", "education_level": "Jenjang",
            "semester": "Semester", "gpa": "IPK", "region": "Kota", "province": "Provinsi",
            "address": "Alamat", "gender": "Jenis Kelamin",
        }.items()}
        r = requests.post(
            f"{API}/admin/participants/import",
            headers=_headers(super_token),
            data={"mapping_json": json.dumps(mapping)},
            files={"file": (f"{TEST_PREFIX}create.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["summary"]["processed"] == 2
        assert data["summary"]["created"] == 2
        assert data["summary"]["failed"] == 0

        # Verify DB
        u = db.users.find_one({"email": f"{TEST_PREFIX.lower()}budi{TEST_EMAIL_DOMAIN}"})
        assert u is not None
        assert u["role"] == "student"
        assert u.get("auth_provider") == "participant_import"

        prof = db.profiles.find_one({"user_id": u["user_id"]})
        assert prof is not None
        assert prof.get("imported_without_documents") is True
        pdata = prof.get("data") or {}
        assert pdata.get("namaLengkap") == f"{TEST_PREFIX}Budi"
        assert pdata.get("nik") == f"{TEST_NIK_PREFIX}100001"
        assert pdata.get("institusi") == "Univ A"
        assert pdata.get("nim") == "N001"
        assert pdata.get("jurusan") == "TI"
        assert pdata.get("jenjang") == "S1"
        assert pdata.get("kota") == "Jakarta Selatan"
        assert pdata.get("provinsi") == "DKI Jakarta"
        assert pdata.get("jenisKelamin") == "Laki-laki"

        reg = db.registrations.find_one({"user_id": u["user_id"]})
        assert reg is not None
        assert reg["status"] == "lolos"
        assert reg.get("imported_without_documents") is True
        assert reg.get("cpm_id")

        # Zero document rows for this user
        assert db.documents.count_documents({"user_id": u["user_id"]}) == 0

    def test_import_duplicate_updates_existing(self, super_token):
        # Re-import Budi with same NIK but changed name
        headers = ["Nama Lengkap", "NIK", "Email"]
        new_email = f"{TEST_PREFIX.lower()}budi2{TEST_EMAIL_DOMAIN}"
        # Keep same email to avoid conflict AND to test NIK duplicate detection use different email
        rows = [[f"{TEST_PREFIX}BudiUpdated", f"{TEST_NIK_PREFIX}100001", new_email]]
        xlsx = build_xlsx(headers, rows)
        mapping = {"name": "Nama Lengkap", "nik": "NIK", "email": "Email"}
        r = requests.post(
            f"{API}/admin/participants/import",
            headers=_headers(super_token),
            data={"mapping_json": json.dumps(mapping)},
            files={"file": (f"{TEST_PREFIX}update.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["summary"]["processed"] == 1
        assert data["summary"]["updated"] == 1
        assert data["summary"]["created"] == 0

        # verify only one user for NIK
        matching = list(db.profiles.find({"data.nik": f"{TEST_NIK_PREFIX}100001"}))
        assert len(matching) == 1
        u = db.users.find_one({"user_id": matching[0]["user_id"]})
        assert u["name"] == f"{TEST_PREFIX}BudiUpdated"

    def test_import_identifier_conflict_fails(self, super_token):
        # Budi's NIK combined with Citra's email -> different existing users -> should fail
        budi_nik = f"{TEST_NIK_PREFIX}100001"
        citra_email = f"{TEST_PREFIX.lower()}citra{TEST_EMAIL_DOMAIN}"
        xlsx = build_xlsx(
            ["Nama Lengkap", "NIK", "Email"],
            [[f"{TEST_PREFIX}Conflict", budi_nik, citra_email]],
        )
        mapping = {"name": "Nama Lengkap", "nik": "NIK", "email": "Email"}
        r = requests.post(
            f"{API}/admin/participants/import",
            headers=_headers(super_token),
            data={"mapping_json": json.dumps(mapping)},
            files={"file": (f"{TEST_PREFIX}conflict.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["summary"]["failed"] == 1
        assert data["summary"]["created"] == 0
        assert data["summary"]["updated"] == 0
        assert data["errors"]
        assert "berbeda" in data["errors"][0]["message"].lower() or "different" in data["errors"][0]["message"].lower()

    def test_import_without_identity_creates_new(self, super_token):
        # No email/NIK/CPM mapped — must still create with internal identity
        xlsx = build_xlsx(["Nama Peserta"], [[f"{TEST_PREFIX}NoIDPerson"]])
        mapping = {"name": "Nama Peserta"}
        r = requests.post(
            f"{API}/admin/participants/import",
            headers=_headers(super_token),
            data={"mapping_json": json.dumps(mapping)},
            files={"file": (f"{TEST_PREFIX}noid_create.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["summary"]["created"] == 1
        u = db.users.find_one({"name": f"{TEST_PREFIX}NoIDPerson"})
        assert u is not None
        assert u["email"].endswith("@mdj.invalid")

    def test_import_rejects_missing_name_mapping(self, super_token):
        xlsx = build_xlsx(["Nama Lengkap"], [["X"]])
        r = requests.post(
            f"{API}/admin/participants/import",
            headers=_headers(super_token),
            data={"mapping_json": json.dumps({"nik": "Nama Lengkap"})},
            files={"file": (f"{TEST_PREFIX}nomap.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            timeout=30,
        )
        assert r.status_code == 400

    def test_import_rejects_invalid_json_mapping(self, super_token):
        xlsx = build_xlsx(["Nama Lengkap"], [["X"]])
        r = requests.post(
            f"{API}/admin/participants/import",
            headers=_headers(super_token),
            data={"mapping_json": "{not-json"},
            files={"file": (f"{TEST_PREFIX}badjson.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            timeout=30,
        )
        assert r.status_code == 400

    def test_import_rejects_non_xlsx(self, super_token):
        r = requests.post(
            f"{API}/admin/participants/import",
            headers=_headers(super_token),
            data={"mapping_json": json.dumps({"name": "A"})},
            files={"file": (f"{TEST_PREFIX}bad.csv", b"a,b\n1,2", "text/csv")},
            timeout=30,
        )
        assert r.status_code == 400
