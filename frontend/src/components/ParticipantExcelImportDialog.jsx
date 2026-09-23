import React, { useRef, useState } from "react";
import { toast } from "sonner";
import {
  AlertTriangle,
  CheckCircle2,
  FileSpreadsheet,
  Loader2,
  Upload,
  X,
} from "lucide-react";
import api from "@/lib/api";

const EMPTY_MAPPING = {};

export default function ParticipantExcelImportDialog({ onClose, onImported }) {
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [mapping, setMapping] = useState(EMPTY_MAPPING);
  const [previewing, setPreviewing] = useState(false);
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState(null);

  const previewFile = async (selectedFile) => {
    if (!selectedFile) return;
    if (!selectedFile.name.toLowerCase().endsWith(".xlsx")) {
      toast.error("Pilih file Excel berformat XLSX.");
      return;
    }
    setPreviewing(true);
    setResult(null);
    const formData = new FormData();
    formData.append("file", selectedFile);
    try {
      const response = await api.post("/admin/participants/import/preview", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 120000,
      });
      setFile(selectedFile);
      setPreview(response.data);
      setMapping(response.data.mapping || {});
      toast.success("Kolom Excel berhasil dibaca. Periksa pemetaan sebelum mengimpor.");
    } catch (error) {
      toast.error(error.response?.data?.detail || "File Excel tidak dapat dibaca.");
      setFile(null);
      setPreview(null);
    } finally {
      setPreviewing(false);
    }
  };

  const importData = async () => {
    if (!file || !preview) return;
    if (!mapping.name) {
      toast.error("Petakan minimal kolom Nama Lengkap sebelum mengimpor.");
      return;
    }
    setImporting(true);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("mapping_json", JSON.stringify(mapping));
    try {
      const response = await api.post("/admin/participants/import", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 120000,
      });
      setResult(response.data);
      onImported();
      const summary = response.data.summary || {};
      const warningCount = (summary.failed || 0) + (summary.campus_conflicts || 0);
      if (warningCount > 0) {
        toast.warning(
          `Import selesai dengan ${warningCount} baris yang perlu diperiksa.`,
        );
      } else {
        toast.success("Import data peserta selesai diproses.");
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Import data peserta gagal.");
    } finally {
      setImporting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-[#1F2937]/50 p-4"
      data-testid="participant-import-dialog"
      onClick={onClose}
    >
      <div
        className="max-h-[90vh] w-full max-w-5xl overflow-y-auto rounded-xl bg-white shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div
          className={[
            "sticky top-0 z-10 flex items-start justify-between gap-4 border-b bg-white",
            "px-6 py-5",
          ].join(" ")}
        >
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-[#0B6B3A]">
              Data Peserta
            </p>
            <h2 className="mt-1 font-display text-xl font-extrabold text-[#1F2937]">
              Import Excel Tanpa Berkas
            </h2>
            <p className="mt-1 text-sm text-[#6B7280]">
              Peserta baru dibuat sebagai Lolos / Penerima. Data NIK, email, atau ID CPM yang sama
              akan diperbarui.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            data-testid="close-participant-import-dialog"
            className="rounded-lg p-2 text-[#6B7280] transition-colors hover:bg-gray-100"
            aria-label="Tutup impor data peserta"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-6 p-6">
          <section
            className="flex flex-col gap-4 border border-dashed border-[#8FE2B4] bg-[#F0FBF5] p-5
              sm:flex-row sm:items-center sm:justify-between"
          >
            <div className="flex items-start gap-3">
              <FileSpreadsheet className="mt-0.5 h-6 w-6 shrink-0 text-[#0B6B3A]" />
              <div>
                <p className="text-sm font-bold text-[#1F2937]">
                  {file ? file.name : "Pilih file Excel Anda"}
                </p>
                <p className="mt-1 text-xs leading-relaxed text-[#6B7280]">
                  Sistem membaca header dari format Excel yang Anda gunakan, kemudian Anda dapat
                  menyesuaikan kolom sebelum data diimpor.
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              disabled={previewing}
              data-testid="participant-import-select-file"
              className={[
                "inline-flex shrink-0 items-center justify-center gap-2 rounded-lg bg-[#0B6B3A]",
                "px-4 py-2.5 text-sm font-bold text-white transition-colors hover:bg-[#07532D]",
                "disabled:opacity-60",
              ].join(" ")}
            >
              {previewing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Upload className="h-4 w-4" />
              )}
              {previewing ? "Membaca Excel..." : "Pilih XLSX"}
            </button>
            <input
              ref={inputRef}
              type="file"
              accept=".xlsx"
              onChange={(event) => previewFile(event.target.files?.[0])}
              data-testid="participant-import-file-input"
              className="hidden"
            />
          </section>

          {preview && (
            <>
              <section className="border border-gray-100 bg-white p-5 shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h3 className="font-display text-lg font-bold text-[#1F2937]">
                      Pemetaan Kolom
                    </h3>
                    <p
                      className="mt-1 text-sm text-[#6B7280]"
                      data-testid="participant-import-row-count"
                    >
                      {preview.row_count} baris data ditemukan. Kolom bertanda wajib perlu
                      dipetakan.
                    </p>
                  </div>
                  {!preview.has_identity_column && (
                    <p
                      className={[
                        "flex max-w-md items-start gap-2 text-xs leading-relaxed",
                        "text-[#92400E]",
                      ].join(" ")}
                      data-testid="participant-import-identity-warning"
                    >
                      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                      NIK, Email, atau ID CPM belum dipetakan. Baris baru tetap dapat dibuat, tetapi
                      pembaruan duplikat tidak dapat dikenali.
                    </p>
                  )}
                </div>
                <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {preview.fields.map((field) => (
                    <label key={field.key} className="text-sm font-bold text-[#1F2937]">
                      {field.label} {field.required && <span className="text-[#DC2626]">*</span>}
                      <select
                        value={mapping[field.key] || ""}
                        onChange={(event) => setMapping((previous) => ({
                          ...previous,
                          [field.key]: event.target.value,
                        }))}
                        data-testid={`participant-import-mapping-${field.key}`}
                        className={[
                          "mt-2 w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5",
                          "text-sm font-medium outline-none focus:border-[#27AE60]",
                        ].join(" ")}
                      >
                        <option value="">Tidak digunakan</option>
                        {preview.headers.map((header) => (
                          <option key={header} value={header}>{header}</option>
                        ))}
                      </select>
                    </label>
                  ))}
                </div>
              </section>

              {preview.samples?.length > 0 && (
                <section className="border border-gray-100 bg-white p-5 shadow-sm">
                  <h3 className="font-display text-lg font-bold text-[#1F2937]">Contoh Data</h3>
                  <div className="mt-4 overflow-x-auto">
                    <table
                      className="min-w-full text-left text-xs"
                      data-testid="participant-import-sample-table"
                    >
                      <thead className="bg-[#F9FAFB] text-[#6B7280]">
                        <tr>
                          {preview.headers.map((header) => (
                            <th key={header} className="whitespace-nowrap px-3 py-2 font-bold">
                              {header}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {preview.samples.map((row, index) => (
                          <tr key={index} className="border-t border-gray-100">
                            {preview.headers.map((header) => (
                              <td
                                key={header}
                                className="max-w-48 truncate px-3 py-2 text-[#4B5563]"
                              >
                                {row[header] || "—"}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              )}

              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={importData}
                  disabled={importing || !mapping.name}
                  data-testid="confirm-participant-import"
                  className={[
                    "inline-flex items-center gap-2 rounded-lg bg-[#27AE60] px-5 py-3 text-sm",
                    "font-bold text-white transition-colors hover:bg-[#0B6B3A]",
                    "disabled:cursor-not-allowed disabled:opacity-60",
                  ].join(" ")}
                >
                  {importing ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <CheckCircle2 className="h-4 w-4" />
                  )}
                  {importing ? "Mengimpor Data..." : "Import sebagai Lolos / Penerima"}
                </button>
              </div>
            </>
          )}

          {result && <ParticipantImportResult result={result} />}
        </div>
      </div>
    </div>
  );
}

function ParticipantImportResult({ result }) {
  const summary = result.summary || {};
  const items = [
    ["Baris diproses", summary.processed || 0],
    ["Peserta baru", summary.created || 0],
    ["Peserta diperbarui", summary.updated || 0],
    ["Kampus baru", summary.campuses_created || 0],
    ["Kampus diperbarui", summary.campuses_updated || 0],
    ["Konflik kampus", summary.campus_conflicts || 0],
    ["Gagal", summary.failed || 0],
  ];
  return (
    <section
      className="border border-[#B7E4C7] bg-[#F0FBF5] p-5"
      data-testid="participant-import-result"
    >
      <h3 className="font-display text-lg font-bold text-[#1F2937]">Hasil Import</h3>
      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {items.map(([label, value]) => (
          <div key={label} className="bg-white p-3">
            <p className="text-xs text-[#6B7280]">{label}</p>
            <p className="mt-1 font-display text-2xl font-extrabold text-[#0B6B3A]">
              {value}
            </p>
          </div>
        ))}
      </div>
      {result.errors?.length > 0 && (
        <div className="mt-4 border-l-4 border-[#F59E0B] bg-[#FFFBEB] p-4">
          <p className="text-sm font-bold text-[#92400E]">Baris yang perlu diperiksa</p>
          <ul className="mt-2 space-y-1 text-xs text-[#92400E]">
            {result.errors.map((item) => (
              <li key={`${item.row_number}-${item.message}`}>
                Baris {item.row_number}: {item.message}
              </li>
            ))}
          </ul>
        </div>
      )}
      {result.warnings?.length > 0 && (
        <div className="mt-4 border-l-4 border-[#F59E0B] bg-[#FFFBEB] p-4">
          <p className="text-sm font-bold text-[#92400E]">Konflik data kampus</p>
          <ul className="mt-2 space-y-1 text-xs text-[#92400E]">
            {result.warnings.map((item) => (
              <li key={`${item.row_number}-${item.message}`}>
                Baris {item.row_number}: {item.message}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}