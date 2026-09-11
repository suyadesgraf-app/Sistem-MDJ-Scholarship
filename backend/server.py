from dotenv import load_dotenv
from pathlib import Path
import os

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, UploadFile, File, Form, Query, Header
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response as StarletteResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import logging
import uuid
import jwt
import bcrypt
import requests

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
    await db.profiles.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"data": payload.data, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return {"message": "Profil disimpan", "data": payload.data}


# ---------------------------------------------------------------------------
# Registration (student)
# ---------------------------------------------------------------------------
@api_router.get("/registration")
async def get_registration(user: dict = Depends(get_current_user)):
    reg = await db.registrations.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return reg or {}


@api_router.post("/registration")
async def submit_registration(payload: RegistrationInput, user: dict = Depends(get_current_user)):
    status = "submitted" if payload.action == "submit" else "draft"
    existing = await db.registrations.find_one({"user_id": user["user_id"]})
    now = datetime.now(timezone.utc).isoformat()
    if existing:
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
        "history": [{"status": status, "note": "Pendaftaran dibuat", "at": now}],
        "created_at": now, "submitted_at": now if status == "submitted" else None, "updated_at": now,
    }
    await db.registrations.insert_one(reg)
    reg.pop("_id", None)
    return reg


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------
@api_router.post("/documents")
async def upload_document(doc_type: str = Form(...), file: UploadFile = File(...),
                          user: dict = Depends(get_current_user)):
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else "bin"
    content_type = file.content_type or MIME_TYPES.get(ext, "application/octet-stream")
    path = f"{APP_NAME}/uploads/{user['user_id']}/{uuid.uuid4()}.{ext}"
    data = await file.read()
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


@api_router.get("/files/{path:path}")
async def download_file(path: str, request: Request, auth: str = Query(None)):
    token = request.cookies.get("access_token") or request.cookies.get("session_token") or auth
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token or not await resolve_user_from_token(token):
        raise HTTPException(status_code=401, detail="Not authenticated")
    record = await db.documents.find_one({"storage_path": path, "is_deleted": False}, {"_id": 0})
    if not record:
        record = await db.site_files.find_one({"storage_path": path, "is_deleted": False}, {"_id": 0})
    data, content_type = get_object(path)
    return StarletteResponse(content=data, media_type=(record or {}).get("content_type", content_type))


# ---------------------------------------------------------------------------
# Site content (public + super admin)
# ---------------------------------------------------------------------------
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
    await db.site_content.update_one(
        {"key": "main"},
        {"$set": {**payload.content, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    content = await db.site_content.find_one({"key": "main"}, {"_id": 0})
    content.pop("key", None)
    return content


@api_router.post("/site/banner")
async def upload_banner(file: UploadFile = File(...), user: dict = Depends(require_roles("super_admin"))):
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else "png"
    content_type = file.content_type or MIME_TYPES.get(ext, "image/png")
    path = f"{APP_NAME}/site/banner_{uuid.uuid4().hex[:8]}.{ext}"
    data = await file.read()
    result = put_object(path, data, content_type)
    await db.site_files.insert_one({
        "storage_path": result["path"], "content_type": content_type,
        "is_deleted": False, "created_at": datetime.now(timezone.utc).isoformat(),
    })
    banner_url = f"/api/files/{result['path']}"
    await db.site_content.update_one({"key": "main"}, {"$set": {"banner_url": banner_url}}, upsert=True)
    return {"banner_url": banner_url, "storage_path": result["path"]}


# ---------------------------------------------------------------------------
# Admin: participants management
# ---------------------------------------------------------------------------
@api_router.get("/admin/stats")
async def admin_stats(user: dict = Depends(require_roles("admin", "super_admin"))):
    regs = await db.registrations.find({}, {"_id": 0}).to_list(5000)
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
    return {
        "total_registrations": total, "total_students": total_students, "total_admins": total_admins,
        "by_status": by_status, "trend": trend_list,
        "verified": by_status.get("lolos", 0),
        "pending": by_status.get("submitted", 0) + by_status.get("verifikasi", 0),
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
    await db.documents.create_index("user_id")
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
        if exists:
            continue
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
