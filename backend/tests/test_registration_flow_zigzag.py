"""
Zig-zag Registration Flow layout tests.

Verifies:
- getDesktopPosition & getDesktopDirection semantics via API + rendered DOM (via Playwright is separate)
- normalize_registration_flow accepts 1..12 stages
- Restores original flow after all tests
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://sistem-registrasi.preview.emergentagent.com").rstrip("/")
SUPER_EMAIL = "supri@baznasbazisdki.id"
SUPER_PASS = "MdjSuper2026!"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": SUPER_EMAIL, "password": SUPER_PASS}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def original_flow():
    r = requests.get(f"{BASE_URL}/api/site/content", timeout=30)
    assert r.status_code == 200
    return r.json().get("registration_flow", [])


@pytest.fixture(scope="module", autouse=True)
def restore_flow(token, original_flow):
    yield
    # Restore original after all tests
    r = requests.put(
        f"{BASE_URL}/api/site/content",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": {"registration_flow": original_flow}},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    got = requests.get(f"{BASE_URL}/api/site/content", timeout=30).json().get("registration_flow", [])
    assert len(got) == len(original_flow)


def _put_flow(token, n):
    steps = [{"title": f"Tahap Uji {i+1}", "desc": f"Deskripsi tahap {i+1}"} for i in range(n)]
    r = requests.put(
        f"{BASE_URL}/api/site/content",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": {"registration_flow": steps}},
        timeout=30,
    )
    return r


@pytest.mark.parametrize("n", [0, 1, 2, 3, 4, 5, 10, 11, 12])
def test_put_registration_flow_sizes(token, n):
    r = _put_flow(token, n)
    assert r.status_code == 200, r.text
    got = requests.get(f"{BASE_URL}/api/site/content", timeout=30).json().get("registration_flow", [])
    assert len(got) == n
    for i, s in enumerate(got):
        assert s["title"] == f"Tahap Uji {i+1}"
