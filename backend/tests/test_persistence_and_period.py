"""
Tests for:
  1. Nama Lengkap persistence across backend restart (bug #1).
  2. Registration window enforcement on POST /api/registration (bug #2).
  3. Restore original site_content settings and demo student profile after test.
"""
import os
import time
import copy
import subprocess
from datetime import datetime, timezone, timedelta

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://sistem-registrasi.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

SUPER = ("supri@baznasbazisdki.id", "MdjSuper2026!")
STUDENT = ("mahasiswa.mdj@baznasbazisdki.id", "MahasiswaMDJ2026!")


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return r.json()["token"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def super_tok():
    return _login(*SUPER)


@pytest.fixture(scope="module")
def student_tok():
    return _login(*STUDENT)


@pytest.fixture(scope="module")
def original_site_content(super_tok):
    r = requests.get(f"{API}/site/content", timeout=30)
    assert r.status_code == 200
    content = r.json()
    content.pop("logo_url", None)
    yield content
    # Restore
    restore = {k: v for k, v in content.items() if k not in ("updated_at",)}
    rr = requests.put(f"{API}/site/content", json={"content": restore}, headers=_h(super_tok), timeout=30)
    assert rr.status_code == 200, f"restore failed: {rr.text}"


@pytest.fixture(scope="module")
def original_student_profile(student_tok):
    r = requests.get(f"{API}/profile", headers=_h(student_tok), timeout=30)
    assert r.status_code == 200
    orig = r.json().get("data", {})
    yield orig
    # Restore profile
    rr = requests.put(f"{API}/profile", json={"data": orig}, headers=_h(student_tok), timeout=30)
    assert rr.status_code == 200, f"profile restore failed: {rr.text}"


def _update_site(super_tok, base_content, **overrides):
    # base_content is /site/content GET. Send with settings overrides. Keep required fields intact.
    new_content = copy.deepcopy(base_content)
    new_content.pop("updated_at", None)
    new_content.pop("logo_url", None)
    settings = dict(new_content.get("settings") or {})
    settings.update(overrides)
    new_content["settings"] = settings
    r = requests.put(f"{API}/site/content", json={"content": new_content}, headers=_h(super_tok), timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


# ---------- Test 1: Persistence across backend restart ----------
def test_1_name_persists_across_backend_restart(student_tok, original_student_profile):
    unique = "Nama Uji Persisten"
    payload_data = dict(original_student_profile)
    payload_data["namaLengkap"] = unique

    r = requests.put(f"{API}/profile", json={"data": payload_data}, headers=_h(student_tok), timeout=30)
    assert r.status_code == 200, r.text

    # Verify /auth/me and /profile
    me = requests.get(f"{API}/auth/me", headers=_h(student_tok), timeout=30).json()
    prof = requests.get(f"{API}/profile", headers=_h(student_tok), timeout=30).json()
    assert me.get("name") == unique
    assert prof.get("data", {}).get("namaLengkap") == unique

    # Restart backend
    subprocess.run(["sudo", "supervisorctl", "restart", "backend"], check=True)
    # wait for service
    for _ in range(20):
        time.sleep(1.5)
        try:
            hc = requests.get(f"{API}/site/content", timeout=5)
            if hc.status_code == 200:
                break
        except requests.RequestException:
            continue

    # Re-login (fresh token) and verify name persisted
    tok2 = _login(*STUDENT)
    me2 = requests.get(f"{API}/auth/me", headers=_h(tok2), timeout=30).json()
    prof2 = requests.get(f"{API}/profile", headers=_h(tok2), timeout=30).json()
    assert me2.get("name") == unique, f"/auth/me.name reverted to {me2.get('name')!r} after restart"
    assert prof2.get("data", {}).get("namaLengkap") == unique


# ---------- Test 2: Registration period enforcement ----------
def test_2a_ended_window_blocks_post_registration(super_tok, student_tok, original_site_content):
    now = datetime.now(timezone.utc)
    start = (now - timedelta(hours=2)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    end = (now - timedelta(hours=1)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    _update_site(super_tok, original_site_content,
                 registration_open=True,
                 registration_start_at=start,
                 registration_end_at=end)
    r = requests.post(f"{API}/registration",
                      json={"category": "Mahasiswa Sarjana (S1)", "action": "draft", "pakta_integritas_agreed": False},
                      headers=_h(student_tok), timeout=30)
    assert r.status_code == 403, f"expected 403 when window ended, got {r.status_code}: {r.text}"


def test_2b_future_window_blocks_post_registration(super_tok, student_tok, original_site_content):
    now = datetime.now(timezone.utc)
    start = (now + timedelta(hours=1)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    end = (now + timedelta(hours=2)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    _update_site(super_tok, original_site_content,
                 registration_open=True,
                 registration_start_at=start,
                 registration_end_at=end)
    r = requests.post(f"{API}/registration",
                      json={"category": "Mahasiswa Sarjana (S1)", "action": "draft", "pakta_integritas_agreed": False},
                      headers=_h(student_tok), timeout=30)
    assert r.status_code == 403, f"expected 403 pre-window, got {r.status_code}: {r.text}"


def test_2c_active_window_allows_post_registration(super_tok, student_tok, original_site_content):
    now = datetime.now(timezone.utc)
    start = (now - timedelta(hours=1)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    end = (now + timedelta(hours=2)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    _update_site(super_tok, original_site_content,
                 registration_open=True,
                 registration_start_at=start,
                 registration_end_at=end)
    r = requests.post(f"{API}/registration",
                      json={"category": "Mahasiswa Sarjana (S1)", "action": "draft", "pakta_integritas_agreed": False},
                      headers=_h(student_tok), timeout=30)
    assert r.status_code == 200, f"expected 200 in active window, got {r.status_code}: {r.text}"


def test_2d_draft_remains_after_period_closed(super_tok, student_tok, original_site_content):
    # After test_2c a draft exists. Now close window and confirm draft still returned by GET /registration.
    now = datetime.now(timezone.utc)
    start = (now - timedelta(hours=2)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    end = (now - timedelta(hours=1)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    _update_site(super_tok, original_site_content,
                 registration_open=True,
                 registration_start_at=start,
                 registration_end_at=end)
    r = requests.get(f"{API}/registration", headers=_h(student_tok), timeout=30)
    assert r.status_code == 200
    assert r.json().get("user_id"), f"draft was wiped: {r.json()}"

    # POST still rejected
    r2 = requests.post(f"{API}/registration",
                       json={"category": "Mahasiswa Sarjana (S1)", "action": "draft", "pakta_integritas_agreed": False},
                       headers=_h(student_tok), timeout=30)
    assert r2.status_code == 403
