import os
import uuid

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient


load_dotenv("/app/backend/.env")

BACKEND_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = BACKEND_URL if BACKEND_URL.endswith("/api") else f"{BACKEND_URL}/api"
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
TEST_EMAIL = f"phone.sync.{uuid.uuid4().hex[:10]}@example.com"
TEST_PASSWORD = "PhoneSync2026!"
TEST_PHONE = "0812-3456-7890"
NORMALIZED_TEST_PHONE = "081234567890"


@pytest.fixture(scope="module")
def mongo_db():
    client = MongoClient(MONGO_URL)
    database = client[DB_NAME]
    yield database
    user = database.users.find_one({"email": TEST_EMAIL}, {"_id": 0, "user_id": 1})
    if user:
        user_id = user["user_id"]
        database.profiles.delete_many({"user_id": user_id})
        database.registrations.delete_many({"user_id": user_id})
        database.users.delete_many({"user_id": user_id})
    client.close()


def test_phone_from_registration_is_returned_in_authenticated_account(mongo_db):
    response = requests.post(
        f"{API}/auth/register",
        json={
            "name": "TEST Phone Sync",
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "phone": TEST_PHONE,
        },
        timeout=30,
    )
    assert response.status_code == 200, response.text
    registered_user = response.json()["user"]
    assert registered_user["phone"] == NORMALIZED_TEST_PHONE
    assert registered_user["phone_verified"] is False

    token = response.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    account_response = requests.get(f"{API}/auth/me", headers=headers, timeout=30)
    assert account_response.status_code == 200, account_response.text
    assert account_response.json()["phone"] == NORMALIZED_TEST_PHONE

    profile_response = requests.get(f"{API}/profile", headers=headers, timeout=30)
    assert profile_response.status_code == 200, profile_response.text
    assert profile_response.json()["data"]["noTelp"] == NORMALIZED_TEST_PHONE


def test_registration_rejects_invalid_phone_format():
    response = requests.post(
        f"{API}/auth/register",
        json={
            "name": "TEST Invalid Phone",
            "email": f"invalid.phone.{uuid.uuid4().hex[:10]}@example.com",
            "password": TEST_PASSWORD,
            "phone": "123",
        },
        timeout=30,
    )
    assert response.status_code == 422, response.text