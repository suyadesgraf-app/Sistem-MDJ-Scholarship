"""Iter41: Site content (Syarat & Kelengkapan Berkas) — GET public, PUT super_admin only, RBAC."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
API = f"{BASE_URL}/api"

SUPER = {"email": "supri@baznasbazisdki.id", "password": "MdjSuper2026!"}
ADMIN = {"email": "admin.mdj@baznasbazisdki.id", "password": "AdminMDJ2026!"}
STUDENT = {"email": "mahasiswa.mdj@baznasbazisdki.id", "password": "MahasiswaMDJ2026!"}


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login failed for {creds['email']}: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def super_token():
    return _login(SUPER)


@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def student_token():
    return _login(STUDENT)


@pytest.fixture(scope="module")
def original_content():
    r = requests.get(f"{API}/site/content", timeout=30)
    assert r.status_code == 200
    data = r.json()
    return {
        "eligibility_requirements": list(data.get("eligibility_requirements") or []),
        "required_documents": list(data.get("required_documents") or []),
    }


# --- Public GET ---
def test_public_get_site_content_lists_counts():
    r = requests.get(f"{API}/site/content", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data.get("eligibility_requirements"), list)
    assert isinstance(data.get("required_documents"), list)
    assert len(data["eligibility_requirements"]) == 6, (
        f"expected 6 eligibility items, got {len(data['eligibility_requirements'])}: {data['eligibility_requirements']}"
    )
    assert len(data["required_documents"]) == 11, (
        f"expected 11 document items, got {len(data['required_documents'])}"
    )
    docs_joined = " ".join(data["required_documents"]).lower()
    assert "surat permohonan" in docs_joined
    assert "pakta integritas" in docs_joined


# --- RBAC on PUT ---
def test_put_site_content_unauth_forbidden():
    r = requests.put(f"{API}/site/content", json={"content": {"eligibility_requirements": []}}, timeout=30)
    assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}"


def test_put_site_content_student_forbidden(student_token):
    r = requests.put(
        f"{API}/site/content",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"content": {"eligibility_requirements": ["x"]}},
        timeout=30,
    )
    assert r.status_code == 403, f"student PUT should be 403, got {r.status_code}"


def test_put_site_content_admin_forbidden(admin_token):
    r = requests.put(
        f"{API}/site/content",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"content": {"eligibility_requirements": ["x"]}},
        timeout=30,
    )
    assert r.status_code == 403, f"admin PUT should be 403, got {r.status_code}"


# --- Super admin edit & add, then restore ---
def test_super_admin_edit_add_and_restore(super_token, original_content):
    headers = {"Authorization": f"Bearer {super_token}"}

    # Edit item 0 + add a new item to eligibility
    edited_elig = list(original_content["eligibility_requirements"])
    original_first = edited_elig[0]
    edited_elig[0] = "TEST_iter41 EDITED syarat pendaftar"
    edited_elig.append("TEST_iter41 syarat tambahan")

    added_doc = list(original_content["required_documents"]) + ["TEST_iter41 berkas tambahan"]

    r = requests.put(
        f"{API}/site/content",
        headers=headers,
        json={"content": {
            "eligibility_requirements": edited_elig,
            "required_documents": added_doc,
        }},
        timeout=30,
    )
    assert r.status_code == 200, f"super_admin PUT failed: {r.status_code} {r.text}"
    resp = r.json()
    assert resp["eligibility_requirements"][0] == "TEST_iter41 EDITED syarat pendaftar"
    assert "TEST_iter41 syarat tambahan" in resp["eligibility_requirements"]
    assert "TEST_iter41 berkas tambahan" in resp["required_documents"]
    assert len(resp["eligibility_requirements"]) == 7
    assert len(resp["required_documents"]) == 12

    # Public GET reflects changes
    r2 = requests.get(f"{API}/site/content", timeout=30)
    pub = r2.json()
    assert pub["eligibility_requirements"][0] == "TEST_iter41 EDITED syarat pendaftar"
    assert "TEST_iter41 berkas tambahan" in pub["required_documents"]

    # Restore
    r3 = requests.put(
        f"{API}/site/content",
        headers=headers,
        json={"content": {
            "eligibility_requirements": original_content["eligibility_requirements"],
            "required_documents": original_content["required_documents"],
        }},
        timeout=30,
    )
    assert r3.status_code == 200
    restored = r3.json()
    assert restored["eligibility_requirements"] == original_content["eligibility_requirements"]
    assert restored["required_documents"] == original_content["required_documents"]
    assert restored["eligibility_requirements"][0] == original_first
    assert len(restored["eligibility_requirements"]) == 6
    assert len(restored["required_documents"]) == 11
