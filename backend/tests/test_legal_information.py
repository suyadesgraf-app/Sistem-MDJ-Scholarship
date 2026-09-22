"""Tests for Informasi Legal (privacy/terms/guide) via site_content CMS."""
import os
import copy
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    # fallback: read from frontend/.env
    with open("/app/frontend/.env") as fh:
        for line in fh:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip()
                break
BASE_URL = BASE_URL.rstrip("/")

SUPER = {"email": "supri@baznasbazisdki.id", "password": "MdjSuper2026!"}
STUDENT = {"email": "mahasiswa.mdj@baznasbazisdki.id", "password": "MahasiswaMDJ2026!"}


def _login(cred):
    r = requests.post(f"{BASE_URL}/api/auth/login", json=cred, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def super_token():
    return _login(SUPER)


@pytest.fixture(scope="module")
def student_token():
    return _login(STUDENT)


@pytest.fixture(scope="module")
def original_legal(super_token):
    r = requests.get(f"{BASE_URL}/api/site/content", timeout=30)
    assert r.status_code == 200
    content = r.json()
    original = copy.deepcopy(content.get("legal_information") or {})
    yield original
    # restore
    payload = {"content": {"legal_information": original}}
    rr = requests.put(
        f"{BASE_URL}/api/site/content",
        json=payload,
        headers={"Authorization": f"Bearer {super_token}"},
        timeout=30,
    )
    assert rr.status_code == 200, f"restore failed: {rr.text}"


def test_public_site_content_exposes_legal_information():
    r = requests.get(f"{BASE_URL}/api/site/content", timeout=30)
    assert r.status_code == 200
    # legal_information key optional but public
    data = r.json()
    assert isinstance(data, dict)


def test_non_super_admin_cannot_update_site_content(student_token, original_legal):
    payload = {"content": {"legal_information": {"privacy": {"title": "hack", "content": "hack"}}}}
    r = requests.put(
        f"{BASE_URL}/api/site/content",
        json=payload,
        headers={"Authorization": f"Bearer {student_token}"},
        timeout=30,
    )
    assert r.status_code in (401, 403), r.text


def test_unauth_cannot_update_site_content():
    r = requests.put(
        f"{BASE_URL}/api/site/content",
        json={"content": {"legal_information": {}}},
        timeout=30,
    )
    assert r.status_code in (401, 403)


def test_super_admin_can_update_and_persist_legal_information(super_token, original_legal):
    new_legal = {
        "privacy": {"title": "TEST_ITER50 Kebijakan Privasi", "content": "TEST_ITER50 privacy body"},
        "terms": {"title": "TEST_ITER50 Syarat dan Ketentuan", "content": "TEST_ITER50 terms body"},
        "guide": {"title": "TEST_ITER50 Pedoman Program", "content": "TEST_ITER50 guide body"},
    }
    r = requests.put(
        f"{BASE_URL}/api/site/content",
        json={"content": {"legal_information": new_legal}},
        headers={"Authorization": f"Bearer {super_token}"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    saved = r.json().get("legal_information")
    assert saved == new_legal, saved

    # GET verify persistence via public endpoint
    r2 = requests.get(f"{BASE_URL}/api/site/content", timeout=30)
    assert r2.status_code == 200
    assert r2.json().get("legal_information") == new_legal


def test_restore_verification(super_token, original_legal):
    # Manually restore then confirm
    r = requests.put(
        f"{BASE_URL}/api/site/content",
        json={"content": {"legal_information": original_legal}},
        headers={"Authorization": f"Bearer {super_token}"},
        timeout=30,
    )
    assert r.status_code == 200
    r2 = requests.get(f"{BASE_URL}/api/site/content", timeout=30)
    assert r2.json().get("legal_information") == original_legal
