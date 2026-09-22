"""Tests for student live chat audio (voice note) attachment support (iter 54).

Focus:
- Backend accepts a valid .webm audio upload via POST /api/student-live-chat/messages.
- Backend rejects unsupported audio ext (e.g., .exe or .txt).
- Attachment content-type is audio/webm.
- Download works for authorized users.

Cleanup: removes ephemeral users/profiles/messages created by this test.
"""
import io
import os
import uuid
import bcrypt
import pytest
import requests
from datetime import datetime, timezone
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                break

MONGO_URL = os.environ.get("MONGO_URL") or "mongodb://localhost:27017"
DB_NAME = os.environ.get("DB_NAME") or "test_database"

STUDENT = ("mahasiswa.mdj@baznasbazisdki.id", "MahasiswaMDJ2026!")
ADMIN = ("admin.mdj@baznasbazisdki.id", "AdminMDJ2026!")

client = MongoClient(MONGO_URL)
mdb = client[DB_NAME]

EPHEMERAL_USER_IDS = []
EPHEMERAL_MESSAGE_IDS = []


def login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json().get("token")


def hdr(t):
    return {"Authorization": f"Bearer {t}"}


def make_webm():
    """Minimal EBML/Matroska header - starts with 0x1A 0x45 0xDF 0xA3 ."""
    ebml = bytes([0x1A, 0x45, 0xDF, 0xA3])
    # Add fake DocType 'webm' body
    body = b"\x9F\x42\x82\x84webm" + b"\x00" * 200
    return ebml + body


def make_ogg():
    return b"OggS" + b"\x00" * 300


def make_mp3():
    # ID3v2 header
    return b"ID3\x03\x00\x00\x00\x00\x00\x00" + b"\x00" * 300


@pytest.fixture(scope="module")
def student_token():
    return login(*STUDENT)


@pytest.fixture(scope="module")
def admin_token():
    return login(*ADMIN)


def test_audio_webm_accepted(student_token):
    """Voice note (.webm) must be accepted and stored as audio/webm."""
    data = make_webm()
    files = {"attachment": ("voice.webm", data, "audio/webm")}
    r = requests.post(f"{BASE_URL}/api/student-live-chat/messages",
                      data={"message": "TEST_slc_audio webm"},
                      files=files, headers=hdr(student_token))
    assert r.status_code == 200, f"webm upload failed: {r.status_code} {r.text}"
    body = r.json()["message"]
    EPHEMERAL_MESSAGE_IDS.append(body["id"])
    att = body.get("attachment")
    assert att is not None, "attachment metadata missing"
    assert att.get("content_type", "").startswith("audio/"), f"unexpected content_type: {att.get('content_type')}"
    assert "storage_path" not in att


def test_audio_ogg_accepted(student_token):
    data = make_ogg()
    files = {"attachment": ("voice.ogg", data, "audio/ogg")}
    r = requests.post(f"{BASE_URL}/api/student-live-chat/messages",
                      data={"message": "TEST_slc_audio ogg"},
                      files=files, headers=hdr(student_token))
    assert r.status_code == 200, f"ogg upload failed: {r.status_code} {r.text}"
    EPHEMERAL_MESSAGE_IDS.append(r.json()["message"]["id"])


def test_audio_mp3_accepted(student_token):
    data = make_mp3()
    files = {"attachment": ("voice.mp3", data, "audio/mpeg")}
    r = requests.post(f"{BASE_URL}/api/student-live-chat/messages",
                      data={"message": "TEST_slc_audio mp3"},
                      files=files, headers=hdr(student_token))
    assert r.status_code == 200, f"mp3 upload failed: {r.status_code} {r.text}"
    EPHEMERAL_MESSAGE_IDS.append(r.json()["message"]["id"])


def test_unsupported_extension_rejected(student_token):
    files = {"attachment": ("virus.exe", b"MZ\x90\x00" + b"\x00" * 100, "application/octet-stream")}
    r = requests.post(f"{BASE_URL}/api/student-live-chat/messages",
                      data={"message": "TEST_slc_audio bad ext"},
                      files=files, headers=hdr(student_token))
    assert r.status_code == 400


def test_admin_can_download_student_audio(student_token, admin_token):
    """Admin Provinsi can access & play student voice note attachment."""
    data = make_webm()
    files = {"attachment": ("voice.webm", data, "audio/webm")}
    r = requests.post(f"{BASE_URL}/api/student-live-chat/messages",
                      data={"message": "TEST_slc_audio admin download"},
                      files=files, headers=hdr(student_token))
    assert r.status_code == 200, r.text
    body = r.json()["message"]
    EPHEMERAL_MESSAGE_IDS.append(body["id"])
    att = body["attachment"]

    r2 = requests.get(f"{BASE_URL}/api/student-live-chat/attachments/{att['id']}",
                      headers=hdr(admin_token))
    assert r2.status_code == 200
    assert r2.headers.get("content-type", "").startswith("audio/"), r2.headers.get("content-type")
    assert len(r2.content) > 0


def test_zzz_cleanup():
    # Remove any TEST_slc_audio messages
    mdb.student_live_chat_messages.delete_many({"message": {"$regex": "^TEST_slc_audio"}})
    if EPHEMERAL_MESSAGE_IDS:
        mdb.student_live_chat_messages.delete_many({"id": {"$in": EPHEMERAL_MESSAGE_IDS}})
    remaining = mdb.student_live_chat_messages.count_documents({"message": {"$regex": "^TEST_slc_audio"}})
    assert remaining == 0
