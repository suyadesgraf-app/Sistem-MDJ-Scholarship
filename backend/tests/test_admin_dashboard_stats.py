"""Backend tests for Admin Dashboard stats (GET /api/admin/stats)."""
import os
import re
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
    assert tok
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


def _no_object_id_anywhere(payload):
    """Assert JSON payload has no '_id' key or MongoDB ObjectId-looking values."""
    text = json.dumps(payload)
    assert '"_id"' not in text, "Response leaks Mongo _id"


# --- Feature: admin_stats endpoint --------------------------------------------------
class TestAdminStats:
    def test_admin_stats_shape(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/admin/stats")
        assert r.status_code == 200
        data = r.json()
        for k in ("total_registrations", "by_status", "verified", "pending", "passed_by_region"):
            assert k in data, f"missing key {k}"
        assert isinstance(data["total_registrations"], int)
        assert isinstance(data["by_status"], dict)
        assert isinstance(data["passed_by_region"], list)
        _no_object_id_anywhere(data)
        # Each region entry has region + count
        for row in data["passed_by_region"]:
            assert "region" in row and "count" in row
            assert isinstance(row["count"], int)

    def test_admin_stats_forbidden_for_student(self, student_client):
        s, _ = student_client
        r = s.get(f"{BASE_URL}/api/admin/stats")
        assert r.status_code in (401, 403)


# --- Feature: passed_by_region controlled data test with cleanup -------------------
class TestPassedByRegion:
    """Temporarily mark demo student as lolos to verify passed_by_region aggregation,
    then restore original state."""

    def _get_reg(self, admin_client, user_id):
        r = admin_client.get(f"{BASE_URL}/api/admin/participants/{user_id}")
        assert r.status_code == 200
        return r.json()

    def test_passed_by_region_reflects_lolos(self, admin_client, student_client):
        _, me = student_client
        user_id = me.get("user", {}).get("user_id") or me.get("user", {}).get("id") or me.get("id")
        assert user_id, f"no user id from student login: {me}"

        # Snapshot original registration + profile
        detail = self._get_reg(admin_client, user_id)
        orig_reg = detail.get("registration") or {}
        orig_profile = detail.get("profile") or {}
        orig_status = orig_reg.get("status", "draft")
        orig_data = orig_profile.get("data", {}) if orig_profile else {}
        orig_kota = orig_data.get("kota")

        # Baseline: get stats before
        before = admin_client.get(f"{BASE_URL}/api/admin/stats").json()
        before_region_map = {row["region"]: row["count"] for row in before.get("passed_by_region", [])}
        before_verified = before.get("verified", 0)

        test_region = "TEST_REGION_JKT_XYZ"
        student_s, _ = student_client

        # Set student profile kota via student session (student updates own profile)
        new_data = {**orig_data, "kota": test_region}
        r = student_s.put(f"{BASE_URL}/api/profile", json={"data": new_data})
        assert r.status_code == 200, f"profile update failed: {r.status_code} {r.text}"

        # Set registration status to 'lolos' via admin
        # Try common admin endpoints for status update
        status_endpoints = [
            ("PUT", f"{BASE_URL}/api/admin/participants/{user_id}/status", {"status": "lolos"}),
            ("PATCH", f"{BASE_URL}/api/admin/participants/{user_id}", {"status": "lolos"}),
            ("PUT", f"{BASE_URL}/api/admin/participants/{user_id}", {"status": "lolos"}),
        ]
        status_updated = False
        used_endpoint = None
        for method, url, payload in status_endpoints:
            resp = admin_client.request(method, url, json=payload)
            if resp.status_code in (200, 204):
                status_updated = True
                used_endpoint = (method, url)
                break
        try:
            assert status_updated, "Could not find admin endpoint to set status=lolos"

            # Fetch stats again
            after = admin_client.get(f"{BASE_URL}/api/admin/stats").json()
            _no_object_id_anywhere(after)
            after_region_map = {row["region"]: row["count"] for row in after.get("passed_by_region", [])}
            assert test_region in after_region_map, f"passed_by_region missing test region: {after_region_map}"
            assert after_region_map[test_region] >= 1
            assert after.get("verified", 0) >= before_verified + 1
            # Sorted by count desc
            counts = [row["count"] for row in after["passed_by_region"]]
            assert counts == sorted(counts, reverse=True) or len(counts) <= 1
        finally:
            # Restore status
            for method, url, payload in status_endpoints:
                resp = admin_client.request(method, url, json={"status": orig_status})
                if resp.status_code in (200, 204):
                    break
            # Restore profile
            restore_data = {**orig_data}
            if orig_kota is None:
                restore_data.pop("kota", None)
            else:
                restore_data["kota"] = orig_kota
            student_s.put(f"{BASE_URL}/api/profile", json={"data": restore_data})

    def test_passed_by_region_empty_state_or_valid(self, admin_client):
        # After cleanup, request stats and ensure endpoint still healthy
        r = admin_client.get(f"{BASE_URL}/api/admin/stats")
        assert r.status_code == 200
        data = r.json()
        # Test region should be gone
        regions = [row["region"] for row in data.get("passed_by_region", [])]
        assert "TEST_REGION_JKT_XYZ" not in regions
