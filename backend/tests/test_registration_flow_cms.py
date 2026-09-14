"""Tests for registration_flow (Alur Pendaftaran) CMS endpoints."""
import os
import copy
import pytest
import requests

def _load_frontend_url():
    with open("/app/frontend/.env") as fh:
        for line in fh:
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip()
    raise RuntimeError("REACT_APP_BACKEND_URL not set")

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or _load_frontend_url()).rstrip("/")
API = f"{BASE_URL}/api"

EXPECTED_TITLES = [
    "Pembuatan Akun",
    "Pendaftaran Online",
    "Seleksi Administrasi",
    "Pengumuman Kelulusan Seleksi Administrasi",
    "Wawancara Assessment",
    "Verifikasi Faktual",
    "Pengumuman Kelulusan Penerima Manfaat",
    "Pengukuhan / Inagurasi",
    "Pencairan Bantuan Tahap I",
    "Pembinaan",
    "Pencairan Bantuan Tahap II",
]

SUPER = {"email": "supri@baznasbazisdki.id", "password": "MdjSuper2026!"}
ADMIN = {"email": "admin.mdj@baznasbazisdki.id", "password": "AdminMDJ2026!"}


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=20)
    assert r.status_code == 200, f"login failed for {creds['email']}: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def super_token():
    return _login(SUPER)


@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def original_flow():
    r = requests.get(f"{API}/site/content", timeout=20)
    assert r.status_code == 200
    return copy.deepcopy(r.json().get("registration_flow"))


def test_get_site_content_has_11_stages_in_order():
    r = requests.get(f"{API}/site/content", timeout=20)
    assert r.status_code == 200
    data = r.json()
    flow = data.get("registration_flow")
    assert isinstance(flow, list)
    assert len(flow) == 11
    titles = [item["title"] for item in flow]
    assert titles == EXPECTED_TITLES
    for item in flow:
        assert "desc" in item


def test_put_registration_flow_preserves_titles_and_updates_desc(super_token, original_flow):
    tampered = [
        {"title": f"HACKED-{i}", "desc": f"TEST desc {i} lorem ipsum"}
        for i in range(11)
    ]
    r = requests.put(
        f"{API}/site/content",
        json={"content": {"registration_flow": tampered}},
        headers={"Authorization": f"Bearer {super_token}"},
        timeout=20,
    )
    assert r.status_code == 200, r.text
    saved = r.json()["registration_flow"]
    assert [i["title"] for i in saved] == EXPECTED_TITLES
    assert [i["desc"] for i in saved] == [f"TEST desc {i} lorem ipsum" for i in range(11)]

    # Persistence
    r2 = requests.get(f"{API}/site/content", timeout=20)
    saved2 = r2.json()["registration_flow"]
    assert [i["desc"] for i in saved2] == [f"TEST desc {i} lorem ipsum" for i in range(11)]

    # Restore original
    restore = requests.put(
        f"{API}/site/content",
        json={"content": {"registration_flow": original_flow}},
        headers={"Authorization": f"Bearer {super_token}"},
        timeout=20,
    )
    assert restore.status_code == 200
    restored = restore.json()["registration_flow"]
    assert [i["title"] for i in restored] == EXPECTED_TITLES
    assert [i["desc"] for i in restored] == [i.get("desc", "") for i in original_flow]


def test_put_registration_flow_invalid_count_returns_400(super_token):
    bad = [{"title": t, "desc": ""} for t in EXPECTED_TITLES[:10]]
    r = requests.put(
        f"{API}/site/content",
        json={"content": {"registration_flow": bad}},
        headers={"Authorization": f"Bearer {super_token}"},
        timeout=20,
    )
    assert r.status_code == 400


def test_non_super_admin_cannot_update_site_content(admin_token):
    r = requests.put(
        f"{API}/site/content",
        json={"content": {"hero": {"title": "should-fail"}}},
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=20,
    )
    assert r.status_code in (401, 403)
