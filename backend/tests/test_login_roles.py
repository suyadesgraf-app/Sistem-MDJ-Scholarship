"""Login tests for demo accounts per review request."""
import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://sistem-registrasi.preview.emergentagent.com").rstrip("/")

ACCOUNTS = [
    ("mahasiswa.mdj@baznasbazisdki.id", "MahasiswaMDJ2026!", "student"),
    ("admin.mdj@baznasbazisdki.id", "AdminMDJ2026!", "admin"),
    ("supri@baznasbazisdki.id", "MdjSuper2026!", "super_admin"),
]


@pytest.mark.parametrize("email,password,role", ACCOUNTS)
def test_login_role(email, password, role):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "token" in data and data["token"]
    assert data["user"]["email"] == email
    assert data["user"]["role"] == role
    # httpOnly cookie
    assert "access_token" in r.cookies


def test_login_invalid():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": "mahasiswa.mdj@baznasbazisdki.id", "password": "wrong"}, timeout=30)
    assert r.status_code == 401
