import React, { useRef, useState } from "react";
import { toast } from "sonner";
import {
  CheckCircle2,
  FileCheck,
  Loader2,
  ScanLine,
  UploadCloud,
} from "lucide-react";
import api from "@/lib/api";
import { DocPreview } from "@/components/DocPreview";

const SCAN_TYPES = [
  {
    id: "ktm",
    label: "Kartu Tanda Mahasiswa (KTM)",
    endpoint: "/profile/extract-ktm",
    docType: "Kartu Tanda Mahasiswa (KTM)",
    description: "AI mengisi kampus, NIM, program studi, dan jenjang bila terbaca.",
  },
  {
    id: "academic",
    label: "KRS / KHS / Transkrip Nilai",
    endpoint: "/profile/extract-academic-record",
    docType: "KRS / KHS / Transkrip Nilai",
    description: "AI mengisi kampus, NIM, program studi, jenjang, semester, dan IPK.",
  },
];

export default function EducationDocumentScan({ docs, setData, onDocumentSaved }) {
  return (
    <div className="grid gap-4 lg:grid-cols-2" data-testid="education-document-scans">
      {SCAN_TYPES.map((config) => (
        <ScanCard
          key={config.id}
          config={config}
          docs={docs}
          setData={setData}
          onDocumentSaved={onDocumentSaved}
        />
      ))}
    </div>
  );
}

function ScanCard({ config, docs, setData, onDocumentSaved }) {
  const inputRef = useRef(null);
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState(null);
  const existing = (docs || []).find((document) => document.doc_type === config.docType);

  const upload = async (file) => {
    if (!file) return;

    const ext = file.name.split(".").pop().toLowerCase();
    if (!["jpg", "jpeg", "png", "webp", "pdf"].includes(ext)) {
      toast.error("Format harus JPG, PNG, WEBP, atau PDF.");
      return;
    }

    setLoading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const { data: response } = await api.post(config.endpoint, formData, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 90000,
      });
      const extracted = response.data || {};
      const fieldCount = Object.keys(extracted).length;

      if (response.document && onDocumentSaved) {
        onDocumentSaved(response.document);
      }

      if (fieldCount === 0) {
        toast.error("Dokumen tersimpan, tetapi data pendidikan belum dapat dibaca dengan jelas.");
        return;
      }

      setData((previous) => ({ ...previous, ...extracted }));
      toast.success(`${fieldCount} data pendidikan terisi otomatis dari ${config.label}.`);
    } catch (error) {
      toast.error(
        error?.response?.data?.detail ||
        `Gagal membaca ${config.label}. Coba unggah dokumen yang lebih jelas.`,
      );
    } finally {
      setLoading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return (
    <div
      className="border-2 border-dashed border-[#27AE60]/35 bg-[#F0FBF5] p-5 rounded-xl"
      data-testid={`education-scan-${config.id}-card`}
    >
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[#E8F6EE]">
          <ScanLine className="h-5 w-5 text-[#27AE60]" />
        </div>
        <div>
          <p className="font-display text-sm font-bold text-[#1F2937]">{config.label}</p>
          <p className="mt-1 text-xs leading-relaxed text-[#6B7280]">{config.description}</p>
        </div>
      </div>

      {existing && (
        <button
          type="button"
          onClick={() => setPreview(existing)}
          data-testid={`education-scan-${config.id}-preview`}
          className="mt-3 flex max-w-full items-center gap-1.5 text-left text-xs font-semibold text-[#0B6B3A] hover:underline"
        >
          <FileCheck className="h-4 w-4 shrink-0 text-[#27AE60]" />
          <span className="truncate">Tersimpan: {existing.original_filename}</span>
        </button>
      )}

      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={loading}
        data-testid={`education-scan-${config.id}-upload-button`}
        className="mt-4 inline-flex items-center gap-2 rounded-lg bg-[#27AE60] px-4 py-2.5 text-xs font-bold text-white transition-colors hover:bg-[#0B6B3A] disabled:opacity-60"
      >
        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <UploadCloud className="h-4 w-4" />}
        {loading ? "Membaca dokumen..." : existing ? "Ganti & Isi Otomatis" : "Unggah & Isi Otomatis"}
      </button>
      <input
        ref={inputRef}
        type="file"
        accept=".jpg,.jpeg,.png,.webp,.pdf"
        className="hidden"
        data-testid={`education-scan-${config.id}-file-input`}
        onChange={(event) => upload(event.target.files[0])}
      />
      <DocPreview doc={preview} onClose={() => setPreview(null)} />
    </div>
  );
}