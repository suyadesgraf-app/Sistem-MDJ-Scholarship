"""Backend tests for auto-registration of student campus (Kampus Lainnya → MDJ-KMP-XXXXXX)."""
import os
import re
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or "http://localhost:8001"
API = f"{BASE_URL}/api"

ADMIN = {"email": "admin.mdj@baznasbazisdki.id", "password": "AdminMDJ2026!"}
STUDENT = {"email": "mahasiswa.mdj@baznasbazisdki.id", "password": "MahasiswaMDJ2026!"}

CODE_RE = re.compile(r"^MDJ-KMP-\d{6}$")
UNIQUE_NAME = f"TEST_AutoKampus_{uuid.uuid4().hex[:8]}"


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_headers():
    return {"Authorization": f"Bearer {_login(ADMIN)}"}


@pytest.fixture(scope="module")
def student_headers():
    return {"Authorization": f"Bearer {_login(STUDENT)}"}


@pytest.fixture(scope="module")
def original_profile(student_headers):
    r = requests.get(f"{API}/profile", headers=student_headers, timeout=20)
    assert r.status_code == 200, r.text
    data = r.json().get("data", {}) or {}
    return data


def test_1_get_campuses_no_object_id_and_baseline(admin_headers):
    r = requests.get(f"{API}/campuses", headers=admin_headers, timeout=20)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    for c in data:
        assert "_id" not in c
        assert "id" in c and "name" in c
    # baseline expected 378
    print(f"Baseline campus count: {len(data)}")


def test_2_student_saves_kampus_lainnya_and_gets_generated_code(student_headers, original_profile):
    # merge existing profile data with new institusi
    new_data = dict(original_profile)
    new_data["institusi"] = UNIQUE_NAME
    r = requests.put(f"{API}/profile", json={"data": new_data}, headers=student_headers, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("campus"), f"expected campus object in response, got {body}"
    campus = body["campus"]
    assert campus["name"] == UNIQUE_NAME
    assert CODE_RE.match(campus["code"]), f"code {campus.get('code')} doesn't match MDJ-KMP-\\d{{6}}"
    assert "_id" not in campus
    # store id for later cleanup
    pytest.created_campus = campus


def test_3_admin_sees_new_campus_in_list(admin_headers):
    r = requests.get(f"{API}/campuses", headers=admin_headers, timeout=20)
    assert r.status_code == 200
    data = r.json()
    match = [c for c in data if c["name"] == UNIQUE_NAME]
    assert match, f"campus {UNIQUE_NAME} not found in admin list"
    assert CODE_RE.match(match[0]["code"])
    for c in data:
        assert "_id" not in c


def test_4_resaving_same_campus_does_not_duplicate(student_headers, original_profile, admin_headers):
    new_data = dict(original_profile)
    new_data["institusi"] = UNIQUE_NAME  # same as before
    r = requests.put(f"{API}/profile", json={"data": new_data}, headers=student_headers, timeout=30)
    assert r.status_code == 200
    body = r.json()
    # since it already exists, backend should return campus=None (no new registration)
    assert body.get("campus") is None, f"expected campus=None on re-save, got {body.get('campus')}"
    # verify no duplicate in list
    lst = requests.get(f"{API}/campuses", headers=admin_headers, timeout=20).json()
    matches = [c for c in lst if c["name"].lower() == UNIQUE_NAME.lower()]
    assert len(matches) == 1, f"expected 1 entry, found {len(matches)}"


def test_5_student_still_403_on_campus_mutations(student_headers):
    r = requests.post(f"{API}/campuses", json={"name": "TEST_hack"},
                     headers={**student_headers, "Content-Type": "application/json"}, timeout=20)
    assert r.status_code == 403
    r = requests.put(f"{API}/campuses/00000000-0000-0000-0000-000000000000",
                     json={"name": "x"},
                     headers={**student_headers, "Content-Type": "application/json"}, timeout=20)
    assert r.status_code == 403
    r = requests.delete(f"{API}/campuses/00000000-0000-0000-0000-000000000000",
                        headers=student_headers, timeout=20)
    assert r.status_code == 403
    files = {"file": ("x.xlsx", b"dummy",
                      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    r = requests.post(f"{API}/campuses/import", files=files, headers=student_headers, timeout=20)
    assert r.status_code == 403


def test_6_cleanup_delete_test_campus_and_restore_profile(admin_headers, student_headers, original_profile):
    # find and delete
    lst = requests.get(f"{API}/campuses", headers=admin_headers, timeout=20).json()
    matches = [c for c in lst if c["name"] == UNIQUE_NAME]
    assert matches, "test campus disappeared before cleanup"
    for m in matches:
        d = requests.delete(f"{API}/campuses/{m['id']}", headers=admin_headers, timeout=20)
        assert d.status_code == 200, d.text
    # verify removed
    lst = requests.get(f"{API}/campuses", headers=admin_headers, timeout=20).json()
    assert not any(c["name"] == UNIQUE_NAME for c in lst)

    # restore student profile to original institusi (or original data)
    r = requests.put(f"{API}/profile", json={"data": original_profile}, headers=student_headers, timeout=30)
    assert r.status_code == 200
    # verify
    prof = requests.get(f"{API}/profile", headers=student_headers, timeout=20).json()
    assert (prof.get("data") or {}).get("institusi") == original_profile.get("institusi")


def test_7_final_campus_total_is_378(admin_headers):
    r = requests.get(f"{API}/campuses", headers=admin_headers, timeout=20)
    assert r.status_code == 200
    data = r.json()
    print(f"Final campus count: {len(data)}")
    assert len(data) == 378, f"expected 378 after cleanup, got {len(data)}"
