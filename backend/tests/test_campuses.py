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
    assert len(data) == 377, f"expected 377 unique campuses, got {len(data)}"
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
