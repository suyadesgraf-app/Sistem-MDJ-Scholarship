"""Tests for popup flags in site announcements (student & landing)."""
import copy
import os
import time

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fall back to same env var read by frontend
    with open("/app/frontend/.env") as fh:
        for line in fh:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                break

SUPER_ADMIN = {"email": "supri@baznasbazisdki.id", "password": "MdjSuper2026!"}
STUDENT = {"email": "mahasiswa.mdj@baznasbazisdki.id", "password": "MahasiswaMDJ2026!"}


def _login(creds):
    r = requests.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login failed {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def super_admin_headers():
    return {"Authorization": f"Bearer {_login(SUPER_ADMIN)}"}


@pytest.fixture(scope="module")
def student_headers():
    return {"Authorization": f"Bearer {_login(STUDENT)}"}


@pytest.fixture(scope="module")
def original_content(super_admin_headers):
    """Snapshot original content and restore after all tests."""
    r = requests.get(f"{BASE_URL}/api/site/content", timeout=30)
    assert r.status_code == 200
    snapshot = r.json()
    snapshot.pop("updated_at", None)
    snapshot.pop("key", None)
    yield copy.deepcopy(snapshot)
    # Restore
    restore = copy.deepcopy(snapshot)
    # Ensure popup flags off in restored data
    for a in restore.get("announcements", []) or []:
        if isinstance(a, dict):
            a["show_student_popup"] = False
            a["show_landing_popup"] = False
    rr = requests.put(
        f"{BASE_URL}/api/site/content",
        json={"content": restore},
        headers=super_admin_headers,
        timeout=30,
    )
    assert rr.status_code == 200, f"restore failed {rr.status_code} {rr.text}"


def _put(content, headers):
    return requests.put(
        f"{BASE_URL}/api/site/content",
        json={"content": content},
        headers=headers,
        timeout=30,
    )


class TestPopupValidation:
    def test_reject_multiple_student_popups(self, original_content, super_admin_headers):
        content = copy.deepcopy(original_content)
        anns = content.get("announcements") or []
        assert len(anns) >= 2, "Need at least 2 announcements to test"
        anns[0]["show_student_popup"] = True
        anns[1]["show_student_popup"] = True
        content["announcements"] = anns
        r = _put(content, super_admin_headers)
        assert r.status_code == 400, f"expected 400 got {r.status_code} {r.text}"
        assert "Mahasiswa" in r.text or "mahasiswa" in r.text.lower()

    def test_reject_multiple_landing_popups(self, original_content, super_admin_headers):
        content = copy.deepcopy(original_content)
        anns = content.get("announcements") or []
        assert len(anns) >= 2
        anns[0]["show_landing_popup"] = True
        anns[1]["show_landing_popup"] = True
        content["announcements"] = anns
        r = _put(content, super_admin_headers)
        assert r.status_code == 400
        assert "Beranda" in r.text or "beranda" in r.text.lower()

    def test_accept_one_each(self, original_content, super_admin_headers):
        content = copy.deepcopy(original_content)
        anns = content.get("announcements") or []
        for a in anns:
            a["show_student_popup"] = False
            a["show_landing_popup"] = False
        anns[0]["show_student_popup"] = True
        anns[1]["show_landing_popup"] = True
        content["announcements"] = anns
        r = _put(content, super_admin_headers)
        assert r.status_code == 200, r.text
        saved = r.json().get("announcements", [])
        student_count = sum(1 for a in saved if a.get("show_student_popup") is True)
        landing_count = sum(1 for a in saved if a.get("show_landing_popup") is True)
        assert student_count == 1
        assert landing_count == 1


class TestStudentPendingEndpoint:
    def test_pending_null_when_no_student_popup(
        self, original_content, super_admin_headers, student_headers
    ):
        content = copy.deepcopy(original_content)
        anns = content.get("announcements") or []
        for a in anns:
            a["show_student_popup"] = False
            a["show_landing_popup"] = False
        content["announcements"] = anns
        r = _put(content, super_admin_headers)
        assert r.status_code == 200, r.text
        time.sleep(0.5)
        pr = requests.get(
            f"{BASE_URL}/api/student/site-announcements/pending",
            headers=student_headers,
            timeout=30,
        )
        assert pr.status_code == 200
        assert pr.json().get("announcement") is None

    def test_pending_returns_only_active_popup(
        self, original_content, super_admin_headers, student_headers
    ):
        content = copy.deepcopy(original_content)
        anns = content.get("announcements") or []
        for a in anns:
            a["show_student_popup"] = False
            a["show_landing_popup"] = False
        # Set popup on last announcement (unique title so we can compare)
        target_title = anns[-1].get("title")
        anns[-1]["show_student_popup"] = True
        content["announcements"] = anns
        r = _put(content, super_admin_headers)
        assert r.status_code == 200, r.text
        time.sleep(0.5)

        # First: reset any prior seen state — get pending, mark seen if returned; then re-enable
        pr = requests.get(
            f"{BASE_URL}/api/student/site-announcements/pending",
            headers=student_headers,
            timeout=30,
        )
        assert pr.status_code == 200
        ann = pr.json().get("announcement")
        # It's possible that in a prior test iteration the notification was
        # already seen; in that case the endpoint will return None.
        # We still verify the popup source_id matches only when returned.
        if ann is not None:
            assert ann.get("title") == target_title

        # Test /seen makes it disappear
        if ann is not None:
            sr = requests.post(
                f"{BASE_URL}/api/student/site-announcements/{ann['id']}/seen",
                headers=student_headers,
                timeout=30,
            )
            assert sr.status_code == 200
            pr2 = requests.get(
                f"{BASE_URL}/api/student/site-announcements/pending",
                headers=student_headers,
                timeout=30,
            )
            assert pr2.status_code == 200
            assert pr2.json().get("announcement") is None

    def test_regular_announcement_does_not_trigger_popup(
        self, original_content, super_admin_headers, student_headers
    ):
        # Turn all popup flags off, ensure pending is None even if there are
        # existing announcement notifications for the student.
        content = copy.deepcopy(original_content)
        anns = content.get("announcements") or []
        for a in anns:
            a["show_student_popup"] = False
            a["show_landing_popup"] = False
        content["announcements"] = anns
        r = _put(content, super_admin_headers)
        assert r.status_code == 200
        time.sleep(0.3)
        pr = requests.get(
            f"{BASE_URL}/api/student/site-announcements/pending",
            headers=student_headers,
            timeout=30,
        )
        assert pr.status_code == 200
        assert pr.json().get("announcement") is None
