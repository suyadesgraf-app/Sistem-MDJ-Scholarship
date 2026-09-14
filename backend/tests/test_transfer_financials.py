"""
Tests for the new Nominal Transfer / paid_student_count / payment_assessment feature.

Covers:
- API GET /api/admin/disbursements/campuses -> stage_one/stage_two contain
  transfer_amount, expected_amount, paid_student_count, recipient_count,
  payment_assessment, payment_difference.
- API GET /api/admin/disbursements/campuses/{key} -> region rows expose same fields.
- No transactions => payment_assessment == 'belum_ada_transfer', no false short/excess.
- Direct unit-style tests on refresh_campus_transfer_financials for
  sesuai (Rp3.000.000), sesuai (Rp3.000.101 unique-code), kurang (Rp2.999.999),
  lebih (Rp3.000.102) and multi-transaction aggregation.
- paid_student_count capped by recipient_count.
"""
import asyncio
import os
import sys
import uuid
import pytest
import pytest_asyncio
import requests

# Import backend module to reach db + refresh function
BACKEND_DIR = "/app/backend"
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import server  # noqa: E402
from server import (  # noqa: E402
    TRANSFER_AMOUNT_PER_STUDENT,
    UNIQUE_TRANSFER_TOLERANCE,
    parse_transfer_amount,
    refresh_campus_transfer_financials,
)
from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402


def _fresh_db():
    """Return a motor db bound to the CURRENT running loop and patch server.db.

    pytest-asyncio creates a new event loop per test; the module-level
    server.db motor client is bound to the first loop and dies afterwards.
    """
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    fresh = client[os.environ["DB_NAME"]]
    server.db = fresh
    return fresh

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL", "https://sistem-registrasi.preview.emergentagent.com"
).rstrip("/")
API = f"{BASE_URL}/api"

PROV_EMAIL = "admin.mdj@baznasbazisdki.id"
PROV_PASS = "AdminMDJ2026!"


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()["token"]


def _h(t):
    return {"Authorization": f"Bearer {t}"}


@pytest.fixture(scope="module")
def prov_token():
    return _login(PROV_EMAIL, PROV_PASS)


# ---------------------------------------------------------------------------
# API contract: new financial fields exposed on list + detail
# ---------------------------------------------------------------------------
FINANCIAL_FIELDS = (
    "transfer_amount",
    "expected_amount",
    "paid_student_count",
    "recipient_count",
    "payment_assessment",
    "payment_difference",
)


class TestFinancialFieldsExposure:
    def test_list_stages_have_financial_fields(self, prov_token):
        r = requests.get(
            f"{API}/admin/disbursements/campuses", headers=_h(prov_token), timeout=30
        )
        assert r.status_code == 200, r.text
        rows = r.json()
        assert rows, "expected at least 1 campus row"
        row = rows[0]
        for stage_key in ("stage_one", "stage_two"):
            stage = row[stage_key]
            for field in FINANCIAL_FIELDS:
                assert field in stage, f"{stage_key} missing {field}"
            # No transactions on default => cannot be false 'kurang'/'lebih'
            if not stage.get("transactions") and stage.get("transfer_amount") in (None, 0):
                # When combined across regions, could be 'belum_ada_transfer' or
                # 'bervariasi' if one region has a transfer while another doesn't.
                assert stage["payment_assessment"] in {
                    "belum_ada_transfer",
                    "bervariasi",
                }
                assert stage["payment_difference"] is None
            # expected_amount must equal recipient_count * 3jt when derived from default
            rc = row["recipient_count"]
            if stage.get("transfer_amount") in (None, 0) and not stage.get("transactions"):
                assert stage["expected_amount"] == rc * TRANSFER_AMOUNT_PER_STUDENT

    def test_detail_region_stages_have_financial_fields(self, prov_token):
        rows = requests.get(
            f"{API}/admin/disbursements/campuses", headers=_h(prov_token), timeout=30
        ).json()
        assert rows
        key = rows[0]["campus_key"]
        r = requests.get(
            f"{API}/admin/disbursements/campuses/{key}", headers=_h(prov_token), timeout=30
        )
        assert r.status_code == 200, r.text
        detail = r.json()
        assert detail["regions"]
        region = detail["regions"][0]
        for stage_key in ("stage_one", "stage_two"):
            stage = region[stage_key]
            for field in FINANCIAL_FIELDS:
                assert field in stage, f"detail {stage_key} missing {field}"
            rc = region["recipient_count"]
            # expected_amount defaults to recipients * 3jt when no transfer yet
            if stage.get("transfer_amount") in (None, 0):
                assert stage["expected_amount"] == rc * TRANSFER_AMOUNT_PER_STUDENT
                assert stage["payment_assessment"] == "belum_ada_transfer"
                assert stage["payment_difference"] is None
                assert stage["paid_student_count"] == 0


# ---------------------------------------------------------------------------
# parse_transfer_amount unit tests
# ---------------------------------------------------------------------------
class TestParseTransferAmount:
    @pytest.mark.parametrize("raw,expected", [
        ("Rp3.000.000", 3_000_000),
        ("3.000.000,00", 3_000_000),
        ("3,000,000", 3_000_000),
        ("3000000", 3_000_000),
        (3_000_000, 3_000_000),
        (3_000_000.0, 3_000_000),
        ("", None),
        (None, None),
        ("Rp 3.000.101", 3_000_101),
    ])
    def test_parse(self, raw, expected):
        assert parse_transfer_amount(raw) == expected


# ---------------------------------------------------------------------------
# refresh_campus_transfer_financials unit-style tests via seeded aggregate
# ---------------------------------------------------------------------------
TEST_CAMPUS_KEY_PREFIX = "TEST_TF_UNIT_"


@pytest_asyncio.fixture
async def seeded_aggregate():
    """Create a temporary campus_disbursements aggregate; cleanup after test."""
    docs = []
    db = _fresh_db()

    async def _seed(transactions, recipient_count=1, stage=1, region="Jakarta Barat"):
        campus_key = f"{TEST_CAMPUS_KEY_PREFIX}{uuid.uuid4().hex[:8]}"
        doc = {
            "id": str(uuid.uuid4()),
            "campus_key": campus_key,
            "campus": f"TEST TF Campus {campus_key}",
            "region": region,
            "stage": stage,
            "status": "belum_diproses",
            "amount": None,
            "disbursed_at": None,
            "reference": "",
            "notes": "",
            "proofs": [],
            "transactions": transactions,
            "recipient_user_ids": [f"tf-recipient-{i}" for i in range(recipient_count)],
            "recipient_count": recipient_count,
        }
        await db.campus_disbursements.insert_one(dict(doc))
        docs.append((campus_key, region, stage))
        return campus_key, region, stage

    yield _seed

    for campus_key, region, stage in docs:
        await db.campus_disbursements.delete_many(
            {"campus_key": campus_key, "region": region, "stage": stage}
        )


async def _seed_and_refresh(seed, transactions, recipient_count=1):
    campus_key, region, stage = await seed(transactions, recipient_count=recipient_count)
    await refresh_campus_transfer_financials(campus_key, region, stage, recipient_count)
    doc = await server.db.campus_disbursements.find_one(
        {"campus_key": campus_key, "region": region, "stage": stage}, {"_id": 0}
    )
    return doc


@pytest.mark.asyncio
class TestRefreshFinancials:
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_exact_amount_is_sesuai_1_student(self, seeded_aggregate):
        doc = await _seed_and_refresh(
            seeded_aggregate,
            [{"amount": 3_000_000}],
            recipient_count=1,
        )
        assert doc["transfer_amount"] == 3_000_000
        assert doc["expected_amount"] == 3_000_000
        assert doc["payment_assessment"] == "sesuai"
        assert doc["paid_student_count"] == 1
        assert doc["payment_difference"] == 0

    @pytest.mark.asyncio
    async def test_unique_code_plus_101_is_sesuai(self, seeded_aggregate):
        doc = await _seed_and_refresh(
            seeded_aggregate,
            [{"amount": 3_000_101}],
            recipient_count=1,
        )
        assert doc["payment_assessment"] == "sesuai"
        assert doc["payment_difference"] == UNIQUE_TRANSFER_TOLERANCE
        assert doc["paid_student_count"] == 1

    @pytest.mark.asyncio
    async def test_shortage_kurang_zero_paid(self, seeded_aggregate):
        doc = await _seed_and_refresh(
            seeded_aggregate,
            [{"amount": 2_999_999}],
            recipient_count=1,
        )
        assert doc["payment_assessment"] == "kurang"
        assert doc["payment_difference"] == -1
        assert doc["paid_student_count"] == 0

    @pytest.mark.asyncio
    async def test_excess_plus_102_is_lebih(self, seeded_aggregate):
        doc = await _seed_and_refresh(
            seeded_aggregate,
            [{"amount": 3_000_102}],
            recipient_count=1,
        )
        assert doc["payment_assessment"] == "lebih"
        assert doc["payment_difference"] == 102
        # floor(3_000_102 / 3_000_000) = 1, capped by recipient_count=1
        assert doc["paid_student_count"] == 1

    @pytest.mark.asyncio
    async def test_multiple_transactions_summed(self, seeded_aggregate):
        doc = await _seed_and_refresh(
            seeded_aggregate,
            [
                {"amount": "Rp1.500.000"},
                {"amount": 1_500_000},
                {"amount": "3.000.050"},  # total = 6_000_050 for 2 students expected 6_000_000
            ],
            recipient_count=2,
        )
        assert doc["transfer_amount"] == 6_000_050
        assert doc["expected_amount"] == 6_000_000
        # +50 within tolerance => sesuai
        assert doc["payment_assessment"] == "sesuai"
        assert doc["paid_student_count"] == 2

    @pytest.mark.asyncio
    async def test_paid_count_capped_by_recipient_count(self, seeded_aggregate):
        # Overpay dramatically: 10jt vs 1 recipient (expected 3jt). Should be 'lebih'
        # and paid_student_count capped to 1 (not floor(10jt/3jt)=3).
        doc = await _seed_and_refresh(
            seeded_aggregate,
            [{"amount": 10_000_000}],
            recipient_count=1,
        )
        assert doc["payment_assessment"] == "lebih"
        assert doc["paid_student_count"] == 1

    @pytest.mark.asyncio
    async def test_no_transactions_belum_ada_transfer(self, seeded_aggregate):
        doc = await _seed_and_refresh(
            seeded_aggregate,
            [],
            recipient_count=3,
        )
        assert doc["payment_assessment"] == "belum_ada_transfer"
        assert doc["transfer_amount"] is None
        assert doc["expected_amount"] == 9_000_000
        assert doc["paid_student_count"] == 0
        assert doc["payment_difference"] is None


# ---------------------------------------------------------------------------
# Demo dataset invariants
# ---------------------------------------------------------------------------
class TestDemoInvariants:
    def test_demo_tf_campuses_preserved(self, prov_token):
        r = requests.get(
            f"{API}/campuses", headers=_h(prov_token), timeout=30,
            params={"search": "DEMO-TF"},
        )
        assert r.status_code == 200
        rows = r.json()
        codes = [c.get("code") for c in rows if str(c.get("code", "")).startswith("DEMO-TF-")]
        assert len(codes) == 24, f"expected 24 DEMO-TF campuses, got {len(codes)}"
