"""Test admin stats available_regions excludes 'Belum diisi'."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://sistem-registrasi.preview.emergentagent.com").rstrip("/")
EXPECTED_REGIONS = {
    "Jakarta Barat", "Jakarta Pusat", "Jakarta Selatan",
    "Jakarta Timur", "Jakarta Utara", "Kepulauan Seribu",
}


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin.mdj@baznasbazisdki.id",
        "password": "AdminMDJ2026!",
    }, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    token = r.json().get("token")
    assert token
    return token


@pytest.fixture(scope="module")
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


def test_stats_available_regions_no_belum_diisi(auth_headers):
    r = requests.get(f"{BASE_URL}/api/admin/stats", headers=auth_headers, timeout=30)
    assert r.status_code == 200
    data = r.json()
    regions = data.get("available_regions", [])
    assert isinstance(regions, list)
    assert "Belum diisi" not in regions, f"Belum diisi leaked into regions: {regions}"
    # Expect only expected regions (subset check - only real Jakarta regions)
    unexpected = set(regions) - EXPECTED_REGIONS
    assert not unexpected, f"unexpected regions: {unexpected}"


def test_stats_total_not_zero(auth_headers):
    r = requests.get(f"{BASE_URL}/api/admin/stats", headers=auth_headers, timeout=30)
    data = r.json()
    assert data.get("total_registrations", 0) > 0, "seed data expected (50 students)"


@pytest.mark.parametrize("region", sorted(EXPECTED_REGIONS))
def test_stats_by_region_ok(auth_headers, region):
    r = requests.get(f"{BASE_URL}/api/admin/stats", params={"region": region}, headers=auth_headers, timeout=30)
    assert r.status_code == 200, f"{region} => {r.status_code}"
    data = r.json()
    assert data.get("selected_region") == region
    assert "by_status" in data


def test_stats_belum_diisi_filter_returns_no_extra(auth_headers):
    # Even if someone passes 'Belum diisi', endpoint should still respond 200
    r = requests.get(f"{BASE_URL}/api/admin/stats", params={"region": "Belum diisi"}, headers=auth_headers, timeout=30)
    assert r.status_code == 200
