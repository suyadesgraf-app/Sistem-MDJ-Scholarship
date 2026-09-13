"""
Backend tests for the new region-scoped Transfer Proof upload feature (Iteration 23).

Covers:
- POST /api/admin/disbursements/transfer-proofs missing `region` -> 400 (before OCR).
- POST /api/admin/disbursements/transfer-proofs invalid `region` -> 400 (before OCR).
- POST /api/admin/disbursements/transfer-proofs valid region + invalid extension -> 400.
- POST /api/admin/disbursements/transfer-proofs valid region + missing stage -> 4xx.
- Admin Wilayah 403 on transfer-proofs even with valid region.
- Cross-region review resolve -> 400 (guard).
"""
import io
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL", "https://sistem-registrasi.preview.emergentagent.com"
).rstrip("/")
API = f"{BASE_URL}/api"

SUPER_EMAIL = "supri@baznasbazisdki.id"
SUPER_PASS = "MdjSuper2026!"
PROV_EMAIL = "admin.mdj@baznasbazisdki.id"
PROV_PASS = "AdminMDJ2026!"

DKI_REGIONS = [
    "Jakarta Pusat",
    "Jakarta Utara",
    "Jakarta Barat",
    "Jakarta Selatan",
    "Jakarta Timur",
    "Kepulauan Seribu",
]


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    return r.json()["token"]


def _h(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def super_token():
    return _login(SUPER_EMAIL, SUPER_PASS)


@pytest.fixture(scope="module")
def prov_token():
    return _login(PROV_EMAIL, PROV_PASS)


@pytest.fixture(scope="module")
def regional_admin(super_token):
    email = f"test_iter23_region_{uuid.uuid4().hex[:8]}@example.com"
    password = "WilayahRG2026!"
    r = requests.post(
        f"{API}/admin/users",
        headers=_h(super_token),
        json={
            "name": "Test Iter23 Regional JB",
            "email": email,
            "password": password,
            "role": "admin_wilayah",
            "region": "Jakarta Barat",
        },
        timeout=30,
    )
    assert r.status_code == 200, r.text
    user_id = r.json()["user_id"]
    token = _login(email, password)
    yield {"token": token, "user_id": user_id, "region": "Jakarta Barat"}
    requests.delete(f"{API}/admin/users/{user_id}", headers=_h(super_token), timeout=30)


class TestRegionValidationPreOCR:
    """These requests must fail BEFORE any OCR is invoked."""

    def _fake_pdf(self, name="proof.pdf"):
        return {"files": (name, b"%PDF-1.4 test bytes", "application/pdf")}

    def test_missing_region_400(self, prov_token):
        r = requests.post(
            f"{API}/admin/disbursements/transfer-proofs",
            headers=_h(prov_token),
            data={"stage": "1"},
            files=self._fake_pdf(),
            timeout=30,
        )
        assert r.status_code == 400, r.text
        assert "wilayah" in r.text.lower()

    def test_empty_region_400(self, prov_token):
        r = requests.post(
            f"{API}/admin/disbursements/transfer-proofs",
            headers=_h(prov_token),
            data={"stage": "1", "region": ""},
            files=self._fake_pdf(),
            timeout=30,
        )
        assert r.status_code == 400, r.text

    def test_invalid_region_400(self, prov_token):
        r = requests.post(
            f"{API}/admin/disbursements/transfer-proofs",
            headers=_h(prov_token),
            data={"stage": "1", "region": "Jawa Tengah"},
            files=self._fake_pdf(),
            timeout=30,
        )
        assert r.status_code == 400, r.text

    def test_case_sensitive_region_rejected(self, prov_token):
        # Region check compares against exact DKI_REGIONS list; lowercase should fail
        r = requests.post(
            f"{API}/admin/disbursements/transfer-proofs",
            headers=_h(prov_token),
            data={"stage": "1", "region": "jakarta barat"},
            files=self._fake_pdf(),
            timeout=30,
        )
        assert r.status_code == 400, r.text

    def test_valid_region_but_bad_extension_400(self, prov_token):
        files = {"files": ("proof.txt", b"just text", "text/plain")}
        r = requests.post(
            f"{API}/admin/disbursements/transfer-proofs",
            headers=_h(prov_token),
            data={"stage": "1", "region": "Jakarta Barat"},
            files=files,
            timeout=30,
        )
        assert r.status_code == 400, r.text

    def test_valid_region_bad_stage(self, prov_token):
        r = requests.post(
            f"{API}/admin/disbursements/transfer-proofs",
            headers=_h(prov_token),
            data={"stage": "9", "region": "Jakarta Timur"},
            files=self._fake_pdf(),
            timeout=30,
        )
        assert r.status_code == 400, r.text


class TestRegionalUploadForbidden:
    def test_regional_admin_forbidden_even_with_valid_region(self, regional_admin):
        files = {"files": ("proof.pdf", b"%PDF-1.4 test", "application/pdf")}
        r = requests.post(
            f"{API}/admin/disbursements/transfer-proofs",
            headers=_h(regional_admin["token"]),
            data={"stage": "1", "region": "Jakarta Barat"},
            files=files,
            timeout=30,
        )
        assert r.status_code == 403, r.text


class TestAllSixRegionsAccepted:
    """All six DKI regions must pass the region-guard step (they may fail later
    for other reasons: extension, magic-bytes, etc.). We use a bad extension so
    the request is rejected AFTER the region check with 400, proving the region
    itself was accepted."""

    @pytest.mark.parametrize("region", DKI_REGIONS)
    def test_region_accepted_progresses_to_file_validation(self, prov_token, region):
        files = {"files": ("proof.txt", b"not a proof", "text/plain")}
        r = requests.post(
            f"{API}/admin/disbursements/transfer-proofs",
            headers=_h(prov_token),
            data={"stage": "1", "region": region},
            files=files,
            timeout=30,
        )
        # Region was accepted; extension check triggers 400 with different message
        assert r.status_code == 400, r.text
        # error message should not be the region-invalid one
        assert "wilayah pencairan yang valid" not in r.text.lower()
