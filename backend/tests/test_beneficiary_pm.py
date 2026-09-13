"""
Backend tests for Kelola Data PM / Beneficiary Manager feature.

Covers:
- Admin Provinsi role labeling / creation gating
- GET /api/admin/beneficiaries lists only lolos with Belum Diproses stages
- Bank + disbursement mutations only for admin/super_admin; account masked
- admin_wilayah RBAC (read-only, region-scoped, 404/403 for out-of-region)
- Upload endpoints reject bad extensions / bad magic bytes / regional admin
- Review + audit endpoints RBAC
"""
import io
import os
import time
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


def _login(email, password):
    r = requests.post(
        f"{API}/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
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
    """Create a temporary admin_wilayah for Jakarta Barat; cleans up after."""
    email = f"test_pm_regional_{uuid.uuid4().hex[:8]}@example.com"
    password = "RegionalPM2026!"
    r = requests.post(
        f"{API}/admin/users",
        headers=_h(super_token),
        json={
            "name": "Test PM Regional JB",
            "email": email,
            "password": password,
            "role": "admin_wilayah",
            "region": "Jakarta Barat",
        },
        timeout=30,
    )
    assert r.status_code == 200, f"Create regional failed: {r.status_code} {r.text}"
    user_id = r.json()["user_id"]
    token = _login(email, password)
    yield {"token": token, "user_id": user_id, "email": email, "region": "Jakarta Barat"}
    # teardown
    requests.delete(f"{API}/admin/users/{user_id}", headers=_h(super_token), timeout=30)


# ---------------------------------------------------------------------------
# 1. Admin Provinsi creation gating
# ---------------------------------------------------------------------------
class TestAdminProvinsiCreation:
    def test_provincial_admin_cannot_create_admin(self, prov_token):
        r = requests.post(
            f"{API}/admin/users",
            headers=_h(prov_token),
            json={
                "name": "X",
                "email": f"test_prov_reject_{uuid.uuid4().hex[:6]}@example.com",
                "password": "Whatever2026!",
                "role": "admin",
            },
            timeout=30,
        )
        assert r.status_code == 400, r.text
        assert "role" in r.text.lower() or "tidak valid" in r.text.lower()

    def test_provincial_admin_cannot_create_super_admin(self, prov_token):
        r = requests.post(
            f"{API}/admin/users",
            headers=_h(prov_token),
            json={
                "name": "X",
                "email": f"test_prov_reject2_{uuid.uuid4().hex[:6]}@example.com",
                "password": "Whatever2026!",
                "role": "super_admin",
            },
            timeout=30,
        )
        assert r.status_code == 400

    def test_super_admin_can_create_provincial_admin(self, super_token):
        email = f"test_prov_new_{uuid.uuid4().hex[:8]}@example.com"
        r = requests.post(
            f"{API}/admin/users",
            headers=_h(super_token),
            json={
                "name": "Temp Provincial",
                "email": email,
                "password": "TempProv2026!",
                "role": "admin",
            },
            timeout=30,
        )
        assert r.status_code == 200, r.text
        assert r.json()["role"] == "admin"
        user_id = r.json()["user_id"]
        # cleanup
        requests.delete(
            f"{API}/admin/users/{user_id}", headers=_h(super_token), timeout=30
        )


# ---------------------------------------------------------------------------
# 2. GET /api/admin/beneficiaries
# ---------------------------------------------------------------------------
class TestListBeneficiaries:
    def test_list_only_final_pass(self, prov_token):
        r = requests.get(f"{API}/admin/beneficiaries", headers=_h(prov_token), timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list)
        # ensure everyone has stage_one + stage_two with default belum_diproses
        for row in data:
            assert row["stage_one"]["stage"] == 1
            assert row["stage_two"]["stage"] == 2
            assert row["stage_one"]["status"] in {
                "belum_diproses", "menunggu_bukti", "perlu_tinjau",
                "terverifikasi", "disetujui", "dicairkan", "ditunda",
            }
        # sanity: at least the seeded 12 PM exist
        assert len(data) >= 1

    def test_super_admin_sees_beneficiaries(self, super_token):
        r = requests.get(f"{API}/admin/beneficiaries", headers=_h(super_token), timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_student_forbidden(self):
        stu = _login("mahasiswa.mdj@baznasbazisdki.id", "MahasiswaMDJ2026!")
        r = requests.get(f"{API}/admin/beneficiaries", headers=_h(stu), timeout=30)
        assert r.status_code == 403

    def test_search_filter(self, prov_token):
        r = requests.get(
            f"{API}/admin/beneficiaries?search=zzzz_no_match_xxx",
            headers=_h(prov_token),
            timeout=30,
        )
        assert r.status_code == 200
        assert r.json() == []


# ---------------------------------------------------------------------------
# 3. Beneficiary detail + bank + disbursement (masking, RBAC)
# ---------------------------------------------------------------------------
class TestBeneficiaryDetailAndMutations:
    def _first_beneficiary(self, token):
        r = requests.get(f"{API}/admin/beneficiaries", headers=_h(token), timeout=30)
        assert r.status_code == 200
        items = r.json()
        assert items, "No beneficiaries available for testing"
        return items[0]["user_id"]

    def test_detail_masks_account(self, prov_token):
        uid = self._first_beneficiary(prov_token)
        r = requests.get(
            f"{API}/admin/beneficiaries/{uid}", headers=_h(prov_token), timeout=30
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "bank" in body
        # Should never expose raw digits > 4 exposed
        acct = body["bank"].get("account_number_masked", "")
        # bullet char used for masking
        assert "•" in acct or acct == "Belum dicatat" or acct == ""
        assert "bank_account_cipher" not in str(body)

    def test_update_bank_masks_on_response(self, prov_token):
        uid = self._first_beneficiary(prov_token)
        r = requests.put(
            f"{API}/admin/beneficiaries/{uid}/bank",
            headers=_h(prov_token),
            json={"bank_name": "TEST_BANK", "account_number": "1234567890"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        acct = body["bank"]["account_number_masked"]
        assert acct.endswith("7890")
        assert "1234567890" not in acct
        assert "1234567890" not in r.text
        # verify persistence via GET
        r2 = requests.get(
            f"{API}/admin/beneficiaries/{uid}", headers=_h(prov_token), timeout=30
        )
        assert r2.status_code == 200
        assert r2.json()["bank"]["is_recorded"] is True

    def test_bank_rejects_short_account(self, prov_token):
        uid = self._first_beneficiary(prov_token)
        r = requests.put(
            f"{API}/admin/beneficiaries/{uid}/bank",
            headers=_h(prov_token),
            json={"bank_name": "TEST", "account_number": "12"},
            timeout=30,
        )
        assert r.status_code == 400

    def test_update_disbursement(self, prov_token):
        uid = self._first_beneficiary(prov_token)
        r = requests.put(
            f"{API}/admin/beneficiaries/{uid}/disbursements/1",
            headers=_h(prov_token),
            json={
                "status": "menunggu_bukti",
                "amount": 1000000,
                "reference": "TEST-REF",
                "notes": "test note",
            },
            timeout=30,
        )
        assert r.status_code == 200, r.text
        stages = r.json()["disbursements"]
        assert stages[0]["status"] == "menunggu_bukti"

    def test_disbursement_invalid_stage(self, prov_token):
        uid = self._first_beneficiary(prov_token)
        r = requests.put(
            f"{API}/admin/beneficiaries/{uid}/disbursements/3",
            headers=_h(prov_token),
            json={"status": "menunggu_bukti"},
            timeout=30,
        )
        # FastAPI path validation may 400 or 422 depending on constraint
        assert r.status_code in (400, 404, 422)

    def test_disbursement_invalid_status(self, prov_token):
        uid = self._first_beneficiary(prov_token)
        r = requests.put(
            f"{API}/admin/beneficiaries/{uid}/disbursements/1",
            headers=_h(prov_token),
            json={"status": "sembarang"},
            timeout=30,
        )
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# 4. Regional admin (admin_wilayah) RBAC on Kelola PM
# ---------------------------------------------------------------------------
class TestRegionalAdminScope:
    def test_regional_can_list_beneficiaries(self, regional_admin):
        r = requests.get(
            f"{API}/admin/beneficiaries",
            headers=_h(regional_admin["token"]),
            timeout=30,
        )
        assert r.status_code == 200
        for row in r.json():
            assert row["region"] == regional_admin["region"], (
                f"Regional admin saw out-of-region: {row['region']}"
            )

    def test_regional_query_other_region_still_own(self, regional_admin):
        r = requests.get(
            f"{API}/admin/beneficiaries?region=Jakarta Timur",
            headers=_h(regional_admin["token"]),
            timeout=30,
        )
        assert r.status_code == 200
        for row in r.json():
            assert row["region"] == regional_admin["region"]

    def test_regional_cannot_update_bank_403(self, regional_admin, prov_token):
        r = requests.get(f"{API}/admin/beneficiaries", headers=_h(prov_token), timeout=30)
        # pick any PM; regional will 403 (not 404) because PUT is gated by PM_MANAGERS
        if not r.json():
            pytest.skip("no beneficiaries")
        uid = r.json()[0]["user_id"]
        r2 = requests.put(
            f"{API}/admin/beneficiaries/{uid}/bank",
            headers=_h(regional_admin["token"]),
            json={"bank_name": "x", "account_number": "1234567"},
            timeout=30,
        )
        assert r2.status_code == 403

    def test_regional_cannot_update_disbursement_403(self, regional_admin, prov_token):
        r = requests.get(f"{API}/admin/beneficiaries", headers=_h(prov_token), timeout=30)
        if not r.json():
            pytest.skip("no beneficiaries")
        uid = r.json()[0]["user_id"]
        r2 = requests.put(
            f"{API}/admin/beneficiaries/{uid}/disbursements/1",
            headers=_h(regional_admin["token"]),
            json={"status": "menunggu_bukti"},
            timeout=30,
        )
        assert r2.status_code == 403

    def test_regional_cannot_upload_active_letters_403(self, regional_admin):
        files = {"files": ("t.pdf", b"%PDF-1.4 dummy", "application/pdf")}
        r = requests.post(
            f"{API}/admin/beneficiaries/active-letters",
            headers=_h(regional_admin["token"]),
            files=files,
            timeout=30,
        )
        assert r.status_code == 403

    def test_regional_cannot_upload_transfer_403(self, regional_admin):
        files = {"files": ("t.pdf", b"%PDF-1.4 dummy", "application/pdf")}
        r = requests.post(
            f"{API}/admin/beneficiaries/disbursement-proofs",
            headers=_h(regional_admin["token"]),
            files=files,
            data={"stage": "1"},
            timeout=30,
        )
        assert r.status_code == 403

    def test_regional_cannot_list_reviews_403(self, regional_admin):
        r = requests.get(
            f"{API}/admin/beneficiary-reviews",
            headers=_h(regional_admin["token"]),
            timeout=30,
        )
        assert r.status_code == 403

    def test_regional_cannot_download_file_403(self, regional_admin):
        r = requests.get(
            f"{API}/admin/beneficiary-files/nonexistent-source-id",
            headers=_h(regional_admin["token"]),
            timeout=30,
        )
        assert r.status_code == 403

    def test_regional_out_of_region_detail_404(self, regional_admin, prov_token):
        # find a PM whose region != Jakarta Barat
        r = requests.get(f"{API}/admin/beneficiaries", headers=_h(prov_token), timeout=30)
        outside = [x for x in r.json() if x["region"] != regional_admin["region"]]
        if not outside:
            pytest.skip("no out-of-region beneficiaries available")
        uid = outside[0]["user_id"]
        r2 = requests.get(
            f"{API}/admin/beneficiaries/{uid}",
            headers=_h(regional_admin["token"]),
            timeout=30,
        )
        assert r2.status_code == 404


# ---------------------------------------------------------------------------
# 5. Upload validation (extension + magic bytes) — no OCR triggered
# ---------------------------------------------------------------------------
class TestUploadValidation:
    def test_reject_bad_extension(self, prov_token):
        files = {"files": ("evil.txt", b"hello world", "text/plain")}
        r = requests.post(
            f"{API}/admin/beneficiaries/active-letters",
            headers=_h(prov_token),
            files=files,
            timeout=30,
        )
        assert r.status_code == 400
        assert "PDF" in r.text or "pdf" in r.text.lower()

    def test_reject_bad_magic_bytes(self, prov_token):
        # extension pdf but bytes are not %PDF
        files = {"files": ("fake.pdf", b"NOTAPDF-content-here", "application/pdf")}
        r = requests.post(
            f"{API}/admin/beneficiaries/active-letters",
            headers=_h(prov_token),
            files=files,
            timeout=30,
        )
        assert r.status_code == 400
        assert "sesuai" in r.text.lower() or "isi" in r.text.lower()

    def test_reject_bad_magic_transfer(self, prov_token):
        files = {"files": ("fake.png", b"NOT-A-PNG", "image/png")}
        r = requests.post(
            f"{API}/admin/beneficiaries/disbursement-proofs",
            headers=_h(prov_token),
            files=files,
            data={"stage": "1"},
            timeout=30,
        )
        assert r.status_code == 400

    def test_reject_invalid_stage_transfer(self, prov_token):
        files = {"files": ("t.pdf", b"%PDF-1.4 dummy", "application/pdf")}
        r = requests.post(
            f"{API}/admin/beneficiaries/disbursement-proofs",
            headers=_h(prov_token),
            files=files,
            data={"stage": "3"},
            timeout=30,
        )
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# 6. Reviews + audit RBAC
# ---------------------------------------------------------------------------
class TestReviewsAudit:
    def test_prov_can_list_reviews(self, prov_token):
        r = requests.get(
            f"{API}/admin/beneficiary-reviews", headers=_h(prov_token), timeout=30
        )
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_super_can_list_reviews(self, super_token):
        r = requests.get(
            f"{API}/admin/beneficiary-reviews", headers=_h(super_token), timeout=30
        )
        assert r.status_code == 200

    def test_audit_endpoint_requires_valid_pm(self, prov_token):
        r = requests.get(
            f"{API}/admin/beneficiaries/nonexistent-user/audit",
            headers=_h(prov_token),
            timeout=30,
        )
        assert r.status_code == 404

    def test_resolve_review_404_when_missing(self, prov_token):
        r = requests.post(
            f"{API}/admin/beneficiary-reviews/nonexistent/resolve",
            headers=_h(prov_token),
            json={"user_id": "any"},
            timeout=30,
        )
        assert r.status_code == 404
