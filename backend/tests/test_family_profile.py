"""Tests for PUT /api/profile family validation and normalization.

Covers review points 5 and 6:
- Reject empty family, invalid NIK, invalid parent status, count mismatch,
  count > 15, empty electricityPower.
- Accept valid family including count = "0" (numeric string).
- GET /api/profile after save returns normalized family and data persists on reload.
"""
import copy
import os
import pytest
import requests

def _load_backend_url():
    val = os.environ.get("REACT_APP_BACKEND_URL")
    if not val:
        env_path = "/app/frontend/.env"
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        val = line.split("=", 1)[1].strip()
                        break
    assert val, "REACT_APP_BACKEND_URL not set"
    return val.rstrip("/")


BASE_URL = _load_backend_url()
STUDENT_EMAIL = "mahasiswa.mdj@baznasbazisdki.id"
STUDENT_PASSWORD = "MahasiswaMDJ2026!"


def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def student_token():
    return _login(STUDENT_EMAIL, STUDENT_PASSWORD)


@pytest.fixture(scope="module")
def headers(student_token):
    return {"Authorization": f"Bearer {student_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module", autouse=True)
def snapshot_and_restore(headers):
    """Save existing profile.data then restore raw via API after tests."""
    r = requests.get(f"{BASE_URL}/api/profile", headers=headers, timeout=30)
    assert r.status_code == 200
    original = r.json().get("data") or {}
    snapshot = copy.deepcopy(original)
    yield snapshot
    # Try to restore. If snapshot lacks family (older state) API will reject; try direct DB restore fallback.
    try:
        requests.put(f"{BASE_URL}/api/profile", headers=headers,
                     json={"data": snapshot}, timeout=30)
    except Exception:
        pass


def _valid_family(count=0, members=None):
    parent = {
        "name": "TEST Ayah",
        "nik": "1234567890123456",
        "status": "hidup",
        "phone": "08123456789",
        "job": "PNS",
        "income": "5000000",
    }
    mother = {**parent, "name": "TEST Ibu", "nik": "6543210987654321", "status": "meninggal"}
    fam = {
        "father": parent,
        "mother": mother,
        "otherMemberCount": count,
        "otherMembers": members if members is not None else [],
        "electricityPower": "1.300 VA",
    }
    return fam


def _member(i=1):
    return {
        "name": f"TEST Anggota {i}",
        "nik": "1111222233334444",
        "relationship": "Kakak",
        "education": "SMA / SMK",
        "job": "Wiraswasta",
        "income": "2500000",
    }


def _put(headers, family, extra=None):
    data = {"namaLengkap": "TEST Mahasiswa MDJ", "email": STUDENT_EMAIL}
    if extra:
        data.update(extra)
    if family is not None:
        data["family"] = family
    return requests.put(f"{BASE_URL}/api/profile", headers=headers, json={"data": data}, timeout=30)


# --- Rejection cases ---
class TestRejections:
    def test_reject_missing_family(self, headers):
        r = _put(headers, None)
        assert r.status_code == 400
        assert "Keluarga" in r.text or "keluarga" in r.text

    def test_reject_empty_family_object(self, headers):
        r = _put(headers, {})
        assert r.status_code == 400

    def test_reject_invalid_nik_length(self, headers):
        fam = _valid_family()
        fam["father"]["nik"] = "12345"
        r = _put(headers, fam)
        assert r.status_code == 400
        assert "16" in r.text

    def test_reject_invalid_parent_status(self, headers):
        fam = _valid_family()
        fam["father"]["status"] = "unknown"
        r = _put(headers, fam)
        assert r.status_code == 400

    def test_reject_count_mismatch(self, headers):
        fam = _valid_family(count=2, members=[_member(1)])  # only 1 supplied
        r = _put(headers, fam)
        assert r.status_code == 400

    def test_reject_count_over_15(self, headers):
        fam = _valid_family(count=16, members=[_member(i) for i in range(16)])
        r = _put(headers, fam)
        assert r.status_code == 400
        assert "15" in r.text

    def test_reject_empty_electricity(self, headers):
        fam = _valid_family()
        fam["electricityPower"] = ""
        r = _put(headers, fam)
        assert r.status_code == 400

    def test_reject_deceased_parent_missing_details(self, headers):
        """Status meninggal still requires name/nik/phone/job/income."""
        fam = _valid_family()
        fam["father"] = {
            "name": "", "nik": "", "status": "meninggal",
            "phone": "", "job": "", "income": "",
        }
        r = _put(headers, fam)
        assert r.status_code == 400


# --- Acceptance & persistence ---
class TestAcceptance:
    def test_accept_valid_family_count_zero_string(self, headers):
        fam = _valid_family(count="0")
        r = _put(headers, fam)
        assert r.status_code == 200, r.text
        data = r.json()["data"]["family"]
        assert data["otherMemberCount"] == 0
        assert data["otherMembers"] == []
        assert data["father"]["nik"] == "1234567890123456"
        assert data["mother"]["status"] == "meninggal"
        assert data["electricityPower"] == "1.300 VA"

    def test_get_returns_normalized_family_after_save(self, headers):
        r = requests.get(f"{BASE_URL}/api/profile", headers=headers, timeout=30)
        assert r.status_code == 200
        fam = r.json()["data"]["family"]
        assert isinstance(fam["otherMemberCount"], int)
        assert fam["otherMemberCount"] == 0
        for key in ("father", "mother"):
            for f in ("name", "nik", "status", "phone", "job", "income"):
                assert fam[key][f], f"parent {key}.{f} missing"

    def test_accept_with_two_members(self, headers):
        fam = _valid_family(count=2, members=[_member(1), _member(2)])
        r = _put(headers, fam)
        assert r.status_code == 200, r.text
        data = r.json()["data"]["family"]
        assert data["otherMemberCount"] == 2
        assert len(data["otherMembers"]) == 2
        assert data["otherMembers"][0]["relationship"] == "Kakak"

        # Persist check
        r2 = requests.get(f"{BASE_URL}/api/profile", headers=headers, timeout=30)
        fam2 = r2.json()["data"]["family"]
        assert fam2["otherMemberCount"] == 2
        assert len(fam2["otherMembers"]) == 2
