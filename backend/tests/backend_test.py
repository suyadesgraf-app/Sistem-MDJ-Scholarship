"""
Backend integration tests for MDJ Scholarship portal.
Covers auth, profile, registration, documents, site content, admin, and role gating.
"""
import io
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://sistem-registrasi.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

SUPER_EMAIL = "supri@baznasbazisdki.id"
SUPER_PASS = "MdjSuper2026!"


# ---------- helpers ----------
def _post(path, token=None, **kwargs):
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return requests.post(f"{API}{path}", headers=headers, timeout=60, **kwargs)


def _get(path, token=None, **kwargs):
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return requests.get(f"{API}{path}", headers=headers, timeout=60, **kwargs)


def _put(path, token=None, **kwargs):
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return requests.put(f"{API}{path}", headers=headers, timeout=60, **kwargs)


def _delete(path, token=None, **kwargs):
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return requests.delete(f"{API}{path}", headers=headers, timeout=60, **kwargs)


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def super_token():
    r = _post("/auth/login", json={"email": SUPER_EMAIL, "password": SUPER_PASS})
    assert r.status_code == 200, f"super admin login failed: {r.status_code} {r.text}"
    body = r.json()
    assert body["user"]["role"] == "super_admin"
    return body["token"]


@pytest.fixture(scope="module")
def student():
    email = f"test_stud_{uuid.uuid4().hex[:8]}@example.com"
    r = _post("/auth/register", json={"name": "Test Student", "email": email, "password": "Passw0rd!", "nik": "3175000000000001", "phone": "0811111111"})
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    body = r.json()
    assert body["user"]["role"] == "student"
    return {"token": body["token"], "user": body["user"], "email": email, "password": "Passw0rd!"}


@pytest.fixture(scope="module")
def admin_account(super_token):
    email = f"TEST_admin_{uuid.uuid4().hex[:8]}@example.com"
    r = _post("/admin/users", token=super_token,
              json={"name": "Test Admin", "email": email, "password": "AdminPass1!", "role": "admin"})
    assert r.status_code == 200, f"create admin failed: {r.status_code} {r.text}"
    admin_user = r.json()
    # login as admin
    r2 = _post("/auth/login", json={"email": email, "password": "AdminPass1!"})
    assert r2.status_code == 200
    return {"token": r2.json()["token"], "user": admin_user, "email": email}


# ---------- Auth ----------
class TestAuth:
    def test_register_and_me(self, student):
        r = _get("/auth/me", token=student["token"])
        assert r.status_code == 200
        assert r.json()["email"] == student["email"]

    def test_login_invalid(self):
        r = _post("/auth/login", json={"email": "nonexistent@ex.com", "password": "bad"})
        assert r.status_code == 401

    def test_duplicate_register(self, student):
        r = _post("/auth/register", json={"name": "x", "email": student["email"], "password": "x1234567"})
        assert r.status_code == 400

    def test_super_admin_login(self, super_token):
        assert super_token

    def test_unauth_me(self):
        r = _get("/auth/me")
        assert r.status_code == 401


# ---------- Profile ----------
class TestProfile:
    def test_get_default_profile(self, student):
        r = _get("/profile", token=student["token"])
        assert r.status_code == 200
        data = r.json().get("data", {})
        assert data.get("email") == student["email"]

    def test_update_profile_and_persist(self, student):
        payload = {"data": {"namaLengkap": "Test Student", "email": student["email"], "institusi": "UI", "jenjang": "S1", "noTelp": "0812"}}
        r = _put("/profile", token=student["token"], json=payload)
        assert r.status_code == 200
        r2 = _get("/profile", token=student["token"])
        assert r2.json()["data"]["institusi"] == "UI"


# ---------- Registration ----------
class TestRegistration:
    def test_create_draft(self, student):
        r = _post("/registration", token=student["token"], json={"category": "Reguler", "action": "draft"})
        assert r.status_code == 200
        assert r.json()["status"] == "draft"

    def test_submit(self, student):
        r = _post("/registration", token=student["token"], json={"category": "Reguler", "action": "submit"})
        assert r.status_code == 200
        assert r.json()["status"] == "submitted"

    def test_get(self, student):
        r = _get("/registration", token=student["token"])
        assert r.status_code == 200
        assert r.json().get("category") == "Reguler"


# ---------- Documents ----------
class TestDocuments:
    def test_upload_and_list(self, student):
        files = {"file": ("test.pdf", io.BytesIO(b"%PDF-1.4 test"), "application/pdf")}
        data = {"doc_type": "ktp"}
        r = _post("/documents", token=student["token"], files=files, data=data)
        assert r.status_code == 200, r.text
        doc_id = r.json()["id"]
        r2 = _get("/documents", token=student["token"])
        assert r2.status_code == 200
        assert any(d["id"] == doc_id for d in r2.json())

    def test_upload_same_type_replaces(self, student):
        files = {"file": ("test2.pdf", io.BytesIO(b"%PDF-1.4 v2"), "application/pdf")}
        r = _post("/documents", token=student["token"], files=files, data={"doc_type": "ktp"})
        assert r.status_code == 200
        r2 = _get("/documents", token=student["token"])
        ktps = [d for d in r2.json() if d["doc_type"] == "ktp"]
        assert len(ktps) == 1

    def test_delete_doc(self, student):
        files = {"file": ("f.png", io.BytesIO(b"\x89PNG\r\n"), "image/png")}
        r = _post("/documents", token=student["token"], files=files, data={"doc_type": "foto"})
        doc_id = r.json()["id"]
        r2 = _delete(f"/documents/{doc_id}", token=student["token"])
        assert r2.status_code == 200
        r3 = _get("/documents", token=student["token"])
        assert not any(d["id"] == doc_id for d in r3.json())


# ---------- Site Content ----------
class TestSiteContent:
    def test_public_get(self):
        r = _get("/site/content")
        assert r.status_code == 200
        body = r.json()
        assert "hero" in body and "timeline" in body and "faqs" in body

    def test_update_by_super(self, super_token):
        new_stats = [{"label": "TEST_metric", "value": "99"}]
        r = _put("/site/content", token=super_token, json={"content": {"stats": new_stats}})
        assert r.status_code == 200
        r2 = _get("/site/content")
        assert r2.json()["stats"][0]["label"] == "TEST_metric"

    def test_update_forbidden_for_student(self, student):
        r = _put("/site/content", token=student["token"], json={"content": {"stats": []}})
        assert r.status_code == 403

    def test_upload_banner(self, super_token):
        files = {"file": ("banner.png", io.BytesIO(b"\x89PNG\r\ntest"), "image/png")}
        r = _post("/site/banner", token=super_token, files=files)
        assert r.status_code == 200, r.text
        assert r.json()["banner_url"].startswith("/api/files/")


# ---------- Admin: participants ----------
class TestAdminParticipants:
    def test_stats(self, super_token):
        r = _get("/admin/stats", token=super_token)
        assert r.status_code == 200
        body = r.json()
        for k in ["total_registrations", "total_students", "total_admins", "by_status"]:
            assert k in body

    def test_list_participants(self, super_token, student):
        r = _get("/admin/participants", token=super_token)
        assert r.status_code == 200
        assert any(p["user_id"] == student["user"]["user_id"] for p in r.json())

    def test_search_filter(self, super_token, student):
        r = _get("/admin/participants", token=super_token, params={"search": student["email"]})
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_participant_detail(self, super_token, student):
        r = _get(f"/admin/participants/{student['user']['user_id']}", token=super_token)
        assert r.status_code == 200
        body = r.json()
        assert body["account"]["email"] == student["email"]
        assert "documents" in body

    def test_update_status(self, super_token, student):
        r = _put(f"/admin/participants/{student['user']['user_id']}/status",
                 token=super_token, json={"status": "verifikasi", "note": "OK"})
        assert r.status_code == 200
        assert r.json()["status"] == "verifikasi"

    def test_invalid_status(self, super_token, student):
        r = _put(f"/admin/participants/{student['user']['user_id']}/status",
                 token=super_token, json={"status": "bogus"})
        assert r.status_code == 400


# ---------- Super admin: users ----------
class TestAdminUsers:
    def test_list_users(self, super_token):
        r = _get("/admin/users", token=super_token)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_admin(self, admin_account):
        assert admin_account["user"]["role"] == "admin"

    def test_toggle_admin(self, super_token, admin_account):
        r = _put(f"/admin/users/{admin_account['user']['user_id']}",
                 token=super_token, json={"is_active": False})
        assert r.status_code == 200
        # reactivate
        _put(f"/admin/users/{admin_account['user']['user_id']}", token=super_token, json={"is_active": True})

    def test_cannot_deactivate_self(self, super_token):
        # get self id
        me = _get("/auth/me", token=super_token).json()
        r = _put(f"/admin/users/{me['user_id']}", token=super_token, json={"is_active": False})
        assert r.status_code == 400

    def test_cannot_delete_primary_super(self, super_token):
        me = _get("/auth/me", token=super_token).json()
        r = _delete(f"/admin/users/{me['user_id']}", token=super_token)
        assert r.status_code == 400

    def test_delete_created_admin(self, super_token):
        # create a temp admin then delete
        email = f"TEST_del_{uuid.uuid4().hex[:8]}@example.com"
        rc = _post("/admin/users", token=super_token,
                   json={"name": "Del", "email": email, "password": "Passw0rd!", "role": "admin"})
        uid = rc.json()["user_id"]
        rd = _delete(f"/admin/users/{uid}", token=super_token)
        assert rd.status_code == 200


# ---------- Role gating ----------
class TestRoleGating:
    def test_student_cannot_list_participants(self, student):
        r = _get("/admin/participants", token=student["token"])
        assert r.status_code == 403

    def test_student_cannot_get_stats(self, student):
        r = _get("/admin/stats", token=student["token"])
        assert r.status_code == 403

    def test_admin_cannot_create_admin(self, admin_account):
        email = f"TEST_x_{uuid.uuid4().hex[:8]}@example.com"
        r = _post("/admin/users", token=admin_account["token"],
                  json={"name": "x", "email": email, "password": "Passw0rd!", "role": "admin"})
        assert r.status_code == 403

    def test_admin_can_list_participants(self, admin_account):
        r = _get("/admin/participants", token=admin_account["token"])
        assert r.status_code == 200

    def test_admin_cannot_update_site(self, admin_account):
        r = _put("/site/content", token=admin_account["token"], json={"content": {}})
        assert r.status_code == 403
