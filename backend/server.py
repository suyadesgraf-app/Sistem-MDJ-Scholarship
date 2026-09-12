from dotenv import load_dotenv
from pathlib import Path
import os

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, UploadFile, File, Form, Query, Header
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response as StarletteResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ReturnDocument
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import logging
import uuid
import jwt
import bcrypt
import requests
import json
import re
import tempfile
import io
from PIL import Image as PILImage
from openpyxl import load_workbook
import secrets
import asyncio
import ipaddress
import httpx
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse
from emergentintegrations.llm.chat import (
    FileContentWithMimeType,
    LlmChat,
    StreamDone,
    TextDelta,
    UserMessage,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

JWT_SECRET = os.environ['JWT_SECRET']
JWT_ALGORITHM = "HS256"
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'supri@baznasbazisdki.id')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'MdjSuper2026!')
DEMO_ADMIN_EMAIL = os.environ['DEMO_ADMIN_EMAIL']
DEMO_ADMIN_PASSWORD = os.environ['DEMO_ADMIN_PASSWORD']
DEMO_STUDENT_EMAIL = os.environ['DEMO_STUDENT_EMAIL']
DEMO_STUDENT_PASSWORD = os.environ['DEMO_STUDENT_PASSWORD']

STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
APP_NAME = "mdj-scholarship"

# Email (Emergent-managed Resend)
EMAIL_BASE_URL = "https://integrations.emergentagent.com"
EMAIL_KEY = os.environ.get("EMERGENT_EMAIL_KEY")
EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "MDJ Scholarship")
EMAIL_REPLY_TO = os.environ.get("EMAIL_REPLY_TO")
APP_BASE_URL = (os.environ.get("APP_BASE_URL") or "").rstrip("/")

# Twilio SMS OTP (optional — phone verification disabled until configured)
TWILIO_ACCOUNT_SID = (os.environ.get("TWILIO_ACCOUNT_SID") or "").strip()
TWILIO_AUTH_TOKEN = (os.environ.get("TWILIO_AUTH_TOKEN") or "").strip()
TWILIO_VERIFY_SERVICE_SID = (os.environ.get("TWILIO_VERIFY_SERVICE_SID") or "").strip()
TWILIO_ENABLED = bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_VERIFY_SERVICE_SID)

EMERGENT_AUTH_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"

MIME_TYPES = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "gif": "image/gif", "webp": "image/webp", "pdf": "application/pdf",
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()
api_router = APIRouter(prefix="/api")

# ---------------------------------------------------------------------------
# Object storage
# ---------------------------------------------------------------------------
storage_key = None


def init_storage(force: bool = False):
    global storage_key
    if storage_key and not force:
        return storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
    resp.raise_for_status()
    storage_key = resp.json()["storage_key"]
    return storage_key


def compress_image(data: bytes, ext: str, content_type: str, max_w: int = 2400, quality: int = 86):
    """Downscale/re-encode raster images to JPEG; non-images (PDF) pass through."""
    if ext not in ("jpg", "jpeg", "png", "webp", "gif", "bmp", "tiff"):
        return data, ext, content_type
    try:
        img = PILImage.open(io.BytesIO(data))
        img = img.convert("RGB")
        if img.width > max_w:
            img = img.resize((max_w, int(img.height * max_w / img.width)), PILImage.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True, progressive=True)
        out = buf.getvalue()
        if len(out) < len(data):
            return out, "jpg", "image/jpeg"
        return data, ext, content_type
    except Exception as e:
        logger.warning(f"Image compression skipped: {e}")
        return data, ext, content_type


def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data, timeout=120,
    )
    if resp.status_code == 404:
        key = init_storage(force=True)
        resp = requests.put(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key, "Content-Type": content_type},
            data=data, timeout=120,
        )
    resp.raise_for_status()
    return resp.json()


def get_object(path: str):
    key = init_storage()
    resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    if resp.status_code == 404:
        key = init_storage(force=True)
        resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


# ---------------------------------------------------------------------------
# Email (Emergent-managed Resend) — guardrail gate + async send
# ---------------------------------------------------------------------------
_SHORTENERS = ("bit.ly", "tinyurl.com", "t.co", "is.gd", "cutt.ly", "goo.gl", "rebrand.ly")
_CRED_ASK = ("reply with your password", "reply with the code", "send your password", "cvv",
             "send us your password", "enter your password below", "confirm your card number",
             "your full card number", "seed phrase", "recovery phrase", "verify your card",
             "social security number", "confirm your bank details")
_HOSTISH = re.compile(r"\b(?:https?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})", re.I)


def _host_ok(host: str) -> bool:
    if not host or "xn--" in host:
        return False
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        pass
    return not any(host == s or host.endswith("." + s) for s in _SHORTENERS)


def _same_site(shown: str, real: str) -> bool:
    return shown == real or real.endswith("." + shown) or shown.endswith("." + real)


class _EmailScan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.urls, self.anchors = set(), [], []
        self._href, self._text = None, []

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag.lower())
        self.urls += [v for k, v in attrs if k.lower() in ("href", "src") and v]
        if tag.lower() == "a":
            self._href = dict((k.lower(), v) for k, v in attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            self.anchors.append((self._href, "".join(self._text)))
            self._href, self._text = None, []


def _assert_safe_email(subject: str, html: str) -> None:
    scan = _EmailScan()
    scan.feed(html)
    if scan.tags & {"form", "input", "textarea", "select"}:
        raise ValueError("No forms or input fields in email (G2)")
    body = f"{subject}\n{html}".lower()
    for p in _CRED_ASK:
        if p in body:
            raise ValueError(f"Email asks the recipient for credentials: {p!r} (G2)")
    for url in scan.urls:
        low = url.strip().lower()
        if low.startswith(("mailto:", "tel:", "cid:", "#")):
            continue
        if not low.startswith("https://"):
            raise ValueError(f"Email links/assets must be absolute https: {url!r} (G3)")
        host = urlparse(low).hostname or ""
        if not _host_ok(host) or urlparse(low).username is not None:
            raise ValueError(f"Shortened, numeric-host or credential-bearing URL: {url!r} (G3)")
    for href, text in scan.anchors:
        real = urlparse(href.strip().lower()).hostname or ""
        if not real:
            continue
        for m in _HOSTISH.finditer(text):
            if not _same_site(m.group(1).lower(), real):
                raise ValueError(f"Anchor text {m.group(1)!r} != real link host {real!r} (G3)")


async def send_email(*, to: str, subject: str, html: str) -> Optional[str]:
    _assert_safe_email(subject, html)
    payload = {"to": [to], "subject": subject, "html": html, "from_name": EMAIL_FROM_NAME}
    if EMAIL_REPLY_TO:
        payload["contact_email"] = EMAIL_REPLY_TO
    try:
        async with httpx.AsyncClient(timeout=30) as http_client:
            resp = await http_client.post(
                f"{EMAIL_BASE_URL}/api/v1/email/send",
                headers={"X-Email-Key": EMAIL_KEY},
                json=payload,
            )
        resp.raise_for_status()
        return resp.json().get("id")
    except httpx.HTTPStatusError as e:
        logger.error(f"Email send failed: {e.response.status_code} {e.response.text}")
        raise HTTPException(status_code=502, detail="Gagal mengirim email verifikasi")
    except Exception as e:
        logger.error(f"Email send error: {str(e)}")
        raise HTTPException(status_code=500, detail="Gagal mengirim email verifikasi")


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(user_id: str, email: str) -> str:
    payload = {"sub": user_id, "email": email, "exp": datetime.now(timezone.utc) + timedelta(days=7), "type": "access"}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def set_auth_cookie(response: Response, token: str):
    response.set_cookie(key="access_token", value=token, httponly=True, secure=True,
                        samesite="none", max_age=604800, path="/")


async def resolve_user_from_token(token: str) -> Optional[dict]:
    # Try JWT first
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") == "access":
            return await db.users.find_one({"user_id": payload["sub"]}, {"_id": 0})
    except jwt.InvalidTokenError:
        pass
    # Fallback: treat as google session token
    session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if session:
        expires_at = session["expires_at"]
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at > datetime.now(timezone.utc):
            return await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    return None


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token") or request.cookies.get("session_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = await resolve_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account is deactivated")
    user.pop("password_hash", None)
    return user


def require_roles(*roles):
    async def checker(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Access denied")
        return user
    return checker


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class RegisterInput(BaseModel):
    name: str
    email: EmailStr
    password: str
    nik: Optional[str] = None
    phone: Optional[str] = None


class LoginInput(BaseModel):
    email: str
    password: str


class GoogleSessionInput(BaseModel):
    session_id: str


class ProfileInput(BaseModel):
    data: Dict[str, Any]


class ChangePasswordInput(BaseModel):
    current_password: str
    new_password: str


class EmailChangeInput(BaseModel):
    new_email: EmailStr
    password: str


class EmailVerifyInput(BaseModel):
    token: str


class PhoneOtpSendInput(BaseModel):
    phone: str


class PhoneOtpVerifyInput(BaseModel):
    phone: str
    code: str


class RegistrationInput(BaseModel):
    category: str
    action: str = "draft"  # draft | submit


class StatusUpdateInput(BaseModel):
    status: str
    note: Optional[str] = None


class CreateAdminInput(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "admin"


class UserToggleInput(BaseModel):
    is_active: bool


class SiteContentInput(BaseModel):
    content: Dict[str, Any]


class CampusInput(BaseModel):
    name: str
    code: Optional[str] = None


REG_STATUSES = ["draft", "submitted", "verifikasi", "lolos_administrasi", "wawancara",
                "verifikasi_faktual", "lolos", "ditolak"]


def clean_user(u: dict) -> dict:
    u = dict(u)
    u.pop("password_hash", None)
    u.pop("_id", None)
    return u


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------
@api_router.post("/auth/register")
async def register(payload: RegisterInput, response: Response):
    email = payload.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email sudah terdaftar")
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    doc = {
        "user_id": user_id, "email": email, "password_hash": hash_password(payload.password),
        "name": payload.name, "role": "student", "auth_provider": "password",
        "nik": payload.nik, "phone": payload.phone, "picture": None,
        "is_active": True, "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(doc)
    token = create_access_token(user_id, email)
    set_auth_cookie(response, token)
    return {"user": clean_user(doc), "token": token}


@api_router.post("/auth/login")
async def login(payload: LoginInput, response: Response):
    identifier = payload.email.lower().strip()
    user = await db.users.find_one(
        {"$or": [{"email": identifier}, {"nik": identifier}]},
    )
    if not user or not user.get("password_hash") or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email atau kata sandi salah")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Akun dinonaktifkan")
    token = create_access_token(user["user_id"], user["email"])
    set_auth_cookie(response, token)
    return {"user": clean_user(user), "token": token}


@api_router.post("/auth/google/session")
async def google_session(payload: GoogleSessionInput, response: Response):
    resp = requests.get(EMERGENT_AUTH_URL, headers={"X-Session-ID": payload.session_id}, timeout=30)
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Google authentication gagal")
    data = resp.json()
    email = data["email"].lower().strip()
    user = await db.users.find_one({"email": email})
    if not user:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        user = {
            "user_id": user_id, "email": email, "password_hash": None, "name": data.get("name", email),
            "role": "student", "auth_provider": "google", "nik": None, "phone": None,
            "picture": data.get("picture"), "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.users.insert_one(user)
    session_token = data["session_token"]
    await db.user_sessions.insert_one({
        "user_id": user["user_id"], "session_token": session_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    response.set_cookie(key="session_token", value=session_token, httponly=True, secure=True,
                        samesite="none", max_age=604800, path="/")
    return {"user": clean_user(user), "token": session_token}


@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if token:
        await db.user_sessions.delete_many({"session_token": token})
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("session_token", path="/")
    return {"message": "Logged out"}


@api_router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return clean_user(user)


# ---------------------------------------------------------------------------
# Account settings — password, email change (verified link), phone OTP
# ---------------------------------------------------------------------------
@api_router.post("/auth/change-password")
async def change_password(payload: ChangePasswordInput, user: dict = Depends(get_current_user)):
    doc = await db.users.find_one({"user_id": user["user_id"]})
    if not doc or not doc.get("password_hash"):
        raise HTTPException(status_code=400, detail="Akun ini masuk lewat Google dan tidak memiliki kata sandi.")
    if not verify_password(payload.current_password, doc["password_hash"]):
        raise HTTPException(status_code=400, detail="Kata sandi saat ini salah.")
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="Kata sandi baru minimal 8 karakter.")
    if verify_password(payload.new_password, doc["password_hash"]):
        raise HTTPException(status_code=400, detail="Kata sandi baru tidak boleh sama dengan yang lama.")
    await db.users.update_one({"user_id": user["user_id"]},
                              {"$set": {"password_hash": hash_password(payload.new_password)}})
    return {"message": "Kata sandi berhasil diperbarui."}


@api_router.post("/auth/email/change-request")
async def request_email_change(payload: EmailChangeInput, user: dict = Depends(get_current_user)):
    doc = await db.users.find_one({"user_id": user["user_id"]})
    if not doc or not doc.get("password_hash"):
        raise HTTPException(status_code=400, detail="Akun Google tidak dapat mengubah email di sini.")
    if not verify_password(payload.password, doc["password_hash"]):
        raise HTTPException(status_code=400, detail="Kata sandi salah.")
    new_email = payload.new_email.lower().strip()
    if new_email == doc["email"]:
        raise HTTPException(status_code=400, detail="Email baru sama dengan email saat ini.")
    if await db.users.find_one({"email": new_email}):
        raise HTTPException(status_code=400, detail="Email tersebut sudah digunakan akun lain.")
    token = secrets.token_urlsafe(32)
    await db.email_change_tokens.update_many({"user_id": user["user_id"], "used": False},
                                             {"$set": {"used": True}})
    await db.email_change_tokens.insert_one({
        "user_id": user["user_id"], "new_email": new_email, "token": token, "used": False,
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    link = f"{APP_BASE_URL}/verify-email?token={token}"
    html = (
        '<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif;color:#1F2937">'
        f'<p>Halo {escape(doc.get("name", ""))},</p>'
        f'<p>Kami menerima permintaan untuk mengubah alamat email akun MDJ Scholarship Anda menjadi '
        f'<strong>{escape(new_email)}</strong>.</p>'
        f'<p>Klik tautan berikut untuk mengonfirmasi perubahan (berlaku 1 jam):</p>'
        f'<p><a href="{escape(link)}" style="display:inline-block;background:#27AE60;color:#ffffff;'
        f'padding:12px 20px;border-radius:10px;text-decoration:none;font-weight:bold">Verifikasi Email Saya</a></p>'
        f'<p style="font-size:12px;color:#888">Jika Anda tidak meminta perubahan ini, abaikan email ini. '
        f'Sent by {escape(EMAIL_FROM_NAME)}. Kami tidak pernah meminta kata sandi Anda melalui email.</p>'
        '</td></tr></table>'
    )
    await send_email(to=new_email, subject="Verifikasi perubahan email MDJ Scholarship", html=html)
    return {"message": f"Tautan verifikasi telah dikirim ke {new_email}. Silakan cek kotak masuk Anda."}


@api_router.post("/auth/email/verify")
async def verify_email_change(payload: EmailVerifyInput):
    rec = await db.email_change_tokens.find_one({"token": payload.token, "used": False})
    if not rec:
        raise HTTPException(status_code=400, detail="Tautan verifikasi tidak valid atau sudah digunakan.")
    expires_at = rec["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Tautan verifikasi sudah kedaluwarsa.")
    new_email = rec["new_email"]
    if await db.users.find_one({"email": new_email, "user_id": {"$ne": rec["user_id"]}}):
        raise HTTPException(status_code=400, detail="Email tersebut sudah digunakan akun lain.")
    await db.users.update_one({"user_id": rec["user_id"]},
                              {"$set": {"email": new_email, "email_verified": True}})
    await db.email_change_tokens.update_one({"token": payload.token}, {"$set": {"used": True}})
    return {"message": "Email berhasil diperbarui.", "email": new_email}


@api_router.post("/auth/phone/send-otp")
async def send_phone_otp(payload: PhoneOtpSendInput, user: dict = Depends(get_current_user)):
    if not TWILIO_ENABLED:
        raise HTTPException(status_code=503, detail="Verifikasi SMS belum dikonfigurasi. Hubungi administrator.")
    phone = payload.phone.strip()
    if not re.fullmatch(r"\+[1-9]\d{7,14}", phone):
        raise HTTPException(status_code=400, detail="Nomor harus format internasional, contoh: +6281234567890.")
    try:
        from twilio.rest import Client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        await asyncio.to_thread(
            lambda: client.verify.v2.services(TWILIO_VERIFY_SERVICE_SID)
            .verifications.create(to=phone, channel="sms")
        )
    except Exception as e:
        logger.error(f"Twilio send OTP failed: {e}")
        raise HTTPException(status_code=502, detail="Gagal mengirim kode OTP. Periksa nomor Anda.")
    return {"message": f"Kode OTP telah dikirim ke {phone}."}


@api_router.post("/auth/phone/verify-otp")
async def verify_phone_otp(payload: PhoneOtpVerifyInput, user: dict = Depends(get_current_user)):
    if not TWILIO_ENABLED:
        raise HTTPException(status_code=503, detail="Verifikasi SMS belum dikonfigurasi. Hubungi administrator.")
    phone = payload.phone.strip()
    try:
        from twilio.rest import Client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        check = await asyncio.to_thread(
            lambda: client.verify.v2.services(TWILIO_VERIFY_SERVICE_SID)
            .verification_checks.create(to=phone, code=payload.code)
        )
    except Exception as e:
        logger.error(f"Twilio verify OTP failed: {e}")
        raise HTTPException(status_code=502, detail="Gagal memverifikasi kode OTP.")
    if check.status != "approved":
        raise HTTPException(status_code=400, detail="Kode OTP salah atau kedaluwarsa.")
    await db.users.update_one({"user_id": user["user_id"]},
                              {"$set": {"phone": phone, "phone_verified": True}})
    return {"message": "Nomor telepon berhasil diverifikasi.", "phone": phone}


# ---------------------------------------------------------------------------
# Student profile
# ---------------------------------------------------------------------------
@api_router.get("/profile")
async def get_profile(user: dict = Depends(get_current_user)):
    profile = await db.profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not profile:
        profile = {"user_id": user["user_id"], "data": {
            "namaLengkap": user.get("name", ""), "email": user.get("email", ""),
            "nik": user.get("nik", ""), "noTelp": user.get("phone", ""),
        }}
    return profile


@api_router.put("/profile")
async def update_profile(payload: ProfileInput, user: dict = Depends(get_current_user)):
    student_campus = None
    if user.get("role") == "student":
        student_campus = await register_student_campus(payload.data.get("institusi"))
    await db.profiles.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"data": payload.data, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return {"message": "Profil disimpan", "data": payload.data, "campus": student_campus}


# ---------------------------------------------------------------------------
# Registration (student)
# ---------------------------------------------------------------------------
STATUS_LABELS = {
    "draft": "Draft",
    "submitted": "Terkirim",
    "verifikasi": "Verifikasi Administrasi",
    "lolos_administrasi": "Lolos Administrasi",
    "wawancara": "Wawancara Assessment",
    "verifikasi_faktual": "Verifikasi Faktual",
    "lolos": "Lolos / Penerima Manfaat",
    "ditolak": "Tidak Lolos",
}


async def create_notification(
    user_id: str,
    notification_type: str,
    title: str,
    message: str,
) -> None:
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": notification_type,
        "title": title,
        "message": message,
        "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })


def announcement_signature(announcement: dict) -> str:
    fields = ("date", "category", "title", "summary")
    return "|".join(str(announcement.get(field, "")).strip() for field in fields)


async def notify_new_announcements(announcements: List[dict]) -> None:
    if not announcements:
        return
    registrations = await db.registrations.find({}, {"_id": 0, "user_id": 1}).to_list(5000)
    recipients = {registration.get("user_id") for registration in registrations}
    notifications = []
    for announcement in announcements:
        for user_id in recipients:
            if not user_id:
                continue
            notifications.append({
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "type": "announcement",
                "title": announcement.get("title") or "Pengumuman MDJ Scholarship",
                "message": announcement.get("summary") or "Ada pengumuman baru dari Admin MDJ.",
                "is_read": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
    if notifications:
        await db.notifications.insert_many(notifications)


async def create_cpm_id(registered_at: Optional[str] = None) -> str:
    year = str(datetime.now(timezone.utc).year)
    if registered_at:
        year = registered_at[:4]
    counter = await db.counters.find_one_and_update(
        {"key": f"cpm-{year}"},
        {"$inc": {"sequence": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    sequence = max(int(counter["sequence"]) - 1, 0)
    return f"CPM-MDJ/{year}/{sequence:06d}"


async def ensure_cpm_id(registration: Optional[dict]) -> Optional[dict]:
    if not registration or registration.get("cpm_id"):
        return registration

    cpm_id = await create_cpm_id(registration.get("created_at"))
    updated = await db.registrations.find_one_and_update(
        {
            "user_id": registration["user_id"],
            "$or": [{"cpm_id": {"$exists": False}}, {"cpm_id": None}],
        },
        {"$set": {"cpm_id": cpm_id}},
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )
    if updated:
        return updated
    return await db.registrations.find_one(
        {"user_id": registration["user_id"]},
        {"_id": 0},
    )


@api_router.get("/registration")
async def get_registration(user: dict = Depends(get_current_user)):
    reg = await db.registrations.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return await ensure_cpm_id(reg) or {}


@api_router.post("/registration")
async def submit_registration(payload: RegistrationInput, user: dict = Depends(get_current_user)):
    status = "submitted" if payload.action == "submit" else "draft"
    existing = await db.registrations.find_one({"user_id": user["user_id"]})
    now = datetime.now(timezone.utc).isoformat()
    if existing:
        await ensure_cpm_id(existing)
        update = {"category": payload.category, "updated_at": now}
        if payload.action == "submit" and existing.get("status") == "draft":
            update["status"] = "submitted"
            update["submitted_at"] = now
        await db.registrations.update_one({"user_id": user["user_id"]}, {"$set": update})
        reg = await db.registrations.find_one({"user_id": user["user_id"]}, {"_id": 0})
        return reg
    reg = {
        "id": str(uuid.uuid4()), "user_id": user["user_id"], "name": user.get("name"),
        "email": user.get("email"), "category": payload.category, "status": status,
        "cpm_id": await create_cpm_id(now),
        "history": [{"status": status, "note": "Pendaftaran dibuat", "at": now}],
        "created_at": now, "submitted_at": now if status == "submitted" else None, "updated_at": now,
    }
    await db.registrations.insert_one(reg)
    reg.pop("_id", None)
    return reg


@api_router.get("/notifications")
async def list_notifications(user: dict = Depends(get_current_user)):
    notifications = await db.notifications.find(
        {"user_id": user["user_id"]},
        {"_id": 0},
    ).sort("created_at", -1).to_list(30)
    unread_count = sum(1 for notification in notifications if not notification.get("is_read"))
    return {"notifications": notifications, "unread_count": unread_count}


@api_router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    user: dict = Depends(get_current_user),
):
    result = await db.notifications.update_one(
        {"id": notification_id, "user_id": user["user_id"]},
        {"$set": {"is_read": True}},
    )
    if not result.matched_count:
        raise HTTPException(status_code=404, detail="Notifikasi tidak ditemukan.")
    return {"message": "Notifikasi ditandai sudah dibaca."}


@api_router.post("/notifications/read-all")
async def mark_all_notifications_read(user: dict = Depends(get_current_user)):
    await db.notifications.update_many(
        {"user_id": user["user_id"], "is_read": False},
        {"$set": {"is_read": True}},
    )
    return {"message": "Semua notifikasi ditandai sudah dibaca."}


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------
@api_router.post("/documents")
async def upload_document(doc_type: str = Form(...), file: UploadFile = File(...),
                          user: dict = Depends(get_current_user)):
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else "bin"
    content_type = file.content_type or MIME_TYPES.get(ext, "application/octet-stream")
    data, ext, content_type = compress_image(
        await file.read(),
        ext,
        content_type,
        max_w=2400,
        quality=86,
    )
    path = f"{APP_NAME}/uploads/{user['user_id']}/{uuid.uuid4()}.{ext}"
    result = put_object(path, data, content_type)
    doc_id = str(uuid.uuid4())
    # Replace any previous doc of same type (soft delete)
    await db.documents.update_many(
        {"user_id": user["user_id"], "doc_type": doc_type, "is_deleted": False},
        {"$set": {"is_deleted": True}},
    )
    record = {
        "id": doc_id, "user_id": user["user_id"], "doc_type": doc_type,
        "storage_path": result["path"], "original_filename": file.filename,
        "content_type": content_type, "size": result["size"], "is_deleted": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.documents.insert_one(record)
    record.pop("_id", None)
    return record


@api_router.get("/documents")
async def list_documents(user: dict = Depends(get_current_user)):
    docs = await db.documents.find({"user_id": user["user_id"], "is_deleted": False}, {"_id": 0}).to_list(200)
    return docs


@api_router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, user: dict = Depends(get_current_user)):
    await db.documents.update_one({"id": doc_id, "user_id": user["user_id"]}, {"$set": {"is_deleted": True}})
    return {"message": "Dokumen dihapus"}


KTP_SYSTEM_PROMPT = """Anda adalah mesin OCR ahli untuk KTP (Kartu Tanda Penduduk) Indonesia.
Ekstrak data dari gambar/PDF KTP yang diberikan dan kembalikan HANYA objek JSON valid,
tanpa penjelasan, tanpa markdown fence. Gunakan skema kunci PERSIS berikut:
{
  "namaLengkap": string,          // Nama sesuai KTP, huruf kapital seperti aslinya
  "nik": string,                  // 16 digit angka saja
  "tempatLahir": string,          // Kota/kabupaten tempat lahir
  "tanggalLahir": string,         // WAJIB format YYYY-MM-DD (konversi dari DD-MM-YYYY)
  "jenisKelamin": string,         // "L" untuk LAKI-LAKI, "P" untuk PEREMPUAN
  "agama": string,                // salah satu: islam, kristen, katolik, hindu, buddha, konghucu
  "statusPerkawinan": string,     // "belum_kawin" (BELUM KAWIN), "kawin" (KAWIN), "cerai" (CERAI HIDUP/MATI)
  "alamatLengkap": string,        // Isi baris ALAMAT
  "rt": string,                   // RT saja (angka)
  "rw": string,                   // RW saja (angka)
  "kelurahan": string,            // KEL/DESA
  "kecamatan": string,            // KECAMATAN
  "kota": string,                 // Kota/Kabupaten (dari header atau alamat)
  "provinsi": string              // Provinsi (dari header KTP)
}
Aturan: gunakan null untuk field yang tidak terbaca. Jangan mengarang data.
Jika file bukan KTP, kembalikan {"error": "bukan_ktp"}."""


KK_SYSTEM_PROMPT = """Anda adalah mesin OCR ahli untuk Kartu Keluarga (KK) Indonesia.
Ekstrak data dari gambar/PDF Kartu Keluarga yang diberikan dan kembalikan HANYA objek JSON valid,
tanpa penjelasan, tanpa markdown fence. Gunakan skema kunci PERSIS berikut:
{
  "noKK": string                  // Nomor Kartu Keluarga, 16 digit angka saja (tertera di bagian atas dokumen, "No. ...")
}
Aturan: gunakan null jika tidak terbaca. Jangan mengarang data.
Jika file bukan Kartu Keluarga, kembalikan {"error": "bukan_dokumen"}."""


KTM_SYSTEM_PROMPT = """Anda adalah mesin OCR ahli untuk Kartu Tanda Mahasiswa (KTM) Indonesia.
Ekstrak data dari gambar/PDF KTM yang diberikan dan kembalikan HANYA objek JSON valid,
tanpa penjelasan atau markdown. Gunakan skema kunci PERSIS berikut:
{
  "institusi": string,
  "nim": string,
  "jurusan": string,
  "jenjang": string
}
Aturan: jenjang hanya "D3", "D4", atau "S1" bila terbaca jelas. Gunakan null untuk field
yang tidak terbaca dan jangan mengarang data. Jika file bukan KTM, kembalikan
{"error": "bukan_ktm"}."""


ACADEMIC_RECORD_SYSTEM_PROMPT = """Anda adalah mesin OCR ahli untuk dokumen akademik Indonesia.
Dokumen dapat berupa KRS, KHS, atau Transkrip Nilai. Ekstrak data dan kembalikan HANYA
objek JSON valid, tanpa penjelasan atau markdown. Gunakan skema kunci PERSIS berikut:
{
  "institusi": string,
  "nim": string,
  "jurusan": string,
  "jenjang": string,
  "semester": string,
  "ipk": string
}
Aturan: semester berisi angka saja bila terbaca. IPK menggunakan format desimal, misalnya
"3.75". Jenjang hanya "D3", "D4", atau "S1" bila terbaca jelas. Gunakan null untuk field
yang tidak terbaca dan jangan mengarang data. Jika file bukan KRS, KHS, atau Transkrip Nilai,
kembalikan {"error": "bukan_dokumen_akademik"}."""


async def _save_scanned_doc(user: dict, doc_type: str, filename: str, ext: str, data: bytes, content_type: str):
    data, ext, content_type = compress_image(
        data,
        ext,
        content_type,
        max_w=2400,
        quality=86,
    )
    path = f"{APP_NAME}/uploads/{user['user_id']}/{uuid.uuid4()}.{ext}"
    result = put_object(path, data, content_type)
    await db.documents.update_many(
        {"user_id": user["user_id"], "doc_type": doc_type, "is_deleted": False},
        {"$set": {"is_deleted": True}},
    )
    record = {
        "id": str(uuid.uuid4()), "user_id": user["user_id"], "doc_type": doc_type,
        "storage_path": result["path"], "original_filename": filename,
        "content_type": content_type, "size": result["size"], "is_deleted": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.documents.insert_one(record)
    record.pop("_id", None)
    return record


async def _extract_document(file: UploadFile, user: dict, label: str, system_prompt: str, allowed: set, doc_type: str):
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else "bin"
    if ext not in ("jpg", "jpeg", "png", "webp", "pdf"):
        raise HTTPException(status_code=400, detail="Format harus JPG, PNG, WEBP, atau PDF.")
    mime = MIME_TYPES.get(ext, "application/octet-stream")
    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Ukuran file maksimal 10MB.")
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        chat = LlmChat(
            api_key=EMERGENT_KEY,
            session_id=f"ocr-{user['user_id']}-{uuid.uuid4()}",
            system_message=system_prompt,
        ).with_model("gemini", "gemini-3.1-pro-preview")
        fc = FileContentWithMimeType(mime_type=mime, file_path=tmp_path)
        chunks = []
        async for event in chat.stream_message(UserMessage(
            text=f"Ekstrak seluruh data dari {label} ini dan kembalikan HANYA JSON sesuai skema.",
            file_contents=[fc],
        )):
            if isinstance(event, TextDelta):
                chunks.append(event.content)
            elif isinstance(event, StreamDone):
                break
        raw = "".join(chunks)
    except Exception as e:
        logger.error(f"{label} extraction failed: {e}")
        raise HTTPException(status_code=502, detail=f"Gagal membaca {label}. Coba lagi dengan foto yang lebih jelas.")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.DOTALL).strip()
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        raise HTTPException(status_code=422, detail=f"Data {label} tidak dapat dikenali. Pastikan foto jelas.")
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail=f"Data {label} tidak dapat dikenali. Pastikan foto jelas.")
    if parsed.get("error"):
        raise HTTPException(status_code=422, detail=f"File yang diunggah bukan {label} yang valid.")

    mapped = {k: str(v).strip() for k, v in parsed.items() if k in allowed and v not in (None, "", "null")}
    for key in ("nik", "noKK"):
        if mapped.get(key):
            mapped[key] = re.sub(r"\D", "", mapped[key])[:16]
    if mapped.get("semester"):
        mapped["semester"] = re.sub(r"\D", "", mapped["semester"])[:2]
    if mapped.get("ipk"):
        mapped["ipk"] = re.sub(r"[^0-9,.]", "", mapped["ipk"]).replace(",", ".")
    if mapped.get("jenjang"):
        jenjang = mapped["jenjang"].upper().replace(" ", "")
        mapped["jenjang"] = jenjang if jenjang in {"D3", "D4", "S1"} else ""
    document = None
    try:
        document = await _save_scanned_doc(user, doc_type, file.filename, ext, data, mime)
    except Exception as e:
        logger.error(f"Auto-save scanned {label} failed: {e}")
        raise HTTPException(
            status_code=502,
            detail="Data terbaca, tetapi dokumen belum tersimpan. Silakan unggah ulang.",
        )
    return {"data": mapped, "document": document}


@api_router.post("/profile/extract-ktp")
async def extract_ktp(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    allowed = {"namaLengkap", "nik", "tempatLahir", "tanggalLahir", "jenisKelamin",
               "agama", "statusPerkawinan", "alamatLengkap", "rt", "rw",
               "kelurahan", "kecamatan", "kota", "provinsi"}
    return await _extract_document(file, user, "KTP", KTP_SYSTEM_PROMPT, allowed, "KTP DKI Jakarta")


@api_router.post("/profile/extract-kk")
async def extract_kk(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    return await _extract_document(file, user, "Kartu Keluarga", KK_SYSTEM_PROMPT, {"noKK"}, "Kartu Keluarga (KK)")


@api_router.post("/profile/extract-ktm")
async def extract_ktm(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    fields = {"institusi", "nim", "jurusan", "jenjang"}
    return await _extract_document(
        file,
        user,
        "Kartu Tanda Mahasiswa",
        KTM_SYSTEM_PROMPT,
        fields,
        "Kartu Tanda Mahasiswa (KTM)",
    )


@api_router.post("/profile/extract-academic-record")
async def extract_academic_record(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    fields = {"institusi", "nim", "jurusan", "jenjang", "semester", "ipk"}
    return await _extract_document(
        file,
        user,
        "KRS, KHS, atau Transkrip Nilai",
        ACADEMIC_RECORD_SYSTEM_PROMPT,
        fields,
        "KRS / KHS / Transkrip Nilai",
    )


@api_router.get("/files/{path:path}")
async def download_file(path: str, request: Request, auth: str = Query(None)):
    site_record = await db.site_files.find_one({"storage_path": path, "is_deleted": False}, {"_id": 0})
    if site_record:
        data, content_type = get_object(path)
        return StarletteResponse(content=data, media_type=site_record.get("content_type", content_type),
                                 headers={"Cache-Control": "public, max-age=31536000, immutable"})
    token = request.cookies.get("access_token") or request.cookies.get("session_token") or auth
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token or not await resolve_user_from_token(token):
        raise HTTPException(status_code=401, detail="Not authenticated")
    record = await db.documents.find_one({"storage_path": path, "is_deleted": False}, {"_id": 0})
    data, content_type = get_object(path)
    return StarletteResponse(content=data, media_type=(record or {}).get("content_type", content_type),
                             headers={"Cache-Control": "private, max-age=3600"})


# ---------------------------------------------------------------------------
# Site content (public + super admin)
# ---------------------------------------------------------------------------
def clean_campus_value(value: Any) -> str:
    return str(value or "").strip()


async def create_student_campus_code() -> str:
    counter = await db.counters.find_one_and_update(
        {"key": "student-campus-code"},
        {"$inc": {"sequence": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return f"MDJ-KMP-{int(counter['sequence']):06d}"


async def register_student_campus(value: Any) -> Optional[dict]:
    name = clean_campus_value(value)
    if len(name) < 2:
        return None
    existing = await db.campuses.find_one(
        {"name": {"$regex": f"^{re.escape(name)}$", "$options": "i"}},
        {"_id": 0},
    )
    if existing:
        return None
    campus = {
        "id": str(uuid.uuid4()),
        "name": name,
        "code": await create_student_campus_code(),
        "source": "student_submission",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.campuses.insert_one(dict(campus))
    return campus


@api_router.get("/campuses")
async def list_campuses(user: dict = Depends(get_current_user)):
    campuses = await db.campuses.find({}, {"_id": 0}).sort("name", 1).to_list(5000)
    return campuses


@api_router.post("/campuses")
async def create_campus(
    payload: CampusInput,
    user: dict = Depends(require_roles("admin", "super_admin")),
):
    name = clean_campus_value(payload.name)
    code = clean_campus_value(payload.code)
    if len(name) < 2:
        raise HTTPException(status_code=400, detail="Nama kampus minimal 2 karakter.")
    if code and await db.campuses.find_one({"code": code}, {"_id": 0, "id": 1}):
        raise HTTPException(status_code=400, detail="Kode kampus sudah terdaftar.")
    if await db.campuses.find_one({"name": name}, {"_id": 0, "id": 1}):
        raise HTTPException(status_code=400, detail="Nama kampus sudah terdaftar.")
    campus = {
        "id": str(uuid.uuid4()),
        "name": name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if code:
        campus["code"] = code
    await db.campuses.insert_one(dict(campus))
    return campus


@api_router.put("/campuses/{campus_id}")
async def update_campus(
    campus_id: str,
    payload: CampusInput,
    user: dict = Depends(require_roles("admin", "super_admin")),
):
    name = clean_campus_value(payload.name)
    code = clean_campus_value(payload.code)
    if len(name) < 2:
        raise HTTPException(status_code=400, detail="Nama kampus minimal 2 karakter.")
    existing = await db.campuses.find_one({"id": campus_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Data kampus tidak ditemukan.")
    duplicate = await db.campuses.find_one(
        {"id": {"$ne": campus_id}, "$or": [{"name": name}, {"code": code}]},
        {"_id": 0, "id": 1},
    )
    if duplicate and (duplicate.get("name") == name or (code and duplicate.get("code") == code)):
        raise HTTPException(status_code=400, detail="Nama atau kode kampus sudah terdaftar.")
    update = {
        "name": name,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    operations = {"$set": update}
    if code:
        update["code"] = code
    else:
        operations["$unset"] = {"code": ""}
    await db.campuses.update_one({"id": campus_id}, operations)
    return {"id": campus_id, **update, "code": code or None}


@api_router.delete("/campuses/{campus_id}")
async def delete_campus(
    campus_id: str,
    user: dict = Depends(require_roles("admin", "super_admin")),
):
    result = await db.campuses.delete_one({"id": campus_id})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Data kampus tidak ditemukan.")
    return {"message": "Data kampus dihapus."}


@api_router.post("/campuses/import")
async def import_campuses(
    file: UploadFile = File(...),
    user: dict = Depends(require_roles("admin", "super_admin")),
):
    if not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="File import harus berformat XLSX.")
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Ukuran file XLSX maksimal 5MB.")
    try:
        workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        worksheet = workbook.active
        rows = worksheet.iter_rows(values_only=True)
        name_index = None
        code_index = None
        for header_row in rows:
            headers = [clean_campus_value(value).lower() for value in header_row]
            if "nama kampus" in headers and "kode kampus" in headers:
                name_index = headers.index("nama kampus")
                code_index = headers.index("kode kampus")
                break
        if name_index is None or code_index is None:
            raise ValueError("Kolom kampus tidak ditemukan")
    except (StopIteration, ValueError, OSError) as error:
        raise HTTPException(
            status_code=400,
            detail="XLSX harus memiliki kolom 'Nama Kampus' dan 'Kode Kampus'.",
        ) from error

    inserted = 0
    updated = 0
    now = datetime.now(timezone.utc).isoformat()
    for row in rows:
        name = clean_campus_value(row[name_index] if len(row) > name_index else "")
        code = clean_campus_value(row[code_index] if len(row) > code_index else "")
        if not name:
            continue
        query = {"code": code} if code else {"name": name}
        existing = await db.campuses.find_one(query, {"_id": 0, "id": 1})
        campus_id = existing["id"] if existing else str(uuid.uuid4())
        operations = {
            "$set": {"name": name, "updated_at": now},
            "$setOnInsert": {"id": campus_id, "created_at": now},
        }
        if code:
            operations["$set"]["code"] = code
        else:
            operations["$unset"] = {"code": ""}
        await db.campuses.update_one(
            query,
            operations,
            upsert=True,
        )
        if existing:
            updated += 1
        else:
            inserted += 1
    workbook.close()
    return {"inserted": inserted, "updated": updated, "total": inserted + updated}


DEFAULT_SITE_CONTENT = {
    "settings": {
        "registration_open": True,
        "period_start": "8 September 2026",
        "period_end": "30 September 2026",
        "announcement_date": "12 Januari 2027",
        "year": "2026",
    },
    "banner_url": None,
    "hero": {
        "eyebrow": "Program Beasiswa Pendidikan DKI Jakarta",
        "title": "Wujudkan Pendidikan dan Masa Depan Terbaikmu",
        "subtitle": "Program Masa Depan Jakarta (MDJ) hadir sebagai wujud nyata dukungan BAZNAS (BAZIS) Provinsi DKI Jakarta. Muda dengan Zakat, Bahagia dengan Manfaat.",
    },
    "stats": [
        {"label": "Total Pendaftar (22-25)", "value": "16.935"},
        {"label": "Penerima Manfaat 2025", "value": "3.049"},
        {"label": "Wilayah Terjangkau", "value": "6"},
        {"label": "Mitra Kampus (UPZ)", "value": "37+"},
    ],
    "timeline": [
        {"title": "Pembuatan Akun", "desc": "Calon pendaftar membuat akun resmi pada portal pendaftaran."},
        {"title": "Pendaftaran Online", "desc": "Pengisian formulir dan pengunggahan berkas persyaratan."},
        {"title": "Seleksi Administrasi", "desc": "Verifikasi dan validasi kesesuaian dokumen pendaftar."},
        {"title": "Pengumuman Seleksi Administrasi", "desc": "Pengumuman peserta yang memenuhi syarat dokumen."},
        {"title": "Wawancara Assessment", "desc": "Sesi penggalian potensi, motivasi, dan komitmen peserta."},
        {"title": "Verifikasi Faktual", "desc": "Survei dan validasi lapangan ke kediaman serta kampus."},
        {"title": "Pengumuman Penerima Manfaat", "desc": "Penetapan akhir peserta terpilih sebagai penerima beasiswa."},
        {"title": "Pengukuhan / Inagurasi", "desc": "Acara peresmian dan penyambutan resmi penerima manfaat baru."},
    ],
    "announcements": [
        {"date": "12 Jan 2026", "category": "Informasi", "title": "Pengukuhan Kader Akademia MDJ", "summary": "Peserta yang lolos seleksi akhir wajib mengikuti kegiatan pengukuhan dan orientasi program pembinaan."},
        {"date": "22 Des 2025", "category": "Pengumuman", "title": "Pengumuman Awardee MDJ Scholarship", "summary": "Daftar nama 3.049 penerima manfaat yang lolos tahap wawancara dan verifikasi faktual telah diterbitkan."},
        {"date": "18 Okt 2025", "category": "Jadwal", "title": "Pelaksanaan Verifikasi Faktual", "summary": "Tim BAZNAS (BAZIS) DKI Jakarta akan melakukan survey ke domisili dan audiensi ke kampus mahasiswa."},
    ],
    "requirements": [
        "Surat Permohonan yang bersangkutan.",
        "KTP Provinsi DKI Jakarta.",
        "Pas Foto berwarna ukuran 3x4.",
        "Kartu Keluarga (KK).",
        "Kartu Tanda Mahasiswa (KTM).",
        "Surat Keterangan Mahasiswa Aktif (Masih Kuliah).",
        "SKTM atau Surat Rekomendasi Masjid/Lembaga Keagamaan Resmi.",
        "Surat Persetujuan Orang Tua/Wali.",
        "Surat Keterangan tidak sedang menerima beasiswa lain.",
        "Pakta Integritas Kader Akademia MDJ (Sesuai format BAZNAS).",
    ],
    "faqs": [
        {"q": "Apa itu Program Masa Depan Jakarta?", "a": "Program Masa Depan Jakarta Scholarship merupakan Bantuan Biaya Pendidikan Mahasiswa DKI Jakarta yang diselenggarakan oleh BAZNAS (BAZIS) Provinsi DKI Jakarta."},
        {"q": "Siapa saja yang dapat mendaftar?", "a": "Mahasiswa (Diploma/Sarjana) aktif yang berdomisili di DKI Jakarta dan memenuhi kriteria keluarga prasejahtera."},
        {"q": "Apakah pendaftaran dikenakan biaya?", "a": "Tidak. Seluruh proses pendaftaran, seleksi, hingga penyaluran dana TIDAK DIPUNGUT BIAYA (Gratis)."},
        {"q": "Bagaimana cara mengetahui status pendaftaran?", "a": "Login ke akun Anda di portal ini. Status akan diperbarui secara berkala pada menu dashboard pendaftar."},
    ],
}


@api_router.get("/site/content")
async def get_site_content():
    content = await db.site_content.find_one({"key": "main"}, {"_id": 0})
    if not content:
        content = {"key": "main", **DEFAULT_SITE_CONTENT}
        await db.site_content.insert_one(dict(content))
        content.pop("_id", None)
    content.pop("key", None)
    return content


@api_router.put("/site/content")
async def update_site_content(payload: SiteContentInput, user: dict = Depends(require_roles("super_admin"))):
    current = await db.site_content.find_one({"key": "main"}, {"_id": 0}) or {}
    incoming_announcements = payload.content.get("announcements")
    new_announcements = []
    if isinstance(incoming_announcements, list):
        existing_signatures = {
            announcement_signature(announcement)
            for announcement in current.get("announcements", [])
        }
        new_announcements = [
            announcement
            for announcement in incoming_announcements
            if announcement_signature(announcement) not in existing_signatures
        ]
    await db.site_content.update_one(
        {"key": "main"},
        {"$set": {**payload.content, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    await notify_new_announcements(new_announcements)
    content = await db.site_content.find_one({"key": "main"}, {"_id": 0})
    content.pop("key", None)
    return content


@api_router.post("/site/banner")
async def upload_banner(file: UploadFile = File(...), user: dict = Depends(require_roles("super_admin"))):
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else "png"
    content_type = file.content_type or MIME_TYPES.get(ext, "image/png")
    data, ext, content_type = compress_image(
        await file.read(),
        ext,
        content_type,
        max_w=1920,
        quality=80,
    )
    path = f"{APP_NAME}/site/banner_{uuid.uuid4().hex[:8]}.{ext}"
    result = put_object(path, data, content_type)
    await db.site_files.insert_one({
        "storage_path": result["path"], "content_type": content_type,
        "is_deleted": False, "created_at": datetime.now(timezone.utc).isoformat(),
    })
    banner_url = f"/api/files/{result['path']}"
    await db.site_content.update_one({"key": "main"}, {"$set": {"banner_url": banner_url}}, upsert=True)
    return {"banner_url": banner_url, "storage_path": result["path"]}


@api_router.post("/site/about-image")
async def upload_about_image(
    file: UploadFile = File(...),
    user: dict = Depends(require_roles("super_admin")),
):
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else "png"
    content_type = file.content_type or MIME_TYPES.get(ext, "image/png")
    data, ext, content_type = compress_image(
        await file.read(),
        ext,
        content_type,
        max_w=1600,
        quality=84,
    )
    path = f"{APP_NAME}/site/about_{uuid.uuid4().hex[:8]}.{ext}"
    result = put_object(path, data, content_type)
    await db.site_files.insert_one({
        "storage_path": result["path"],
        "content_type": content_type,
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    about_url = f"/api/files/{result['path']}"
    await db.site_content.update_one(
        {"key": "main"},
        {"$set": {"about_url": about_url}},
        upsert=True,
    )
    return {"about_url": about_url, "storage_path": result["path"]}


@api_router.post("/site/logo")
async def upload_site_logo(
    file: UploadFile = File(...),
    user: dict = Depends(require_roles("super_admin")),
):
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else "bin"
    if ext not in ("jpg", "jpeg", "png", "webp"):
        raise HTTPException(status_code=400, detail="Logo harus berupa JPG, PNG, atau WEBP.")
    content_type = file.content_type or MIME_TYPES.get(ext, "image/png")
    data, ext, content_type = compress_image(
        await file.read(),
        ext,
        content_type,
        max_w=512,
        quality=92,
    )
    path = f"{APP_NAME}/site/logo_{uuid.uuid4().hex[:8]}.{ext}"
    result = put_object(path, data, content_type)
    await db.site_files.insert_one({
        "storage_path": result["path"],
        "content_type": content_type,
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    logo_url = f"/api/files/{result['path']}"
    await db.site_content.update_one(
        {"key": "main"},
        {"$set": {"logo_url": logo_url}},
        upsert=True,
    )
    return {"logo_url": logo_url, "storage_path": result["path"]}


# ---------------------------------------------------------------------------
# Admin: participants management
# ---------------------------------------------------------------------------
@api_router.get("/admin/stats")
async def admin_stats(
    region: Optional[str] = None,
    user: dict = Depends(require_roles("admin", "super_admin")),
):
    all_regs = await db.registrations.find({}, {"_id": 0}).to_list(5000)
    user_ids = [registration["user_id"] for registration in all_regs]
    profiles = await db.profiles.find(
        {"user_id": {"$in": user_ids}},
        {"_id": 0, "user_id": 1, "data": 1},
    ).to_list(5000)
    profile_data = {
        profile["user_id"]: profile.get("data", {})
        for profile in profiles
    }

    def region_name(registration: dict) -> str:
        data = profile_data.get(registration["user_id"], {})
        return str(data.get("kota") or data.get("provinsi") or "Belum diisi").strip()

    available_regions = sorted({region_name(registration) for registration in all_regs})
    regs = all_regs
    if region and region != "all":
        regs = [registration for registration in all_regs if region_name(registration) == region]
    total = len(regs)
    by_status = {}
    for r in regs:
        by_status[r.get("status", "draft")] = by_status.get(r.get("status", "draft"), 0) + 1
    total_students = await db.users.count_documents({"role": "student"})
    total_admins = await db.users.count_documents({"role": {"$in": ["admin", "super_admin"]}})
    # trend by month (submitted_at)
    trend = {}
    for r in regs:
        ts = r.get("submitted_at") or r.get("created_at")
        if ts:
            month = ts[:7]
            trend[month] = trend.get(month, 0) + 1
    trend_list = [{"month": k, "count": v} for k, v in sorted(trend.items())]
    passed_by_region = {}
    for registration in regs:
        if registration.get("status") != "lolos":
            continue
        passed_region = region_name(registration)
        passed_by_region[passed_region] = passed_by_region.get(passed_region, 0) + 1
    passed_region_data = [
        {"region": region, "count": count}
        for region, count in sorted(passed_by_region.items(), key=lambda item: (-item[1], item[0]))
    ]
    site_content = await db.site_content.find_one({"key": "main"}, {"_id": 0}) or {}
    return {
        "total_registrations": total, "total_students": total_students, "total_admins": total_admins,
        "by_status": by_status, "trend": trend_list,
        "verified": by_status.get("lolos", 0),
        "pending": by_status.get("submitted", 0) + by_status.get("verifikasi", 0),
        "passed_by_region": passed_region_data,
        "available_regions": available_regions,
        "announcement_count": len(site_content.get("announcements", [])),
        "selected_region": region or "all",
    }


@api_router.get("/admin/participants")
async def list_participants(status: Optional[str] = None, search: Optional[str] = None,
                            user: dict = Depends(require_roles("admin", "super_admin"))):
    query = {}
    if status and status != "all":
        query["status"] = status
    regs = await db.registrations.find(query, {"_id": 0}).sort("created_at", -1).to_list(2000)
    result = []
    for r in regs:
        profile = await db.profiles.find_one({"user_id": r["user_id"]}, {"_id": 0})
        pdata = (profile or {}).get("data", {})
        doc_count = await db.documents.count_documents({"user_id": r["user_id"], "is_deleted": False})
        item = {
            **r,
            "institusi": pdata.get("institusi", "-"),
            "jenjang": pdata.get("jenjang", "-"),
            "phone": pdata.get("noTelp", "-"),
            "doc_count": doc_count,
        }
        if search:
            s = search.lower()
            if s not in (r.get("name", "").lower() + r.get("email", "").lower() + pdata.get("institusi", "").lower()):
                continue
        result.append(item)
    return result


@api_router.get("/admin/participants/{user_id}")
async def participant_detail(user_id: str, user: dict = Depends(require_roles("admin", "super_admin"))):
    reg = await db.registrations.find_one({"user_id": user_id}, {"_id": 0})
    profile = await db.profiles.find_one({"user_id": user_id}, {"_id": 0})
    docs = await db.documents.find({"user_id": user_id, "is_deleted": False}, {"_id": 0}).to_list(200)
    account = await db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
    for d in docs:
        d["url"] = f"/api/files/{d['storage_path']}"
    return {"registration": reg or {}, "profile": (profile or {}).get("data", {}),
            "documents": docs, "account": account or {}}


@api_router.put("/admin/participants/{user_id}/status")
async def update_participant_status(user_id: str, payload: StatusUpdateInput,
                                    user: dict = Depends(require_roles("admin", "super_admin"))):
    if payload.status not in REG_STATUSES:
        raise HTTPException(status_code=400, detail="Status tidak valid")
    reg = await db.registrations.find_one({"user_id": user_id})
    if not reg:
        raise HTTPException(status_code=404, detail="Pendaftar tidak ditemukan")
    now = datetime.now(timezone.utc).isoformat()
    entry = {"status": payload.status, "note": payload.note or "", "at": now, "by": user.get("name")}
    await db.registrations.update_one(
        {"user_id": user_id},
        {"$set": {"status": payload.status, "updated_at": now}, "$push": {"history": entry}},
    )
    if payload.status != reg.get("status"):
        label = STATUS_LABELS.get(payload.status, payload.status)
        await create_notification(
            user_id,
            "selection_progress",
            "Perkembangan seleksi diperbarui",
            f"Status seleksi Anda diperbarui menjadi {label}.",
        )
    updated = await db.registrations.find_one({"user_id": user_id}, {"_id": 0})
    return updated


# ---------------------------------------------------------------------------
# Super admin: user/admin management
# ---------------------------------------------------------------------------
@api_router.get("/admin/users")
async def list_users(role: Optional[str] = None, user: dict = Depends(require_roles("super_admin"))):
    query = {}
    if role and role != "all":
        query["role"] = role
    users = await db.users.find(query, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(2000)
    return users


@api_router.post("/admin/users")
async def create_admin(payload: CreateAdminInput, user: dict = Depends(require_roles("super_admin"))):
    if payload.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=400, detail="Role tidak valid")
    email = payload.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email sudah terdaftar")
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    doc = {
        "user_id": user_id, "email": email, "password_hash": hash_password(payload.password),
        "name": payload.name, "role": payload.role, "auth_provider": "password",
        "nik": None, "phone": None, "picture": None, "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(doc)
    return clean_user(doc)


@api_router.put("/admin/users/{user_id}")
async def toggle_user(user_id: str, payload: UserToggleInput, user: dict = Depends(require_roles("super_admin"))):
    if user_id == user["user_id"]:
        raise HTTPException(status_code=400, detail="Tidak dapat menonaktifkan akun sendiri")
    await db.users.update_one({"user_id": user_id}, {"$set": {"is_active": payload.is_active}})
    return {"message": "Status akun diperbarui"}


@api_router.delete("/admin/users/{user_id}")
async def delete_user(user_id: str, user: dict = Depends(require_roles("super_admin"))):
    target = await db.users.find_one({"user_id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    if target.get("email") == ADMIN_EMAIL:
        raise HTTPException(status_code=400, detail="Tidak dapat menghapus super admin utama")
    await db.users.delete_one({"user_id": user_id})
    return {"message": "User dihapus"}


@api_router.get("/")
async def root():
    return {"message": "MDJ Scholarship API"}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("user_id")
    await db.user_sessions.create_index("session_token")
    await db.registrations.create_index("user_id")
    await db.registrations.create_index("cpm_id", unique=True, sparse=True)
    await db.documents.create_index("user_id")
    await db.campuses.create_index("id", unique=True)
    await db.campuses.create_index("code", unique=True, sparse=True)
    # Seed super admin
    existing = await db.users.find_one({"email": ADMIN_EMAIL})
    if not existing:
        await db.users.insert_one({
            "user_id": f"user_{uuid.uuid4().hex[:12]}", "email": ADMIN_EMAIL,
            "password_hash": hash_password(ADMIN_PASSWORD), "name": "Super Admin MDJ",
            "role": "super_admin", "auth_provider": "password", "nik": None, "phone": None,
            "picture": None, "is_active": True, "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info("Seeded super admin")
    elif not verify_password(ADMIN_PASSWORD, existing.get("password_hash") or ""):
        await db.users.update_one(
            {"email": ADMIN_EMAIL},
            {
                "$set": {
                    "password_hash": hash_password(ADMIN_PASSWORD),
                    "role": "super_admin",
                }
            },
        )

    demo_accounts = [
        {
            "email": DEMO_STUDENT_EMAIL,
            "password": DEMO_STUDENT_PASSWORD,
            "name": "Mahasiswa Demo MDJ",
            "role": "student",
        },
        {
            "email": DEMO_ADMIN_EMAIL,
            "password": DEMO_ADMIN_PASSWORD,
            "name": "Admin Pendaftaran MDJ",
            "role": "admin",
        },
    ]
    for account in demo_accounts:
        exists = await db.users.find_one({"email": account["email"]}, {"_id": 0})
        if not exists:
            await db.users.insert_one(
                {
                    "user_id": f"user_{uuid.uuid4().hex[:12]}",
                    "email": account["email"],
                    "password_hash": hash_password(account["password"]),
                    "name": account["name"],
                    "role": account["role"],
                    "auth_provider": "password",
                    "nik": None,
                    "phone": None,
                    "picture": None,
                    "is_active": True,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            logger.info("Seeded demo %s account", account["role"])
            continue

        updates = {}
        if exists.get("role") != account["role"]:
            updates["role"] = account["role"]
        if exists.get("name") != account["name"]:
            updates["name"] = account["name"]
        if not exists.get("is_active", True):
            updates["is_active"] = True
        if not verify_password(account["password"], exists.get("password_hash") or ""):
            updates["password_hash"] = hash_password(account["password"])
        if updates:
            await db.users.update_one({"email": account["email"]}, {"$set": updates})
            logger.info("Refreshed demo %s account", account["role"])
    # Seed site content
    if not await db.site_content.find_one({"key": "main"}):
        await db.site_content.insert_one({"key": "main", **DEFAULT_SITE_CONTENT})
    try:
        init_storage()
        logger.info("Storage initialized")
    except Exception as e:
        logger.error(f"Storage init failed: {e}")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
