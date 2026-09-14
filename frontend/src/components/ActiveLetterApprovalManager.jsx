import React, { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { FileCheck2, Loader2, ShieldAlert, Upload } from "lucide-react";
import api, { formatApiError } from "@/lib/api";

const WORKFLOWS = {
  factual_verification: {
    label: "Verifikasi Faktual",
    uploadLabel: "Unggah Surat untuk Verifikasi Faktual",
    description: "Persetujuan akan meloloskan mahasiswa pada Verifikasi Faktual.",
  },
  stage_ii_disbursement: {
    label: "Pencairan Tahap II",
    uploadLabel: "Unggah Surat untuk Pencairan Tahap II",
    description: "Persetujuan akan menandai mahasiswa layak Pencairan Tahap II.",
  },
};

export default function ActiveLetterApprovalManager() {
  const fileInput = useRef(null);
  const [workflow, setWorkflow] = useState("factual_verification");
  const [recommendations, setRecommendations] = useState([]);
  const [selected, setSelected] = useState({});
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [deciding, setDeciding] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get("/admin/active-letter-approvals", { params: { workflow } });
      setRecommendations(response.data || []);
      setSelected({});
    } catch (error) {
      toast.error(formatApiError(error.response?.data?.detail));
    } finally {
      setLoading(false);
    }
  }, [workflow]);

  useEffect(() => {
    load();
  }, [load]);

  const upload = async (files) => {
    if (!files?.length) return;
    setUploading(true);
    const formData = new FormData();
    formData.append("workflow", workflow);
    Array.from(files).forEach((file) => formData.append("files", file));
    try {
      const response = await api.post("/admin/active-letter-approvals/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 120000,
      });
      const summary = response.data.summary || {};
      toast.success(`${summary.recommended || 0} rekomendasi menunggu persetujuan.`);
      await load();
    } catch (error) {
      toast.error(formatApiError(error.response?.data?.detail));
    } finally {
      setUploading(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  };

  const decide = async (action, applyAll = false) => {
    const recommendationIds = Object.entries(selected)
      .filter(([, isSelected]) => isSelected)
      .map(([id]) => id);
    if (!applyAll && recommendationIds.length === 0) {
      toast.error("Pilih rekomendasi yang akan diproses.");
      return;
    }
    setDeciding(true);
    try {
      const response = await api.post("/admin/active-letter-approvals/decision", {
        action,
        apply_all: applyAll,
        workflow,
        source_ids: applyAll ? [...new Set(recommended.map((item) => item.source_id))] : [],
        recommendation_ids: recommendationIds,
      });
      const skipped = response.data.skipped || 0;
      const suffix = skipped ? `, ${skipped} dilewati karena status peserta berubah.` : ".";
      toast.success(`${response.data.processed} rekomendasi berhasil diproses${suffix}`);
      await load();
    } catch (error) {
      toast.error(formatApiError(error.response?.data?.detail));
    } finally {
      setDeciding(false);
    }
  };

  const recommended = recommendations.filter((item) => item.recommendation === "recommended");
  const quarantined = recommendations.filter((item) => item.recommendation === "quarantined");
  const workflowInfo = WORKFLOWS[workflow];

  return (
    <div className="space-y-7" data-testid="active-letter-approval-manager">
      <section className="border-l-4 border-[#0B6B3A] bg-[#F0FBF5] px-5 py-4">
        <p className="text-xs font-bold uppercase tracking-wide text-[#0B6B3A]">Surat Aktif Kampus</p>
        <h2 className="mt-1 font-display text-2xl font-extrabold text-[#1F2937]">
          Persetujuan Verifikasi dan Pencairan
        </h2>
        <p className="mt-2 max-w-4xl text-sm leading-relaxed text-[#6B7280]">
          AI hanya mengenali kampus dan mahasiswa pada surat. Perubahan status baru berlaku setelah
          Admin Provinsi atau Super Admin menyetujui rekomendasi.
        </p>
      </section>

      <section className="flex flex-col gap-3 border border-[#B7E4C7] bg-white p-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-[#0B6B3A]">Proses Aktif</p>
          <p className="mt-1 text-sm text-[#6B7280]">{workflowInfo.description}</p>
        </div>
        <div className="inline-flex rounded-lg border border-[#B7E4C7] p-1" data-testid="active-letter-workflow-selector">
          {Object.entries(WORKFLOWS).map(([value, item]) => (
            <button
              key={value}
              type="button"
              onClick={() => setWorkflow(value)}
              data-testid={`select-active-letter-workflow-${value}`}
              className={`rounded-md px-4 py-2.5 text-sm font-bold ${workflow === value ? "bg-[#0B6B3A] text-white" : "text-[#6B7280] hover:bg-[#F0FBF5]"}`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </section>

      <section className="flex flex-col gap-4 border border-gray-100 bg-white p-5 shadow-sm sm:flex-row sm:items-center sm:justify-between">
        <div className="flex gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[#E8F6EE] text-[#0B6B3A]">
            <FileCheck2 className="h-5 w-5" />
          </div>
          <div>
            <h3 className="font-bold text-[#1F2937]">{workflowInfo.uploadLabel}</h3>
            <p className="mt-1 text-sm text-[#6B7280]">PDF, JPG, JPEG, atau PNG; satu surat dapat memuat banyak mahasiswa.</p>
          </div>
        </div>
        <div>
          <button
            type="button"
            onClick={() => fileInput.current?.click()}
            disabled={uploading}
            data-testid="upload-active-letter-approval-button"
            className="inline-flex items-center gap-2 rounded-lg bg-[#0B6B3A] px-4 py-2.5 text-sm font-bold text-white hover:bg-[#07532d] disabled:opacity-60"
          >
            {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
            {uploading ? "Membaca surat..." : "Pilih Surat Aktif"}
          </button>
          <input
            ref={fileInput}
            type="file"
            multiple
            accept=".pdf,.jpg,.jpeg,.png"
            className="hidden"
            data-testid="active-letter-approval-file-input"
            onChange={(event) => upload(event.target.files)}
          />
        </div>
      </section>

      <section className="space-y-4" data-testid="active-letter-recommendations">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <div>
            <h3 className="font-display text-lg font-bold text-[#1F2937]">Rekomendasi Menunggu Persetujuan</h3>
            <p className="mt-1 text-sm text-[#6B7280]">{recommended.length} mahasiswa cocok dengan surat aktif.</p>
          </div>
          {recommended.length > 0 && (
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => decide("approve", true)}
                disabled={deciding}
                data-testid="approve-all-active-letter-button"
                className="rounded-lg bg-[#27AE60] px-4 py-2.5 text-sm font-bold text-white hover:bg-[#0B6B3A] disabled:opacity-60"
              >
                Setujui Semua yang Cocok
              </button>
              <button
                type="button"
                onClick={() => decide("approve")}
                disabled={deciding}
                data-testid="approve-selected-active-letter-button"
                className="rounded-lg border border-[#27AE60] px-4 py-2.5 text-sm font-bold text-[#0B6B3A] hover:bg-[#F0FBF5] disabled:opacity-60"
              >
                Setujui Pilihan
              </button>
            </div>
          )}
        </div>

        <div className="overflow-x-auto rounded-xl border border-gray-100 bg-white shadow-sm">
          <table className="w-full min-w-[58rem] text-left text-sm" data-testid="active-letter-approvals-table">
            <thead className="border-b border-gray-100 bg-[#F9FAFB] text-xs text-[#6B7280]">
              <tr>
                <th className="px-4 py-3 font-semibold">Pilih</th>
                <th className="px-4 py-3 font-semibold">Mahasiswa</th>
                <th className="px-4 py-3 font-semibold">NIM</th>
                <th className="px-4 py-3 font-semibold">Kampus</th>
                <th className="px-4 py-3 font-semibold">Wilayah</th>
                <th className="px-4 py-3 font-semibold">Alasan AI</th>
              </tr>
            </thead>
            <tbody>
              {loading ? <LoadingRow /> : recommended.length === 0 ? <EmptyRow /> : recommended.map((item) => (
                <tr key={item.id} className="border-b border-gray-50 last:border-0">
                  <td className="px-4 py-3.5">
                    <input
                      type="checkbox"
                      checked={Boolean(selected[item.id])}
                      onChange={(event) => setSelected((current) => ({ ...current, [item.id]: event.target.checked }))}
                      data-testid={`active-letter-approval-select-${item.id}`}
                    />
                  </td>
                  <td className="px-4 py-3.5 font-bold text-[#1F2937]">{item.student?.name || "-"}</td>
                  <td className="px-4 py-3.5 text-[#6B7280]">{item.student?.nim || "-"}</td>
                  <td className="px-4 py-3.5 text-[#6B7280]">{item.campus || "-"}</td>
                  <td className="px-4 py-3.5 text-[#6B7280]">{item.region || "-"}</td>
                  <td className="px-4 py-3.5 text-[#6B7280]">{item.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {quarantined.length > 0 && (
        <section className="border border-[#FDE68A] bg-[#FFFBEB] p-5" data-testid="active-letter-quarantine">
          <div className="flex items-center gap-2">
            <ShieldAlert className="h-5 w-5 text-[#B45309]" />
            <h3 className="font-display text-lg font-bold text-[#1F2937]">Perlu Ditinjau</h3>
          </div>
          <div className="mt-4 space-y-2">
            {quarantined.map((item) => (
              <div key={item.id} className="border border-[#FDE68A] bg-white p-3 text-sm">
                <p className="font-bold text-[#1F2937]">{item.student?.name || "Mahasiswa tidak terbaca"}</p>
                <p className="mt-1 text-[#6B7280]">{item.reason}</p>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function LoadingRow() {
  return (
    <tr>
      <td colSpan={6} className="px-5 py-12 text-center">
        <Loader2 className="mx-auto h-5 w-5 animate-spin text-[#27AE60]" />
      </td>
    </tr>
  );
}

function EmptyRow() {
  return (
    <tr>
      <td colSpan={6} className="px-5 py-12 text-center text-sm text-[#6B7280]">
        Belum ada rekomendasi surat aktif untuk proses ini.
      </td>
    </tr>
  );
}