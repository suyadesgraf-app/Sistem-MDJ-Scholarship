"""Iter49 - Public site announcement attachments (banner image, doc attachment, external link).

Covers:
- POST /api/super-admin/site-announcements/upload (super_admin only, mime whitelist)
- GET  /api/site/announcement-files/{file_id} (public, returns bytes)
- PUT  /api/site/content preserves+adds temp announcements; restores after test
"""
import io
import os
import pytest
import requests
from PIL import Image

def _load_backend_url():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if v:
        return v.rstrip("/")
    envpath = "/app/frontend/.env"
    if os.path.exists(envpath):
        for line in open(envpath):
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip().rstrip("/")
    raise RuntimeError("REACT_APP_BACKEND_URL not configured")


BASE_URL = _load_backend_url()
API = f"{BASE_URL}/api"

SUPER = {"email": "supri@baznasbazisdki.id", "password": "MdjSuper2026!"}
STUDENT = {"email": "mahasiswa.mdj@baznasbazisdki.id", "password": "MahasiswaMDJ2026!"}


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login failed for {creds['email']}: {r.status_code} {r.text}"
    return r.json()["token"]


def _headers(tok):
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def super_tok():
    return _login(SUPER)


@pytest.fixture(scope="module")
def student_tok():
    return _login(STUDENT)


@pytest.fixture(scope="module")
def png_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (11, 107, 58)).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture(scope="module")
def pdf_bytes():
    # minimal valid-ish PDF header
    return (
        b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
    )


# --- Upload endpoint auth/permission ---
def test_upload_requires_auth(png_bytes):
    r = requests.post(
        f"{API}/super-admin/site-announcements/upload",
        files={"file": ("t.png", png_bytes, "image/png")},
        timeout=30,
    )
    assert r.status_code in (401, 403), r.status_code


def test_upload_forbidden_for_student(student_tok, png_bytes):
    r = requests.post(
        f"{API}/super-admin/site-announcements/upload",
        headers=_headers(student_tok),
        files={"file": ("t.png", png_bytes, "image/png")},
        timeout=30,
    )
    assert r.status_code == 403, f"expected 403, got {r.status_code} {r.text}"


# --- Upload endpoint validation ---
def test_upload_rejects_unsupported_extension(super_tok):
    r = requests.post(
        f"{API}/super-admin/site-announcements/upload",
        headers=_headers(super_tok),
        files={"file": ("evil.txt", b"hello", "text/plain")},
        timeout=30,
    )
    assert r.status_code == 400, f"expected 400, got {r.status_code} {r.text}"


# --- Upload PNG banner and fetch publicly ---
def test_upload_png_and_public_fetch(super_tok, png_bytes):
    r = requests.post(
        f"{API}/super-admin/site-announcements/upload",
        headers=_headers(super_tok),
        files={"file": ("TEST_banner_iter49.png", png_bytes, "image/png")},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["content_type"] == "image/png"
    assert body["name"] == "TEST_banner_iter49.png"
    assert body["url"].startswith("/api/site/announcement-files/")
    file_id = body["id"]
    # Public GET (no auth)
    g = requests.get(f"{API}/site/announcement-files/{file_id}", timeout=30)
    assert g.status_code == 200
    assert g.headers.get("content-type", "").startswith("image/png")
    assert g.content == png_bytes
    # Stash for restoration test
    pytest.png_file_id = file_id
    pytest.png_url = body["url"]
    pytest.png_name = body["name"]


def test_upload_pdf_and_public_fetch(super_tok, pdf_bytes):
    r = requests.post(
        f"{API}/super-admin/site-announcements/upload",
        headers=_headers(super_tok),
        files={"file": ("TEST_lampiran_iter49.pdf", pdf_bytes, "application/pdf")},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["content_type"] == "application/pdf"
    file_id = body["id"]
    g = requests.get(f"{API}/site/announcement-files/{file_id}", timeout=30)
    assert g.status_code == 200
    assert g.headers.get("content-type", "").startswith("application/pdf")
    assert g.content == pdf_bytes
    pytest.pdf_file_id = file_id
    pytest.pdf_url = body["url"]
    pytest.pdf_name = body["name"]


def test_public_fetch_404_when_missing():
    r = requests.get(f"{API}/site/announcement-files/nonexistent-id-xyz", timeout=30)
    assert r.status_code == 404


# --- Full flow: put content with banner/attachment/link, verify public content, restore ---
def test_site_content_announcement_lifecycle(super_tok):
    # Read original content (public endpoint)
    orig = requests.get(f"{API}/site/content", timeout=30)
    assert orig.status_code == 200
    original_content = orig.json()
    original_ann = list(original_content.get("announcements", []))

    try:
        temp_announcements = original_ann + [
            {
                "date": "2026-01-01",
                "category": "TEST_ITER49",
                "title": "TEST_ITER49 Banner Announcement",
                "summary": "Temporary banner test",
                "banner": {
                    "id": pytest.png_file_id,
                    "url": pytest.png_url,
                    "name": pytest.png_name,
                    "content_type": "image/png",
                },
            },
            {
                "date": "2026-01-02",
                "category": "TEST_ITER49",
                "title": "TEST_ITER49 Attachment Announcement",
                "summary": "Temporary PDF test",
                "attachment": {
                    "id": pytest.pdf_file_id,
                    "url": pytest.pdf_url,
                    "name": pytest.pdf_name,
                    "content_type": "application/pdf",
                },
            },
            {
                "date": "2026-01-03",
                "category": "TEST_ITER49",
                "title": "TEST_ITER49 Link Announcement",
                "summary": "Temporary link test",
                "link": "https://example.com/pengumuman",
            },
        ]

        put = requests.put(
            f"{API}/site/content",
            headers=_headers(super_tok),
            json={"content": {"announcements": temp_announcements}},
            timeout=30,
        )
        assert put.status_code == 200, put.text
        after = put.json().get("announcements", [])
        titles = [a.get("title") for a in after]
        assert "TEST_ITER49 Banner Announcement" in titles
        assert "TEST_ITER49 Attachment Announcement" in titles
        assert "TEST_ITER49 Link Announcement" in titles

        # Public site content shows same
        pub = requests.get(f"{API}/site/content", timeout=30).json()
        pub_by_title = {a.get("title"): a for a in pub.get("announcements", [])}
        assert pub_by_title["TEST_ITER49 Banner Announcement"]["banner"]["url"] == pytest.png_url
        assert pub_by_title["TEST_ITER49 Attachment Announcement"]["attachment"]["url"] == pytest.pdf_url
        assert pub_by_title["TEST_ITER49 Link Announcement"]["link"] == "https://example.com/pengumuman"
    finally:
        # Always restore original announcements list exactly
        restore = requests.put(
            f"{API}/site/content",
            headers=_headers(super_tok),
            json={"content": {"announcements": original_ann}},
            timeout=30,
        )
        assert restore.status_code == 200
        final = requests.get(f"{API}/site/content", timeout=30).json()
        # No TEST_ITER49 announcements should remain
        assert not any(
            (a.get("category") == "TEST_ITER49") or str(a.get("title", "")).startswith("TEST_ITER49")
            for a in final.get("announcements", [])
        )
