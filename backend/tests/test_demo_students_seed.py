"""Tests for POST /api/admin/demo-students/seed and dashboard region distribution."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL is required"

SUPER_ADMIN = {"email": "supri@baznasbazisdki.id", "password": "MdjSuper2026!"}
ADMIN = {"email": "admin.mdj@baznasbazisdki.id", "password": "AdminMDJ2026!"}
STUDENT = {"email": "mahasiswa.mdj@baznasbazisdki.id", "password": "MahasiswaMDJ2026!"}

EXPECTED_REGIONS = {
    "Jakarta Pusat", "Jakarta Utara", "Jakarta Barat",
    "Jakarta Selatan", "Jakarta Timur", "Kepulauan Seribu",
}
EXPECTED_STATUS = {
    "lolos": 12, "submitted": 8, "verifikasi": 8,
    "lolos_administrasi": 7, "wawancara": 6,
    "verifikasi_faktual": 5, "ditolak": 4,
}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login {creds['email']} failed: {r.status_code} {r.text}"
    token = r.json().get("token") or r.json().get("access_token")
    if token:
        s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="module")
def super_admin():
    return _login(SUPER_ADMIN)


@pytest.fixture(scope="module")
def admin():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def student():
    return _login(STUDENT)


# --- Seed endpoint access & idempotency ---
class TestSeedEndpoint:
    def test_student_forbidden(self, student):
        r = student.post(f"{BASE_URL}/api/admin/demo-students/seed")
        assert r.status_code == 403

    def test_admin_forbidden(self, admin):
        r = admin.post(f"{BASE_URL}/api/admin/demo-students/seed")
        assert r.status_code == 403

    def test_super_admin_idempotent(self, super_admin):
        r = super_admin.post(f"{BASE_URL}/api/admin/demo-students/seed")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["total"] == 50
        assert data["created"] == 0
        assert data["skipped"] == 50
        assert set(data["regions"]) == EXPECTED_REGIONS
        assert data["by_status"] == EXPECTED_STATUS


# --- Data verification via participants list ---
class TestSeededData:
    @pytest.fixture(scope="class")
    def seeded(self, super_admin):
        # Ensure seed exists
        super_admin.post(f"{BASE_URL}/api/admin/demo-students/seed")
        r = super_admin.get(f"{BASE_URL}/api/admin/participants", params={"limit": 500})
        assert r.status_code == 200, r.text
        items = r.json()
        if isinstance(items, dict):
            items = items.get("items") or items.get("data") or []
        # Filter seeded records via user_id prefix (backup: registrations endpoint)
        seeded = [it for it in items if str(it.get("user_id", "")).startswith("student_uji_mdj_")]
        return seeded

    def test_50_seeded_records(self, seeded):
        assert len(seeded) == 50, f"expected 50 seeded, got {len(seeded)}"

    def test_status_distribution(self, seeded):
        counts = {}
        for it in seeded:
            s = it.get("status")
            counts[s] = counts.get(s, 0) + 1
        for status, expected in EXPECTED_STATUS.items():
            assert counts.get(status) == expected, f"{status}: got {counts.get(status)}, expected {expected}"

    def test_all_regions_covered(self, seeded, super_admin):
        # participants list does not include kota; fetch profile per user
        regions = set()
        by_user_region = {}
        for it in seeded:
            uid = it["user_id"]
            r = super_admin.get(f"{BASE_URL}/api/admin/participants/{uid}")
            assert r.status_code == 200
            profile = r.json().get("profile") or {}
            region = profile.get("kota")
            by_user_region[uid] = (region, it.get("status"))
            if region:
                regions.add(region)
        assert EXPECTED_REGIONS.issubset(regions), f"missing regions: {EXPECTED_REGIONS - regions}"
        # Also verify lolos across all 6 regions
        lolos_regions = {reg for (reg, st) in by_user_region.values() if st == "lolos" and reg}
        assert lolos_regions == EXPECTED_REGIONS, f"lolos regions coverage: {lolos_regions}"

    def test_seeded_have_campus_and_profile(self, seeded, super_admin):
        # Load campuses to validate institusi belongs to registered campuses
        rc = super_admin.get(f"{BASE_URL}/api/campuses")
        assert rc.status_code == 200
        campuses = rc.json()
        if isinstance(campuses, dict):
            campuses = campuses.get("items") or campuses.get("data") or []
        campus_names = {c.get("name") for c in campuses}
        missing = []
        for it in seeded[:10]:
            profile = it.get("profile") or {}
            inst = profile.get("institusi") or it.get("institusi")
            if inst and inst not in campus_names:
                missing.append(inst)
        assert not missing, f"institusi not registered: {missing}"


# --- Dashboard admin stats ---
class TestDashboardStats:
    def test_recipient_totals(self, admin):
        r = admin.get(f"{BASE_URL}/api/admin/stats")
        assert r.status_code == 200, r.text
        data = r.json()
        # Total penerima manfaat (lolos)
        passed_by_region = data.get("passed_by_region") or {}
        assert isinstance(passed_by_region, (dict, list))
        if isinstance(passed_by_region, list):
            total_passed = sum(item.get("count", 0) for item in passed_by_region)
            regions = {item.get("region") or item.get("kota") for item in passed_by_region}
        else:
            total_passed = sum(passed_by_region.values())
            regions = set(passed_by_region.keys())
        assert total_passed >= 12, f"expected >=12 lolos, got {total_passed}"
        assert EXPECTED_REGIONS.issubset(regions), f"missing regions in dashboard: {EXPECTED_REGIONS - regions}"

    def test_total_registrations_at_least_53(self, admin):
        r = admin.get(f"{BASE_URL}/api/admin/stats")
        assert r.status_code == 200
        data = r.json()
        total = data.get("total_registrations") or data.get("total_applicants") or data.get("total")
        assert total is not None
        assert total >= 53, f"expected >=53 total, got {total}"
