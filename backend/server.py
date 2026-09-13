from dotenv import load_dotenv
from pathlib import Path
import os

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, UploadFile, File, Form, Query, Header
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response as StarletteResponse, StreamingResponse
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
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
import secrets
import asyncio
import ipaddress
import random
import httpx
import base64
import hashlib
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse
from cryptography.fernet import Fernet, InvalidToken
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
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
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
    region: Optional[str] = None


class UserToggleInput(BaseModel):
    is_active: bool


class SiteContentInput(BaseModel):
    content: Dict[str, Any]


class CampusInput(BaseModel):
    name: str
    code: Optional[str] = None


class VerificationApprovalInput(BaseModel):
    recommendation_ids: List[str] = []
    approve_all: bool = False


class BeneficiaryBankInput(BaseModel):
    bank_name: str = ""
    account_number: str = ""


class DisbursementInput(BaseModel):
    status: str
    amount: Optional[float] = None
    disbursed_at: Optional[str] = None
    reference: str = ""
    notes: str = ""


class BeneficiaryReviewResolveInput(BaseModel):
    user_id: str


REG_STATUSES = ["draft", "submitted", "verifikasi", "lolos_administrasi", "wawancara",
                "verifikasi_faktual", "lolos", "ditolak"]
REGIONAL_ADMIN_ROLE = "admin_wilayah"
MANAGEMENT_ROLES = ("admin", "super_admin", REGIONAL_ADMIN_ROLE)
DKI_REGIONS = [
    "Jakarta Pusat",
    "Jakarta Utara",
    "Jakarta Barat",
    "Jakarta Selatan",
    "Jakarta Timur",
    "Kepulauan Seribu",
]
DISBURSEMENT_STATUSES = [
    "belum_diproses",
    "menunggu_bukti",
    "perlu_tinjau",
    "terverifikasi",
    "disetujui",
    "dicairkan",
    "ditunda",
]
PM_MANAGERS = ("admin", "super_admin")
PM_ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}


def clean_user(u: dict) -> dict:
    u = dict(u)
    u.pop("password_hash", None)
    u.pop("_id", None)
    return u


def regional_admin_region(user: dict) -> Optional[str]:
    if user.get("role") != REGIONAL_ADMIN_ROLE:
        return None
    region = str(user.get("region") or "").strip()
    if region not in DKI_REGIONS:
        raise HTTPException(status_code=403, detail="Wilayah Admin Wilayah tidak valid.")
    return region


def profile_region(profile_data: dict) -> str:
    return str(profile_data.get("kota") or profile_data.get("provinsi") or "").strip()


async def participant_scope_query(user: dict) -> dict:
    region = regional_admin_region(user)
    if not region:
        return {}
    profiles = await db.profiles.find(
        {"$or": [{"data.kota": region}, {"data.provinsi": region}]},
        {"_id": 0, "user_id": 1},
    ).to_list(5000)
    user_ids = [profile["user_id"] for profile in profiles if profile.get("user_id")]
    return {"user_id": {"$in": user_ids}}


async def require_participant_scope(user: dict, user_id: str) -> None:
    region = regional_admin_region(user)
    if not region:
        return
    profile = await db.profiles.find_one({"user_id": user_id}, {"_id": 0, "data": 1})
    if not profile or profile_region(profile.get("data", {})) != region:
        raise HTTPException(status_code=404, detail="Pendaftar tidak ditemukan")


def can_manage_admin_account(actor: dict, target: dict) -> bool:
    if actor.get("role") == "super_admin":
        return True
    return (
        actor.get("role") == "admin"
        and target.get("role") == REGIONAL_ADMIN_ROLE
    )


def bank_cipher() -> Fernet:
    key = hashlib.sha256(JWT_SECRET.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def normalize_nim(value: Any) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", str(value or "")).upper()


def normalize_account_number(value: Any) -> str:
    return re.sub(r"\D", "", str(value or ""))


def mask_account_number(value: str) -> str:
    if not value:
        return "Belum dicatat"
    if len(value) <= 4:
        return "•" * len(value)
    return f"{'•' * (len(value) - 4)}{value[-4:]}"


def encrypt_account_number(value: str) -> str:
    return bank_cipher().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_account_number(value: str) -> str:
    if not value:
        return ""
    try:
        return bank_cipher().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return ""


async def audit_beneficiary_action(
    actor: dict,
    action: str,
    user_id: Optional[str] = None,
    detail: Optional[dict] = None,
) -> None:
    await db.beneficiary_audit_events.insert_one({
        "id": str(uuid.uuid4()),
        "actor_id": actor["user_id"],
        "actor_name": actor.get("name", "Admin"),
        "action": action,
        "user_id": user_id,
        "detail": detail or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    })


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
# Penerima Manfaat and disbursement management
# ---------------------------------------------------------------------------
PM_ACTIVE_LETTER_PROMPT = """Anda adalah mesin OCR dokumen kampus Indonesia.
Dokumen adalah surat keterangan mahasiswa aktif atau surat jawaban verifikasi yang dapat
berisi tabel banyak mahasiswa. Kembalikan HANYA JSON valid dengan skema:
{
  "students": [
    {
      "name": string,
      "nim": string,
      "study_program": string,
      "semester": string,
      "evidence": string
    }
  ]
}
Ekstrak SEMUA baris mahasiswa. Pertahankan NIM persis seperti tertulis, termasuk nol di
depan. Gunakan string kosong bila tidak terbaca dan jangan menebak data."""

PM_TRANSFER_PROOF_PROMPT = """Anda adalah mesin OCR bukti transfer Indonesia.
Bukti dapat berupa transfer massal dengan banyak transaksi. Kembalikan HANYA JSON valid:
{
  "transactions": [
    {
      "name": string,
      "nim": string,
      "campus": string,
      "account_number": string,
      "bank_name": string,
      "status": string,
      "amount": string,
      "reference": string,
      "date": string,
      "evidence": string
    }
  ],
  "summary": {"total_amount": string, "date": string, "reference": string}
}
Prioritaskan nomor rekening penerima. Ekstrak semua transaksi yang terlihat, jangan
menebak digit rekening, dan gunakan string kosong untuk data yang tidak terbaca."""


def pm_content_type(ext: str) -> str:
    return MIME_TYPES.get(ext, "application/octet-stream")


def pm_magic_matches(data: bytes, ext: str) -> bool:
    signatures = {
        "pdf": b"%PDF",
        "jpg": b"\xff\xd8\xff",
        "jpeg": b"\xff\xd8\xff",
        "png": b"\x89PNG\r\n\x1a\n",
    }
    return bool(data) and data.startswith(signatures[ext])


async def read_pm_upload(file: UploadFile) -> tuple:
    filename = file.filename or "dokumen"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in PM_ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Gunakan PDF, JPG, JPEG, atau PNG.")
    data = await file.read()
    if not data or len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Ukuran berkas harus antara 1 byte dan 10MB.")
    if not pm_magic_matches(data, ext):
        raise HTTPException(status_code=400, detail="Isi berkas tidak sesuai dengan formatnya.")
    return filename, ext, data, pm_content_type(ext)


async def store_pm_source(
    actor: dict,
    source_type: str,
    filename: str,
    ext: str,
    data: bytes,
    content_type: str,
    stage: Optional[int] = None,
) -> dict:
    source_id = str(uuid.uuid4())
    path = f"{APP_NAME}/beneficiary-sources/{source_id}.{ext}"
    result = put_object(path, data, content_type)
    source = {
        "id": source_id,
        "source_type": source_type,
        "stage": stage,
        "storage_path": result["path"],
        "original_filename": filename,
        "content_type": content_type,
        "size": result["size"],
        "sha256": hashlib.sha256(data).hexdigest(),
        "status": "processing",
        "uploaded_by": actor["user_id"],
        "uploaded_by_name": actor.get("name", "Admin"),
        "matched_user_ids": [],
        "regions": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.beneficiary_sources.insert_one(dict(source))
    await audit_beneficiary_action(actor, f"upload_{source_type}", detail={"source_id": source_id})
    return source


async def extract_pm_payload(
    data: bytes,
    content_type: str,
    actor: dict,
    prompt: str,
    source_label: str,
) -> dict:
    suffix = ".pdf" if content_type == "application/pdf" else ".img"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(data)
            tmp_path = temp_file.name
        chat = LlmChat(
            api_key=EMERGENT_KEY,
            session_id=f"pm-ocr-{actor['user_id']}-{uuid.uuid4()}",
            system_message=prompt,
        ).with_model("gemini", "gemini-3.1-pro-preview")
        file_content = FileContentWithMimeType(mime_type=content_type, file_path=tmp_path)
        chunks = []
        async for event in chat.stream_message(UserMessage(
            text=f"Baca {source_label} ini dan kembalikan JSON sesuai skema.",
            file_contents=[file_content],
        )):
            if isinstance(event, TextDelta):
                chunks.append(event.content)
            elif isinstance(event, StreamDone):
                break
        raw = "".join(chunks).strip()
    except Exception as error:
        logger.error("PM OCR failed: %s", error)
        raise HTTPException(status_code=502, detail="AI belum dapat membaca berkas. Coba lagi nanti.")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.DOTALL).strip()
    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not match:
        raise HTTPException(status_code=422, detail="Hasil OCR tidak dapat dibaca sebagai data.")
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=422, detail="Hasil OCR tidak valid.") from error
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=422, detail="Hasil OCR tidak memiliki struktur yang valid.")
    return parsed


async def final_beneficiary_index(user: Optional[dict] = None) -> Dict[str, List[dict]]:
    query = {"status": "lolos"}
    if user:
        query.update(await participant_scope_query(user))
    registrations = await db.registrations.find(query, {"_id": 0}).to_list(5000)
    user_ids = [registration["user_id"] for registration in registrations]
    profiles = await db.profiles.find(
        {"user_id": {"$in": user_ids}},
        {"_id": 0, "user_id": 1, "data": 1},
    ).to_list(5000)
    profiles_by_user = {profile["user_id"]: profile.get("data", {}) for profile in profiles}
    index: Dict[str, List[dict]] = {}
    for registration in registrations:
        profile = profiles_by_user.get(registration["user_id"], {})
        name = registration.get("name") or profile.get("namaLengkap", "")
        nim = normalize_nim(profile.get("nim"))
        key = f"{normalized_name(name)}|{nim}"
        if not normalized_name(name) or not nim:
            continue
        index.setdefault(key, []).append({
            "registration": registration,
            "profile": profile,
            "region": profile_region(profile),
        })
    return index


def beneficiary_campus(profile: dict) -> str:
    return str(profile.get("institusi") or "Kampus belum diisi").strip()


def campus_disbursement_key(campus: str) -> str:
    normalized = normalized_name(campus) or "kampus-belum-diisi"
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:20]
    return f"campus_{digest}"


async def final_beneficiary_rows(user: Optional[dict] = None) -> List[dict]:
    query = {"status": "lolos"}
    if user:
        query.update(await participant_scope_query(user))
    registrations = await db.registrations.find(query, {"_id": 0}).to_list(5000)
    user_ids = [item["user_id"] for item in registrations]
    profiles = await db.profiles.find(
        {"user_id": {"$in": user_ids}},
        {"_id": 0, "user_id": 1, "data": 1},
    ).to_list(5000)
    profiles_by_user = {item["user_id"]: item.get("data", {}) for item in profiles}
    rows = []
    for registration in registrations:
        profile = profiles_by_user.get(registration["user_id"], {})
        campus = beneficiary_campus(profile)
        rows.append({
            "user_id": registration["user_id"],
            "name": registration.get("name") or profile.get("namaLengkap", "-"),
            "cpm_id": registration.get("cpm_id", "-"),
            "nim": profile.get("nim", "-"),
            "campus": campus,
            "campus_key": campus_disbursement_key(campus),
            "region": profile_region(profile) or "Belum diisi",
            "study_program": profile.get("jurusan", "-"),
            "semester": profile.get("semester", "-"),
        })
    return rows


def default_campus_disbursement(stage: int) -> dict:
    return {
        "stage": stage,
        "status": "belum_diproses",
        "amount": None,
        "disbursed_at": None,
        "reference": "",
        "notes": "",
        "proofs": [],
        "transactions": [],
    }


async def ensure_campus_disbursement(
    campus_key: str,
    campus: str,
    region: str,
    stage: int,
    recipient_ids: List[str],
) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    defaults = default_campus_disbursement(stage)
    defaults.update({
        "id": str(uuid.uuid4()),
        "campus_key": campus_key,
        "campus": campus,
        "region": region,
        "created_at": now,
    })
    await db.campus_disbursements.update_one(
        {"campus_key": campus_key, "region": region, "stage": stage},
        {
            "$setOnInsert": defaults,
            "$set": {"recipient_user_ids": recipient_ids, "synced_at": now},
        },
        upsert=True,
    )
    return await db.campus_disbursements.find_one(
        {"campus_key": campus_key, "region": region, "stage": stage},
        {"_id": 0},
    )


def serialize_campus_disbursement(record: Optional[dict], stage: int) -> dict:
    data = record or default_campus_disbursement(stage)
    return {
        "stage": stage,
        "status": data.get("status", "belum_diproses"),
        "amount": data.get("amount"),
        "disbursed_at": data.get("disbursed_at"),
        "reference": data.get("reference", ""),
        "notes": data.get("notes", ""),
        "proofs": data.get("proofs", []),
        "transactions": data.get("transactions", []),
        "updated_at": data.get("updated_at"),
    }


def combine_campus_stage(records: List[dict], stage: int) -> dict:
    items = [serialize_campus_disbursement(record, stage) for record in records]
    if not items:
        return default_campus_disbursement(stage)
    statuses = {item["status"] for item in items}
    proof_ids = {
        proof.get("source_id")
        for item in items
        for proof in item.get("proofs", [])
        if proof.get("source_id")
    }
    return {
        "stage": stage,
        "status": statuses.pop() if len(statuses) == 1 else "bervariasi",
        "amount": sum(float(item["amount"] or 0) for item in items) or None,
        "proof_count": len(proof_ids),
        "region_count": len(items),
    }


async def visible_campus_groups(user: dict, requested_region: Optional[str] = None) -> dict:
    scope_region = regional_admin_region(user)
    selected_region = scope_region or requested_region
    rows = await final_beneficiary_rows(user)
    grouped: Dict[str, dict] = {}
    for row in rows:
        if selected_region and selected_region != "all" and row["region"] != selected_region:
            continue
        campus = grouped.setdefault(row["campus_key"], {
            "campus_key": row["campus_key"],
            "campus": row["campus"],
            "by_region": {},
        })
        campus["by_region"].setdefault(row["region"], []).append(row)
    campus_keys = list(grouped)
    if not campus_keys:
        return grouped
    record_query = {"campus_key": {"$in": campus_keys}}
    if selected_region and selected_region != "all":
        record_query["region"] = selected_region
    records = await db.campus_disbursements.find(record_query, {"_id": 0}).to_list(5000)
    for record in records:
        campus = grouped.get(record.get("campus_key"))
        if not campus or record.get("region") not in campus["by_region"]:
            continue
        campus.setdefault("records", {}).setdefault(record["region"], {})[record["stage"]] = record
    return grouped


@api_router.get("/admin/disbursements/campuses")
async def list_campus_disbursements(
    region: Optional[str] = None,
    search: Optional[str] = None,
    user: dict = Depends(require_roles(*MANAGEMENT_ROLES)),
):
    groups = await visible_campus_groups(user, region)
    keyword = (search or "").strip().lower()
    result = []
    for group in groups.values():
        if keyword and keyword not in group["campus"].lower():
            continue
        region_records = group.get("records", {})
        stage_one = combine_campus_stage(
            [records.get(1) for records in region_records.values() if records.get(1)],
            1,
        )
        stage_two = combine_campus_stage(
            [records.get(2) for records in region_records.values() if records.get(2)],
            2,
        )
        recipient_count = sum(len(items) for items in group["by_region"].values())
        result.append({
            "campus_key": group["campus_key"],
            "campus": group["campus"],
            "recipient_count": recipient_count,
            "region_count": len(group["by_region"]),
            "regions": sorted(group["by_region"]),
            "stage_one": stage_one,
            "stage_two": stage_two,
            "proof_count": len({
                proof.get("source_id")
                for stage in (stage_one, stage_two)
                for record in group.get("records", {}).values()
                for item in record.values()
                for proof in item.get("proofs", [])
                if proof.get("source_id")
            }),
        })
    return sorted(result, key=lambda item: item["campus"].lower())


@api_router.get("/admin/disbursements/campuses/{campus_key}")
async def campus_disbursement_detail(
    campus_key: str,
    user: dict = Depends(require_roles(*MANAGEMENT_ROLES)),
):
    groups = await visible_campus_groups(user)
    group = groups.get(campus_key)
    if not group:
        raise HTTPException(status_code=404, detail="Kampus atau data pencairan tidak ditemukan.")
    region_records = group.get("records", {})
    regions = []
    for region, recipients in sorted(group["by_region"].items()):
        records = region_records.get(region, {})
        regions.append({
            "region": region,
            "recipient_count": len(recipients),
            "recipients": recipients,
            "stage_one": serialize_campus_disbursement(records.get(1), 1),
            "stage_two": serialize_campus_disbursement(records.get(2), 2),
        })
    return {
        "campus_key": campus_key,
        "campus": group["campus"],
        "regions": regions,
    }


@api_router.get("/admin/disbursements/campuses/{campus_key}/audit")
async def campus_disbursement_audit(
    campus_key: str,
    user: dict = Depends(require_roles(*MANAGEMENT_ROLES)),
):
    group = (await visible_campus_groups(user)).get(campus_key)
    if not group:
        raise HTTPException(status_code=404, detail="Kampus atau riwayat tidak ditemukan.")
    query = {"detail.campus_key": campus_key}
    scope_region = regional_admin_region(user)
    if scope_region:
        query["detail.region"] = scope_region
    return await db.beneficiary_audit_events.find(query, {"_id": 0}).sort(
        "created_at",
        -1,
    ).to_list(100)


@api_router.put("/admin/disbursements/campuses/{campus_key}/regions/{region}/stages/{stage}")
async def update_campus_disbursement(
    campus_key: str,
    region: str,
    stage: int,
    payload: DisbursementInput,
    user: dict = Depends(require_roles(*PM_MANAGERS)),
):
    if stage not in (1, 2):
        raise HTTPException(status_code=400, detail="Tahap pencairan harus 1 atau 2.")
    if payload.status not in DISBURSEMENT_STATUSES:
        raise HTTPException(status_code=400, detail="Status pencairan tidak valid.")
    if payload.amount is not None and payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Nominal pencairan harus lebih dari nol.")
    all_groups = await visible_campus_groups(user)
    group = all_groups.get(campus_key)
    recipients = (group or {}).get("by_region", {}).get(region, [])
    if not recipients:
        raise HTTPException(status_code=404, detail="Wilayah pencairan tidak ditemukan.")
    record = await ensure_campus_disbursement(
        campus_key,
        group["campus"],
        region,
        stage,
        [item["user_id"] for item in recipients],
    )
    await db.campus_disbursements.update_one(
        {"id": record["id"]},
        {
            "$set": {
                "status": payload.status,
                "amount": payload.amount,
                "disbursed_at": payload.disbursed_at,
                "reference": payload.reference.strip(),
                "notes": payload.notes.strip(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "updated_by": user["user_id"],
            }
        },
    )
    await audit_beneficiary_action(
        user,
        "update_campus_disbursement",
        detail={"campus_key": campus_key, "region": region, "stage": stage},
    )
    return await campus_disbursement_detail(campus_key, user)


async def attach_transfer_to_campus_disbursement(
    actor: dict,
    source: dict,
    transaction: dict,
    beneficiary: dict,
    account_match: str,
) -> None:
    registration = beneficiary["registration"]
    profile = beneficiary["profile"]
    campus = beneficiary_campus(profile)
    campus_key = campus_disbursement_key(campus)
    region = profile_region(profile) or "Belum diisi"
    stage = int(source["stage"])
    await ensure_campus_disbursement(
        campus_key,
        campus,
        region,
        stage,
        [registration["user_id"]],
    )
    proof = {
        "source_id": source["id"],
        "original_filename": source["original_filename"],
        "attached_at": datetime.now(timezone.utc).isoformat(),
    }
    transaction_entry = {
        "source_id": source["id"],
        "user_id": registration["user_id"],
        "name": registration.get("name") or profile.get("namaLengkap", ""),
        "nim": normalize_nim(profile.get("nim")),
        "amount": str(transaction.get("amount") or ""),
        "reference": str(transaction.get("reference") or ""),
        "account_number_masked": mask_account_number(transaction.get("account_number")),
        "account_match": account_match,
    }
    aggregate = await db.campus_disbursements.find_one(
        {"campus_key": campus_key, "region": region, "stage": stage},
        {"_id": 0},
    ) or {}
    existing_transactions = aggregate.get("transactions", [])
    if not any(
        item.get("source_id") == source["id"]
        and item.get("user_id") == registration["user_id"]
        for item in existing_transactions
    ):
        await db.campus_disbursements.update_one(
            {"campus_key": campus_key, "region": region, "stage": stage},
            {
                "$addToSet": {
                    "proofs": proof,
                    "recipient_user_ids": registration["user_id"],
                },
                "$push": {"transactions": transaction_entry},
                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()},
            },
        )
    await audit_beneficiary_action(
        actor,
        "attach_transfer_to_campus_disbursement",
        registration["user_id"],
        {"campus_key": campus_key, "region": region, "stage": stage, "source_id": source["id"]},
    )


async def get_final_beneficiary(user: dict, user_id: str) -> dict:
    await require_participant_scope(user, user_id)
    registration = await db.registrations.find_one(
        {"user_id": user_id, "status": "lolos"},
        {"_id": 0},
    )
    if not registration:
        raise HTTPException(status_code=404, detail="Penerima Manfaat tidak ditemukan.")
    profile = await db.profiles.find_one({"user_id": user_id}, {"_id": 0}) or {}
    return {"registration": registration, "profile": profile.get("data", {})}


async def ensure_disbursement(user_id: str, stage: int) -> dict:
    await db.beneficiary_disbursements.update_one(
        {"user_id": user_id, "stage": stage},
        {
            "$setOnInsert": {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "stage": stage,
                "status": "belum_diproses",
                "amount": None,
                "disbursed_at": None,
                "reference": "",
                "notes": "",
                "proofs": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        },
        upsert=True,
    )
    return await db.beneficiary_disbursements.find_one(
        {"user_id": user_id, "stage": stage},
        {"_id": 0},
    )


def serialize_disbursement(record: Optional[dict], stage: int) -> dict:
    data = record or {"stage": stage, "status": "belum_diproses", "proofs": []}
    return {
        "stage": stage,
        "status": data.get("status", "belum_diproses"),
        "amount": data.get("amount"),
        "disbursed_at": data.get("disbursed_at"),
        "reference": data.get("reference", ""),
        "notes": data.get("notes", ""),
        "proofs": data.get("proofs", []),
        "updated_at": data.get("updated_at"),
    }


async def beneficiary_view(user: dict, user_id: str) -> dict:
    beneficiary = await get_final_beneficiary(user, user_id)
    registration = beneficiary["registration"]
    profile = beneficiary["profile"]
    record = await db.beneficiary_records.find_one({"user_id": user_id}, {"_id": 0}) or {}
    stages = await db.beneficiary_disbursements.find(
        {"user_id": user_id},
        {"_id": 0},
    ).to_list(2)
    by_stage = {item.get("stage"): item for item in stages}
    return {
        "user_id": user_id,
        "name": registration.get("name") or profile.get("namaLengkap", "-"),
        "email": registration.get("email") or profile.get("email", "-"),
        "cpm_id": registration.get("cpm_id", "-"),
        "nim": profile.get("nim", "-"),
        "campus": profile.get("institusi", "-"),
        "study_program": profile.get("jurusan", "-"),
        "semester": profile.get("semester", "-"),
        "region": profile_region(profile) or "Belum diisi",
        "bank": {
            "bank_name": record.get("bank_name", ""),
            "account_number_masked": mask_account_number(
                decrypt_account_number(record.get("bank_account_cipher", ""))
            ),
            "is_recorded": bool(record.get("bank_account_cipher")),
        },
        "active_letters": record.get("active_letters", []),
        "disbursements": [
            serialize_disbursement(by_stage.get(1), 1),
            serialize_disbursement(by_stage.get(2), 2),
        ],
    }


async def create_beneficiary_review(
    actor: dict,
    source: dict,
    kind: str,
    payload: dict,
    reason: str,
) -> None:
    review = {
        "id": str(uuid.uuid4()),
        "source_id": source["id"],
        "source_type": source["source_type"],
        "stage": source.get("stage"),
        "kind": kind,
        "payload": payload,
        "reason": reason,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.beneficiary_reviews.insert_one(review)
    await audit_beneficiary_action(actor, "create_pm_review", detail={"review_id": review["id"]})


@api_router.get("/admin/beneficiaries")
async def list_beneficiaries(
    region: Optional[str] = None,
    search: Optional[str] = None,
    user: dict = Depends(require_roles(*MANAGEMENT_ROLES)),
):
    scope_region = regional_admin_region(user)
    query = {"status": "lolos"}
    query.update(await participant_scope_query(user))
    registrations = await db.registrations.find(query, {"_id": 0}).sort("created_at", -1).to_list(2000)
    user_ids = [registration["user_id"] for registration in registrations]
    profiles = await db.profiles.find(
        {"user_id": {"$in": user_ids}},
        {"_id": 0, "user_id": 1, "data": 1},
    ).to_list(2000)
    records = await db.beneficiary_records.find(
        {"user_id": {"$in": user_ids}},
        {"_id": 0},
    ).to_list(2000)
    disbursements = await db.beneficiary_disbursements.find(
        {"user_id": {"$in": user_ids}},
        {"_id": 0},
    ).to_list(4000)
    profiles_by_user = {item["user_id"]: item.get("data", {}) for item in profiles}
    records_by_user = {item["user_id"]: item for item in records}
    disbursements_by_user: Dict[str, Dict[int, dict]] = {}
    for item in disbursements:
        disbursements_by_user.setdefault(item["user_id"], {})[item["stage"]] = item
    selected_region = scope_region or region
    result = []
    for registration in registrations:
        profile = profiles_by_user.get(registration["user_id"], {})
        beneficiary_region = profile_region(profile) or "Belum diisi"
        if selected_region and selected_region != "all" and beneficiary_region != selected_region:
            continue
        record = records_by_user.get(registration["user_id"], {})
        keyword = " ".join([
            str(registration.get("name", "")),
            str(registration.get("email", "")),
            str(profile.get("nim", "")),
            str(profile.get("institusi", "")),
        ]).lower()
        if search and search.strip().lower() not in keyword:
            continue
        stages = disbursements_by_user.get(registration["user_id"], {})
        result.append({
            "user_id": registration["user_id"],
            "name": registration.get("name") or profile.get("namaLengkap", "-"),
            "email": registration.get("email") or profile.get("email", "-"),
            "cpm_id": registration.get("cpm_id", "-"),
            "nim": profile.get("nim", "-"),
            "campus": profile.get("institusi", "-"),
            "study_program": profile.get("jurusan", "-"),
            "semester": profile.get("semester", "-"),
            "region": beneficiary_region,
            "active_letter_count": len(record.get("active_letters", [])),
            "bank_recorded": bool(record.get("bank_account_cipher")),
            "stage_one": serialize_disbursement(stages.get(1), 1),
            "stage_two": serialize_disbursement(stages.get(2), 2),
        })
    return result


@api_router.get("/admin/beneficiaries/{user_id}")
async def beneficiary_detail(
    user_id: str,
    user: dict = Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return await beneficiary_view(user, user_id)


@api_router.put("/admin/beneficiaries/{user_id}/bank")
async def update_beneficiary_bank(
    user_id: str,
    payload: BeneficiaryBankInput,
    user: dict = Depends(require_roles(*PM_MANAGERS)),
):
    await get_final_beneficiary(user, user_id)
    account_number = normalize_account_number(payload.account_number)
    if account_number and not 6 <= len(account_number) <= 24:
        raise HTTPException(status_code=400, detail="Nomor rekening harus terdiri dari 6–24 digit.")
    now = datetime.now(timezone.utc).isoformat()
    update = {
        "bank_name": payload.bank_name.strip(),
        "updated_at": now,
        "updated_by": user["user_id"],
    }
    if account_number:
        update["bank_account_cipher"] = encrypt_account_number(account_number)
    await db.beneficiary_records.update_one(
        {"user_id": user_id},
        {"$set": update, "$setOnInsert": {"user_id": user_id, "active_letters": []}},
        upsert=True,
    )
    await audit_beneficiary_action(user, "update_beneficiary_bank", user_id)
    return await beneficiary_view(user, user_id)


@api_router.put("/admin/beneficiaries/{user_id}/disbursements/{stage}")
async def update_disbursement(
    user_id: str,
    stage: int,
    payload: DisbursementInput,
    user: dict = Depends(require_roles(*PM_MANAGERS)),
):
    if stage not in (1, 2):
        raise HTTPException(status_code=400, detail="Tahap pencairan harus 1 atau 2.")
    if payload.status not in DISBURSEMENT_STATUSES:
        raise HTTPException(status_code=400, detail="Status pencairan tidak valid.")
    if payload.amount is not None and payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Nominal pencairan harus lebih dari nol.")
    await get_final_beneficiary(user, user_id)
    await ensure_disbursement(user_id, stage)
    await db.beneficiary_disbursements.update_one(
        {"user_id": user_id, "stage": stage},
        {
            "$set": {
                "status": payload.status,
                "amount": payload.amount,
                "disbursed_at": payload.disbursed_at,
                "reference": payload.reference.strip(),
                "notes": payload.notes.strip(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "updated_by": user["user_id"],
            }
        },
    )
    await audit_beneficiary_action(
        user,
        "update_disbursement",
        user_id,
        {"stage": stage, "status": payload.status},
    )
    return await beneficiary_view(user, user_id)


@api_router.get("/admin/beneficiaries/{user_id}/audit")
async def beneficiary_audit(
    user_id: str,
    user: dict = Depends(require_roles(*MANAGEMENT_ROLES)),
):
    await get_final_beneficiary(user, user_id)
    return await db.beneficiary_audit_events.find(
        {"user_id": user_id},
        {"_id": 0},
    ).sort("created_at", -1).to_list(100)


@api_router.get("/admin/beneficiary-reviews")
async def list_beneficiary_reviews(
    user: dict = Depends(require_roles(*PM_MANAGERS)),
):
    return await db.beneficiary_reviews.find(
        {"status": "pending"},
        {"_id": 0},
    ).sort("created_at", -1).to_list(300)


@api_router.get("/admin/beneficiary-files/{source_id}")
async def download_beneficiary_file(
    source_id: str,
    user: dict = Depends(require_roles(*PM_MANAGERS)),
):
    source = await db.beneficiary_sources.find_one({"id": source_id}, {"_id": 0})
    if not source:
        raise HTTPException(status_code=404, detail="Berkas Penerima Manfaat tidak ditemukan.")
    data, content_type = get_object(source["storage_path"])
    headers = {"Content-Disposition": f'inline; filename="{source["original_filename"]}"'}
    await audit_beneficiary_action(user, "download_beneficiary_source", detail={"source_id": source_id})
    return StarletteResponse(
        content=data,
        media_type=source.get("content_type", content_type),
        headers=headers,
    )


async def attach_active_letter(
    actor: dict,
    source: dict,
    student: dict,
    beneficiary: dict,
) -> bool:
    registration = beneficiary["registration"]
    profile = beneficiary["profile"]
    user_id = registration["user_id"]
    letter = {
        "source_id": source["id"],
        "original_filename": source["original_filename"],
        "matched_at": datetime.now(timezone.utc).isoformat(),
        "matched_name": student.get("name", ""),
        "matched_nim": normalize_nim(student.get("nim")),
        "study_program": student.get("study_program", ""),
        "semester": student.get("semester", ""),
        "evidence": student.get("evidence", ""),
    }
    record = await db.beneficiary_records.find_one({"user_id": user_id}, {"_id": 0}) or {}
    if any(item.get("source_id") == source["id"] for item in record.get("active_letters", [])):
        return False
    await db.beneficiary_records.update_one(
        {"user_id": user_id},
        {
            "$setOnInsert": {
                "user_id": user_id,
                "active_letters": [],
            },
            "$push": {"active_letters": letter},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()},
        },
        upsert=True,
    )
    await audit_beneficiary_action(
        actor,
        "attach_active_letter",
        user_id,
        {"source_id": source["id"], "region": profile_region(profile)},
    )
    return True


@api_router.post("/admin/beneficiaries/active-letters")
async def upload_active_letters(
    files: List[UploadFile] = File(...),
    user: dict = Depends(require_roles(*PM_MANAGERS)),
):
    if not files or len(files) > 20:
        raise HTTPException(status_code=400, detail="Unggah antara 1 hingga 20 berkas surat.")
    beneficiary_index = await final_beneficiary_index()
    summary = {"uploaded": 0, "matched": 0, "duplicate": 0, "review": 0, "failed": 0}
    sources = []
    for file in files:
        filename, ext, data, content_type = await read_pm_upload(file)
        source = await store_pm_source(
            user,
            "active_letter",
            filename,
            ext,
            data,
            content_type,
        )
        summary["uploaded"] += 1
        try:
            extracted = await extract_pm_payload(
                data,
                content_type,
                user,
                PM_ACTIVE_LETTER_PROMPT,
                "surat keterangan mahasiswa aktif",
            )
            students = extracted.get("students", [])
            if not isinstance(students, list):
                students = []
            matched_user_ids = []
            regions = set()
            for raw_student in students:
                student = raw_student if isinstance(raw_student, dict) else {}
                name = normalized_name(student.get("name"))
                nim = normalize_nim(student.get("nim"))
                if not name or not nim:
                    await create_beneficiary_review(
                        user,
                        source,
                        "active_letter_incomplete",
                        student,
                        "Nama atau NIM tidak terbaca lengkap.",
                    )
                    summary["review"] += 1
                    continue
                matches = beneficiary_index.get(f"{name}|{nim}", [])
                if len(matches) != 1:
                    reason = (
                        "Mahasiswa belum berstatus lulus tahap akhir."
                        if not matches
                        else "Data nama dan NIM cocok ke lebih dari satu Penerima Manfaat."
                    )
                    await create_beneficiary_review(
                        user,
                        source,
                        "active_letter_unmatched",
                        student,
                        reason,
                    )
                    summary["review"] += 1
                    continue
                beneficiary = matches[0]
                attached = await attach_active_letter(user, source, student, beneficiary)
                if attached:
                    matched_user_ids.append(beneficiary["registration"]["user_id"])
                    regions.add(beneficiary["region"])
                    summary["matched"] += 1
                else:
                    await create_beneficiary_review(
                        user,
                        source,
                        "active_letter_duplicate",
                        student,
                        "Surat ini sudah tertempel pada Penerima Manfaat tersebut.",
                    )
                    summary["duplicate"] += 1
            status = "processed" if students else "needs_review"
            await db.beneficiary_sources.update_one(
                {"id": source["id"]},
                {
                    "$set": {
                        "status": status,
                        "extraction": {"students": students},
                        "matched_user_ids": matched_user_ids,
                        "regions": sorted(regions),
                        "processed_at": datetime.now(timezone.utc).isoformat(),
                    }
                },
            )
        except HTTPException as error:
            await db.beneficiary_sources.update_one(
                {"id": source["id"]},
                {"$set": {"status": "failed", "error": error.detail}},
            )
            await create_beneficiary_review(
                user,
                source,
                "active_letter_ocr_failed",
                {},
                str(error.detail),
            )
            summary["failed"] += 1
        sources.append({"id": source["id"], "filename": filename})
    return {"summary": summary, "sources": sources}


async def attach_transfer_transaction(
    actor: dict,
    source: dict,
    transaction: dict,
    beneficiary: dict,
) -> None:
    user_id = beneficiary["registration"]["user_id"]
    stage = int(source["stage"])
    record = await db.beneficiary_records.find_one({"user_id": user_id}, {"_id": 0}) or {}
    saved_account = decrypt_account_number(record.get("bank_account_cipher", ""))
    extracted_account = normalize_account_number(transaction.get("account_number"))
    if extracted_account and saved_account:
        account_match = "sesuai" if extracted_account == saved_account else "tidak_sesuai"
    else:
        account_match = "perlu_tinjau"
    await ensure_disbursement(user_id, stage)
    proof = {
        "source_id": source["id"],
        "original_filename": source["original_filename"],
        "account_number_masked": mask_account_number(extracted_account),
        "bank_name": str(transaction.get("bank_name") or ""),
        "transaction_status": str(transaction.get("status") or ""),
        "amount": str(transaction.get("amount") or ""),
        "reference": str(transaction.get("reference") or ""),
        "date": str(transaction.get("date") or ""),
        "account_match": account_match,
        "evidence": str(transaction.get("evidence") or ""),
        "attached_at": datetime.now(timezone.utc).isoformat(),
    }
    disbursement = await db.beneficiary_disbursements.find_one(
        {"user_id": user_id, "stage": stage},
        {"_id": 0},
    ) or {}
    if not any(item.get("source_id") == source["id"] for item in disbursement.get("proofs", [])):
        await db.beneficiary_disbursements.update_one(
            {"user_id": user_id, "stage": stage},
            {
                "$push": {"proofs": proof},
                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()},
            },
        )
    await audit_beneficiary_action(
        actor,
        "attach_transfer_proof",
        user_id,
        {"source_id": source["id"], "stage": stage, "account_match": account_match},
    )
    await attach_transfer_to_campus_disbursement(
        actor,
        source,
        transaction,
        beneficiary,
        account_match,
    )


@api_router.post("/admin/disbursements/transfer-proofs")
@api_router.post("/admin/beneficiaries/disbursement-proofs")
async def upload_disbursement_proofs(
    stage: int = Form(...),
    files: List[UploadFile] = File(...),
    user: dict = Depends(require_roles(*PM_MANAGERS)),
):
    if stage not in (1, 2):
        raise HTTPException(status_code=400, detail="Tahap pencairan harus 1 atau 2.")
    if not files or len(files) > 20:
        raise HTTPException(status_code=400, detail="Unggah antara 1 hingga 20 bukti transfer.")
    beneficiary_index = await final_beneficiary_index()
    summary = {"uploaded": 0, "matched": 0, "review": 0, "failed": 0}
    sources = []
    for file in files:
        filename, ext, data, content_type = await read_pm_upload(file)
        source = await store_pm_source(
            user,
            "transfer_proof",
            filename,
            ext,
            data,
            content_type,
            stage,
        )
        summary["uploaded"] += 1
        try:
            extracted = await extract_pm_payload(
                data,
                content_type,
                user,
                PM_TRANSFER_PROOF_PROMPT,
                "bukti transfer",
            )
            transactions = extracted.get("transactions", [])
            if not isinstance(transactions, list):
                transactions = []
            matched_user_ids = []
            regions = set()
            for raw_transaction in transactions:
                transaction = raw_transaction if isinstance(raw_transaction, dict) else {}
                name = normalized_name(transaction.get("name"))
                nim = normalize_nim(transaction.get("nim"))
                if not name or not nim:
                    await create_beneficiary_review(
                        user,
                        source,
                        "transfer_incomplete",
                        transaction,
                        "Nama atau NIM tidak cukup untuk memetakan transaksi.",
                    )
                    summary["review"] += 1
                    continue
                matches = beneficiary_index.get(f"{name}|{nim}", [])
                if len(matches) != 1:
                    reason = (
                        "Transaksi belum dapat dipetakan ke Penerima Manfaat lulus akhir."
                        if not matches
                        else "Transaksi cocok ke lebih dari satu Penerima Manfaat."
                    )
                    await create_beneficiary_review(
                        user,
                        source,
                        "transfer_unmatched",
                        transaction,
                        reason,
                    )
                    summary["review"] += 1
                    continue
                beneficiary = matches[0]
                await attach_transfer_transaction(user, source, transaction, beneficiary)
                matched_user_ids.append(beneficiary["registration"]["user_id"])
                regions.add(beneficiary["region"])
                summary["matched"] += 1
            status = "processed" if transactions else "needs_review"
            await db.beneficiary_sources.update_one(
                {"id": source["id"]},
                {
                    "$set": {
                        "status": status,
                        "extraction": {
                            "transactions": transactions,
                            "summary": extracted.get("summary", {}),
                        },
                        "matched_user_ids": matched_user_ids,
                        "regions": sorted(regions),
                        "processed_at": datetime.now(timezone.utc).isoformat(),
                    }
                },
            )
        except HTTPException as error:
            await db.beneficiary_sources.update_one(
                {"id": source["id"]},
                {"$set": {"status": "failed", "error": error.detail}},
            )
            await create_beneficiary_review(
                user,
                source,
                "transfer_ocr_failed",
                {},
                str(error.detail),
            )
            summary["failed"] += 1
        sources.append({"id": source["id"], "filename": filename})
    return {"summary": summary, "sources": sources}


@api_router.post("/admin/beneficiary-reviews/{review_id}/resolve")
async def resolve_beneficiary_review(
    review_id: str,
    payload: BeneficiaryReviewResolveInput,
    user: dict = Depends(require_roles(*PM_MANAGERS)),
):
    review = await db.beneficiary_reviews.find_one(
        {"id": review_id, "status": "pending"},
        {"_id": 0},
    )
    if not review:
        raise HTTPException(status_code=404, detail="Item tinjauan tidak ditemukan.")
    source = await db.beneficiary_sources.find_one({"id": review["source_id"]}, {"_id": 0})
    if not source:
        raise HTTPException(status_code=404, detail="Berkas sumber tidak ditemukan.")
    beneficiary = await get_final_beneficiary(user, payload.user_id)
    if source["source_type"] == "active_letter":
        await attach_active_letter(user, source, review.get("payload", {}), beneficiary)
    elif source["source_type"] == "transfer_proof":
        await attach_transfer_transaction(user, source, review.get("payload", {}), beneficiary)
    else:
        raise HTTPException(status_code=400, detail="Jenis item tinjauan tidak didukung.")
    await db.beneficiary_reviews.update_one(
        {"id": review_id},
        {
            "$set": {
                "status": "resolved",
                "resolved_user_id": payload.user_id,
                "resolved_by": user["user_id"],
                "resolved_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )
    await audit_beneficiary_action(
        user,
        "resolve_pm_review",
        payload.user_id,
        {"review_id": review_id, "source_id": source["id"]},
    )
    return {"message": "Item tinjauan berhasil dipetakan ke Penerima Manfaat."}


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
IMPORT_STAGE_CONFIG = {
    "wawancara_lolos": {
        "label": "Hasil Lolos Wawancara",
        "target_status": "verifikasi_faktual",
    },
    "kelulusan_akhir": {
        "label": "Hasil Kelulusan Akhir",
        "target_status": "lolos",
    },
}

REQUIRED_VERIFICATION_DOCUMENTS = [
    "KTP DKI Jakarta",
    "Kartu Keluarga (KK)",
    "Pas Foto 3x4",
    "Kartu Tanda Mahasiswa (KTM)",
    "KRS / KHS / Transkrip Nilai",
    "Surat Keterangan Mahasiswa Aktif",
    "SKTM / Surat Rekomendasi",
    "Surat Persetujuan Orang Tua",
    "Surat Keterangan Tidak Menerima Beasiswa Lain",
    "Pakta Integritas",
]

REQUIRED_VERIFICATION_FIELDS = {
    "namaLengkap": "Nama lengkap",
    "email": "Email",
    "nik": "NIK",
    "noTelp": "Nomor telepon",
    "alamatLengkap": "Alamat lengkap",
    "kota": "Wilayah/kota domisili",
    "provinsi": "Provinsi",
    "institusi": "Perguruan tinggi",
    "nim": "NIM",
    "jenjang": "Jenjang pendidikan",
    "jurusan": "Program studi",
    "semester": "Semester",
    "ipk": "IPK",
    "biayaPendidikanSemester": "Biaya pendidikan per semester",
}

IMPORT_FIELD_ALIASES = {
    "cpm_id": {"idcpm", "cpmid", "nomorcpm", "idcalonpenerimamanfaat"},
    "nik": {"nik", "nomorindukkependudukan"},
    "email": {"email", "emailmahasiswa", "alamatemail"},
    "name": {"nama", "namamahasiswa", "namalengkap", "peserta"},
    "campus": {"kampus", "namakampus", "perguruantinggi", "universitas"},
    "region": {"wilayah", "kota", "kotakabupaten", "domisili", "kabupaten"},
}

STATUS_RANK = {
    "draft": 0,
    "submitted": 1,
    "verifikasi": 2,
    "lolos_administrasi": 3,
    "wawancara": 4,
    "verifikasi_faktual": 5,
    "lolos": 6,
    "ditolak": -1,
}


def normalized_import_value(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def normalized_name(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def normalized_cpm(value: Any) -> str:
    match = re.search(r"CPM-MDJ/\d{4}/\d{6}", str(value or "").upper())
    return match.group(0) if match else ""


def find_import_header_row(rows: List[tuple]) -> int:
    best_index = 0
    best_score = -1
    for index, row in enumerate(rows[:10]):
        score = sum(
            normalized_import_value(value) in aliases
            for value in row
            for aliases in IMPORT_FIELD_ALIASES.values()
        )
        if score > best_score:
            best_index = index
            best_score = score
    return best_index


def deterministic_import_mapping(headers: List[str]) -> Dict[str, Optional[str]]:
    mapping = {}
    for field, aliases in IMPORT_FIELD_ALIASES.items():
        mapping[field] = next(
            (header for header in headers if normalized_import_value(header) in aliases),
            None,
        )
    return mapping


async def ai_import_mapping(headers: List[str], sample_rows: List[dict]) -> Dict[str, Optional[str]]:
    if not EMERGENT_KEY:
        return {}
    prompt = (
        "Anda membantu import hasil seleksi beasiswa Indonesia. Petakan nama kolom sumber ke field "
        "berikut: cpm_id, nik, email, name, campus, region. Gunakan hanya nama kolom yang persis "
        "ada pada daftar headers atau null jika tidak ada. Kembalikan HANYA JSON object.\n"
        f"Headers: {json.dumps(headers, ensure_ascii=False)}\n"
        f"Contoh baris: {json.dumps(sample_rows[:5], ensure_ascii=False)}"
    )
    try:
        chat = LlmChat(
            api_key=EMERGENT_KEY,
            session_id=f"selection-import-map-{uuid.uuid4()}",
            system_message="Anda adalah asisten pemetaan kolom data yang teliti.",
        ).with_model("gemini", "gemini-3.1-pro-preview")
        chunks = []
        async for event in chat.stream_message(UserMessage(text=prompt)):
            if isinstance(event, TextDelta):
                chunks.append(event.content)
            elif isinstance(event, StreamDone):
                break
        match = re.search(r"\{.*\}", "".join(chunks), flags=re.DOTALL)
        parsed = json.loads(match.group(0)) if match else {}
        return {
            field: value
            for field, value in parsed.items()
            if field in IMPORT_FIELD_ALIASES and value in headers
        }
    except Exception as error:
        logger.warning(f"AI import mapping skipped: {error}")
        return {}


async def ai_review_notes(items: List[dict]) -> Dict[int, str]:
    if not EMERGENT_KEY or not items:
        return {}
    prompt_items = [
        {
            "row_number": item["row_number"],
            "kind": item["kind"],
            "reason": item["reason"],
            "data": item["imported_data"],
        }
        for item in items[:25]
    ]
    prompt = (
        "Berikan catatan singkat Bahasa Indonesia untuk tiap data import beasiswa yang perlu ditinjau. "
        "Jangan mengubah atau menyimpulkan kecocokan peserta. Kembalikan HANYA JSON object dengan "
        "format {\"notes\":[{\"row_number\":2,\"note\":\"...\"}]}. Data: "
        f"{json.dumps(prompt_items, ensure_ascii=False)}"
    )
    try:
        chat = LlmChat(
            api_key=EMERGENT_KEY,
            session_id=f"selection-import-review-{uuid.uuid4()}",
            system_message="Anda adalah asisten pemeriksaan data seleksi beasiswa.",
        ).with_model("gemini", "gemini-3.1-pro-preview")
        chunks = []
        async for event in chat.stream_message(UserMessage(text=prompt)):
            if isinstance(event, TextDelta):
                chunks.append(event.content)
            elif isinstance(event, StreamDone):
                break
        match = re.search(r"\{.*\}", "".join(chunks), flags=re.DOTALL)
        notes = json.loads(match.group(0)).get("notes", []) if match else []
        return {int(note["row_number"]): str(note["note"]) for note in notes if note.get("note")}
    except Exception as error:
        logger.warning(f"AI import review skipped: {error}")
        return {}


async def build_participant_match_indexes(
    user: Optional[dict] = None,
) -> Dict[str, Dict[str, List[dict]]]:
    query = await participant_scope_query(user) if user else {}
    registrations = await db.registrations.find(query, {"_id": 0}).to_list(5000)
    user_ids = [registration["user_id"] for registration in registrations]
    profiles = await db.profiles.find(
        {"user_id": {"$in": user_ids}},
        {"_id": 0, "user_id": 1, "data": 1},
    ).to_list(5000)
    profile_data = {profile["user_id"]: profile.get("data", {}) for profile in profiles}
    indexes = {"cpm_id": {}, "nik": {}, "email": {}, "name_campus_region": {}}
    for registration in registrations:
        data = profile_data.get(registration["user_id"], {})
        candidate = {"registration": registration, "profile": data}
        keys = {
            "cpm_id": normalized_cpm(registration.get("cpm_id")),
            "nik": re.sub(r"\D", "", str(data.get("nik", ""))),
            "email": normalized_name(registration.get("email") or data.get("email")),
            "name_campus_region": "|".join([
                normalized_name(registration.get("name") or data.get("namaLengkap")),
                normalized_name(data.get("institusi")),
                normalized_name(data.get("kota") or data.get("provinsi")),
            ]),
        }
        for index_name, key in keys.items():
            if key:
                indexes[index_name].setdefault(key, []).append(candidate)
    return indexes


def match_imported_participant(data: dict, indexes: Dict[str, Dict[str, List[dict]]]) -> tuple:
    checks = [
        ("cpm_id", normalized_cpm(data.get("cpm_id"))),
        ("nik", re.sub(r"\D", "", str(data.get("nik", "")))),
        ("email", normalized_name(data.get("email"))),
        ("name_campus_region", "|".join([
            normalized_name(data.get("name")),
            normalized_name(data.get("campus")),
            normalized_name(data.get("region")),
        ])),
    ]
    for index_name, key in checks:
        if not key or (index_name == "name_campus_region" and key.count("|") != 2):
            continue
        candidates = indexes[index_name].get(key, [])
        if len(candidates) == 1:
            return candidates[0], index_name, None
        if len(candidates) > 1:
            return None, index_name, "Data identitas cocok ke lebih dari satu peserta."
    return None, None, None


def imported_differences(imported: dict, candidate: dict) -> List[str]:
    registration = candidate["registration"]
    profile = candidate["profile"]
    comparisons = [
        ("Nama", imported.get("name"), registration.get("name") or profile.get("namaLengkap")),
        ("Kampus", imported.get("campus"), profile.get("institusi")),
        ("Wilayah", imported.get("region"), profile.get("kota") or profile.get("provinsi")),
    ]
    return [
        label
        for label, source, saved in comparisons
        if source and saved and normalized_name(source) != normalized_name(saved)
    ]


def verification_issues(profile: dict, document_types: set, campus_names: set) -> List[str]:
    issues = [
        label
        for key, label in REQUIRED_VERIFICATION_FIELDS.items()
        if not str(profile.get(key, "")).strip()
    ]
    nik = re.sub(r"\D", "", str(profile.get("nik", "")))
    if nik and len(nik) != 16:
        issues.append("Format NIK tidak 16 digit")
    try:
        ipk = float(str(profile.get("ipk", "")).replace(",", "."))
        if not 0 <= ipk <= 4:
            issues.append("IPK di luar rentang 0 sampai 4")
    except (TypeError, ValueError):
        if profile.get("ipk"):
            issues.append("Format IPK tidak valid")
    biaya = re.sub(r"\D", "", str(profile.get("biayaPendidikanSemester", "")))
    if profile.get("biayaPendidikanSemester") and not biaya:
        issues.append("Format biaya pendidikan tidak valid")
    institution = normalized_name(profile.get("institusi"))
    if institution and institution not in campus_names:
        issues.append("Kampus belum terdaftar pada data kampus")
    missing_documents = [
        document
        for document in REQUIRED_VERIFICATION_DOCUMENTS
        if document not in document_types
    ]
    if missing_documents:
        issues.append(f"Berkas belum lengkap: {', '.join(missing_documents)}")
    return issues


async def ai_administration_recommendations(candidates: List[dict]) -> Dict[str, dict]:
    if not EMERGENT_KEY or not candidates:
        return {}
    results = {}
    for start in range(0, len(candidates), 20):
        batch = candidates[start:start + 20]
        prompt = (
            "Anda membantu verifikasi administrasi beasiswa. Data berikut sudah lulus pemeriksaan "
            "kelengkapan aturan sistem. Nilai kewajaran data administratif secara konservatif tanpa "
            "mengubah data. Kembalikan HANYA JSON {\"results\":[{\"user_id\":\"...\","
            "\"recommend\":\"recommended|review\",\"summary\":\"...\",\"issues\":[\"...\"]}]}. "
            "Gunakan recommended jika tidak ada konflik eksplisit di data yang diberikan. Jangan menebak "
            "bahwa data fiktif dari pola nama, domain email, nomor, atau alamat. Gunakan review hanya jika "
            "ada kontradiksi eksplisit. Catatan: Anda tidak memeriksa keaslian visual dokumen. Data: "
            f"{json.dumps(batch, ensure_ascii=False)}"
        )
        try:
            chat = LlmChat(
                api_key=EMERGENT_KEY,
                session_id=f"admin-verification-{uuid.uuid4()}",
                system_message="Anda adalah asisten verifikasi administrasi beasiswa yang teliti.",
            ).with_model("gemini", "gemini-3.1-pro-preview")
            chunks = []
            async for event in chat.stream_message(UserMessage(text=prompt)):
                if isinstance(event, TextDelta):
                    chunks.append(event.content)
                elif isinstance(event, StreamDone):
                    break
            match = re.search(r"\{.*\}", "".join(chunks), flags=re.DOTALL)
            parsed = json.loads(match.group(0)).get("results", []) if match else []
            for item in parsed:
                user_id = item.get("user_id")
                if user_id:
                    results[user_id] = item
        except Exception as error:
            logger.warning(f"AI administrative verification skipped: {error}")
    return results


@api_router.post("/admin/verification-recommendations/generate")
async def generate_verification_recommendations(
    user: dict = Depends(require_roles(*MANAGEMENT_ROLES)),
):
    registration_query = await participant_scope_query(user)
    registration_query["status"] = {"$in": ["submitted", "verifikasi"]}
    registrations = await db.registrations.find(
        registration_query,
        {"_id": 0},
    ).to_list(5000)
    user_ids = [registration["user_id"] for registration in registrations]
    profiles = await db.profiles.find(
        {"user_id": {"$in": user_ids}},
        {"_id": 0, "user_id": 1, "data": 1},
    ).to_list(5000)
    documents = await db.documents.find(
        {"user_id": {"$in": user_ids}, "is_deleted": {"$ne": True}},
        {"_id": 0, "user_id": 1, "doc_type": 1},
    ).to_list(100000)
    campuses = await db.campuses.find({}, {"_id": 0, "name": 1}).to_list(5000)
    profiles_by_user = {profile["user_id"]: profile.get("data", {}) for profile in profiles}
    documents_by_user = {}
    for document in documents:
        documents_by_user.setdefault(document["user_id"], set()).add(document["doc_type"])
    campus_names = {normalized_name(campus.get("name")) for campus in campuses}

    candidate_checks = []
    ai_candidates = []
    for registration in registrations:
        profile = profiles_by_user.get(registration["user_id"], {})
        document_types = documents_by_user.get(registration["user_id"], set())
        issues = verification_issues(profile, document_types, campus_names)
        candidate = {
            "user_id": registration["user_id"],
            "name": registration.get("name") or profile.get("namaLengkap", "-"),
            "cpm_id": registration.get("cpm_id", "-"),
            "profile": profile,
            "documents": sorted(document_types),
            "issues": issues,
        }
        candidate_checks.append(candidate)
        if not issues:
            ai_candidates.append(candidate)

    ai_results = await ai_administration_recommendations(ai_candidates)
    now = datetime.now(timezone.utc).isoformat()
    recommendations = []
    for candidate in candidate_checks:
        ai_result = ai_results.get(candidate["user_id"], {})
        issues = candidate["issues"] + ai_result.get("issues", [])
        is_recommended = not candidate["issues"] and ai_result.get("recommend") == "recommended"
        recommendation = {
            "id": str(uuid.uuid4()),
            "user_id": candidate["user_id"],
            "name": candidate["name"],
            "cpm_id": candidate["cpm_id"],
            "recommendation": "recommended" if is_recommended else "review",
            "approval_status": "pending",
            "score": 100 if is_recommended else max(0, 100 - len(issues) * 8),
            "issues": issues,
            "ai_summary": ai_result.get("summary") or (
                "Pemeriksaan aturan menemukan data yang perlu dilengkapi."
                if candidate["issues"]
                else "AI belum dapat memberikan rekomendasi otomatis."
            ),
            "document_count": len(candidate["documents"]),
            "region": profile_region(candidate["profile"]),
            "analyzed_at": now,
            "analyzed_by": user["user_id"],
        }
        existing = await db.verification_recommendations.find_one(
            {"user_id": candidate["user_id"]},
            {"_id": 0, "id": 1},
        )
        if existing:
            recommendation["id"] = existing["id"]
        await db.verification_recommendations.update_one(
            {"user_id": candidate["user_id"]},
            {"$set": recommendation},
            upsert=True,
        )
        recommendations.append(recommendation)

    return {
        "total": len(recommendations),
        "recommended": sum(item["recommendation"] == "recommended" for item in recommendations),
        "review": sum(item["recommendation"] == "review" for item in recommendations),
    }


@api_router.get("/admin/verification-recommendations")
async def list_verification_recommendations(
    user: dict = Depends(require_roles(*MANAGEMENT_ROLES)),
):
    query = {"approval_status": "pending"}
    scope_query = await participant_scope_query(user)
    if scope_query:
        query.update(scope_query)
    return await db.verification_recommendations.find(
        query,
        {"_id": 0},
    ).sort("analyzed_at", -1).to_list(5000)


@api_router.post("/admin/verification-recommendations/approve")
async def approve_verification_recommendations(
    payload: VerificationApprovalInput,
    user: dict = Depends(require_roles(*MANAGEMENT_ROLES)),
):
    if not payload.approve_all and not payload.recommendation_ids:
        raise HTTPException(status_code=400, detail="Pilih minimal satu rekomendasi untuk disetujui.")
    query = {"recommendation": "recommended", "approval_status": "pending"}
    scope_query = await participant_scope_query(user)
    if scope_query:
        query.update(scope_query)
    if not payload.approve_all:
        query["id"] = {"$in": payload.recommendation_ids}
    recommendations = await db.verification_recommendations.find(query, {"_id": 0}).to_list(5000)
    now = datetime.now(timezone.utc).isoformat()
    approved = 0
    for recommendation in recommendations:
        result = await db.registrations.update_one(
            {
                "user_id": recommendation["user_id"],
                "status": {"$in": ["submitted", "verifikasi"]},
            },
            {
                "$set": {"status": "lolos_administrasi", "updated_at": now},
                "$push": {
                    "history": {
                        "status": "lolos_administrasi",
                        "note": "Lolos Administrasi disetujui Admin dari rekomendasi AI.",
                        "at": now,
                    },
                },
            },
        )
        if not result.modified_count:
            continue
        await db.verification_recommendations.update_one(
            {"id": recommendation["id"]},
            {"$set": {"approval_status": "approved", "approved_at": now, "approved_by": user["user_id"]}},
        )
        await create_notification(
            recommendation["user_id"],
            "selection_progress",
            "Perkembangan seleksi diperbarui",
            "Anda dinyatakan Lolos Administrasi setelah verifikasi oleh Admin.",
        )
        approved += 1
    return {"message": "Rekomendasi berhasil disetujui.", "approved": approved}


@api_router.post("/admin/selection-imports")
async def import_selection_results(
    stage: str = Form(...),
    file: UploadFile = File(...),
    user: dict = Depends(require_roles(*MANAGEMENT_ROLES)),
):
    if stage not in IMPORT_STAGE_CONFIG:
        raise HTTPException(status_code=400, detail="Jenis hasil import tidak valid.")
    if not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="File hasil seleksi harus berformat XLSX.")
    file_data = await file.read()
    if len(file_data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Ukuran file XLSX maksimal 10MB.")
    try:
        workbook = load_workbook(io.BytesIO(file_data), read_only=True, data_only=True)
        worksheet = workbook.active
        rows = list(worksheet.iter_rows(values_only=True))
        workbook.close()
    except Exception as error:
        raise HTTPException(status_code=400, detail="File XLSX tidak dapat dibaca.") from error
    if len(rows) < 2:
        raise HTTPException(status_code=400, detail="File XLSX belum memiliki data peserta.")

    header_index = find_import_header_row(rows)
    headers = [str(value or "").strip() for value in rows[header_index]]
    if not any(headers):
        raise HTTPException(status_code=400, detail="Header kolom XLSX tidak ditemukan.")
    raw_rows = rows[header_index + 1:header_index + 1001]
    sample_rows = [
        {headers[index]: str(value or "").strip() for index, value in enumerate(row) if index < len(headers)}
        for row in raw_rows[:5]
    ]
    mapping = deterministic_import_mapping(headers)
    ai_mapping = await ai_import_mapping(headers, sample_rows)
    for field, header in ai_mapping.items():
        if not mapping.get(field):
            mapping[field] = header

    import_id = str(uuid.uuid4())
    path = f"{APP_NAME}/selection-imports/{import_id}.xlsx"
    try:
        storage_result = put_object(path, file_data, MIME_TYPES["xlsx"])
    except Exception as error:
        logger.error(f"Selection import storage failed: {error}")
        raise HTTPException(status_code=502, detail="File import belum dapat disimpan untuk audit.")

    header_positions = {header: index for index, header in enumerate(headers)}
    indexes = await build_participant_match_indexes(user)
    region_scope = regional_admin_region(user)
    target_status = IMPORT_STAGE_CONFIG[stage]["target_status"]
    summary = {"matched": 0, "updated": 0, "unchanged": 0, "review": 0, "new": 0, "invalid": 0}
    review_items = []
    now = datetime.now(timezone.utc).isoformat()

    for offset, row in enumerate(raw_rows, start=header_index + 2):
        raw_data = {
            header: str(row[index] or "").strip()
            for header, index in header_positions.items()
            if index < len(row) and row[index] not in (None, "")
        }
        if not raw_data:
            continue
        imported = {
            field: raw_data.get(header, "")
            for field, header in mapping.items()
            if header
        }
        candidate, matched_by, matching_error = match_imported_participant(imported, indexes)
        review_base = {
            "id": str(uuid.uuid4()),
            "import_id": import_id,
            "stage": stage,
            "status": "pending",
            "row_number": offset,
            "imported_data": imported,
            "raw_data": raw_data,
            "region_scope": region_scope,
            "created_at": now,
        }
        if matching_error:
            review_items.append({
                **review_base,
                "kind": "mismatch",
                "reason": matching_error,
                "differences": [],
            })
            summary["review"] += 1
            continue
        if not candidate:
            identity_values = [imported.get(key) for key in ("cpm_id", "nik", "email", "name")]
            kind = "new_participant" if any(identity_values) else "invalid"
            reason = (
                "Peserta belum ditemukan di data pendaftaran."
                if kind == "new_participant"
                else "Tidak ada data identitas yang dapat dipakai untuk mencocokkan peserta."
            )
            review_items.append({
                **review_base,
                "kind": kind,
                "reason": reason,
                "differences": [],
            })
            summary["new" if kind == "new_participant" else "invalid"] += 1
            continue

        differences = imported_differences(imported, candidate)
        if differences:
            review_items.append({
                **review_base,
                "kind": "mismatch",
                "reason": "Data import tidak sesuai dengan data pendaftaran.",
                "differences": differences,
                "matched_user_id": candidate["registration"]["user_id"],
                "matched_by": matched_by,
            })
            summary["review"] += 1
            continue

        registration = candidate["registration"]
        summary["matched"] += 1
        if STATUS_RANK.get(registration.get("status"), 0) >= STATUS_RANK[target_status]:
            summary["unchanged"] += 1
            continue
        entry = {
            "status": target_status,
            "note": f"{IMPORT_STAGE_CONFIG[stage]['label']} diimpor oleh Admin.",
            "at": now,
        }
        await db.registrations.update_one(
            {"user_id": registration["user_id"]},
            {
                "$set": {"status": target_status, "updated_at": now},
                "$push": {"history": entry},
            },
        )
        await create_notification(
            registration["user_id"],
            "selection_progress",
            "Perkembangan seleksi diperbarui",
            f"{IMPORT_STAGE_CONFIG[stage]['label']} telah diperbarui dari hasil import Admin.",
        )
        summary["updated"] += 1

    ai_notes = await ai_review_notes(review_items)
    for item in review_items:
        item["ai_note"] = ai_notes.get(item["row_number"], "")
    if review_items:
        await db.selection_import_review.insert_many([dict(item) for item in review_items])

    import_record = {
        "id": import_id,
        "stage": stage,
        "stage_label": IMPORT_STAGE_CONFIG[stage]["label"],
        "original_filename": file.filename,
        "storage_path": storage_result["path"],
        "content_type": MIME_TYPES["xlsx"],
        "size": storage_result["size"],
        "mapping": mapping,
        "summary": summary,
        "review_count": len(review_items),
        "imported_by": user["user_id"],
        "region_scope": region_scope,
        "created_at": now,
    }
    await db.selection_imports.insert_one(dict(import_record))
    return {
        "import_id": import_id,
        "stage": stage,
        "mapping": mapping,
        "summary": summary,
        "review_count": len(review_items),
    }


@api_router.get("/admin/selection-imports")
async def list_selection_imports(
    user: dict = Depends(require_roles(*MANAGEMENT_ROLES)),
):
    query = {}
    region_scope = regional_admin_region(user)
    if region_scope:
        query["region_scope"] = region_scope
    return await db.selection_imports.find(query, {"_id": 0}).sort("created_at", -1).to_list(50)


@api_router.get("/admin/selection-import-review")
async def list_selection_import_review(
    kind: Optional[str] = None,
    user: dict = Depends(require_roles(*MANAGEMENT_ROLES)),
):
    query = {"status": "pending"}
    region_scope = regional_admin_region(user)
    if region_scope:
        query["region_scope"] = region_scope
    if kind == "new":
        query["kind"] = "new_participant"
    elif kind == "review":
        query["kind"] = {"$in": ["mismatch", "invalid"]}
    return await db.selection_import_review.find(query, {"_id": 0}).sort("created_at", -1).to_list(300)


@api_router.delete("/admin/selection-import-review/{item_id}")
async def dismiss_selection_import_review(
    item_id: str,
    user: dict = Depends(require_roles(*MANAGEMENT_ROLES)),
):
    query = {"id": item_id, "status": "pending"}
    region_scope = regional_admin_region(user)
    if region_scope:
        query["region_scope"] = region_scope
    result = await db.selection_import_review.update_one(
        query,
        {"$set": {"status": "dismissed", "dismissed_at": datetime.now(timezone.utc).isoformat()}},
    )
    if not result.matched_count:
        raise HTTPException(status_code=404, detail="Data tinjauan tidak ditemukan.")
    return {"message": "Data dihapus dari daftar tinjauan."}


@api_router.get("/admin/selection-imports/{import_id}/file")
async def download_selection_import_file(
    import_id: str,
    user: dict = Depends(require_roles(*MANAGEMENT_ROLES)),
):
    record = await db.selection_imports.find_one({"id": import_id}, {"_id": 0})
    region_scope = regional_admin_region(user)
    if not record or (region_scope and record.get("region_scope") != region_scope):
        raise HTTPException(status_code=404, detail="Riwayat import tidak ditemukan.")
    data, content_type = get_object(record["storage_path"])
    headers = {"Content-Disposition": f'attachment; filename="{record["original_filename"]}"'}
    return StarletteResponse(content=data, media_type=content_type, headers=headers)


@api_router.get("/admin/stats")
async def admin_stats(
    region: Optional[str] = None,
    user: dict = Depends(require_roles(*MANAGEMENT_ROLES)),
):
    scope_region = regional_admin_region(user)
    scope_query = await participant_scope_query(user)
    all_regs = await db.registrations.find(scope_query, {"_id": 0}).to_list(5000)
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

    available_regions = sorted({
        region_name(registration)
        for registration in all_regs
        if region_name(registration) != "Belum diisi"
    })
    if scope_region:
        available_regions = [scope_region]
    regs = all_regs
    selected_region = scope_region or region or "all"
    if selected_region != "all":
        regs = [
            registration
            for registration in all_regs
            if region_name(registration) == selected_region
        ]
    total = len(regs)
    by_status = {}
    for r in regs:
        by_status[r.get("status", "draft")] = by_status.get(r.get("status", "draft"), 0) + 1
    if scope_region:
        total_students = len({registration["user_id"] for registration in regs})
        total_admins = await db.users.count_documents(
            {"role": REGIONAL_ADMIN_ROLE, "region": scope_region}
        )
    else:
        total_students = await db.users.count_documents({"role": "student"})
        total_admins = await db.users.count_documents(
            {"role": {"$in": ["admin", "super_admin", REGIONAL_ADMIN_ROLE]}}
        )
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
        "selected_region": selected_region,
    }


@api_router.get("/admin/participants")
async def list_participants(
    status: Optional[str] = None,
    search: Optional[str] = None,
    region: Optional[str] = None,
    user: dict = Depends(require_roles(*MANAGEMENT_ROLES)),
):
    scope_region = regional_admin_region(user)
    query = await participant_scope_query(user)
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
            "nim": pdata.get("nim", "-"),
            "jurusan": pdata.get("jurusan", "-"),
            "semester": pdata.get("semester", "-"),
            "ipk": pdata.get("ipk", "-"),
            "biaya_pendidikan_semester": pdata.get("biayaPendidikanSemester", "-"),
            "wilayah": pdata.get("kota") or pdata.get("provinsi") or "-",
            "provinsi": pdata.get("provinsi", "-"),
            "phone": pdata.get("noTelp", "-"),
            "doc_count": doc_count,
        }
        selected_region = scope_region or region
        if selected_region and item["wilayah"] != selected_region:
            continue
        if search:
            s = search.lower()
            if s not in (r.get("name", "").lower() + r.get("email", "").lower() + pdata.get("institusi", "").lower()):
                continue
        result.append(item)
    return result


@api_router.get("/admin/participants/export.xlsx")
async def export_participants_excel(
    status: Optional[str] = None,
    search: Optional[str] = None,
    region: Optional[str] = None,
    user: dict = Depends(require_roles(*MANAGEMENT_ROLES)),
):
    participants = await list_participants(status, search, region, user)
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Data Peserta MDJ"
    headers = [
        "No.",
        "Nama",
        "Email",
        "ID CPM",
        "Kampus",
        "NIM",
        "Jenjang",
        "Jurusan",
        "Semester",
        "IPK",
        "Biaya Pendidikan / Semester (Rp)",
        "Wilayah",
        "Provinsi",
        "Nomor Telepon",
        "Dokumen Diunggah",
        "Status Pendaftaran",
        "Tanggal Daftar",
    ]
    worksheet.append(headers)
    header_fill = PatternFill("solid", fgColor="0B6B3A")
    for cell in worksheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill

    for index, participant in enumerate(participants, start=1):
        worksheet.append([
            index,
            participant.get("name", "-"),
            participant.get("email", "-"),
            participant.get("cpm_id", "-"),
            participant.get("institusi", "-"),
            participant.get("nim", "-"),
            participant.get("jenjang", "-"),
            participant.get("jurusan", "-"),
            participant.get("semester", "-"),
            participant.get("ipk", "-"),
            participant.get("biaya_pendidikan_semester", "-"),
            participant.get("wilayah", "-"),
            participant.get("provinsi", "-"),
            participant.get("phone", "-"),
            participant.get("doc_count", 0),
            STATUS_LABELS.get(participant.get("status"), participant.get("status", "-")),
            participant.get("created_at", "-"),
        ])

    widths = [6, 28, 34, 24, 34, 18, 12, 24, 12, 10, 30, 20, 16, 20, 18, 28, 24]
    for index, width in enumerate(widths, start=1):
        worksheet.column_dimensions[chr(64 + index)].width = width
    worksheet.freeze_panes = "A2"

    stream = io.BytesIO()
    workbook.save(stream)
    stream.seek(0)
    filename = f"data-peserta-mdj-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.xlsx"
    headers_response = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers_response,
    )


@api_router.post("/admin/demo-students/seed")
async def seed_demo_students(
    user: dict = Depends(require_roles("super_admin")),
):
    seed_batch = "mdj-student-sample-2026"
    campuses = await db.campuses.find({}, {"_id": 0, "id": 1, "name": 1}).to_list(5000)
    if not campuses:
        raise HTTPException(status_code=400, detail="Impor data kampus sebelum membuat data uji.")

    statuses = (
        ["lolos"] * 12
        + ["submitted"] * 8
        + ["verifikasi"] * 8
        + ["lolos_administrasi"] * 7
        + ["wawancara"] * 6
        + ["verifikasi_faktual"] * 5
        + ["ditolak"] * 4
    )
    regions = [
        "Jakarta Pusat",
        "Jakarta Utara",
        "Jakarta Barat",
        "Jakarta Selatan",
        "Jakarta Timur",
        "Kepulauan Seribu",
    ]
    majors = [
        "Ilmu Komputer",
        "Akuntansi",
        "Manajemen",
        "Ilmu Komunikasi",
        "Kesehatan Masyarakat",
        "Teknik Informatika",
    ]
    first_names = [
        "Alya", "Bagas", "Citra", "Dimas", "Erika", "Fajar", "Gita", "Hafiz", "Indah", "Jihan",
    ]
    last_names = ["Pratama", "Lestari", "Saputra", "Permata", "Nugroho"]
    generator = random.Random(20260912)
    generator.shuffle(statuses)
    generator.shuffle(campuses)
    for region_index in range(len(regions)):
        if statuses[region_index] == "lolos":
            continue
        passed_index = statuses.index("lolos", len(regions))
        statuses[region_index], statuses[passed_index] = statuses[passed_index], statuses[region_index]

    created = 0
    skipped = 0
    by_status = {}
    for index in range(50):
        user_id = f"student_uji_mdj_{index + 1:03d}"
        existing = await db.registrations.find_one({"user_id": user_id}, {"_id": 0, "id": 1})
        if existing:
            await db.registrations.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "status": statuses[index],
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    },
                },
            )
            by_status[statuses[index]] = by_status.get(statuses[index], 0) + 1
            skipped += 1
            continue

        status = statuses[index]
        region = regions[index % len(regions)]
        campus = campuses[index % len(campuses)]
        name = f"{first_names[index % len(first_names)]} {last_names[index % len(last_names)]}"
        email = f"uji.mdj.{index + 1:03d}@contoh.invalid"
        created_at = datetime(2026, 8, 1, tzinfo=timezone.utc) + timedelta(days=index)
        timestamp = created_at.isoformat()
        user_record = await db.users.find_one({"user_id": user_id}, {"_id": 0, "user_id": 1})
        if not user_record:
            await db.users.insert_one({
                "user_id": user_id,
                "email": email,
                "password_hash": hash_password(secrets.token_urlsafe(32)),
                "name": name,
                "role": "student",
                "auth_provider": "demo_seed",
                "is_active": True,
                "is_test_data": True,
                "seed_batch": seed_batch,
                "created_at": timestamp,
            })

        profile = {
            "namaLengkap": name,
            "email": email,
            "noTelp": f"+62812{index + 1000000:07d}",
            "institusi": campus["name"],
            "jurusan": majors[index % len(majors)],
            "jenjang": "S1",
            "semester": str((index % 8) + 1),
            "ipk": f"{3.10 + ((index * 7) % 80) / 100:.2f}",
            "biayaPendidikanSemester": str(2500000 + (index % 7) * 500000),
            "kota": region,
            "provinsi": "DKI Jakarta",
        }
        await db.profiles.update_one(
            {"user_id": user_id},
            {"$set": {"data": profile, "updated_at": timestamp, "is_test_data": True}},
            upsert=True,
        )
        cpm_id = await create_cpm_id(timestamp)
        registration = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": name,
            "email": email,
            "category": "Mahasiswa Sarjana (S1)",
            "status": status,
            "cpm_id": cpm_id,
            "history": [{"status": status, "note": "Data uji dibuat", "at": timestamp}],
            "created_at": timestamp,
            "submitted_at": timestamp,
            "updated_at": timestamp,
            "is_test_data": True,
            "seed_batch": seed_batch,
        }
        await db.registrations.insert_one(registration)
        created += 1
        by_status[status] = by_status.get(status, 0) + 1

    return {
        "message": "Data uji mahasiswa berhasil disiapkan.",
        "created": created,
        "skipped": skipped,
        "total": created + skipped,
        "by_status": by_status,
        "regions": regions,
    }


@api_router.get("/admin/participants/{user_id}")
async def participant_detail(
    user_id: str,
    user: dict = Depends(require_roles(*MANAGEMENT_ROLES)),
):
    await require_participant_scope(user, user_id)
    reg = await db.registrations.find_one({"user_id": user_id}, {"_id": 0})
    if not reg:
        raise HTTPException(status_code=404, detail="Pendaftar tidak ditemukan")
    profile = await db.profiles.find_one({"user_id": user_id}, {"_id": 0})
    docs = await db.documents.find({"user_id": user_id, "is_deleted": False}, {"_id": 0}).to_list(200)
    account = await db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
    for d in docs:
        d["url"] = f"/api/files/{d['storage_path']}"
    return {"registration": reg or {}, "profile": (profile or {}).get("data", {}),
            "documents": docs, "account": account or {}}


@api_router.put("/admin/participants/{user_id}/status")
async def update_participant_status(user_id: str, payload: StatusUpdateInput,
                                    user: dict = Depends(require_roles(*MANAGEMENT_ROLES))):
    if payload.status not in REG_STATUSES:
        raise HTTPException(status_code=400, detail="Status tidak valid")
    await require_participant_scope(user, user_id)
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
async def list_users(
    role: Optional[str] = None,
    user: dict = Depends(require_roles("admin", "super_admin")),
):
    query = {}
    if user.get("role") == "admin":
        query["role"] = REGIONAL_ADMIN_ROLE
    elif role and role != "all":
        query["role"] = role
    users = await db.users.find(query, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(2000)
    return users


@api_router.post("/admin/users")
async def create_admin(
    payload: CreateAdminInput,
    user: dict = Depends(require_roles("admin", "super_admin")),
):
    is_provincial_admin = user.get("role") == "admin"
    allowed_roles = [REGIONAL_ADMIN_ROLE] if is_provincial_admin else [
        "admin",
        "super_admin",
        REGIONAL_ADMIN_ROLE,
    ]
    if payload.role not in allowed_roles:
        raise HTTPException(status_code=400, detail="Role tidak valid")
    region = str(payload.region or "").strip()
    if payload.role == REGIONAL_ADMIN_ROLE and region not in DKI_REGIONS:
        raise HTTPException(status_code=400, detail="Wilayah Admin Wilayah wajib dipilih.")
    if payload.role != REGIONAL_ADMIN_ROLE:
        region = None
    email = payload.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email sudah terdaftar")
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    doc = {
        "user_id": user_id, "email": email, "password_hash": hash_password(payload.password),
        "name": payload.name, "role": payload.role, "auth_provider": "password",
        "nik": None, "phone": None, "picture": None, "is_active": True,
        "region": region,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(doc)
    return clean_user(doc)


@api_router.put("/admin/users/{user_id}")
async def toggle_user(
    user_id: str,
    payload: UserToggleInput,
    user: dict = Depends(require_roles("admin", "super_admin")),
):
    if user_id == user["user_id"]:
        raise HTTPException(status_code=400, detail="Tidak dapat menonaktifkan akun sendiri")
    target = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not target or not can_manage_admin_account(user, target):
        raise HTTPException(status_code=404, detail="Akun admin tidak ditemukan")
    await db.users.update_one({"user_id": user_id}, {"$set": {"is_active": payload.is_active}})
    return {"message": "Status akun diperbarui"}


@api_router.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: str,
    user: dict = Depends(require_roles("admin", "super_admin")),
):
    target = await db.users.find_one({"user_id": user_id})
    if not target or not can_manage_admin_account(user, target):
        raise HTTPException(status_code=404, detail="Akun admin tidak ditemukan")
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
    await db.selection_imports.create_index("id", unique=True)
    await db.selection_import_review.create_index([("status", 1), ("created_at", -1)])
    await db.verification_recommendations.create_index("user_id", unique=True)
    await db.verification_recommendations.create_index([("approval_status", 1), ("analyzed_at", -1)])
    await db.beneficiary_records.create_index("user_id", unique=True)
    await db.beneficiary_disbursements.create_index([("user_id", 1), ("stage", 1)], unique=True)
    await db.beneficiary_sources.create_index("id", unique=True)
    await db.beneficiary_sources.create_index([("source_type", 1), ("created_at", -1)])
    await db.beneficiary_reviews.create_index([("status", 1), ("created_at", -1)])
    await db.beneficiary_audit_events.create_index([("user_id", 1), ("created_at", -1)])
    await db.campus_disbursements.create_index(
        [("campus_key", 1), ("region", 1), ("stage", 1)],
        unique=True,
    )
    await db.campus_disbursements.create_index([("region", 1), ("stage", 1)])
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
            "name": "Admin Provinsi MDJ",
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
