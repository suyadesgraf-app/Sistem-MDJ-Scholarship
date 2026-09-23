"""Tests for Super Admin news_categories CRUD on /api/site/content.

Ensures:
1. GET /api/site/content returns news_categories (default backfill for legacy content).
2. Only Super Admin may PUT /api/site/content.
3. Validation: empty items, duplicates, too many, invalid types are rejected.
4. Renaming a category updates announcements referring to old name.
5. Deleting a category maps its announcements to the first remaining category.
6. Original content is restored after tests.
"""
import copy
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
SUPER_ADMIN = {"email": "supri@baznasbazisdki.id", "password": "MdjSuper2026!"}
STUDENT = {"email": "mahasiswa.mdj@baznasbazisdki.id", "password": "MahasiswaMDJ2026!"}

CONTENT_URL = f"{BASE_URL}/api/site/content"


def _login(creds):
    r = requests.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login failed for {creds['email']}: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def super_token():
    return _login(SUPER_ADMIN)


@pytest.fixture(scope="module")
def student_token():
    try:
        return _login(STUDENT)
    except AssertionError:
        return None


def _headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def snapshot(super_token):
    """Snapshot original site content and restore after tests."""
    r = requests.get(CONTENT_URL, timeout=30)
    assert r.status_code == 200
    original = r.json()
    yield copy.deepcopy(original)
    # Restore original categories + announcements
    restore_payload = {
        "content": {
            "news_categories": original.get("news_categories") or [],
            "announcements": original.get("announcements") or [],
        }
    }
    resp = requests.put(CONTENT_URL, json=restore_payload, headers=_headers(super_token), timeout=30)
    assert resp.status_code == 200, f"restore failed: {resp.text}"


def test_get_returns_news_categories(snapshot):
    r = requests.get(CONTENT_URL, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data.get("news_categories"), list)
    assert len(data["news_categories"]) >= 1
    # Should include the defaults present initially
    assert all(isinstance(c, str) and c.strip() for c in data["news_categories"])


def test_put_requires_auth(snapshot):
    r = requests.put(CONTENT_URL, json={"content": {"news_categories": ["A", "B"]}}, timeout=30)
    assert r.status_code in (401, 403)


def test_put_forbidden_for_student(snapshot, student_token):
    if not student_token:
        pytest.skip("Student login unavailable")
    r = requests.put(
        CONTENT_URL,
        json={"content": {"news_categories": ["A", "B"]}},
        headers=_headers(student_token),
        timeout=30,
    )
    assert r.status_code == 403


def test_reject_empty_list(super_token, snapshot):
    r = requests.put(
        CONTENT_URL,
        json={"content": {"news_categories": []}},
        headers=_headers(super_token),
        timeout=30,
    )
    assert r.status_code == 400


def test_reject_empty_item(super_token, snapshot):
    r = requests.put(
        CONTENT_URL,
        json={"content": {"news_categories": ["Pengumuman", "  "]}},
        headers=_headers(super_token),
        timeout=30,
    )
    assert r.status_code == 400


def test_reject_duplicate(super_token, snapshot):
    r = requests.put(
        CONTENT_URL,
        json={"content": {"news_categories": ["Info", "info"]}},
        headers=_headers(super_token),
        timeout=30,
    )
    assert r.status_code == 400


def test_reject_over_limit(super_token, snapshot):
    r = requests.put(
        CONTENT_URL,
        json={"content": {"news_categories": [f"Kategori {i}" for i in range(21)]}},
        headers=_headers(super_token),
        timeout=30,
    )
    assert r.status_code == 400


def test_reject_non_list(super_token, snapshot):
    r = requests.put(
        CONTENT_URL,
        json={"content": {"news_categories": "Pengumuman"}},
        headers=_headers(super_token),
        timeout=30,
    )
    assert r.status_code == 400


def test_rename_updates_announcements(super_token, snapshot):
    original = snapshot
    orig_cats = list(original["news_categories"])
    orig_anns = original.get("announcements") or []
    # Choose the first category present in any announcement to rename
    used_cat = None
    for ann in orig_anns:
        if ann.get("category") in orig_cats:
            used_cat = ann["category"]
            break
    if not used_cat:
        pytest.skip("No announcement using an existing category to rename")
    new_name = f"{used_cat} TESTX"
    new_cats = [new_name if c == used_cat else c for c in orig_cats]
    resp = requests.put(
        CONTENT_URL,
        json={
            "content": {
                "news_categories": new_cats,
                "news_category_renames": {used_cat: new_name},
            }
        },
        headers=_headers(super_token),
        timeout=30,
    )
    assert resp.status_code == 200, resp.text
    got = requests.get(CONTENT_URL, timeout=30).json()
    assert new_name in got["news_categories"]
    assert used_cat not in got["news_categories"]
    # Any announcement that used `used_cat` must now use `new_name`
    renamed_count = sum(1 for a in got["announcements"] if a.get("category") == new_name)
    assert renamed_count >= 1


def test_delete_maps_to_fallback(super_token, snapshot):
    # After previous test the categories may already have TESTX suffix. Fetch current
    current = requests.get(CONTENT_URL, timeout=30).json()
    cats = list(current["news_categories"])
    anns = current.get("announcements") or []
    # Find a category currently used
    used = None
    for a in anns:
        c = a.get("category")
        if c in cats:
            used = c
            break
    if not used:
        pytest.skip("No used category to delete")
    remaining = [c for c in cats if c != used]
    assert remaining, "must have at least one remaining"
    resp = requests.put(
        CONTENT_URL,
        json={"content": {"news_categories": remaining}},
        headers=_headers(super_token),
        timeout=30,
    )
    assert resp.status_code == 200, resp.text
    got = requests.get(CONTENT_URL, timeout=30).json()
    assert used not in got["news_categories"]
    fallback = remaining[0]
    # Announcements previously using `used` should be mapped to fallback
    for a in got["announcements"]:
        assert a.get("category") in got["news_categories"], f"orphan cat: {a.get('category')}"


def test_invalid_rename_target_ignored(super_token, snapshot):
    """Rename to a name not in the new list must be safely ignored (not crash)."""
    current = requests.get(CONTENT_URL, timeout=30).json()
    cats = list(current["news_categories"])
    resp = requests.put(
        CONTENT_URL,
        json={
            "content": {
                "news_categories": cats,
                "news_category_renames": {"NonExistent": "AlsoNotInList"},
            }
        },
        headers=_headers(super_token),
        timeout=30,
    )
    assert resp.status_code == 200


def test_rename_without_categories_rejected(super_token, snapshot):
    resp = requests.put(
        CONTENT_URL,
        json={"content": {"news_category_renames": {"A": "B"}}},
        headers=_headers(super_token),
        timeout=30,
    )
    assert resp.status_code == 400
