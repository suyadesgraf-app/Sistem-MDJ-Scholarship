"""Backend tests for Admin Ringkasan (GET /api/admin/stats?region=)."""
import os
import json
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://sistem-registrasi.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin.mdj@baznasbazisdki.id"
ADMIN_PASSWORD = "AdminMDJ2026!"
STUDENT_EMAIL = "mahasiswa.mdj@baznasbazisdki.id"
STUDENT_PASSWORD = "MahasiswaMDJ2026!"


def _login(session, email, password):
    r = session.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text}"
    tok = r.json().get("token")
    session.headers.update({"Authorization": f"Bearer {tok}"})
    return r.json()


@pytest.fixture(scope="module")
def admin_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    _login(s, ADMIN_EMAIL, ADMIN_PASSWORD)
    return s


@pytest.fixture(scope="module")
def student_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    me = _login(s, STUDENT_EMAIL, STUDENT_PASSWORD)
    return s, me


def _no_object_id(payload):
    assert '"_id"' not in json.dumps(payload), "Response leaks Mongo _id"


class TestAdminStatsShape:
    def test_new_keys_present(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/admin/stats")
        assert r.status_code == 200
        data = r.json()
        for k in ("total_registrations", "by_status", "verified", "pending",
                  "passed_by_region", "selected_region", "available_regions",
                  "announcement_count"):
            assert k in data, f"missing key {k}"
        assert data["selected_region"] == "all"
        assert isinstance(data["available_regions"], list)
        assert isinstance(data["announcement_count"], int)
        _no_object_id(data)

    def test_forbidden_for_student(self, student_client):
        s, _ = student_client
        r = s.get(f"{BASE_URL}/api/admin/stats")
        assert r.status_code in (401, 403)

    def test_region_filter_all_equivalent(self, admin_client):
        r1 = admin_client.get(f"{BASE_URL}/api/admin/stats").json()
        r2 = admin_client.get(f"{BASE_URL}/api/admin/stats", params={"region": "all"}).json()
        assert r1["total_registrations"] == r2["total_registrations"]
        assert r2["selected_region"] == "all"


class TestRegionFilter:
    def test_region_filter_uses_controlled_data(self, admin_client, student_client):
        student_s, me = student_client
        user_id = me.get("user", {}).get("user_id") or me.get("user", {}).get("id") or me.get("id")
        assert user_id

        # Get baseline profile
        detail = admin_client.get(f"{BASE_URL}/api/admin/participants/{user_id}").json()
        orig_profile = detail.get("profile") or {}
        orig_data = orig_profile.get("data", {}) if orig_profile else {}
        orig_kota = orig_data.get("kota")

        test_region = "TEST_REGION_SUMMARY_XYZ"
        new_data = {**orig_data, "kota": test_region}
        r = student_s.put(f"{BASE_URL}/api/profile", json={"data": new_data})
        assert r.status_code == 200

        try:
            # Overall must include TEST region as available
            overall = admin_client.get(f"{BASE_URL}/api/admin/stats").json()
            assert test_region in overall["available_regions"]
            base_total = overall["total_registrations"]
            assert base_total >= 1

            # Filter by TEST region → total should be 1 (just demo student)
            filtered = admin_client.get(f"{BASE_URL}/api/admin/stats", params={"region": test_region}).json()
            assert filtered["selected_region"] == test_region
            assert filtered["total_registrations"] == 1
            _no_object_id(filtered)

            # Filter by unknown region → 0
            zero = admin_client.get(f"{BASE_URL}/api/admin/stats", params={"region": "TOTALLY_UNKNOWN_NOWHERE"}).json()
            assert zero["total_registrations"] == 0
        finally:
            restore = {**orig_data}
            if orig_kota is None:
                restore.pop("kota", None)
            else:
                restore["kota"] = orig_kota
            student_s.put(f"{BASE_URL}/api/profile", json={"data": restore})
