"""Tests for /api/auth/google/session and Google register flow (iteration 31)."""
import os
import uuid
from unittest.mock import patch, MagicMock

import pytest
import requests
from pathlib import Path


def _load_frontend_env():
    env_path = Path("/app/frontend/.env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip()
    return ""


BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or _load_frontend_env()).rstrip("/")
API = f"{BASE_URL}/api"


# ---- 1. Invalid session_id must return 401 without creating user ----
class TestGoogleSessionInvalid:
    def test_invalid_session_returns_401(self):
        r = requests.post(
            f"{API}/auth/google/session",
            json={"session_id": f"invalid_{uuid.uuid4().hex}"},
            timeout=30,
        )
        assert r.status_code == 401, f"expected 401 got {r.status_code}: {r.text}"

    def test_missing_session_id_rejected(self):
        r = requests.post(f"{API}/auth/google/session", json={}, timeout=30)
        assert r.status_code in (400, 422)


# ---- 2. Direct method-level test with mocked emergent provider ----
class TestGoogleSessionMocked:
    """Import the app and drive google_session with mocked HTTP + mocked DB."""

    def test_new_google_email_creates_student_user(self):
        import sys
        sys.path.insert(0, "/app/backend")
        import server  # noqa: E402
        import asyncio

        test_email_new = f"test_gauth_{uuid.uuid4().hex[:8]}@example.com"
        session_tok_new = f"tok_{uuid.uuid4().hex}"
        mocked_new = MagicMock()
        mocked_new.status_code = 200
        mocked_new.json.return_value = {
            "email": test_email_new, "name": "TEST Google User",
            "picture": "https://example.com/p.png", "session_token": session_tok_new,
        }
        response_new = MagicMock()

        test_email_dup = f"test_gdup_{uuid.uuid4().hex[:8]}@example.com"
        session_tok_dup = f"tok_{uuid.uuid4().hex}"
        mocked_dup = MagicMock()
        mocked_dup.status_code = 200
        mocked_dup.json.return_value = {
            "email": test_email_dup, "name": "google name",
            "picture": None, "session_token": session_tok_dup,
        }
        response_dup = MagicMock()

        async def scenario():
            results = {}
            try:
                # --- new-user scenario ---
                with patch.object(server.requests, "get", return_value=mocked_new):
                    results["new"] = await server.google_session(
                        server.GoogleSessionInput(session_id="anything"), response_new,
                    )
                results["new_sess"] = await server.db.user_sessions.find_one(
                    {"session_token": session_tok_new}, {"_id": 0}
                )
                results["new_user"] = await server.db.users.find_one(
                    {"email": test_email_new}, {"_id": 0}
                )

                # --- pre-existing email scenario ---
                await server.db.users.insert_one({
                    "user_id": f"user_seed_{uuid.uuid4().hex[:8]}",
                    "email": test_email_dup, "password_hash": "x", "name": "Preexisting",
                    "role": "student", "auth_provider": "password",
                    "is_active": True, "auth_version": 0,
                })
                with patch.object(server.requests, "get", return_value=mocked_dup):
                    results["dup"] = await server.google_session(
                        server.GoogleSessionInput(session_id="x"), response_dup,
                    )
                results["dup_count"] = await server.db.users.count_documents(
                    {"email": test_email_dup}
                )
                return results
            finally:
                await server.db.user_sessions.delete_many(
                    {"session_token": {"$in": [session_tok_new, session_tok_dup]}}
                )
                await server.db.users.delete_many(
                    {"email": {"$in": [test_email_new, test_email_dup]}}
                )

        r = asyncio.run(scenario())

        # New user assertions
        assert r["new"]["user"]["email"] == test_email_new
        assert r["new"]["user"]["role"] == "student"
        assert r["new"]["user"].get("auth_provider") == "google"
        assert r["new"]["token"] == session_tok_new
        response_new.set_cookie.assert_called_once()
        kwargs = response_new.set_cookie.call_args.kwargs
        assert kwargs["max_age"] == 604800
        assert kwargs["httponly"] is True
        assert r["new_sess"] is not None
        assert r["new_user"] and r["new_user"]["role"] == "student"
        assert r["new_user"]["auth_provider"] == "google"

        # Dedup assertions
        assert r["dup"]["user"]["email"] == test_email_dup
        assert r["dup_count"] == 1, f"user duplicated (count={r['dup_count']})"

    def test_provider_failure_returns_401(self):
        import sys
        sys.path.insert(0, "/app/backend")
        import server
        import asyncio
        from fastapi import HTTPException

        mocked_resp = MagicMock()
        mocked_resp.status_code = 401
        response = MagicMock()

        async def run():
            with patch.object(server.requests, "get", return_value=mocked_resp):
                await server.google_session(
                    server.GoogleSessionInput(session_id="bad"), response
                )

        with pytest.raises(HTTPException) as ei:
            asyncio.run(run())
        assert ei.value.status_code == 401
        response.set_cookie.assert_not_called()


# ---- 3. /login flow smoke: email/password still works ----
class TestLoginNoRegression:
    def test_admin_login_works(self):
        r = requests.post(
            f"{API}/auth/login",
            json={"email": "supri@baznasbazisdki.id", "password": "MdjSuper2026!"},
            timeout=30,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["user"]["role"] == "super_admin"
        assert body["token"]
