"""Tests for iteration_32: profile namaLengkap → users.name sync.

Covers:
1. PUT /api/profile with non-empty namaLengkap updates users.name and response.user is clean (no _id)
2. GET /api/auth/me returns updated name
3. Fresh /api/auth/login returns updated name
4. PUT /api/profile with empty namaLengkap does NOT overwrite users.name and response.user is null
5. cpm_id on registration is preserved across profile update
"""
import os
import uuid
import time
import asyncio
import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

TEST_EMAIL = f"test_profile_sync_{uuid.uuid4().hex[:8]}@example.com"
TEST_PASSWORD = "TestPass123!"
ORIG_NAME = "TEST Nama Awal"
NEW_NAME = "TEST Nama Baru Sinkron"
SEED_CPM_ID = f"CPMTEST{uuid.uuid4().hex[:8].upper()}"


@pytest.fixture(scope="module")
def registered_user():
    r = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"name": ORIG_NAME, "email": TEST_EMAIL, "password": TEST_PASSWORD},
        timeout=30,
    )
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    body = r.json()
    assert "user" in body and "token" in body
    assert "_id" not in body["user"]
    assert body["user"]["name"] == ORIG_NAME
    yield {"token": body["token"], "user_id": body["user"]["user_id"]}

    # Cleanup: remove from DB directly
    async def cleanup():
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        uid = body["user"]["user_id"]
        await db.users.delete_many({"user_id": uid})
        await db.profiles.delete_many({"user_id": uid})
        await db.registrations.delete_many({"user_id": uid})
        await db.user_sessions.delete_many({"user_id": uid})
        await db.documents.delete_many({"user_id": uid})
        await db.notifications.delete_many({"user_id": uid})
        client.close()
    asyncio.run(cleanup())


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def test_put_profile_with_name_updates_user_and_response_clean(registered_user):
    token = registered_user["token"]
    payload = {"data": {"namaLengkap": NEW_NAME, "email": TEST_EMAIL}}
    r = requests.put(f"{BASE_URL}/api/profile", headers=_auth_headers(token), json=payload, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["user"] is not None, "user must be returned when namaLengkap is non-empty"
    assert "_id" not in body["user"], "response user must not include Mongo _id"
    assert body["user"]["name"] == NEW_NAME
    assert body["user"]["user_id"] == registered_user["user_id"]
    assert "password_hash" not in body["user"]


def test_get_auth_me_reflects_updated_name(registered_user):
    r = requests.get(f"{BASE_URL}/api/auth/me", headers=_auth_headers(registered_user["token"]), timeout=30)
    assert r.status_code == 200
    me = r.json()
    assert me["name"] == NEW_NAME
    assert "_id" not in me


def test_fresh_login_shows_new_name(registered_user):
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["user"]["name"] == NEW_NAME
    assert "_id" not in body["user"]


def test_put_profile_empty_name_does_not_overwrite_user(registered_user):
    token = registered_user["token"]
    payload = {"data": {"namaLengkap": "   ", "email": TEST_EMAIL, "alamat": "Jl Test"}}
    r = requests.put(f"{BASE_URL}/api/profile", headers=_auth_headers(token), json=payload, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("user") is None, "response.user must be null when namaLengkap is empty"

    # GET /auth/me still returns previous good name
    r2 = requests.get(f"{BASE_URL}/api/auth/me", headers=_auth_headers(token), timeout=30)
    assert r2.status_code == 200
    assert r2.json()["name"] == NEW_NAME, "users.name must NOT be blanked out"


def test_cpm_id_preserved_after_profile_update(registered_user):
    token = registered_user["token"]
    uid = registered_user["user_id"]

    # Seed registration with cpm_id directly in Mongo
    async def seed_and_read():
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        await db.registrations.update_one(
            {"user_id": uid},
            {"$set": {
                "user_id": uid,
                "cpm_id": SEED_CPM_ID,
                "status": "draft",
                "created_at": "2026-01-01T00:00:00+00:00",
            }},
            upsert=True,
        )
        seeded = await db.registrations.find_one({"user_id": uid})
        client.close()
        return seeded

    async def read_reg():
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        reg = await db.registrations.find_one({"user_id": uid})
        client.close()
        return reg

    seeded = asyncio.run(seed_and_read())
    assert seeded["cpm_id"] == SEED_CPM_ID

    # Update profile with another new display name
    another_name = "TEST Nama Sekali Lagi"
    r = requests.put(
        f"{BASE_URL}/api/profile",
        headers=_auth_headers(token),
        json={"data": {"namaLengkap": another_name, "email": TEST_EMAIL}},
        timeout=30,
    )
    assert r.status_code == 200
    assert r.json()["user"]["name"] == another_name

    # cpm_id must be untouched
    after = asyncio.run(read_reg())
    assert after["cpm_id"] == SEED_CPM_ID
