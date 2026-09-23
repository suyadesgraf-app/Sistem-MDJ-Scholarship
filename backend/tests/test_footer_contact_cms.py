"""Backend tests for footer & Hubungi Kami CMS content."""
import copy
import os

import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

SUPER_ADMIN_EMAIL = "supri@baznasbazisdki.id"
SUPER_ADMIN_PASSWORD = "MdjSuper2026!"


@pytest.fixture(scope="module")
def auth_headers():
    resp = requests.post(
        f"{API}/auth/login",
        json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD},
        timeout=30,
    )
    assert resp.status_code == 200, resp.text
    token = resp.json().get("token") or resp.json().get("access_token")
    assert token
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def original_content(auth_headers):
    resp = requests.get(f"{API}/site/content", timeout=30)
    assert resp.status_code == 200
    data = resp.json()
    assert "footer" in data
    assert isinstance(data["footer"].get("social_links"), list)
    assert isinstance(data["footer"].get("contact", {}).get("items"), list)
    return data


@pytest.fixture(scope="module", autouse=True)
def restore_footer(auth_headers, original_content):
    """Ensure original footer is restored after all tests."""
    yield
    payload = {"content": {"footer": copy.deepcopy(original_content["footer"])}}
    r = requests.put(f"{API}/site/content", json=payload, headers=auth_headers, timeout=30)
    assert r.status_code == 200, f"Failed to restore footer: {r.text}"


def _current_footer():
    r = requests.get(f"{API}/site/content", timeout=30)
    r.raise_for_status()
    return r.json()["footer"]


def test_get_site_content_returns_footer_shape(original_content):
    footer = original_content["footer"]
    assert "social_links" in footer
    assert "contact" in footer
    assert "title" in footer["contact"]
    assert "items" in footer["contact"]
    # default platforms present
    platforms = {s.get("platform") for s in footer["social_links"]}
    assert {"facebook", "instagram", "youtube"}.issubset(platforms)


def test_put_footer_adds_extra_social_and_contact_and_persists(auth_headers, original_content):
    new_footer = copy.deepcopy(original_content["footer"])
    new_footer["social_links"].append({
        "platform": "other",
        "label": "TEST_TikTok",
        "url": "https://www.tiktok.com/@test_mdj",
    })
    new_footer["contact"]["items"].append({
        "type": "phone",
        "label": "TEST_Hotline Tambahan",
        "value": "021-0000-1234",
        "url": "tel:+62210001234",
    })
    r = requests.put(
        f"{API}/site/content",
        json={"content": {"footer": new_footer}},
        headers=auth_headers,
        timeout=30,
    )
    assert r.status_code == 200, r.text

    persisted = _current_footer()
    labels = [s["label"] for s in persisted["social_links"]]
    contacts = [c["label"] for c in persisted["contact"]["items"]]
    assert "TEST_TikTok" in labels
    assert "TEST_Hotline Tambahan" in contacts
    # url stored intact
    tt = next(s for s in persisted["social_links"] if s["label"] == "TEST_TikTok")
    assert tt["url"] == "https://www.tiktok.com/@test_mdj"


def test_put_footer_rejects_javascript_scheme_social(auth_headers, original_content):
    bad_footer = copy.deepcopy(original_content["footer"])
    bad_footer["social_links"].append({
        "platform": "other",
        "label": "TEST_XSS",
        "url": "javascript:alert(1)",
    })
    r = requests.put(
        f"{API}/site/content",
        json={"content": {"footer": bad_footer}},
        headers=auth_headers,
        timeout=30,
    )
    assert r.status_code == 422, r.text

    # confirm not saved
    persisted = _current_footer()
    labels = [s["label"] for s in persisted["social_links"]]
    assert "TEST_XSS" not in labels


def test_put_footer_rejects_javascript_scheme_contact_url(auth_headers, original_content):
    bad_footer = copy.deepcopy(original_content["footer"])
    bad_footer["contact"]["items"].append({
        "type": "other",
        "label": "TEST_BadContact",
        "value": "click me",
        "url": "javascript:alert(2)",
    })
    r = requests.put(
        f"{API}/site/content",
        json={"content": {"footer": bad_footer}},
        headers=auth_headers,
        timeout=30,
    )
    assert r.status_code == 422, r.text
    persisted = _current_footer()
    labels = [c["label"] for c in persisted["contact"]["items"]]
    assert "TEST_BadContact" not in labels


def test_contact_allows_mailto_and_tel(auth_headers, original_content):
    footer = copy.deepcopy(original_content["footer"])
    footer["contact"]["items"].append({
        "type": "email",
        "label": "TEST_Mail",
        "value": "hello@test.invalid",
        "url": "mailto:hello@test.invalid",
    })
    r = requests.put(
        f"{API}/site/content",
        json={"content": {"footer": footer}},
        headers=auth_headers,
        timeout=30,
    )
    assert r.status_code == 200, r.text
    persisted = _current_footer()
    assert any(c["label"] == "TEST_Mail" for c in persisted["contact"]["items"])


def test_social_url_scheme_is_case_insensitive(auth_headers, original_content):
    footer = copy.deepcopy(original_content["footer"])
    footer["social_links"].append({
        "platform": "other",
        "label": "TEST_Uppercase Scheme",
        "url": "HTTPS://example.org/mdj",
    })
    response = requests.put(
        f"{API}/site/content",
        json={"content": {"footer": footer}},
        headers=auth_headers,
        timeout=30,
    )
    assert response.status_code == 200, response.text
