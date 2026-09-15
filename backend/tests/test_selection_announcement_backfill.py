"""Iter34: Selection-announcement late-status BACKFILL via GET /student/selection-announcements/pending.

Reproduces the CPM-MDJ/2026/000062 race: a Published campaign exists BEFORE the student's
registration status flips to a selection-result status, so the student is not among the
original recipients. The pending endpoint must backfill safely (create notif, flag reg)
and remain idempotent + category-scoped.

All temp users/regs/notifications/campaigns are cleaned up on teardown. The real published
campaign (id=1722585f-6260-4aa5-a959-da1d30fe0143) is NEVER touched, and the real student
CPM-MDJ/2026/000062 is never mutated.
"""
import os
import uuid
import bcrypt
import requests
import pytest
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

PROTECTED_CAMPAIGN_ID = "1722585f-6260-4aa5-a959-da1d30fe0143"
PROTECTED_STUDENT_USER_IDS = set()  # will be discovered at runtime
TAG = "TEST_iter34_backfill"


# ---- helpers ----
def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login failed {email}: {r.status_code} {r.text}"
    return r.json()["token"]


def _hdr(t):
    return {"Authorization": f"Bearer {t}"}


def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


@pytest.fixture(scope="module")
def mongo():
    c = MongoClient(MONGO_URL)
    yield c[DB_NAME]
    c.close()


@pytest.fixture(scope="module")
def protected_snapshot(mongo):
    """Snapshot the real published campaign + real student registration so we can assert non-mutation."""
    camp = mongo.selection_announcements.find_one({"id": PROTECTED_CAMPAIGN_ID}, {"_id": 0})
    real_reg = mongo.registrations.find_one({"registration_number": "CPM-MDJ/2026/000062"}, {"_id": 0})
    if real_reg:
        PROTECTED_STUDENT_USER_IDS.add(real_reg["user_id"])
    yield {"campaign": camp, "reg": real_reg}


def _mk_user(mongo, category, status, published_flag=False):
    """Create a temp student user + registration. Registration timestamps are AFTER campaign published_at."""
    uid = str(uuid.uuid4())
    email = f"test_iter34_{uuid.uuid4().hex[:8]}@contoh.invalid"
    password = "TestPass123!"
    hp = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    now = _iso(datetime.now(timezone.utc))
    mongo.users.insert_one({
        "id": uid, "user_id": uid, "email": email, "name": f"TEST34 {status}",
        "role": "student", "is_active": True, "password_hash": hp,
        "created_at": now, "test_tag": TAG,
    })
    reg_doc = {
        "id": str(uuid.uuid4()), "user_id": uid, "email": email,
        "name": f"TEST34 {status}", "category": category,
        "status": status, "created_at": now, "test_tag": TAG,
    }
    if published_flag:
        reg_doc["is_announcement_published"] = True
    mongo.registrations.insert_one(reg_doc)
    return {"user_id": uid, "email": email, "password": password, "category": category, "status": status}


def _mk_campaign(mongo, category, published_at=None):
    cid = str(uuid.uuid4())
    # Use far-future published_at so this test campaign wins the sort over any
    # pre-existing real Published campaign (e.g., the protected 1722585f...
    # campaign published 2026-09-15).
    published_at = published_at or _iso(datetime(2099, 1, 1, tzinfo=timezone.utc))
    mongo.selection_announcements.insert_one({
        "id": cid,
        "title": f"TEST34 Pengumuman Hasil Seleksi Berkas {category}",
        "message": "Silakan lihat hasil seleksi berkas Anda.",
        "category": category,
        "status_publikasi": "Published",
        "published_at": published_at,
        "created_at": published_at,
        "passed_count": 0,
        "failed_count": 0,
        "recipient_count": 0,
        "late_recipient_count": 0,
        "test_tag": TAG,
    })
    return cid


@pytest.fixture
def cleanup(mongo):
    created = {"user_ids": [], "campaign_ids": []}
    yield created
    if created["user_ids"]:
        uids = created["user_ids"]
        # sanity: never touch protected users
        assert not (set(uids) & PROTECTED_STUDENT_USER_IDS)
        mongo.users.delete_many({"user_id": {"$in": uids}})
        mongo.registrations.delete_many({"user_id": {"$in": uids}})
        mongo.notifications.delete_many({"user_id": {"$in": uids}})
        mongo.sessions.delete_many({"user_id": {"$in": uids}})
        mongo.profiles.delete_many({"user_id": {"$in": uids}})
    if created["campaign_ids"]:
        # never touch protected campaign
        cids = [c for c in created["campaign_ids"] if c != PROTECTED_CAMPAIGN_ID]
        mongo.selection_announcements.delete_many({"id": {"$in": cids}})
    # global tag sweep as safety net
    mongo.users.delete_many({"test_tag": TAG})
    mongo.registrations.delete_many({"test_tag": TAG})
    mongo.notifications.delete_many({"category": {"$regex": "^TEST34_"}})
    mongo.selection_announcements.delete_many({"test_tag": TAG})


# ---- 1. backfill "all" campaign for late passed student ----
class TestBackfillAllCampaign:
    def test_late_passed_gets_notif_and_flag_and_idempotent(self, mongo, cleanup, protected_snapshot):
        cid = _mk_campaign(mongo, "all")
        cleanup["campaign_ids"].append(cid)
        u = _mk_user(mongo, category="TEST34_KAT_A", status="lolos_administrasi")
        cleanup["user_ids"].append(u["user_id"])

        tok = _login(u["email"], u["password"])
        # first pending call → should backfill
        r1 = requests.get(f"{API}/student/selection-announcements/pending", headers=_hdr(tok), timeout=30)
        assert r1.status_code == 200
        ann = r1.json()["announcement"]
        assert ann is not None, "expected backfilled notification"
        assert ann["type"] == "selection_result"
        assert ann["result"] == "passed"
        assert ann["announcement_id"] == cid
        assert ann["is_popup_seen"] is False
        assert ann["is_read"] is False
        # no mongo _id leaked
        assert "_id" not in ann
        first_notif_id = ann["id"]

        # registration flagged
        reg = mongo.registrations.find_one({"user_id": u["user_id"]})
        assert reg.get("is_announcement_published") is True
        assert reg.get("selection_announcement_id") == cid
        assert "selection_announcement_published_at" in reg

        # second call must NOT create duplicate
        r2 = requests.get(f"{API}/student/selection-announcements/pending", headers=_hdr(tok), timeout=30)
        assert r2.status_code == 200
        ann2 = r2.json()["announcement"]
        assert ann2 is not None
        assert ann2["id"] == first_notif_id
        notif_count = mongo.notifications.count_documents(
            {"user_id": u["user_id"], "type": "selection_result"}
        )
        assert notif_count == 1

        # POST seen -> pending null
        s = requests.post(
            f"{API}/student/selection-announcements/{first_notif_id}/seen",
            headers=_hdr(tok), timeout=30,
        )
        assert s.status_code == 200
        r3 = requests.get(f"{API}/student/selection-announcements/pending", headers=_hdr(tok), timeout=30)
        assert r3.status_code == 200
        assert r3.json()["announcement"] is None

        # late_recipient_count incremented on the campaign
        camp = mongo.selection_announcements.find_one({"id": cid})
        assert camp.get("late_recipient_count", 0) >= 1

    def test_late_failed_gets_failed_result(self, mongo, cleanup):
        cid = _mk_campaign(mongo, "all")
        cleanup["campaign_ids"].append(cid)
        u = _mk_user(mongo, category="TEST34_KAT_B", status="ditolak")
        cleanup["user_ids"].append(u["user_id"])
        tok = _login(u["email"], u["password"])
        r = requests.get(f"{API}/student/selection-announcements/pending", headers=_hdr(tok), timeout=30)
        assert r.status_code == 200
        ann = r.json()["announcement"]
        assert ann is not None
        assert ann["result"] == "failed"
        assert ann["announcement_id"] == cid


# ---- 2. category-specific isolation ----
class TestCategoryIsolation:
    def test_category_specific_campaign_only_backfills_matching(self, mongo, cleanup):
        cat_match = "TEST34_KAT_MATCH"
        cat_other = "TEST34_KAT_OTHER"
        cid = _mk_campaign(mongo, cat_match)
        cleanup["campaign_ids"].append(cid)

        u_match = _mk_user(mongo, category=cat_match, status="lolos_administrasi")
        u_other = _mk_user(mongo, category=cat_other, status="lolos_administrasi")
        cleanup["user_ids"] += [u_match["user_id"], u_other["user_id"]]

        tok_m = _login(u_match["email"], u_match["password"])
        tok_o = _login(u_other["email"], u_other["password"])

        r_m = requests.get(f"{API}/student/selection-announcements/pending", headers=_hdr(tok_m), timeout=30)
        r_o = requests.get(f"{API}/student/selection-announcements/pending", headers=_hdr(tok_o), timeout=30)

        assert r_m.json()["announcement"] is not None
        assert r_m.json()["announcement"]["announcement_id"] == cid
        # Other-category student may still be backfilled by the pre-existing
        # real "all" campaign in this env, but they MUST NOT receive our
        # category-specific test campaign.
        other_ann = r_o.json()["announcement"]
        if other_ann is not None:
            assert other_ann["announcement_id"] != cid, (
                "category-specific campaign leaked to a different-category student"
            )

        # ensure other user's registration was NOT tagged with OUR campaign id
        reg_o = mongo.registrations.find_one({"user_id": u_other["user_id"]})
        assert reg_o.get("selection_announcement_id") != cid


# ---- 3. non-eligible cases ----
class TestNonEligibleCases:
    def test_already_published_flag_skips_backfill(self, mongo, cleanup):
        cid = _mk_campaign(mongo, "all")
        cleanup["campaign_ids"].append(cid)
        u = _mk_user(mongo, category="TEST34_KAT_ALREADY", status="lolos_administrasi",
                     published_flag=True)
        cleanup["user_ids"].append(u["user_id"])
        tok = _login(u["email"], u["password"])
        r = requests.get(f"{API}/student/selection-announcements/pending", headers=_hdr(tok), timeout=30)
        assert r.status_code == 200
        # no existing unseen notif, and backfill must be skipped since flag=True
        assert r.json()["announcement"] is None
        # no notif inserted
        assert mongo.notifications.count_documents(
            {"user_id": u["user_id"], "type": "selection_result"}
        ) == 0

    def test_non_final_status_skips_backfill(self, mongo, cleanup):
        cid = _mk_campaign(mongo, "all")
        cleanup["campaign_ids"].append(cid)
        u = _mk_user(mongo, category="TEST34_KAT_NON_FINAL", status="submitted")
        cleanup["user_ids"].append(u["user_id"])
        tok = _login(u["email"], u["password"])
        r = requests.get(f"{API}/student/selection-announcements/pending", headers=_hdr(tok), timeout=30)
        assert r.status_code == 200
        assert r.json()["announcement"] is None
        assert mongo.notifications.count_documents(
            {"user_id": u["user_id"], "type": "selection_result"}
        ) == 0

    def test_no_published_campaign_no_backfill(self, mongo, cleanup):
        # Skipped in envs where a real Published "all" campaign exists — that
        # campaign will always match any final-status student. We keep the
        # test as documentation of intent.
        real_pub = mongo.selection_announcements.find_one(
            {"status_publikasi": "Published", "category": "all"}
        )
        if real_pub:
            pytest.skip("Real Published 'all' campaign exists; test invariant not applicable")
        # student with final status but only a DRAFT campaign for their category
        cat = "TEST34_KAT_NOPUB"
        cid = str(uuid.uuid4())
        mongo.selection_announcements.insert_one({
            "id": cid, "title": "draft", "message": "draft", "category": cat,
            "status_publikasi": "Draft",
            "published_at": _iso(datetime.now(timezone.utc)),
            "created_at": _iso(datetime.now(timezone.utc)),
            "test_tag": TAG,
        })
        cleanup["campaign_ids"].append(cid)
        u = _mk_user(mongo, category=cat, status="lolos_administrasi")
        cleanup["user_ids"].append(u["user_id"])
        tok = _login(u["email"], u["password"])
        r = requests.get(f"{API}/student/selection-announcements/pending", headers=_hdr(tok), timeout=30)
        assert r.status_code == 200
        assert r.json()["announcement"] is None
        assert mongo.notifications.count_documents(
            {"user_id": u["user_id"], "type": "selection_result"}
        ) == 0


# ---- 4. protected data untouched ----
class TestProtectedDataUntouched:
    def test_real_campaign_still_published(self, mongo, protected_snapshot):
        camp_before = protected_snapshot["campaign"]
        if not camp_before:
            pytest.skip("Real protected campaign not present in this env")
        camp_after = mongo.selection_announcements.find_one({"id": PROTECTED_CAMPAIGN_ID}, {"_id": 0})
        assert camp_after is not None
        assert camp_after.get("status_publikasi") == camp_before.get("status_publikasi")
        assert camp_after.get("category") == camp_before.get("category")

    def test_real_student_registration_untouched(self, mongo, protected_snapshot):
        reg_before = protected_snapshot["reg"]
        if not reg_before:
            pytest.skip("Real student CPM-MDJ/2026/000062 not present in this env")
        reg_after = mongo.registrations.find_one(
            {"registration_number": "CPM-MDJ/2026/000062"}, {"_id": 0}
        )
        assert reg_after is not None
        # We only care about the announcement-flag lineage; leave other fields alone
        assert reg_after.get("status") == reg_before.get("status")
        assert reg_after.get("user_id") == reg_before.get("user_id")
