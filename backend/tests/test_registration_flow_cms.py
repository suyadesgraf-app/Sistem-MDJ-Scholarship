"""Tests for the flexible registration_flow (Alur Pendaftaran) CMS endpoint.

The feature intentionally supports:
- Empty list (0 stages)
- Arbitrary titles/descriptions
- Reordering
- Up to 30 stages

Validation:
- Empty title -> 400
- Duplicate title (case-insensitive) -> 400
- Title > 120 chars -> 400
- Description > 800 chars -> 400
- Non-dict item -> 400
- > 30 stages -> 400
- Non-list -> 400
- Non-super-admin cannot PUT
"""
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
    return copy.deepcopy(r.json().get("registration_flow") or [])


@pytest.fixture(autouse=True)
def _restore_flow_after_each_test(super_token, original_flow):
    yield
    # Restore original flow after every test to avoid leaking state to prod
    restore = requests.put(
        f"{API}/site/content",
        json={"content": {"registration_flow": original_flow}},
        headers={"Authorization": f"Bearer {super_token}"},
        timeout=20,
    )
    assert restore.status_code == 200, f"restore failed: {restore.status_code} {restore.text}"


def _put(super_token, flow):
    return requests.put(
        f"{API}/site/content",
        json={"content": {"registration_flow": flow}},
        headers={"Authorization": f"Bearer {super_token}"},
        timeout=20,
    )


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------

def test_non_super_admin_cannot_update_registration_flow(admin_token):
    r = requests.put(
        f"{API}/site/content",
        json={"content": {"registration_flow": [{"title": "X", "desc": ""}]}},
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=20,
    )
    assert r.status_code in (401, 403)


def test_unauthenticated_cannot_update(super_token):
    r = requests.put(
        f"{API}/site/content",
        json={"content": {"registration_flow": []}},
        timeout=20,
    )
    assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------

def test_put_empty_list_is_allowed_and_persisted(super_token):
    r = _put(super_token, [])
    assert r.status_code == 200, r.text
    assert r.json()["registration_flow"] == []
    # Verify persistence
    r2 = requests.get(f"{API}/site/content", timeout=20)
    assert r2.json().get("registration_flow") == []


def test_put_new_titles_and_descriptions(super_token):
    new_flow = [
        {"title": "TEST Tahap A", "desc": "Deskripsi A"},
        {"title": "TEST Tahap B", "desc": "Deskripsi B panjang " * 5},
        {"title": "TEST Tahap C", "desc": ""},
    ]
    r = _put(super_token, new_flow)
    assert r.status_code == 200, r.text
    saved = r.json()["registration_flow"]
    assert [i["title"] for i in saved] == ["TEST Tahap A", "TEST Tahap B", "TEST Tahap C"]
    assert saved[0]["desc"] == "Deskripsi A"
    assert saved[2]["desc"] == ""
    # Persistence
    r2 = requests.get(f"{API}/site/content", timeout=20)
    assert [i["title"] for i in r2.json()["registration_flow"]] == \
        ["TEST Tahap A", "TEST Tahap B", "TEST Tahap C"]


def test_put_reorder_stages(super_token):
    flow = [
        {"title": "TEST Satu", "desc": "1"},
        {"title": "TEST Dua", "desc": "2"},
        {"title": "TEST Tiga", "desc": "3"},
    ]
    assert _put(super_token, flow).status_code == 200
    reordered = [flow[2], flow[0], flow[1]]
    r = _put(super_token, reordered)
    assert r.status_code == 200
    saved = r.json()["registration_flow"]
    assert [i["title"] for i in saved] == ["TEST Tiga", "TEST Satu", "TEST Dua"]


def test_put_edit_title_and_desc(super_token):
    flow = [{"title": "TEST Awal", "desc": "awal"}]
    assert _put(super_token, flow).status_code == 200
    edited = [{"title": "TEST Awal Diedit", "desc": "keterangan baru"}]
    r = _put(super_token, edited)
    assert r.status_code == 200
    saved = r.json()["registration_flow"]
    assert saved == [{"title": "TEST Awal Diedit", "desc": "keterangan baru"}]


def test_put_30_stages_boundary_allowed(super_token):
    flow = [{"title": f"TEST T{i:02d}", "desc": ""} for i in range(30)]
    r = _put(super_token, flow)
    assert r.status_code == 200, r.text
    assert len(r.json()["registration_flow"]) == 30


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------

def test_reject_empty_title(super_token):
    r = _put(super_token, [{"title": "   ", "desc": "x"}])
    assert r.status_code == 400
    assert "judul" in r.text.lower()


def test_reject_duplicate_title_case_insensitive(super_token):
    r = _put(super_token, [
        {"title": "TEST Duplikat", "desc": ""},
        {"title": "test duplikat", "desc": ""},
    ])
    assert r.status_code == 400
    assert "duplikat" in r.text.lower()


def test_reject_title_over_120_chars(super_token):
    r = _put(super_token, [{"title": "A" * 121, "desc": ""}])
    assert r.status_code == 400
    assert "120" in r.text or "karakter" in r.text.lower()


def test_reject_description_over_800_chars(super_token):
    r = _put(super_token, [{"title": "TEST X", "desc": "d" * 801}])
    assert r.status_code == 400
    assert "800" in r.text or "keterangan" in r.text.lower()


def test_reject_non_dict_item(super_token):
    r = _put(super_token, ["not a dict"])
    assert r.status_code == 400


def test_reject_more_than_30_stages(super_token):
    flow = [{"title": f"TEST U{i:02d}", "desc": ""} for i in range(31)]
    r = _put(super_token, flow)
    assert r.status_code == 400
    assert "30" in r.text


def test_reject_non_list_registration_flow(super_token):
    r = requests.put(
        f"{API}/site/content",
        json={"content": {"registration_flow": {"not": "a list"}}},
        headers={"Authorization": f"Bearer {super_token}"},
        timeout=20,
    )
    assert r.status_code == 400
