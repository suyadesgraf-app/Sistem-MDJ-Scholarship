"""Backend tests for Super Admin participant Excel import — Campus bank sync (iter 65).

Covers:
- Preview auto-maps Nama Bank / No Rekening / Atas Nama Rekening to campus_bank_* fields
- Import auto-creates ONE campus per unique campus name (two rows same campus -> 1 create)
- Campus master persists bank_name, encrypted account cipher, and holder name
- Re-import identical bank/account does NOT duplicate campus and does NOT conflict
- Conflicting bank/account/holder for existing campus -> master unchanged +
  campus_conflicts counter + warnings row entries; participant still processed
- Campus without existing bank data gets updated when full bank info provided
- Account number without holder is NON-destructive warning; cipher NOT stored
- List /api/campuses returns bank_name for super_admin, hides raw account (masked)
- Cleanup all TEST_ users/profiles/registrations/documents/participant_imports/campuses
"""
import io
import json
import os
import re

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

TEST_PREFIX = "TEST_CAMPBANK_"
TEST_NIK_PREFIX = "9999922"
TEST_EMAIL_DOMAIN = "@test-campbank.invalid"
TEST_CAMPUS_PREFIX = "TEST_CAMPBANK_UNIV_"

mongo_client = MongoClient(MONGO_URL)
db = mongo_client[DB_NAME]


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def super_token():
    return _login(SUPER_ADMIN)


def _hdr(token):
    return {"Authorization": f"Bearer {token}"}


def build_xlsx(header_row, data_rows):
    wb = Workbook(); ws = wb.active
    ws.append(header_row)
    for r in data_rows:
        ws.append(r)
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    return buf.getvalue()


def cleanup():
    email_re = {"$regex": TEST_EMAIL_DOMAIN + "$", "$options": "i"}
    nik_re = {"$regex": f"^{TEST_NIK_PREFIX}"}
    user_ids = set()
    for u in db.users.find({"$or": [{"email": email_re}, {"name": {"$regex": f"^{TEST_PREFIX}"}}]}, {"user_id": 1}):
        user_ids.add(u["user_id"])
    for p in db.profiles.find({"$or": [{"data.email": email_re}, {"data.nik": nik_re}]}, {"user_id": 1}):
        user_ids.add(p["user_id"])
    if user_ids:
        q = {"user_id": {"$in": list(user_ids)}}
        db.users.delete_many(q)
        db.profiles.delete_many(q)
        db.registrations.delete_many(q)
        db.documents.delete_many(q)
    db.participant_imports.delete_many({"original_filename": {"$regex": f"^{TEST_PREFIX}"}})
    db.campuses.delete_many({"name": {"$regex": f"^{re.escape(TEST_CAMPUS_PREFIX)}"}})


@pytest.fixture(scope="module", autouse=True)
def _cleanup_module():
    cleanup()
    yield
    cleanup()


# ---------- Preview ----------

def test_preview_maps_campus_bank_columns(super_token):
    """Auto-map for headers 'Nama Bank', 'No Rekening', 'Atas Nama Rekening'."""
    headers = [
        "Nama Lengkap", "NIK", "Perguruan Tinggi",
        "Nama Bank", "No Rekening", "Atas Nama Rekening",
    ]
    rows = [[
        f"{TEST_PREFIX}Amir", f"{TEST_NIK_PREFIX}00001", f"{TEST_CAMPUS_PREFIX}Alpha",
        "BSI", "1234567890", f"{TEST_CAMPUS_PREFIX}Alpha PT",
    ]]
    xlsx = build_xlsx(headers, rows)
    r = requests.post(
        f"{API}/admin/participants/import/preview",
        headers=_hdr(super_token),
        files={"file": (f"{TEST_PREFIX}preview.xlsx", xlsx,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    m = data["mapping"]
    assert m["campus_bank_name"] == "Nama Bank"
    assert m["campus_account_number"] == "No Rekening"
    assert m["campus_account_holder"] == "Atas Nama Rekening"
    keys = {f["key"] for f in data["fields"]}
    assert {"campus_bank_name", "campus_account_number", "campus_account_holder"}.issubset(keys)


# ---------- Import: new campus + dedup ----------

BANK_HEADERS = [
    "Nama Lengkap", "NIK", "Email", "Kampus",
    "Nama Bank", "No Rekening", "Atas Nama Rekening",
]
BANK_MAPPING = {
    "name": "Nama Lengkap", "nik": "NIK", "email": "Email", "campus": "Kampus",
    "campus_bank_name": "Nama Bank", "campus_account_number": "No Rekening",
    "campus_account_holder": "Atas Nama Rekening",
}


def _post_import(token, filename, headers_row, rows, mapping=None):
    xlsx = build_xlsx(headers_row, rows)
    return requests.post(
        f"{API}/admin/participants/import",
        headers=_hdr(token),
        data={"mapping_json": json.dumps(mapping or BANK_MAPPING)},
        files={"file": (filename, xlsx,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        timeout=60,
    )


def test_import_creates_one_campus_for_two_rows_same_campus(super_token):
    campus_name = f"{TEST_CAMPUS_PREFIX}Alpha"
    rows = [
        [f"{TEST_PREFIX}A1", f"{TEST_NIK_PREFIX}00001",
         f"{TEST_PREFIX.lower()}a1{TEST_EMAIL_DOMAIN}", campus_name,
         "BSI", "1234567890", f"{campus_name} Yayasan"],
        [f"{TEST_PREFIX}A2", f"{TEST_NIK_PREFIX}00002",
         f"{TEST_PREFIX.lower()}a2{TEST_EMAIL_DOMAIN}", campus_name,
         "BSI", "1234567890", f"{campus_name} Yayasan"],
    ]
    r = _post_import(super_token, f"{TEST_PREFIX}alpha.xlsx", BANK_HEADERS, rows)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["summary"]["processed"] == 2
    assert data["summary"]["created"] == 2  # 2 participants
    assert data["summary"]["failed"] == 0
    assert data["summary"]["campuses_created"] == 1  # only ONE campus
    assert data["summary"]["campuses_updated"] == 0
    assert data["summary"]["campus_conflicts"] == 0

    # DB verification
    campuses = list(db.campuses.find({"name": campus_name}))
    assert len(campuses) == 1
    c = campuses[0]
    assert c.get("bank_name") == "BSI"
    assert c.get("bank_account_holder_name") == f"{campus_name} Yayasan"
    # cipher present, not raw account
    assert c.get("bank_account_cipher")
    assert "1234567890" not in str(c.get("bank_account_cipher"))
    assert c.get("source") == "participant_import"


def test_reimport_same_bank_no_duplicate_no_conflict(super_token):
    campus_name = f"{TEST_CAMPUS_PREFIX}Alpha"
    rows = [
        [f"{TEST_PREFIX}A1", f"{TEST_NIK_PREFIX}00001",
         f"{TEST_PREFIX.lower()}a1{TEST_EMAIL_DOMAIN}", campus_name,
         "BSI", "1234567890", f"{campus_name} Yayasan"],
    ]
    r = _post_import(super_token, f"{TEST_PREFIX}alpha_re.xlsx", BANK_HEADERS, rows)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["summary"]["campuses_created"] == 0
    assert data["summary"]["campus_conflicts"] == 0
    assert not data["warnings"]
    # still exactly 1 campus
    assert db.campuses.count_documents({"name": campus_name}) == 1


def test_conflict_row_keeps_master_and_warns(super_token):
    """Different account for existing campus -> master unchanged, warning issued,
    participant still processed."""
    campus_name = f"{TEST_CAMPUS_PREFIX}Alpha"
    # Snapshot pre-state
    pre = db.campuses.find_one({"name": campus_name})
    assert pre and pre.get("bank_account_cipher")
    pre_cipher = pre["bank_account_cipher"]

    rows = [
        [f"{TEST_PREFIX}A3", f"{TEST_NIK_PREFIX}00003",
         f"{TEST_PREFIX.lower()}a3{TEST_EMAIL_DOMAIN}", campus_name,
         "BCA", "9998887770", "Yayasan Lain"],
    ]
    r = _post_import(super_token, f"{TEST_PREFIX}conflict.xlsx", BANK_HEADERS, rows)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["summary"]["processed"] == 1
    assert data["summary"]["created"] == 1  # participant still created
    assert data["summary"]["failed"] == 0
    assert data["summary"]["campus_conflicts"] == 1
    assert data["summary"]["campuses_updated"] == 0
    assert data["warnings"], "Expected warnings list to be non-empty"
    w = data["warnings"][0]
    assert w.get("row_number") == 2
    assert "konflik" in w.get("message", "").lower() or "conflict" in w.get("message", "").lower()

    # Master unchanged
    after = db.campuses.find_one({"name": campus_name})
    assert after["bank_name"] == "BSI"
    assert after["bank_account_cipher"] == pre_cipher
    assert after["bank_account_holder_name"] == f"{campus_name} Yayasan"

    # Participant persisted
    u = db.users.find_one({"email": f"{TEST_PREFIX.lower()}a3{TEST_EMAIL_DOMAIN}"})
    assert u is not None
    assert db.registrations.find_one({"user_id": u["user_id"], "status": "lolos"}) is not None


def test_update_master_when_no_prior_bank(super_token):
    """Campus exists without bank info; providing full bank data should update it."""
    campus_name = f"{TEST_CAMPUS_PREFIX}Beta"
    # First: create campus via import WITHOUT bank data
    rows_no_bank = [[
        f"{TEST_PREFIX}B1", f"{TEST_NIK_PREFIX}00010",
        f"{TEST_PREFIX.lower()}b1{TEST_EMAIL_DOMAIN}", campus_name,
        "", "", "",
    ]]
    r = _post_import(super_token, f"{TEST_PREFIX}beta_new.xlsx", BANK_HEADERS, rows_no_bank)
    assert r.status_code == 200
    d1 = r.json()
    assert d1["summary"]["campuses_created"] == 1
    c1 = db.campuses.find_one({"name": campus_name})
    assert c1 is not None
    assert not c1.get("bank_name")
    assert not c1.get("bank_account_cipher")

    # Second: same campus + full bank data -> should UPDATE master
    rows_bank = [[
        f"{TEST_PREFIX}B2", f"{TEST_NIK_PREFIX}00011",
        f"{TEST_PREFIX.lower()}b2{TEST_EMAIL_DOMAIN}", campus_name,
        "Mandiri", "5551112223", "Yayasan Beta",
    ]]
    r = _post_import(super_token, f"{TEST_PREFIX}beta_upd.xlsx", BANK_HEADERS, rows_bank)
    assert r.status_code == 200
    d2 = r.json()
    assert d2["summary"]["campuses_created"] == 0
    assert d2["summary"]["campuses_updated"] == 1
    assert d2["summary"]["campus_conflicts"] == 0
    c2 = db.campuses.find_one({"name": campus_name})
    assert c2["bank_name"] == "Mandiri"
    assert c2["bank_account_holder_name"] == "Yayasan Beta"
    assert c2.get("bank_account_cipher")


def test_account_without_holder_is_non_destructive_warning(super_token):
    """Account number provided but holder missing -> cipher NOT stored, warning added,
    campus still created (no bank fields)."""
    campus_name = f"{TEST_CAMPUS_PREFIX}Gamma"
    rows = [[
        f"{TEST_PREFIX}G1", f"{TEST_NIK_PREFIX}00020",
        f"{TEST_PREFIX.lower()}g1{TEST_EMAIL_DOMAIN}", campus_name,
        "BNI", "7778889990", "",  # holder empty
    ]]
    r = _post_import(super_token, f"{TEST_PREFIX}gamma.xlsx", BANK_HEADERS, rows)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["summary"]["campuses_created"] == 1
    assert data["summary"]["campus_conflicts"] == 1  # counted as warning
    assert data["warnings"]
    msg = data["warnings"][0]["message"].lower()
    assert "pemilik" in msg or "holder" in msg

    c = db.campuses.find_one({"name": campus_name})
    assert c is not None
    assert c.get("bank_name") == "BNI"  # bank name OK to store
    assert not c.get("bank_account_cipher"), "account cipher must NOT be stored w/o holder"
    assert not c.get("bank_account_holder_name")


# ---------- Campus list endpoint ----------

def test_campus_list_shows_bank_name_for_super_admin(super_token):
    r = requests.get(f"{API}/campuses", headers=_hdr(super_token), timeout=30)
    assert r.status_code == 200
    items = r.json()
    alpha = next((c for c in items if c["name"] == f"{TEST_CAMPUS_PREFIX}Alpha"), None)
    assert alpha is not None
    assert alpha.get("bank_name") == "BSI"
    assert alpha.get("has_bank_account") is True
    # Raw account NOT leaked in list
    assert "bank_account_cipher" not in alpha
    assert "1234567890" not in json.dumps(alpha)
    # Masked account may be present
    masked = alpha.get("bank_account_number_masked", "")
    assert "1234567890" not in masked
