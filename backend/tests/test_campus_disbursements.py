"""
Backend tests for the new Pencairan Dana (Campus Disbursements) feature.

Endpoints under test:
- GET  /api/admin/disbursements/campuses
- GET  /api/admin/disbursements/campuses/{campus_key}
- GET  /api/admin/disbursements/campuses/{campus_key}/audit
- PUT  /api/admin/disbursements/campuses/{campus_key}/regions/{region}/stages/{stage}
- POST /api/admin/disbursements/transfer-proofs  (alias route, validation-only)

Covers:
- Admin Provinsi listing: 1 row per campus, from lolos only, includes
  recipient_count, region_count, stage_one/stage_two, proof_count.
- Detail split per region with recipients, both stages.
- Update aggregate persists and does not break individual PM data.
- Admin Wilayah scoping: list scoped even with region= query,
  detail out-of-region -> 404, update aggregate -> 403,
  transfer-proofs alias upload -> 403, audit scoped.
- transfer-proofs alias validates file (extension) and stage.
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
STUDENT_EMAIL = "mahasiswa.mdj@baznasbazisdki.id"
STUDENT_PASS = "MahasiswaMDJ2026!"


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
def student_token():
    try:
        return _login(STUDENT_EMAIL, STUDENT_PASS)
    except AssertionError:
        return None


@pytest.fixture(scope="module")
def regional_admin(super_token):
    email = f"test_cd_regional_{uuid.uuid4().hex[:8]}@example.com"
    password = "RegionalCD2026!"
    r = requests.post(
        f"{API}/admin/users",
        headers=_h(super_token),
        json={
            "name": "Test CD Regional JB",
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


# ---------------------------------------------------------------------------
# 1. Campus list (Admin Provinsi)
# ---------------------------------------------------------------------------
class TestCampusList:
    def test_prov_list_shape(self, prov_token):
        r = requests.get(f"{API}/admin/disbursements/campuses", headers=_h(prov_token), timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        # One row per campus_key
        keys = [item["campus_key"] for item in data]
        assert len(keys) == len(set(keys))
        first = data[0]
        for field in (
            "campus_key",
            "campus",
            "recipient_count",
            "region_count",
            "regions",
            "stage_one",
            "stage_two",
            "proof_count",
        ):
            assert field in first, f"Missing field {field}"
        assert isinstance(first["recipient_count"], int)
        assert first["recipient_count"] >= 1
        assert isinstance(first["region_count"], int)
        assert first["region_count"] == len(first["regions"])
        assert first["stage_one"]["stage"] == 1
        assert first["stage_two"]["stage"] == 2

    def test_prov_list_search_filter(self, prov_token):
        base = requests.get(
            f"{API}/admin/disbursements/campuses", headers=_h(prov_token), timeout=30
        ).json()
        if not base:
            pytest.skip("no campuses to search on")
        keyword = base[0]["campus"].split()[0].lower()
        r = requests.get(
            f"{API}/admin/disbursements/campuses",
            headers=_h(prov_token),
            params={"search": keyword},
            timeout=30,
        )
        assert r.status_code == 200
        for item in r.json():
            assert keyword in item["campus"].lower()

    def test_student_forbidden(self, student_token):
        if not student_token:
            pytest.skip("no student login")
        r = requests.get(
            f"{API}/admin/disbursements/campuses", headers=_h(student_token), timeout=30
        )
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# 2. Campus detail structure
# ---------------------------------------------------------------------------
class TestCampusDetail:
    def test_detail_structure(self, prov_token):
        campuses = requests.get(
            f"{API}/admin/disbursements/campuses", headers=_h(prov_token), timeout=30
        ).json()
        assert campuses, "expected at least one campus"
        campus_key = campuses[0]["campus_key"]
        r = requests.get(
            f"{API}/admin/disbursements/campuses/{campus_key}",
            headers=_h(prov_token),
            timeout=30,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["campus_key"] == campus_key
        assert isinstance(data["regions"], list)
        assert len(data["regions"]) >= 1
        region = data["regions"][0]
        assert "region" in region
        assert "recipients" in region and isinstance(region["recipients"], list)
        assert region["recipient_count"] == len(region["recipients"])
        # Every recipient must be a lolos final PM (has user_id + nim)
        for rec in region["recipients"]:
            assert "user_id" in rec and "nim" in rec and "campus" in rec
        assert region["stage_one"]["stage"] == 1
        assert region["stage_two"]["stage"] == 2
        for stage in (region["stage_one"], region["stage_two"]):
            assert stage["status"] in {
                "belum_diproses",
                "menunggu_bukti",
                "perlu_tinjau",
                "terverifikasi",
                "disetujui",
                "dicairkan",
                "ditunda",
            }

    def test_detail_unknown_campus_404(self, prov_token):
        r = requests.get(
            f"{API}/admin/disbursements/campuses/campus_doesnotexist",
            headers=_h(prov_token),
            timeout=30,
        )
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# 3. Aggregate update round-trip
# ---------------------------------------------------------------------------
class TestUpdateAggregate:
    def test_update_persists_and_reverts(self, prov_token):
        campuses = requests.get(
            f"{API}/admin/disbursements/campuses", headers=_h(prov_token), timeout=30
        ).json()
        assert campuses
        campus_key = campuses[0]["campus_key"]
        detail = requests.get(
            f"{API}/admin/disbursements/campuses/{campus_key}",
            headers=_h(prov_token),
            timeout=30,
        ).json()
        region = detail["regions"][0]["region"]
        original = detail["regions"][0]["stage_one"]

        payload = {
            "status": "menunggu_bukti",
            "amount": 1234567,
            "disbursed_at": "2026-01-15",
            "reference": "TEST-CD-REF",
            "notes": "TEST_CD notes",
        }
        r = requests.put(
            f"{API}/admin/disbursements/campuses/{campus_key}/regions/{region}/stages/1",
            headers=_h(prov_token),
            json=payload,
            timeout=30,
        )
        assert r.status_code == 200, r.text
        got = r.json()
        stage = next(
            item["stage_one"] for item in got["regions"] if item["region"] == region
        )
        assert stage["status"] == "menunggu_bukti"
        assert stage["amount"] == 1234567
        assert stage["reference"] == "TEST-CD-REF"
        assert stage["notes"] == "TEST_CD notes"

        # GET again to confirm persistence
        detail2 = requests.get(
            f"{API}/admin/disbursements/campuses/{campus_key}",
            headers=_h(prov_token),
            timeout=30,
        ).json()
        stage2 = next(
            item["stage_one"] for item in detail2["regions"] if item["region"] == region
        )
        assert stage2["reference"] == "TEST-CD-REF"

        # Detail must still expose per-region recipients (not broken)
        for item in detail2["regions"]:
            assert isinstance(item["recipients"], list)
            assert item["recipient_count"] == len(item["recipients"])

        # Revert
        revert = {
            "status": original.get("status", "belum_diproses"),
            "amount": original.get("amount"),
            "disbursed_at": original.get("disbursed_at") or "",
            "reference": original.get("reference", ""),
            "notes": original.get("notes", ""),
        }
        rv = requests.put(
            f"{API}/admin/disbursements/campuses/{campus_key}/regions/{region}/stages/1",
            headers=_h(prov_token),
            json=revert,
            timeout=30,
        )
        assert rv.status_code == 200

    def test_update_invalid_stage(self, prov_token):
        campuses = requests.get(
            f"{API}/admin/disbursements/campuses", headers=_h(prov_token), timeout=30
        ).json()
        campus_key = campuses[0]["campus_key"]
        detail = requests.get(
            f"{API}/admin/disbursements/campuses/{campus_key}",
            headers=_h(prov_token),
            timeout=30,
        ).json()
        region = detail["regions"][0]["region"]
        r = requests.put(
            f"{API}/admin/disbursements/campuses/{campus_key}/regions/{region}/stages/3",
            headers=_h(prov_token),
            json={"status": "belum_diproses", "amount": None,
                  "disbursed_at": "", "reference": "", "notes": ""},
            timeout=30,
        )
        assert r.status_code == 400

    def test_update_invalid_status(self, prov_token):
        campuses = requests.get(
            f"{API}/admin/disbursements/campuses", headers=_h(prov_token), timeout=30
        ).json()
        campus_key = campuses[0]["campus_key"]
        detail = requests.get(
            f"{API}/admin/disbursements/campuses/{campus_key}",
            headers=_h(prov_token),
            timeout=30,
        ).json()
        region = detail["regions"][0]["region"]
        r = requests.put(
            f"{API}/admin/disbursements/campuses/{campus_key}/regions/{region}/stages/1",
            headers=_h(prov_token),
            json={"status": "totally_wrong", "amount": None,
                  "disbursed_at": "", "reference": "", "notes": ""},
            timeout=30,
        )
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# 4. Regional admin scoping (admin_wilayah)
# ---------------------------------------------------------------------------
class TestRegionalScope:
    def test_list_scoped_even_with_other_region(self, regional_admin):
        r = requests.get(
            f"{API}/admin/disbursements/campuses",
            headers=_h(regional_admin["token"]),
            params={"region": "Jakarta Timur"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        # every returned campus should list ONLY Jakarta Barat
        for item in data:
            assert item["regions"] == ["Jakarta Barat"], item
            assert item["region_count"] == 1

    def test_out_of_region_detail_404(self, prov_token, regional_admin):
        # find a campus that is NOT in Jakarta Barat when possible
        prov_list = requests.get(
            f"{API}/admin/disbursements/campuses",
            headers=_h(prov_token),
            timeout=30,
        ).json()
        outside = None
        for item in prov_list:
            if "Jakarta Barat" not in item["regions"]:
                outside = item["campus_key"]
                break
        if not outside:
            pytest.skip("no campus outside Jakarta Barat")
        r = requests.get(
            f"{API}/admin/disbursements/campuses/{outside}",
            headers=_h(regional_admin["token"]),
            timeout=30,
        )
        assert r.status_code == 404

    def test_regional_update_aggregate_forbidden(self, prov_token, regional_admin):
        # Pick a campus visible to regional admin (Jakarta Barat)
        r = requests.get(
            f"{API}/admin/disbursements/campuses",
            headers=_h(regional_admin["token"]),
            timeout=30,
        )
        assert r.status_code == 200
        items = r.json()
        if not items:
            pytest.skip("regional admin sees no campuses to attempt update")
        campus_key = items[0]["campus_key"]
        put = requests.put(
            f"{API}/admin/disbursements/campuses/{campus_key}/regions/Jakarta Barat/stages/1",
            headers=_h(regional_admin["token"]),
            json={"status": "menunggu_bukti", "amount": 100000,
                  "disbursed_at": "", "reference": "", "notes": ""},
            timeout=30,
        )
        assert put.status_code == 403

    def test_regional_transfer_proofs_alias_forbidden(self, regional_admin):
        files = {"files": ("t.pdf", b"%PDF-1.4 test", "application/pdf")}
        r = requests.post(
            f"{API}/admin/disbursements/transfer-proofs",
            headers=_h(regional_admin["token"]),
            data={"stage": "1"},
            files=files,
            timeout=30,
        )
        assert r.status_code == 403

    def test_regional_audit_scoped(self, regional_admin):
        r = requests.get(
            f"{API}/admin/disbursements/campuses",
            headers=_h(regional_admin["token"]),
            timeout=30,
        )
        items = r.json()
        if not items:
            pytest.skip("no campus for regional audit")
        campus_key = items[0]["campus_key"]
        rr = requests.get(
            f"{API}/admin/disbursements/campuses/{campus_key}/audit",
            headers=_h(regional_admin["token"]),
            timeout=30,
        )
        assert rr.status_code == 200
        assert isinstance(rr.json(), list)


# ---------------------------------------------------------------------------
# 5. transfer-proofs alias validation-only
# ---------------------------------------------------------------------------
class TestTransferProofsAlias:
    def test_alias_bad_stage(self, prov_token):
        files = {"files": ("t.pdf", b"%PDF-1.4 test", "application/pdf")}
        r = requests.post(
            f"{API}/admin/disbursements/transfer-proofs",
            headers=_h(prov_token),
            data={"stage": "5"},
            files=files,
            timeout=30,
        )
        assert r.status_code == 400

    def test_alias_bad_extension(self, prov_token):
        files = {"files": ("hello.txt", b"not a proof", "text/plain")}
        r = requests.post(
            f"{API}/admin/disbursements/transfer-proofs",
            headers=_h(prov_token),
            data={"stage": "1"},
            files=files,
            timeout=30,
        )
        assert r.status_code == 400

    def test_alias_bad_magic_bytes(self, prov_token):
        # .pdf extension but non-PDF content should fail magic-bytes check
        files = {"files": ("fake.pdf", b"NOTAPDFXX", "application/pdf")}
        r = requests.post(
            f"{API}/admin/disbursements/transfer-proofs",
            headers=_h(prov_token),
            data={"stage": "1"},
            files=files,
            timeout=30,
        )
        assert r.status_code == 400

    def test_alias_empty_files(self, prov_token):
        r = requests.post(
            f"{API}/admin/disbursements/transfer-proofs",
            headers=_h(prov_token),
            data={"stage": "1"},
            files={},
            timeout=30,
        )
        assert r.status_code in (400, 422)


# ---------------------------------------------------------------------------
# 6. Audit endpoint for Admin Provinsi
# ---------------------------------------------------------------------------
class TestCampusAudit:
    def test_audit_ok(self, prov_token):
        campuses = requests.get(
            f"{API}/admin/disbursements/campuses", headers=_h(prov_token), timeout=30
        ).json()
        campus_key = campuses[0]["campus_key"]
        r = requests.get(
            f"{API}/admin/disbursements/campuses/{campus_key}/audit",
            headers=_h(prov_token),
            timeout=30,
        )
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_audit_unknown_campus_404(self, prov_token):
        r = requests.get(
            f"{API}/admin/disbursements/campuses/campus_bogus/audit",
            headers=_h(prov_token),
            timeout=30,
        )
        assert r.status_code == 404
