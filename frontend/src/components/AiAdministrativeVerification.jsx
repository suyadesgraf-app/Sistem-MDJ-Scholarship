import React, { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  CheckSquare,
  FileCheck,
  Loader2,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import api from "@/lib/api";

export default function AiAdministrativeVerification() {
  const [recommendations, setRecommendations] = useState([]);
  const [filter, setFilter] = useState("all");
  const [selected, setSelected] = useState([]);
  const [analyzing, setAnalyzing] = useState(false);
  const [approving, setApproving] = useState(false);
  const [confirmation, setConfirmation] = useState(null);

  const load = useCallback(async () => {
    try {
      const response = await api.get("/admin/verification-recommendations");
      setRecommendations(response.data || []);
    } catch {
      toast.error("Rekomendasi verifikasi belum dapat dimuat.");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const analyze = async () => {
    setAnalyzing(true);
    try {
      const response = await api.post("/admin/verification-recommendations/generate");
      await load();
      toast.success(
        `Analisis selesai: ${response.data.recommended} rekomendasi dan ${response.data.review} perlu ditinjau.`,
      );
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Analisis AI belum dapat dijalankan.");
    } finally {
      setAnalyzing(false);
    }
  };

  const recommended = useMemo(
    () => recommendations.filter((item) => item.recommendation === "recommended"),
    [recommendations],
  );
  const visible = useMemo(() => {
    if (filter === "recommended") return recommended;
    if (filter === "review") return recommendations.filter((item) => item.recommendation === "review");
    return recommendations;
  }, [filter, recommendations, recommended]);

  const toggleSelected = (id) => {
    setSelected((previous) => (
      previous.includes(id) ? previous.filter((item) => item !== id) : [...previous, id]
    ));
  };

  const approve = async () => {
    if (!confirmation) return;
    setApproving(true);
    try {
      const response = await api.post("/admin/verification-recommendations/approve", {
        recommendation_ids: confirmation.mode === "selected" ? selected : [],
        approve_all: confirmation.mode === "all",
      });
      setRecommendations((previous) => previous.filter((item) => (
        confirmation.mode === "all" || !selected.includes(item.id)
      )));
      setSelected([]);
      setConfirmation(null);
      toast.success(`${response.data.approved} peserta disetujui Lolos Administrasi.`);
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Persetujuan massal belum berhasil.");
    } finally {
      setApproving(false);
    }
  };

  const counts = {
    total: recommendations.length,
    recommended: recommended.length,
    review: recommendations.filter((item) => item.recommendation === "review").length,
  };

  return (
    <div className="space-y-7" data-testid="ai-verification-manager">
      <section className="border-l-4 border-[#0B6B3A] bg-[#F0FBF5] px-5 py-4">
        <p className="text-xs font-bold uppercase tracking-wide text-[#0B6B3A]">Verifikasi Administrasi AI</p>
        <h2 className="mt-1 font-display text-2xl font-extrabold text-[#1F2937]">
          Rekomendasi kelulusan administrasi dengan persetujuan Admin
        </h2>
        <p className="mt-2 max-w-4xl text-sm leading-relaxed text-[#6B7280]">
          AI memeriksa data wajib, kampus terdaftar, serta 10 berkas persyaratan. Status peserta tidak
          berubah sampai Admin menyetujui rekomendasi.
        </p>
      </section>

      <section className="flex flex-col justify-between gap-4 border border-gray-100 bg-white p-5 shadow-sm lg:flex-row lg:items-center">
        <div className="flex items-start gap-3">
          <Bot className="mt-0.5 h-6 w-6 shrink-0 text-[#0B6B3A]" />
          <p className="max-w-2xl text-sm leading-relaxed text-[#6B7280]">
            Peserta berstatus Terkirim atau Verifikasi Administrasi akan dianalisis. Data yang kurang
            tetap berada dalam daftar Perlu Ditinjau tanpa perubahan status.
          </p>
        </div>
        <button
          type="button"
          onClick={analyze}
          disabled={analyzing}
          data-testid="generate-ai-verification-button"
          className="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg bg-[#0B6B3A] px-5 py-2.5 text-sm font-bold text-white transition-colors hover:bg-[#07532d] disabled:opacity-60"
        >
          {analyzing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
          {analyzing ? "Menganalisis..." : "Analisis dengan AI"}
        </button>
      </section>

      <section className="grid grid-cols-3 gap-3" data-testid="ai-verification-summary">
        <SummaryCard label="Dianalisis" value={counts.total} testId="ai-verification-total" />
        <SummaryCard label="Direkomendasikan" value={counts.recommended} testId="ai-verification-recommended" />
        <SummaryCard label="Perlu Ditinjau" value={counts.review} testId="ai-verification-review" />
      </section>

      <section className="border border-gray-100 bg-white shadow-sm" data-testid="ai-verification-results">
        <div className="flex flex-col gap-4 border-b border-gray-100 px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-wrap gap-2">
            <FilterButton label="Semua" active={filter === "all"} onClick={() => setFilter("all")} testId="verification-filter-all" />
            <FilterButton label="Direkomendasikan" active={filter === "recommended"} onClick={() => setFilter("recommended")} testId="verification-filter-recommended" />
            <FilterButton label="Perlu Ditinjau" active={filter === "review"} onClick={() => setFilter("review")} testId="verification-filter-review" />
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" disabled={!selected.length} onClick={() => setConfirmation({ mode: "selected", count: selected.length })} data-testid="approve-selected-verification-button" className="rounded-lg border border-[#27AE60] px-4 py-2 text-sm font-bold text-[#0B6B3A] hover:bg-[#F0FBF5] disabled:cursor-not-allowed disabled:opacity-50">
              Setujui Terpilih ({selected.length})
            </button>
            <button type="button" disabled={!recommended.length} onClick={() => setConfirmation({ mode: "all", count: recommended.length })} data-testid="approve-all-verification-button" className="rounded-lg bg-[#27AE60] px-4 py-2 text-sm font-bold text-white hover:bg-[#0B6B3A] disabled:cursor-not-allowed disabled:opacity-50">
              Setujui Semua Rekomendasi
            </button>
          </div>
        </div>

        <div className="divide-y divide-gray-100">
          {visible.length === 0 ? (
            <div className="py-12 text-center" data-testid="empty-ai-verification-results">
              <ShieldCheck className="mx-auto h-8 w-8 text-gray-300" />
              <p className="mt-3 text-sm font-semibold text-[#6B7280]">Belum ada hasil analisis.</p>
            </div>
          ) : visible.map((item) => (
            <RecommendationRow
              key={item.id}
              item={item}
              checked={selected.includes(item.id)}
              onToggle={() => toggleSelected(item.id)}
            />
          ))}
        </div>
      </section>

      {confirmation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" data-testid="verification-approval-dialog">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-2xl">
            <CheckCircle2 className="h-9 w-9 text-[#27AE60]" />
            <h3 className="mt-3 font-display text-xl font-bold text-[#1F2937]">Setujui Lolos Administrasi?</h3>
            <p className="mt-2 text-sm leading-relaxed text-[#6B7280]">
              Status {confirmation.count} peserta akan diperbarui menjadi Lolos Administrasi dan peserta
              akan menerima notifikasi.
            </p>
            <div className="mt-6 flex justify-end gap-2">
              <button type="button" onClick={() => setConfirmation(null)} data-testid="cancel-verification-approval-button" className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-bold text-[#1F2937] hover:bg-gray-50">Batal</button>
              <button type="button" onClick={approve} disabled={approving} data-testid="confirm-verification-approval-button" className="inline-flex items-center gap-2 rounded-lg bg-[#27AE60] px-4 py-2 text-sm font-bold text-white hover:bg-[#0B6B3A] disabled:opacity-60">{approving && <Loader2 className="h-4 w-4 animate-spin" />}Setujui</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function SummaryCard({ label, value, testId }) {
  return <div className="border border-gray-100 bg-white p-4 shadow-sm" data-testid={testId}><p className="text-xs text-[#6B7280]">{label}</p><p className="mt-1 font-display text-2xl font-extrabold text-[#0B6B3A]">{value}</p></div>;
}

function FilterButton({ label, active, onClick, testId }) {
  return <button type="button" onClick={onClick} data-testid={testId} className={`rounded-lg px-3 py-2 text-sm font-bold transition-colors ${active ? "bg-[#E8F6EE] text-[#0B6B3A]" : "text-[#6B7280] hover:bg-gray-50"}`}>{label}</button>;
}

function RecommendationRow({ item, checked, onToggle }) {
  const recommended = item.recommendation === "recommended";
  return (
    <div className="flex flex-col gap-4 p-5 lg:flex-row lg:items-start lg:justify-between" data-testid={`verification-recommendation-${item.id}`}>
      <div className="flex min-w-0 gap-3">
        {recommended ? <input type="checkbox" checked={checked} onChange={onToggle} data-testid={`verification-select-${item.id}`} className="mt-1 h-4 w-4 accent-[#27AE60]" /> : <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-[#D99A00]" />}
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2"><p className="text-sm font-bold text-[#1F2937]">{item.name}</p><span className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${recommended ? "bg-[#E8F6EE] text-[#0B6B3A]" : "bg-[#FEF3C7] text-[#92400E]"}`}>{recommended ? "Direkomendasikan" : "Perlu Ditinjau"}</span></div>
          <p className="mt-1 text-xs text-[#6B7280]">ID: {item.cpm_id} · Skor kelengkapan: {item.score}% · {item.document_count}/10 berkas</p>
          <p className="mt-2 text-sm leading-relaxed text-[#6B7280]">{item.ai_summary}</p>
          {item.issues?.length > 0 && <p className="mt-2 text-xs font-semibold leading-relaxed text-[#92400E]">Perlu dilengkapi: {item.issues.join("; ")}</p>}
        </div>
      </div>
      <div className="shrink-0 text-left lg:text-right"><p className="text-xs font-bold text-[#6B7280]">Hasil AI</p><p className="mt-1 text-sm font-bold text-[#0B6B3A]">{recommended ? "Layak Lolos Administrasi" : "Belum direkomendasikan"}</p></div>
    </div>
  );
}