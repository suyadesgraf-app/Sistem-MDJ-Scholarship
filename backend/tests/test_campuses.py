"""Backend regression tests for the Kampus (Campus) admin feature."""
import io
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or "http://localhost:8001"
API = f"{BASE_URL}/api"
XLSX_PATH = "/tmp/cms-masa-depan-jakarta.xlsx"

ADMIN = {"email": "admin.mdj@baznasbazisdki.id", "password": "AdminMDJ2026!"}
STUDENT = {"email": "mahasiswa.mdj@baznasbazisdki.id", "password": "MahasiswaMDJ2026!"}


class _Client:
    def __init__(self, token):
        self.headers = {"Authorization": f"Bearer {token}"}

    def get(self, url, **kw):
        return requests.get(url, headers={**self.headers, **kw.pop("headers", {})}, **kw)

    def post(self, url, **kw):
        h = dict(self.headers)
        # only set json content-type when not multipart
        if "files" not in kw and "json" in kw:
            h["Content-Type"] = "application/json"
        h.update(kw.pop("headers", {}))
        return requests.post(url, headers=h, **kw)

    def put(self, url, **kw):
        h = {**self.headers, "Content-Type": "application/json", **kw.pop("headers", {})}
        return requests.put(url, headers=h, **kw)

    def delete(self, url, **kw):
        return requests.delete(url, headers={**self.headers, **kw.pop("headers", {})}, **kw)


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=20)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return _Client(r.json()["token"])


@pytest.fixture(scope="module")
def admin_client():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def student_client():
    return _login(STUDENT)


# ---------------- GET /campuses ----------------
def test_student_can_list_campuses_expects_377_unique(student_client):
    r = student_client.get(f"{API}/campuses", timeout=20)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    # 377 base seed + 24 DEMO-TF-* campuses added for transfer-proof demo = 401 minimum.
    # Allow additional test-created campuses.
    assert len(data) >= 377, f"expected >=377 unique campuses, got {len(data)}"
    demo = [c for c in data if str(c.get("code", "")).startswith("DEMO-TF-")]
    assert len(demo) == 24, f"expected 24 DEMO-TF- campuses, got {len(demo)}"
    # Ensure student never sees campus bank data
    for c in data:
        assert "bank_account_holder_name" not in c
        assert "bank_account_number_masked" not in c
        assert "bank_account_cipher" not in c
        assert "has_bank_account" not in c
    # No Mongo _id leak
    for c in data:
        assert "_id" not in c
        assert "id" in c and "name" in c
    # STIKES RS Husada Jakarta with code 01-JK1-001 exists
    husada = [c for c in data if c.get("code") == "01-JK1-001"]
    assert husada, "STIKES RS Husada Jakarta (01-JK1-001) not found"
    assert "husada" in husada[0]["name"].lower()


# ---------------- Admin CRUD ----------------
def test_admin_full_crud_cycle(admin_client):
    # CREATE
    payload = {"name": "TEST_Kampus Unit Alpha", "code": "TEST-ALPHA-001"}
    r = admin_client.post(f"{API}/campuses", json=payload, timeout=20)
    assert r.status_code == 200, r.text
    created = r.json()
    assert created["name"] == payload["name"]
    assert created["code"] == payload["code"]
    cid = created["id"]

    # duplicate name/code rejected
    dup = admin_client.post(f"{API}/campuses", json=payload, timeout=20)
    assert dup.status_code == 400

    # GET list contains new campus (persistence check)
    lst = admin_client.get(f"{API}/campuses", timeout=20).json()
    assert any(c["id"] == cid for c in lst)

    # UPDATE
    upd = admin_client.put(
        f"{API}/campuses/{cid}",
        json={"name": "TEST_Kampus Unit Beta", "code": "TEST-BETA-001"},
        timeout=20,
    )
    assert upd.status_code == 200, upd.text
    lst = admin_client.get(f"{API}/campuses", timeout=20).json()
    updated = next(c for c in lst if c["id"] == cid)
    assert updated["name"] == "TEST_Kampus Unit Beta"
    assert updated["code"] == "TEST-BETA-001"

    # DELETE (cleanup)
    d = admin_client.delete(f"{API}/campuses/{cid}", timeout=20)
    assert d.status_code == 200
    lst = admin_client.get(f"{API}/campuses", timeout=20).json()
    assert not any(c["id"] == cid for c in lst)


# ---------------- Idempotent import ----------------
def test_reimport_xlsx_is_idempotent_final_377(admin_client):
    if not os.path.exists(XLSX_PATH):
        pytest.skip(f"{XLSX_PATH} not present")
    before = admin_client.get(f"{API}/campuses", timeout=20).json()
    before_count = len(before)
    with open(XLSX_PATH, "rb") as fh:
        files = {"file": ("cms-masa-depan-jakarta.xlsx", fh,
                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        r = admin_client.post(f"{API}/campuses/import", files=files, timeout=60)
    assert r.status_code == 200, r.text
    body = r.json()
    # On re-import, nothing should be inserted; all rows update in place
    assert body["inserted"] == 0, f"expected 0 new inserts on re-import, got {body}"
    after = admin_client.get(f"{API}/campuses", timeout=20).json()
    assert len(after) == before_count == 377, f"before={before_count} after={len(after)}"


# ---------------- Bank-account (Nomor Rekening) feature ----------------
MASK_CHAR = "\u2022"  # backend uses U+2022 BULLET


def _mask_of(digits: str) -> str:
    """Client-side expectation of masking: keep last 4, mask others."""
    d = "".join(ch for ch in digits if ch.isdigit())
    if len(d) <= 4:
        return d
    return MASK_CHAR * (len(d) - 4) + d[-4:]


def test_admin_create_update_campus_with_bank_returns_masked(admin_client):
    """Campus create/update accepts holder+account; response exposes masked only, no cipher."""
    payload = {
        "name": "TEST_Kampus Rekening Alpha",
        "code": "TEST-BANK-ALPHA",
        "bank_account_holder_name": "YAYASAN TEST ALPHA",
        "bank_account_number": "1234567890",
    }
    r = admin_client.post(f"{API}/campuses", json=payload, timeout=20)
    assert r.status_code == 200, r.text
    created = r.json()
    try:
        # Response never exposes raw account nor cipher
        assert "bank_account_cipher" not in created
        assert created.get("bank_account_holder_name") == "YAYASAN TEST ALPHA"
        assert created.get("has_bank_account") is True
        assert created["bank_account_number_masked"] == _mask_of("1234567890")
        assert "1234567890" not in created["bank_account_number_masked"][:-4]

        # UPDATE: change holder + number
        upd = admin_client.put(
            f"{API}/campuses/{created['id']}",
            json={
                "name": payload["name"],
                "code": payload["code"],
                "bank_account_holder_name": "YAYASAN TEST BETA",
                "bank_account_number": "9876543210",
            },
            timeout=20,
        )
        assert upd.status_code == 200, upd.text
        u = upd.json()
        assert "bank_account_cipher" not in u
        assert u["bank_account_holder_name"] == "YAYASAN TEST BETA"
        assert u["bank_account_number_masked"] == _mask_of("9876543210")

        # GET list as admin: masked visible, no cipher
        lst = admin_client.get(f"{API}/campuses", timeout=20).json()
        item = next(c for c in lst if c["id"] == created["id"])
        assert "bank_account_cipher" not in item
        assert item["bank_account_number_masked"] == _mask_of("9876543210")
        assert item["has_bank_account"] is True
    finally:
        admin_client.delete(f"{API}/campuses/{created['id']}", timeout=20)


def test_admin_create_bank_requires_holder_when_number_given(admin_client):
    payload = {
        "name": "TEST_Kampus Rekening NoHolder",
        "bank_account_number": "1234567890",
    }
    r = admin_client.post(f"{API}/campuses", json=payload, timeout=20)
    assert r.status_code == 400, r.text
    assert "pemilik rekening" in r.text.lower()


def test_admin_create_bank_rejects_bad_length(admin_client):
    payload = {
        "name": "TEST_Kampus Rekening BadLen",
        "bank_account_holder_name": "YAYASAN TEST",
        "bank_account_number": "123",  # too short
    }
    r = admin_client.post(f"{API}/campuses", json=payload, timeout=20)
    assert r.status_code == 400
    assert "6" in r.text or "24" in r.text or "digit" in r.text.lower()


def test_student_never_receives_bank_fields(student_client):
    """Student sees no holder / masked / cipher / has_bank_account keys."""
    r = student_client.get(f"{API}/campuses", timeout=20)
    assert r.status_code == 200
    for c in r.json():
        for banned in (
            "bank_account_holder_name",
            "bank_account_number_masked",
            "bank_account_cipher",
            "has_bank_account",
        ):
            assert banned not in c, f"student saw '{banned}' on campus {c.get('code')}"


def test_admin_sees_demo_masters_masked_only(admin_client):
    """The 24 DEMO-TF-* seeded masters must show holder+masked but no cipher/raw."""
    lst = admin_client.get(f"{API}/campuses", timeout=20).json()
    demo = [c for c in lst if str(c.get("code", "")).startswith("DEMO-TF-")]
    assert len(demo) == 24
    for c in demo:
        assert "bank_account_cipher" not in c
        assert c.get("has_bank_account") is True
        assert c.get("bank_account_holder_name"), c
        masked = c.get("bank_account_number_masked", "")
        assert masked, c
        # Masked format: majority stars, last 4 digits visible
        assert masked.startswith(MASK_CHAR), masked
        assert masked[-4:].isdigit(), masked


def test_admin_wilayah_never_receives_bank_fields():
    """Admin Wilayah (regional admin) must not see campus banking data."""
    import uuid as _uuid
    # Login as super admin to create ephemeral admin_wilayah
    su = requests.post(f"{API}/auth/login",
                       json={"email": "supri@baznasbazisdki.id",
                             "password": "MdjSuper2026!"}, timeout=20)
    assert su.status_code == 200
    su_tok = su.json()["token"]
    su_hdr = {"Authorization": f"Bearer {su_tok}"}
    email = f"test_bank_wil_{_uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{API}/admin/users", headers=su_hdr, timeout=20,
                      json={"name": "TEST Bank Wil", "email": email,
                            "password": "Password123!", "role": "admin_wilayah",
                            "region": "Jakarta Utara"})
    assert r.status_code == 200, r.text
    try:
        wil = requests.post(f"{API}/auth/login",
                            json={"email": email, "password": "Password123!"}, timeout=20)
        assert wil.status_code == 200, wil.text
        wil_hdr = {"Authorization": f"Bearer {wil.json()['token']}"}
        lst = requests.get(f"{API}/campuses", headers=wil_hdr, timeout=20).json()
        assert isinstance(lst, list) and len(lst) > 0
        for c in lst:
            for banned in (
                "bank_account_holder_name",
                "bank_account_number_masked",
                "bank_account_cipher",
                "has_bank_account",
            ):
                assert banned not in c, f"admin_wilayah leaked '{banned}'"
    finally:
        # cleanup - list users and delete
        users = requests.get(f"{API}/admin/users", headers=su_hdr, timeout=20).json()
        target = next((u for u in users if u.get("email") == email), None)
        if target:
            requests.delete(f"{API}/admin/users/{target['user_id']}",
                            headers=su_hdr, timeout=20)



# ---------------- 403 for student on admin ops ----------------
def test_student_cannot_mutate_campuses(student_client):
    # POST
    r = student_client.post(f"{API}/campuses", json={"name": "TEST_hack"}, timeout=20)
    assert r.status_code == 403
    # PUT (needs an id — use a fake uuid)
    r = student_client.put(f"{API}/campuses/00000000-0000-0000-0000-000000000000",
                           json={"name": "TEST_hack"}, timeout=20)
    assert r.status_code == 403
    # DELETE
    r = student_client.delete(f"{API}/campuses/00000000-0000-0000-0000-000000000000", timeout=20)
    assert r.status_code == 403
    # IMPORT
    files = {"file": ("x.xlsx", io.BytesIO(b"dummy"),
                      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    r = student_client.post(f"{API}/campuses/import", files=files, timeout=20)
    assert r.status_code == 403
