"""Tests for CPM ID (Calon Penerima Manfaat) generation & persistence on /api/registration."""
import os
import re
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://sistem-registrasi.preview.emergentagent.com").rstrip("/")
STUDENT_EMAIL = "mahasiswa.mdj@baznasbazisdki.id"
STUDENT_PASSWORD = "MahasiswaMDJ2026!"
ADMIN_EMAIL = "admin.mdj@baznasbazisdki.id"
ADMIN_PASSWORD = "AdminMDJ2026!"

CPM_PATTERN = re.compile(r"^CPM-MDJ/\d{4}/\d{6}$")


def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def student_headers():
    return {"Authorization": f"Bearer {_login(STUDENT_EMAIL, STUDENT_PASSWORD)}"}


@pytest.fixture(scope="module")
def admin_headers():
    return {"Authorization": f"Bearer {_login(ADMIN_EMAIL, ADMIN_PASSWORD)}"}


class TestCPMId:
    def test_student_get_registration_has_cpm_id(self, student_headers):
        r = requests.get(f"{BASE_URL}/api/registration", headers=student_headers, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "cpm_id" in data, f"cpm_id missing: {data}"
        assert CPM_PATTERN.match(data["cpm_id"]), f"cpm_id format invalid: {data['cpm_id']}"

    def test_cpm_id_stable_across_multiple_gets(self, student_headers):
        ids = []
        for _ in range(3):
            r = requests.get(f"{BASE_URL}/api/registration", headers=student_headers, timeout=30)
            assert r.status_code == 200
            ids.append(r.json().get("cpm_id"))
        assert len(set(ids)) == 1, f"cpm_id changed across GETs: {ids}"

    def test_cpm_id_unchanged_after_draft_post(self, student_headers):
        r0 = requests.get(f"{BASE_URL}/api/registration", headers=student_headers, timeout=30)
        original = r0.json().get("cpm_id")
        category = r0.json().get("category") or "sarjana"
        r1 = requests.post(
            f"{BASE_URL}/api/registration",
            headers=student_headers,
            json={"category": category, "action": "draft"},
            timeout=30,
        )
        assert r1.status_code == 200, r1.text
        assert r1.json().get("cpm_id") == original
        # And verify GET again
        r2 = requests.get(f"{BASE_URL}/api/registration", headers=student_headers, timeout=30)
        assert r2.json().get("cpm_id") == original

    def test_demo_student_expected_id(self, student_headers):
        r = requests.get(f"{BASE_URL}/api/registration", headers=student_headers, timeout=30)
        cpm = r.json().get("cpm_id")
        # First registered student for 2026 should be 000000
        assert cpm == "CPM-MDJ/2026/000000", f"Expected CPM-MDJ/2026/000000, got {cpm}"

    def test_admin_registration_endpoint_not_cpm(self, admin_headers):
        # Admin hitting /api/registration should NOT be treated as student.
        # It may 403/404 or return empty, but must NOT create CPM for admin.
        r = requests.get(f"{BASE_URL}/api/registration", headers=admin_headers, timeout=30)
        # Accept any non-500. If returned, cpm_id should not exist for admin.
        assert r.status_code != 500
        if r.status_code == 200:
            body = r.json()
            # admin has no registration => empty dict expected
            assert not body.get("cpm_id"), f"admin should not have cpm_id, got {body}"
