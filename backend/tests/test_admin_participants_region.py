"""Regression tests for Admin Participants panel: region filter, totals, and no Kategori column."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://sistem-registrasi.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin.mdj@baznasbazisdki.id"
ADMIN_PASSWORD = "AdminMDJ2026!"

EXPECTED_REGIONS = {"Jakarta Barat", "Jakarta Pusat", "Jakarta Selatan",
                    "Jakarta Timur", "Jakarta Utara", "Kepulauan Seribu"}


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def auth(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# --- /api/admin/stats available_regions ---
def test_available_regions_only_six(auth):
    r = requests.get(f"{BASE_URL}/api/admin/stats", headers=auth, timeout=15)
    assert r.status_code == 200
    regions = r.json().get("available_regions", [])
    assert set(regions) == EXPECTED_REGIONS
    assert "Belum diisi" not in regions
    assert "-" not in regions


# --- /api/admin/participants totals ---
def test_participants_total_is_53(auth):
    r = requests.get(f"{BASE_URL}/api/admin/participants", headers=auth, timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 53, f"Expected 53 participants, got {len(data)}"


def test_participants_have_wilayah_field(auth):
    r = requests.get(f"{BASE_URL}/api/admin/participants", headers=auth, timeout=15)
    for p in r.json():
        assert "wilayah" in p
        assert "user_id" in p


# --- Per-region filter ---
@pytest.mark.parametrize("region,expected", [
    ("Jakarta Pusat", 9),
    ("Jakarta Utara", 9),
    ("Jakarta Barat", 8),
    ("Jakarta Selatan", 8),
    ("Jakarta Timur", 8),
    ("Kepulauan Seribu", 8),
])
def test_filter_per_region(auth, region, expected):
    r = requests.get(f"{BASE_URL}/api/admin/participants",
                     headers=auth, params={"region": region}, timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == expected, f"{region} expected {expected}, got {len(data)}"
    for p in data:
        assert p["wilayah"] == region


def test_region_sums_equal_or_less_than_total(auth):
    total = 0
    for region in EXPECTED_REGIONS:
        r = requests.get(f"{BASE_URL}/api/admin/participants",
                         headers=auth, params={"region": region}, timeout=15)
        total += len(r.json())
    # 3 participants have wilayah="-" so region-filtered sum should be 50
    assert total == 50
