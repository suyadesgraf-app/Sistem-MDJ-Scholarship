"""Regression tests for Admin Wilayah (regional admin) RBAC and data scoping."""
import os
import uuid
from datetime import datetime, timezone

import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

SUPER_EMAIL = "supri@baznasbazisdki.id"
SUPER_PASSWORD = "MdjSuper2026!"
ADMIN_EMAIL = "admin.mdj@baznasbazisdki.id"
ADMIN_PASSWORD = "AdminMDJ2026!"

TEST_TAG = "TEST_admin_wilayah"

client = MongoClient(MONGO_URL)
db = client[DB_NAME]


def _login(email: str, password: str) -> str:
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _hdr(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _cleanup():
    # Remove all TEST_ tagged data
    users = list(db.users.find({"test_tag": TEST_TAG}, {"user_id": 1}))
    uids = [u["user_id"] for u in users]
    if uids:
        db.profiles.delete_many({"user_id": {"$in": uids}})
        db.registrations.delete_many({"user_id": {"$in": uids}})
        db.documents.delete_many({"user_id": {"$in": uids}})
        db.notifications.delete_many({"user_id": {"$in": uids}})
    db.users.delete_many({"test_tag": TEST_TAG})
    # Also purge admin_wilayah accounts with TEST_ prefix email
    db.users.delete_many({"email": {"$regex": "^test_admin_wilayah_"}})


@pytest.fixture(scope="module", autouse=True)
def cleanup_before_after():
    _cleanup()
    yield
    _cleanup()


@pytest.fixture(scope="module")
def super_token():
    return _login(SUPER_EMAIL, SUPER_PASSWORD)


@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture(scope="module")
def seeded_participants():
    """Create 2 participants: 1 Jakarta Barat, 1 Jakarta Timur."""
    users = []
    for region in ("Jakarta Barat", "Jakarta Timur"):
        uid = f"user_{uuid.uuid4().hex[:12]}"
        email = f"test_admin_wilayah_p_{uid}@contoh.invalid"
        now = datetime.now(timezone.utc).isoformat()
        db.users.insert_one({
            "user_id": uid, "email": email, "name": f"TEST Peserta {region}",
            "role": "student", "auth_provider": "password",
            "password_hash": "$2b$12$abcdefghijklmnopqrstuv",
            "is_active": True, "created_at": now, "test_tag": TEST_TAG,
        })
        db.profiles.insert_one({
            "user_id": uid,
            "data": {"kota": region, "provinsi": "DKI Jakarta", "institusi": "Kampus Uji",
                     "jenjang": "S1", "nim": "123", "jurusan": "Uji", "semester": "3", "ipk": "3.5"},
            "created_at": now,
        })
        db.registrations.insert_one({
            "user_id": uid, "name": f"TEST Peserta {region}", "email": email,
            "status": "submitted", "created_at": now, "submitted_at": now, "history": [],
        })
        users.append({"user_id": uid, "region": region, "email": email})
    yield users


# --- Super admin: create regional admin ---
def test_super_admin_creates_regional_admin(super_token):
    email = f"test_admin_wilayah_jb_{uuid.uuid4().hex[:6]}@example.com"
    r = requests.post(f"{BASE_URL}/api/admin/users", headers=_hdr(super_token), timeout=20,
                      json={"name": "TEST Admin Barat", "email": email, "password": "Password123!",
                            "role": "admin_wilayah", "region": "Jakarta Barat"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["role"] == "admin_wilayah"
    assert body["region"] == "Jakarta Barat"


def test_super_admin_creates_regional_admin_requires_region(super_token):
    email = f"test_admin_wilayah_nore_{uuid.uuid4().hex[:6]}@example.com"
    r = requests.post(f"{BASE_URL}/api/admin/users", headers=_hdr(super_token), timeout=20,
                      json={"name": "TEST NoRegion", "email": email, "password": "Password123!",
                            "role": "admin_wilayah"})
    assert r.status_code == 400


def test_super_admin_creates_regional_admin_invalid_region(super_token):
    email = f"test_admin_wilayah_bad_{uuid.uuid4().hex[:6]}@example.com"
    r = requests.post(f"{BASE_URL}/api/admin/users", headers=_hdr(super_token), timeout=20,
                      json={"name": "TEST Bad", "email": email, "password": "Password123!",
                            "role": "admin_wilayah", "region": "Bandung"})
    assert r.status_code == 400


# --- Admin/PIC creates regional admin OK; cannot create admin/super_admin ---
def test_admin_pic_can_create_regional_admin(admin_token):
    email = f"test_admin_wilayah_pic_{uuid.uuid4().hex[:6]}@example.com"
    r = requests.post(f"{BASE_URL}/api/admin/users", headers=_hdr(admin_token), timeout=20,
                      json={"name": "TEST PIC Created", "email": email, "password": "Password123!",
                            "role": "admin_wilayah", "region": "Jakarta Timur"})
    assert r.status_code == 200, r.text
    assert r.json()["region"] == "Jakarta Timur"


def test_admin_pic_cannot_create_admin_role(admin_token):
    email = f"test_admin_wilayah_admin_{uuid.uuid4().hex[:6]}@example.com"
    r = requests.post(f"{BASE_URL}/api/admin/users", headers=_hdr(admin_token), timeout=20,
                      json={"name": "TEST Admin", "email": email, "password": "Password123!",
                            "role": "admin"})
    assert r.status_code == 400


def test_admin_pic_cannot_create_super_admin_role(admin_token):
    email = f"test_admin_wilayah_super_{uuid.uuid4().hex[:6]}@example.com"
    r = requests.post(f"{BASE_URL}/api/admin/users", headers=_hdr(admin_token), timeout=20,
                      json={"name": "TEST Super", "email": email, "password": "Password123!",
                            "role": "super_admin"})
    assert r.status_code == 400


# --- Setup: create a Jakarta Barat regional admin with known password for scope tests ---
@pytest.fixture(scope="module")
def jb_regional_admin(super_token):
    email = f"test_admin_wilayah_scope_{uuid.uuid4().hex[:6]}@example.com"
    password = "Password123!"
    r = requests.post(f"{BASE_URL}/api/admin/users", headers=_hdr(super_token), timeout=20,
                      json={"name": "TEST Scope JB", "email": email, "password": password,
                            "role": "admin_wilayah", "region": "Jakarta Barat"})
    assert r.status_code == 200, r.text
    token = _login(email, password)
    return {"email": email, "token": token, "user_id": r.json()["user_id"]}


# --- Regional admin sees only own region participants ---
def test_regional_admin_lists_only_own_region(jb_regional_admin, seeded_participants):
    r = requests.get(f"{BASE_URL}/api/admin/participants", headers=_hdr(jb_regional_admin["token"]), timeout=20)
    assert r.status_code == 200
    items = r.json()
    for item in items:
        assert item.get("wilayah") == "Jakarta Barat", item.get("wilayah")
    # our JB seed must be present
    uids = [i["user_id"] for i in items]
    jb = next(p for p in seeded_participants if p["region"] == "Jakarta Barat")
    jt = next(p for p in seeded_participants if p["region"] == "Jakarta Timur")
    assert jb["user_id"] in uids
    assert jt["user_id"] not in uids


def test_regional_admin_region_all_still_scoped(jb_regional_admin, seeded_participants):
    r = requests.get(f"{BASE_URL}/api/admin/participants?region=all",
                     headers=_hdr(jb_regional_admin["token"]), timeout=20)
    assert r.status_code == 200
    jt_uid = next(p["user_id"] for p in seeded_participants if p["region"] == "Jakarta Timur")
    for item in r.json():
        assert item.get("wilayah") == "Jakarta Barat"
        assert item["user_id"] != jt_uid


def test_regional_admin_region_other_still_scoped(jb_regional_admin, seeded_participants):
    r = requests.get(f"{BASE_URL}/api/admin/participants?region=Jakarta Timur",
                     headers=_hdr(jb_regional_admin["token"]), timeout=20)
    assert r.status_code == 200
    for item in r.json():
        assert item.get("wilayah") == "Jakarta Barat"


def test_regional_admin_stats_scoped(jb_regional_admin):
    r = requests.get(f"{BASE_URL}/api/admin/stats?region=Jakarta Timur",
                     headers=_hdr(jb_regional_admin["token"]), timeout=20)
    assert r.status_code == 200
    data = r.json()
    assert data["selected_region"] == "Jakarta Barat"
    assert data["available_regions"] == ["Jakarta Barat"]


def test_regional_admin_detail_cross_region_404(jb_regional_admin, seeded_participants):
    jt_uid = next(p["user_id"] for p in seeded_participants if p["region"] == "Jakarta Timur")
    r = requests.get(f"{BASE_URL}/api/admin/participants/{jt_uid}",
                     headers=_hdr(jb_regional_admin["token"]), timeout=20)
    assert r.status_code == 404


def test_regional_admin_status_update_cross_region_404(jb_regional_admin, seeded_participants):
    jt_uid = next(p["user_id"] for p in seeded_participants if p["region"] == "Jakarta Timur")
    r = requests.put(f"{BASE_URL}/api/admin/participants/{jt_uid}/status",
                     headers=_hdr(jb_regional_admin["token"]), timeout=20,
                     json={"status": "verifikasi"})
    assert r.status_code == 404


def test_regional_admin_detail_own_region_ok(jb_regional_admin, seeded_participants):
    jb_uid = next(p["user_id"] for p in seeded_participants if p["region"] == "Jakarta Barat")
    r = requests.get(f"{BASE_URL}/api/admin/participants/{jb_uid}",
                     headers=_hdr(jb_regional_admin["token"]), timeout=20)
    assert r.status_code == 200


def test_regional_admin_cannot_list_admin_users(jb_regional_admin):
    r = requests.get(f"{BASE_URL}/api/admin/users",
                     headers=_hdr(jb_regional_admin["token"]), timeout=20)
    assert r.status_code == 403


def test_regional_admin_cannot_create_admin_users(jb_regional_admin):
    r = requests.post(f"{BASE_URL}/api/admin/users",
                      headers=_hdr(jb_regional_admin["token"]), timeout=20,
                      json={"name": "x", "email": "x@example.com", "password": "Password123!",
                            "role": "admin_wilayah", "region": "Jakarta Barat"})
    assert r.status_code == 403


def test_regional_admin_export_scoped(jb_regional_admin, seeded_participants):
    r = requests.get(f"{BASE_URL}/api/admin/participants/export.xlsx?region=all",
                     headers=_hdr(jb_regional_admin["token"]), timeout=30)
    assert r.status_code == 200
    assert "spreadsheet" in r.headers.get("content-type", "").lower() or \
           "openxml" in r.headers.get("content-type", "").lower()
    # ensure JT peserta email not embedded in binary
    jt_email = next(p["email"] for p in seeded_participants if p["region"] == "Jakarta Timur")
    assert jt_email.encode() not in r.content


# --- Provincial admin still manages everything ---
def test_admin_pic_sees_all_regions(admin_token, seeded_participants):
    r = requests.get(f"{BASE_URL}/api/admin/participants",
                     headers=_hdr(admin_token), timeout=20)
    assert r.status_code == 200
    uids = [i["user_id"] for i in r.json()]
    for p in seeded_participants:
        assert p["user_id"] in uids


def test_super_admin_toggle_and_delete_regional_admin(super_token):
    email = f"test_admin_wilayah_toggle_{uuid.uuid4().hex[:6]}@example.com"
    r = requests.post(f"{BASE_URL}/api/admin/users", headers=_hdr(super_token), timeout=20,
                      json={"name": "TEST Toggle", "email": email, "password": "Password123!",
                            "role": "admin_wilayah", "region": "Jakarta Selatan"})
    assert r.status_code == 200
    uid = r.json()["user_id"]
    r2 = requests.put(f"{BASE_URL}/api/admin/users/{uid}",
                      headers=_hdr(super_token), timeout=20, json={"is_active": False})
    assert r2.status_code == 200
    r3 = requests.delete(f"{BASE_URL}/api/admin/users/{uid}",
                         headers=_hdr(super_token), timeout=20)
    assert r3.status_code == 200


def test_admin_pic_can_toggle_and_delete_regional_admin_only(admin_token, super_token):
    # Create a regional admin as admin/PIC
    email = f"test_admin_wilayah_pic_del_{uuid.uuid4().hex[:6]}@example.com"
    r = requests.post(f"{BASE_URL}/api/admin/users", headers=_hdr(admin_token), timeout=20,
                      json={"name": "TEST PIC Del", "email": email, "password": "Password123!",
                            "role": "admin_wilayah", "region": "Jakarta Utara"})
    assert r.status_code == 200
    uid = r.json()["user_id"]
    r2 = requests.delete(f"{BASE_URL}/api/admin/users/{uid}",
                         headers=_hdr(admin_token), timeout=20)
    assert r2.status_code == 200

    # Admin/PIC should NOT be able to delete a super_admin
    supri = db.users.find_one({"email": SUPER_EMAIL}, {"user_id": 1})
    if supri:
        r3 = requests.delete(f"{BASE_URL}/api/admin/users/{supri['user_id']}",
                             headers=_hdr(admin_token), timeout=20)
        assert r3.status_code == 404
