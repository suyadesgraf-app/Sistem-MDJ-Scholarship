"""Tests for /api/student-live-chat/* (iter 38).

Coverage:
- Student can list conversations (own), send text, list own messages.
- Regional Admin Wilayah scope: matching region sees convo, non-matching sees 404.
- Admin Provinsi / Super Admin: full visibility + can reply.
- Student ownership: student A cannot request student B's conversation/messages/attachment.
- Attachment: valid PNG/PDF accepted, response never leaks storage_path; invalid extension, magic-byte
  mismatch, oversize, empty (no message + no attachment) are rejected. Download 200 for authorized;
  404 for other student, 403 for non-management non-owner if applicable.
- Auth: unauthenticated GET/POST/download rejected.

Cleanup: removes all ephemeral users/profiles/messages created (does not touch demo/admin accounts).
"""
import io
import os
import uuid
import time
import struct
import zlib
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

SUPER_ADMIN = ("supri@baznasbazisdki.id", "MdjSuper2026!")
ADMIN = ("admin.mdj@baznasbazisdki.id", "AdminMDJ2026!")
STUDENT = ("mahasiswa.mdj@baznasbazisdki.id", "MahasiswaMDJ2026!")

client = MongoClient(MONGO_URL)
mdb = client[DB_NAME]

# Track ephemeral IDs to clean up on teardown
EPHEMERAL_USER_IDS = []
EPHEMERAL_MESSAGE_IDS = []


def login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    data = r.json()
    return data.get("token") or data.get("access_token")


def hdr(token):
    return {"Authorization": f"Bearer {token}"}


def make_png(size_bytes=None):
    """Build minimal valid PNG (magic + IHDR + IEND). Optionally pad IDAT for size."""
    signature = b"\x89PNG\r\n\x1a\n"
    def chunk(ctype, data):
        return struct.pack(">I", len(data)) + ctype + data + struct.pack(">I", zlib.crc32(ctype + data) & 0xffffffff)
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    # tiny valid IDAT with 1x1 pixel
    raw = b"\x00\xff\xff\xff"
    idat_data = zlib.compress(raw)
    png = signature + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat_data) + chunk(b"IEND", b"")
    if size_bytes and len(png) < size_bytes:
        # pad via extra tEXt chunk to reach approx size
        pad_len = size_bytes - len(png) - 12  # chunk overhead
        if pad_len > 0:
            png = signature + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat_data) + chunk(b"tEXt", b"pad\x00" + b"A" * pad_len) + chunk(b"IEND", b"")
    return png


def make_pdf():
    return b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


@pytest.fixture(scope="module")
def admin_token():
    return login(*ADMIN)


@pytest.fixture(scope="module")
def super_token():
    return login(*SUPER_ADMIN)


@pytest.fixture(scope="module")
def demo_student_token():
    return login(*STUDENT)


def _create_user(role, region_kota=None, extra_profile=None):
    """Directly create ephemeral user (+ optional profile) in Mongo, return (user_id, email, password, token)."""
    uid = f"TEST_slc_{uuid.uuid4().hex[:10]}"
    email = f"{uid}@contoh.invalid".lower()
    password = "TestPass123!"
    doc = {
        "user_id": uid,
        "email": email,
        "password_hash": bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
        "name": f"Ephem {role} {uid[-4:]}",
        "role": role,
        "is_active": True,
        "auth_version": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if role == "admin_wilayah" and region_kota:
        doc["region"] = region_kota
    mdb.users.insert_one(doc)
    EPHEMERAL_USER_IDS.append(uid)
    if role == "student" and region_kota:
        prof_data = {"kota": region_kota, "provinsi": region_kota, "nama_lengkap": doc["name"]}
        if extra_profile:
            prof_data.update(extra_profile)
        mdb.profiles.insert_one({"user_id": uid, "data": prof_data, "created_at": doc["created_at"]})
    token = login(email, password)
    return uid, email, password, token


@pytest.fixture(scope="module")
def ephem_env():
    """Create 2 students in different regions + 2 regional admins (matching + non-matching)."""
    student_a_uid, _, _, student_a_tok = _create_user("student", region_kota="Jakarta Pusat")
    student_b_uid, _, _, student_b_tok = _create_user("student", region_kota="Jakarta Timur")
    admin_pusat_uid, _, _, admin_pusat_tok = _create_user("admin_wilayah", region_kota="Jakarta Pusat")
    admin_timur_uid, _, _, admin_timur_tok = _create_user("admin_wilayah", region_kota="Jakarta Timur")
    yield {
        "student_a": {"uid": student_a_uid, "token": student_a_tok, "region": "Jakarta Pusat"},
        "student_b": {"uid": student_b_uid, "token": student_b_tok, "region": "Jakarta Timur"},
        "admin_pusat": {"uid": admin_pusat_uid, "token": admin_pusat_tok, "region": "Jakarta Pusat"},
        "admin_timur": {"uid": admin_timur_uid, "token": admin_timur_tok, "region": "Jakarta Timur"},
    }


# ---------------- AUTH / RBAC ----------------

def test_unauth_conversations():
    r = requests.get(f"{BASE_URL}/api/student-live-chat/conversations")
    assert r.status_code in (401, 403), r.text


def test_unauth_messages_list():
    r = requests.get(f"{BASE_URL}/api/student-live-chat/messages")
    assert r.status_code in (401, 403)


def test_unauth_post_message():
    r = requests.post(f"{BASE_URL}/api/student-live-chat/messages", data={"message": "hi"})
    assert r.status_code in (401, 403)


# ---------------- STUDENT FLOW ----------------

def test_student_self_conversation_send_and_list(ephem_env):
    s = ephem_env["student_a"]
    # Post text-only message as student
    r = requests.post(f"{BASE_URL}/api/student-live-chat/messages",
                      data={"message": "TEST_slc hello from student"},
                      headers=hdr(s["token"]))
    assert r.status_code == 200, r.text
    body = r.json()["message"]
    assert body["message"] == "TEST_slc hello from student"
    assert body["student_id"] == s["uid"]
    assert body["sender_id"] == s["uid"]
    assert body["sender_role"] == "student"
    assert "attachment" not in body or body["attachment"] is None
    assert "_id" not in body
    EPHEMERAL_MESSAGE_IDS.append(body["id"])

    # List own messages
    r = requests.get(f"{BASE_URL}/api/student-live-chat/messages", headers=hdr(s["token"]))
    assert r.status_code == 200
    j = r.json()
    assert j["student"]["user_id"] == s["uid"]
    assert any(m["id"] == body["id"] for m in j["messages"])


def test_student_cannot_query_other_student(ephem_env):
    a = ephem_env["student_a"]
    b = ephem_env["student_b"]
    r = requests.get(f"{BASE_URL}/api/student-live-chat/messages",
                     params={"student_id": b["uid"]}, headers=hdr(a["token"]))
    assert r.status_code == 404, r.text


def test_student_post_empty_no_attachment_rejected(ephem_env):
    s = ephem_env["student_a"]
    r = requests.post(f"{BASE_URL}/api/student-live-chat/messages",
                      data={"message": "   "}, headers=hdr(s["token"]))
    assert r.status_code == 400
    assert "kosong" in r.text.lower() or "tulis" in r.text.lower()


def test_student_cannot_list_conversations(ephem_env):
    r = requests.get(f"{BASE_URL}/api/student-live-chat/conversations",
                     headers=hdr(ephem_env["student_a"]["token"]))
    assert r.status_code == 403


# ---------------- ADMIN PROVINSI / SUPER ADMIN ----------------

def test_admin_provinsi_sees_conversation_and_can_reply(admin_token, ephem_env):
    a = ephem_env["student_a"]
    # Ensure student has at least one message (previous test created one); if not, create one
    r = requests.get(f"{BASE_URL}/api/student-live-chat/conversations", headers=hdr(admin_token))
    assert r.status_code == 200
    conv = r.json()["conversations"]
    assert any(c["student_id"] == a["uid"] for c in conv), "Admin Provinsi should see ephem student A"

    # Reply as admin
    r = requests.post(f"{BASE_URL}/api/student-live-chat/messages",
                      data={"message": "TEST_slc reply from admin provinsi", "student_id": a["uid"]},
                      headers=hdr(admin_token))
    assert r.status_code == 200, r.text
    reply = r.json()["message"]
    EPHEMERAL_MESSAGE_IDS.append(reply["id"])
    assert reply["student_id"] == a["uid"]
    assert reply["sender_role"] == "admin"

    # Student sees admin's reply
    r = requests.get(f"{BASE_URL}/api/student-live-chat/messages", headers=hdr(a["token"]))
    assert r.status_code == 200
    ids = [m["id"] for m in r.json()["messages"]]
    assert reply["id"] in ids


def test_super_admin_can_reply(super_token, ephem_env):
    a = ephem_env["student_a"]
    r = requests.post(f"{BASE_URL}/api/student-live-chat/messages",
                      data={"message": "TEST_slc reply from super", "student_id": a["uid"]},
                      headers=hdr(super_token))
    assert r.status_code == 200
    EPHEMERAL_MESSAGE_IDS.append(r.json()["message"]["id"])


# ---------------- REGIONAL ADMIN WILAYAH SCOPE ----------------

def test_admin_wilayah_matching_can_access(ephem_env):
    a = ephem_env["student_a"]
    ap = ephem_env["admin_pusat"]
    r = requests.get(f"{BASE_URL}/api/student-live-chat/conversations", headers=hdr(ap["token"]))
    assert r.status_code == 200
    conv = r.json()["conversations"]
    assert any(c["student_id"] == a["uid"] for c in conv), "Matching regional admin should see student"
    # student_b (Jakarta Timur) must NOT appear
    assert not any(c["student_id"] == ephem_env["student_b"]["uid"] for c in conv)

    r = requests.get(f"{BASE_URL}/api/student-live-chat/messages",
                     params={"student_id": a["uid"]}, headers=hdr(ap["token"]))
    assert r.status_code == 200

    r = requests.post(f"{BASE_URL}/api/student-live-chat/messages",
                      data={"message": "TEST_slc reply admin wilayah pusat", "student_id": a["uid"]},
                      headers=hdr(ap["token"]))
    assert r.status_code == 200
    EPHEMERAL_MESSAGE_IDS.append(r.json()["message"]["id"])


def test_admin_wilayah_nonmatching_gets_404(ephem_env):
    a = ephem_env["student_a"]  # Jakarta Pusat
    at = ephem_env["admin_timur"]  # Jakarta Timur admin

    # Listing conversations returns 200 but student A NOT included
    r = requests.get(f"{BASE_URL}/api/student-live-chat/conversations", headers=hdr(at["token"]))
    assert r.status_code == 200
    assert not any(c["student_id"] == a["uid"] for c in r.json()["conversations"])

    # Direct message list for A -> 404
    r = requests.get(f"{BASE_URL}/api/student-live-chat/messages",
                     params={"student_id": a["uid"]}, headers=hdr(at["token"]))
    assert r.status_code == 404

    # Reply attempt -> 404
    r = requests.post(f"{BASE_URL}/api/student-live-chat/messages",
                      data={"message": "should be blocked", "student_id": a["uid"]},
                      headers=hdr(at["token"]))
    assert r.status_code == 404


# ---------------- ATTACHMENTS ----------------

def test_attachment_valid_png(ephem_env):
    s = ephem_env["student_a"]
    png = make_png()
    files = {"attachment": ("photo.png", png, "image/png")}
    r = requests.post(f"{BASE_URL}/api/student-live-chat/messages",
                      data={"message": "TEST_slc with png"},
                      files=files, headers=hdr(s["token"]))
    assert r.status_code == 200, r.text
    body = r.json()["message"]
    EPHEMERAL_MESSAGE_IDS.append(body["id"])
    assert body["attachment"] is not None
    att = body["attachment"]
    assert "storage_path" not in att, f"storage_path leaked: {att}"
    assert att["original_filename"] == "photo.png"
    assert att["size"] > 0
    assert "id" in att
    # Owner student can download
    r2 = requests.get(f"{BASE_URL}/api/student-live-chat/attachments/{att['id']}", headers=hdr(s["token"]))
    assert r2.status_code == 200
    assert len(r2.content) > 0


def test_attachment_valid_pdf(ephem_env, admin_token):
    s = ephem_env["student_a"]
    pdf = make_pdf()
    files = {"attachment": ("doc.pdf", pdf, "application/pdf")}
    r = requests.post(f"{BASE_URL}/api/student-live-chat/messages",
                      data={"message": "TEST_slc pdf"}, files=files, headers=hdr(s["token"]))
    assert r.status_code == 200, r.text
    att = r.json()["message"]["attachment"]
    EPHEMERAL_MESSAGE_IDS.append(r.json()["message"]["id"])
    # Admin Provinsi can also download
    r2 = requests.get(f"{BASE_URL}/api/student-live-chat/attachments/{att['id']}", headers=hdr(admin_token))
    assert r2.status_code == 200


def test_attachment_invalid_extension(ephem_env):
    s = ephem_env["student_a"]
    files = {"attachment": ("evil.exe", b"MZ\x90\x00", "application/octet-stream")}
    r = requests.post(f"{BASE_URL}/api/student-live-chat/messages",
                      data={"message": "TEST_slc bad ext"}, files=files, headers=hdr(s["token"]))
    assert r.status_code == 400


def test_attachment_magic_byte_mismatch(ephem_env):
    s = ephem_env["student_a"]
    # .png extension but content is not PNG
    files = {"attachment": ("fake.png", b"NOTAPNG!!" * 20, "image/png")}
    r = requests.post(f"{BASE_URL}/api/student-live-chat/messages",
                      data={"message": "TEST_slc magic mismatch"}, files=files, headers=hdr(s["token"]))
    assert r.status_code == 400


def test_attachment_oversize_rejected(ephem_env):
    s = ephem_env["student_a"]
    # 11 MB PDF (starts with %PDF)
    big = b"%PDF-1.4\n" + b"A" * (11 * 1024 * 1024)
    files = {"attachment": ("big.pdf", big, "application/pdf")}
    r = requests.post(f"{BASE_URL}/api/student-live-chat/messages",
                      data={"message": "TEST_slc big"}, files=files, headers=hdr(s["token"]))
    assert r.status_code in (400, 413)


def test_attachment_download_other_student_forbidden(ephem_env):
    """Student B cannot download student A's attachment."""
    a = ephem_env["student_a"]
    b = ephem_env["student_b"]
    png = make_png()
    files = {"attachment": ("photo.png", png, "image/png")}
    r = requests.post(f"{BASE_URL}/api/student-live-chat/messages",
                      data={"message": "TEST_slc private"}, files=files, headers=hdr(a["token"]))
    assert r.status_code == 200
    att = r.json()["message"]["attachment"]
    EPHEMERAL_MESSAGE_IDS.append(r.json()["message"]["id"])

    r2 = requests.get(f"{BASE_URL}/api/student-live-chat/attachments/{att['id']}", headers=hdr(b["token"]))
    assert r2.status_code == 404


def test_attachment_download_nonmatching_regional_admin_forbidden(ephem_env):
    a = ephem_env["student_a"]
    at = ephem_env["admin_timur"]
    png = make_png()
    files = {"attachment": ("photo.png", png, "image/png")}
    r = requests.post(f"{BASE_URL}/api/student-live-chat/messages",
                      data={"message": "TEST_slc region private"}, files=files, headers=hdr(a["token"]))
    att = r.json()["message"]["attachment"]
    EPHEMERAL_MESSAGE_IDS.append(r.json()["message"]["id"])

    r2 = requests.get(f"{BASE_URL}/api/student-live-chat/attachments/{att['id']}", headers=hdr(at["token"]))
    assert r2.status_code == 404


def test_attachment_download_unauth():
    r = requests.get(f"{BASE_URL}/api/student-live-chat/attachments/{uuid.uuid4()}")
    assert r.status_code == 401


# ---------------- CLEANUP ----------------

def test_zzz_cleanup_ephemeral():
    """Explicit cleanup: remove all ephemeral users, profiles, and TEST_ messages."""
    # Delete any messages referencing ephemeral student ids (regardless of tracked list)
    if EPHEMERAL_USER_IDS:
        mdb.student_live_chat_messages.delete_many({"student_id": {"$in": EPHEMERAL_USER_IDS}})
        mdb.student_live_chat_messages.delete_many({"sender_id": {"$in": EPHEMERAL_USER_IDS}})
    # Also delete any test messages containing TEST_slc marker (belt & suspenders)
    mdb.student_live_chat_messages.delete_many({"message": {"$regex": "^TEST_slc"}})
    if EPHEMERAL_MESSAGE_IDS:
        mdb.student_live_chat_messages.delete_many({"id": {"$in": EPHEMERAL_MESSAGE_IDS}})

    # Delete ephemeral users and profiles
    if EPHEMERAL_USER_IDS:
        mdb.users.delete_many({"user_id": {"$in": EPHEMERAL_USER_IDS}})
        mdb.profiles.delete_many({"user_id": {"$in": EPHEMERAL_USER_IDS}})

    # Assertions
    remaining_users = mdb.users.count_documents({"user_id": {"$regex": "^TEST_slc_"}})
    remaining_msgs = mdb.student_live_chat_messages.count_documents({"message": {"$regex": "^TEST_slc"}})
    assert remaining_users == 0
    assert remaining_msgs == 0
