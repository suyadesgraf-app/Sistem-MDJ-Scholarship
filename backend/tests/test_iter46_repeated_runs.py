"""Iter46: 3-run repetition to ensure syarat/program are consistently grounded.
Also confirms genuine unrelated question still returns fallback each time."""
import json
import os
import time

import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://sistem-registrasi.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
STUDENT = {"email": "mahasiswa.mdj@baznasbazisdki.id", "password": "MahasiswaMDJ2026!"}
OUT_OF_SCOPE = "Maaf, pertanyaan tersebut berada di luar cakupan referensi dokumen yang tersedia."
SYARAT_PDF = "SYARAT DAN KETENTUAN (TERMS & CONDITIONS).pdf"
EXPECTED_REFS = {"KEBIJAKAN PRIVASI.pdf", SYARAT_PDF, "PAKTA INTEGRITAS PENDAFTAR.pdf"}


def _token():
    r = requests.post(f"{API}/auth/login", json=STUDENT, timeout=30)
    r.raise_for_status()
    return r.json()["token"]


def _consume(tok, q):
    r = requests.post(f"{API}/student/ai-chat/stream",
                      headers={"Authorization": f"Bearer {tok}"},
                      json={"question": q}, stream=True, timeout=120)
    assert r.status_code == 200
    deltas, sources, event = [], None, None
    for line in r.iter_lines(decode_unicode=True):
        if line == "":
            event = None
            continue
        if line and line.startswith("event: "):
            event = line[7:].strip()
        elif line and line.startswith("data: "):
            try:
                d = json.loads(line[6:])
            except Exception:
                continue
            if event == "done":
                sources = d.get("sources")
                break
            if "text" in d:
                deltas.append(d["text"])
    r.close()
    return "".join(deltas), sources or []


def test_syarat_three_runs():
    tok = _token()
    for i in range(3):
        ans, srcs = _consume(tok, "syaratnya apa ajah?")
        assert SYARAT_PDF in srcs, f"run {i}: SYARAT missing in {srcs}"
        assert ans.strip() != OUT_OF_SCOPE, f"run {i}: got fallback. srcs={srcs}"
        assert len(ans.strip()) > 20, f"run {i}: too short: {ans!r}"
        time.sleep(1)


def test_program_three_runs():
    tok = _token()
    for i in range(3):
        ans, srcs = _consume(tok, "program apa sih ini?")
        assert any(s in EXPECTED_REFS for s in srcs), f"run {i}: bad srcs {srcs}"
        assert ans.strip() != OUT_OF_SCOPE, f"run {i}: got fallback. srcs={srcs}"
        assert len(ans.strip()) > 20, f"run {i}: too short: {ans!r}"
        time.sleep(1)


def test_unrelated_stays_out_of_scope():
    tok = _token()
    ans, srcs = _consume(tok, "Bagaimana resep memasak rendang khas Padang paling enak?")
    assert OUT_OF_SCOPE in ans, f"expected fallback got {ans[:200]!r} srcs={srcs}"
