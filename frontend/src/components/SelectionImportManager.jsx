import React, { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import {
  AlertTriangle,
  Bot,
  Download,
  FileSpreadsheet,
  Inbox,
  Loader2,
  Trash2,
  UserPlus,
} from "lucide-react";
import api from "@/lib/api";

const IMPORT_STAGES = [
  { value: "wawancara_lolos", label: "Hasil Lolos Wawancara → Verifikasi Faktual" },
  { value: "kelulusan_akhir", label: "Hasil Kelulusan Akhir → Penerima Manfaat" },
];

export default function SelectionImportManager() {
  const inputRef = useRef(null);
  const [stage, setStage] = useState("wawancara_lolos");
  const [uploading, setUploading] = useState(false);
  const [imports, setImports] = useState([]);
  const [reviewItems, setReviewItems] = useState([]);
  const [activeTab, setActiveTab] = useState("review");
  const [lastResult, setLastResult] = useState(null);

  const load = useCallback(async () => {
    try {
      const [importsResponse, reviewResponse] = await Promise.all([
        api.get("/admin/selection-imports"),
        api.get("/admin/selection-import-review"),
      ]);
      setImports(importsResponse.data || []);
      setReviewItems(reviewResponse.data || []);
    } catch {
      toast.error("Riwayat import belum dapat dimuat.");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const upload = async (file) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".xlsx")) {
      toast.error("Pilih file hasil seleksi berformat XLSX.");
      return;
    }
    setUploading(true);
    const formData = new FormData();
    formData.append("stage", stage);
    formData.append("file", file);
    try {
      const response = await api.post("/admin/selection-imports", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 120000,
      });
      setLastResult(response.data);
      toast.success("Hasil import telah diproses.");
      await load();
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Gagal memproses file import.");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  const dismissItem = async (itemId) => {
    try {
      await api.delete(`/admin/selection-import-review/${itemId}`);
      setReviewItems((previous) => previous.filter((item) => item.id !== itemId));
      toast.success("Data dihapus dari daftar tinjauan.");
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Gagal menghapus data tinjauan.");
    }
  };

  const downloadImport = async (record) => {
    try {
      const response = await api.get(`/admin/selection-imports/${record.id}/file`, {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = record.original_filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      toast.error("File audit belum dapat diunduh.");
    }
  };

  const visibleItems = reviewItems.filter((item) => (
    activeTab === "new" ? item.kind === "new_participant" : item.kind !== "new_participant"
  ));
  const reviewCount = reviewItems.filter((item) => item.kind !== "new_participant").length;
  const newCount = reviewItems.filter((item) => item.kind === "new_participant").length;

  return (
    <div className="space-y-7" data-testid="selection-import-manager">
      <section className="border-l-4 border-[#0B6B3A] bg-[#F0FBF5] px-5 py-4">
        <p className="text-xs font-bold uppercase tracking-wide text-[#0B6B3A]">Import Seleksi</p>
        <h2 className="mt-1 font-display text-2xl font-extrabold text-[#1F2937]">
          Hasil Wawancara dan Kelulusan Akhir
        </h2>
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-[#6B7280]">
          Peserta cocok diperbarui otomatis. Data baru dan data yang tidak sesuai dipisahkan untuk ditinjau.
        </p>
      </section>

      <section className="grid gap-5 border border-gray-100 bg-white p-5 shadow-sm lg:grid-cols-[1fr_auto]">
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="text-sm font-bold text-[#1F2937]">
            Jenis Hasil Import
            <select
              value={stage}
              onChange={(event) => setStage(event.target.value)}
              data-testid="selection-import-stage"
              className="mt-2 w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm font-medium outline-none focus:border-[#27AE60]"
            >
              {IMPORT_STAGES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
            </select>
          </label>
          <div className="text-sm text-[#6B7280] sm:pt-7">
            Cocokkan otomatis: ID CPM → NIK → Email → Nama, Kampus, dan Wilayah.
          </div>
        </div>
        <div className="flex items-end">
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={uploading}
            data-testid="selection-import-upload-button"
            className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-[#27AE60] px-5 py-2.5 text-sm font-bold text-white transition-colors hover:bg-[#0B6B3A] disabled:opacity-60 lg:w-auto"
          >
            {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileSpreadsheet className="h-4 w-4" />}
            {uploading ? "Memeriksa data..." : "Import XLSX"}
          </button>
          <input
            ref={inputRef}
            type="file"
            accept=".xlsx"
            className="hidden"
            data-testid="selection-import-file-input"
            onChange={(event) => upload(event.target.files[0])}
          />
        </div>
      </section>

      {lastResult && <ImportSummary result={lastResult} />}

      <section className="border border-gray-100 bg-white shadow-sm" data-testid="selection-import-review-panel">
        <div className="flex flex-wrap gap-2 border-b border-gray-100 px-5 pt-4">
          <ReviewTab active={activeTab === "review"} count={reviewCount} label="Perlu Ditinjau" onClick={() => setActiveTab("review")} testId="review-tab" />
          <ReviewTab active={activeTab === "new"} count={newCount} label="Peserta Baru dari Import" onClick={() => setActiveTab("new")} testId="new-imported-tab" />
        </div>
        <div className="p-5">
          {visibleItems.length === 0 ? (
            <div className="py-10 text-center" data-testid="empty-import-review">
              <Inbox className="mx-auto h-7 w-7 text-gray-300" />
              <p className="mt-3 text-sm font-semibold text-[#6B7280]">Tidak ada data yang perlu ditinjau.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {visibleItems.map((item) => <ReviewItem key={item.id} item={item} onDismiss={dismissItem} />)}
            </div>
          )}
        </div>
      </section>

      <section className="border border-gray-100 bg-white p-5 shadow-sm" data-testid="selection-import-history">
        <h3 className="font-display text-lg font-bold text-[#1F2937]">Riwayat Import</h3>
        <div className="mt-4 divide-y divide-gray-100">
          {imports.length === 0 ? (
            <p className="py-5 text-sm text-[#6B7280]">Belum ada file hasil seleksi yang diimpor.</p>
          ) : imports.map((record) => (
            <div key={record.id} className="flex flex-col gap-3 py-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0">
                <p className="truncate text-sm font-bold text-[#1F2937]">{record.original_filename}</p>
                <p className="mt-1 text-xs text-[#6B7280]">
                  {record.stage_label} · {record.summary?.updated || 0} status diperbarui · {record.review_count || 0} ditinjau
                </p>
              </div>
              <button type="button" onClick={() => downloadImport(record)} data-testid={`download-import-${record.id}`} className="inline-flex shrink-0 items-center gap-2 text-sm font-bold text-[#0B6B3A] hover:underline">
                <Download className="h-4 w-4" /> Unduh File
              </button>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function ImportSummary({ result }) {
  const items = [
    ["Cocok", result.summary?.matched || 0],
    ["Status diperbarui", result.summary?.updated || 0],
    ["Perlu ditinjau", result.summary?.review || 0],
    ["Peserta baru", result.summary?.new || 0],
  ];
  return (
    <section className="grid grid-cols-2 gap-3 lg:grid-cols-4" data-testid="selection-import-summary">
      {items.map(([label, value]) => (
        <div key={label} className="border border-gray-100 bg-white p-4 shadow-sm">
          <p className="text-xs text-[#6B7280]">{label}</p>
          <p className="mt-1 font-display text-2xl font-extrabold text-[#0B6B3A]">{value}</p>
        </div>
      ))}
    </section>
  );
}

function ReviewTab({ active, count, label, onClick, testId }) {
  return (
    <button type="button" onClick={onClick} data-testid={testId} className={`border-b-2 px-3 py-3 text-sm font-bold transition-colors ${active ? "border-[#27AE60] text-[#0B6B3A]" : "border-transparent text-[#6B7280] hover:text-[#1F2937]"}`}>
      {label} <span className="ml-1 rounded-full bg-gray-100 px-2 py-0.5 text-xs">{count}</span>
    </button>
  );
}

function ReviewItem({ item, onDismiss }) {
  const isNew = item.kind === "new_participant";
  const details = [
    item.imported_data?.cpm_id,
    item.imported_data?.email,
    item.imported_data?.name,
    item.imported_data?.campus,
    item.imported_data?.region,
  ].filter(Boolean).join(" · ");
  return (
    <div className="flex flex-col gap-4 border border-gray-100 bg-[#FAFAFA] p-4 sm:flex-row sm:items-start sm:justify-between" data-testid={`import-review-item-${item.id}`}>
      <div className="flex min-w-0 gap-3">
        <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${isNew ? "bg-[#DBEAFE]" : "bg-[#FEF3C7]"}`}>
          {isNew ? <UserPlus className="h-4 w-4 text-[#2563EB]" /> : <AlertTriangle className="h-4 w-4 text-[#D99A00]" />}
        </div>
        <div className="min-w-0">
          <p className="text-sm font-bold text-[#1F2937]">Baris {item.row_number} · {isNew ? "Peserta Baru" : "Data Tidak Sesuai"}</p>
          <p className="mt-1 text-sm text-[#6B7280]">{item.reason}</p>
          {item.differences?.length > 0 && <p className="mt-1 text-xs font-semibold text-[#92400E]">Berbeda: {item.differences.join(", ")}</p>}
          {details && <p className="mt-1 truncate text-xs text-[#6B7280]">{details}</p>}
          {item.ai_note && <p className="mt-2 flex gap-1.5 text-xs leading-relaxed text-[#0B6B3A]"><Bot className="mt-0.5 h-3.5 w-3.5 shrink-0" />{item.ai_note}</p>}
        </div>
      </div>
      <button type="button" onClick={() => onDismiss(item.id)} data-testid={`dismiss-import-review-${item.id}`} className="inline-flex shrink-0 items-center justify-center gap-1.5 rounded-lg border border-[#FECACA] bg-white px-3 py-2 text-xs font-bold text-[#B91C1C] hover:bg-[#FEF2F2]">
        <Trash2 className="h-3.5 w-3.5" /> Hapus dari daftar
      </button>
    </div>
  );
}