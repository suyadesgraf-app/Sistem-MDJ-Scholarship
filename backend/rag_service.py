import io
import os
import re
import tempfile
from pathlib import Path

import pandas as pd
from docx import Document
from openpyxl import load_workbook
from pypdf import PdfReader

from emergentintegrations.llm.chat import (
    FileContentWithMimeType,
    LlmChat,
    StreamDone,
    TextDelta,
    UserMessage,
)

GEMINI_MODEL = "gemini-3.8-flash"
OUT_OF_SCOPE_MESSAGE = (
    "Maaf, pertanyaan tersebut berada di luar cakupan referensi dokumen yang tersedia."
)


def split_reference_text(text: str, size: int = 900) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    return [normalized[index:index + size] for index in range(0, len(normalized), size)]


def reference_tokens(text: str) -> set[str]:
    stop_words = {"yang", "dan", "atau", "untuk", "dengan", "dari", "pada", "ini", "itu", "apa", "sih"}
    synonyms = {
        "syarat": {"syarat", "persyaratan", "ketentuan", "kriteria"},
        "persyaratan": {"syarat", "persyaratan", "ketentuan", "kriteria"},
        "ketentuan": {"syarat", "persyaratan", "ketentuan", "kriteria"},
        "program": {"program", "beasiswa", "scholarship", "mdj", "masa", "depan", "jakarta"},
        "beasiswa": {"program", "beasiswa", "scholarship", "mdj"},
    }
    tokens = set()
    for token in re.findall(r"[a-zA-Z0-9]{3,}", text.lower()):
        normalized = token[:-3] if token.endswith("nya") and len(token) > 5 else token
        if normalized in stop_words:
            continue
        tokens.add(normalized)
        tokens.update(synonyms.get(normalized, set()))
    return tokens


def extract_pdf(data: bytes) -> str:
    return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages)


def extract_docx(data: bytes) -> str:
    document = Document(io.BytesIO(data))
    return "\n".join(paragraph.text for paragraph in document.paragraphs)


def extract_excel(data: bytes, extension: str) -> str:
    if extension == "xlsx":
        workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        lines = []
        for worksheet in workbook.worksheets:
            lines.append(f"Sheet: {worksheet.title}")
            lines.extend(" | ".join(str(value or "") for value in row) for row in worksheet.iter_rows(values_only=True))
        return "\n".join(lines)
    sheets = pd.read_excel(io.BytesIO(data), sheet_name=None, engine="xlrd")
    return "\n".join(f"Sheet: {name}\n{sheet.to_csv(index=False)}" for name, sheet in sheets.items())


async def extract_with_gemini_file(data: bytes, filename: str, mime_type: str, api_key: str) -> str:
    suffix = Path(filename).suffix or ".bin"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temporary_file:
        temporary_file.write(data)
        temporary_path = temporary_file.name
    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"reference-ingest-{Path(temporary_path).stem}",
            system_message="Ekstrak isi faktual file secara lengkap dalam Bahasa Indonesia tanpa menambah informasi.",
        ).with_model("gemini", GEMINI_MODEL)
        extracted = []
        message = UserMessage(
            text="Transkripkan seluruh teks, tabel, dan informasi faktual dalam file referensi ini.",
            file_contents=[FileContentWithMimeType(file_path=temporary_path, mime_type=mime_type)],
        )
        async for event in chat.stream_message(message):
            if isinstance(event, TextDelta):
                extracted.append(event.content)
            elif isinstance(event, StreamDone):
                break
        return "".join(extracted).strip()
    finally:
        os.unlink(temporary_path)


async def extract_reference_text(
    data: bytes,
    filename: str,
    extension: str,
    mime_type: str,
    api_key: str,
) -> str:
    if extension == "pdf":
        return extract_pdf(data)
    if extension == "docx":
        return extract_docx(data)
    if extension in {"xls", "xlsx"}:
        return extract_excel(data, extension)
    return await extract_with_gemini_file(data, filename, mime_type, api_key)