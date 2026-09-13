import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import {
  BadgeCheck,
  Banknote,
  CheckCircle2,
  Download,
  Eye,
  FileCheck2,
  FileUp,
  Landmark,
  Loader2,
  Search,
  ShieldAlert,
  Upload,
  X,
} from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

const REGIONS = [
  "Jakarta Pusat",
  "Jakarta Utara",
  "Jakarta Barat",
  "Jakarta Selatan",
  "Jakarta Timur",
  "Kepulauan Seribu",
];

const DISBURSEMENT_STATUSES = [
  ["belum_diproses", "Belum Diproses"],
  ["menunggu_bukti", "Menunggu Bukti"],
  ["perlu_tinjau", "Perlu Ditinjau"],
  ["terverifikasi", "Terverifikasi"],
  ["disetujui", "Disetujui"],
  ["dicairkan", "Dicairkan"],
  ["ditunda", "Ditunda"],
];

const money = (value) => {
  if (value === null || value === undefined || value === "") return "Belum dicatat";
  return new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency: "IDR",
    maximumFractionDigits: 0,
  }).format(Number(value));
};

const stageLabel = (stage) => `Tahap ${stage === 1 ? "I" : "II"}`;

const emptyStageDraft = (stage) => ({
  stage,
  status: "belum_diproses",
  amount: "",
  disbursed_at: "",
  reference: "",
  notes: "",
});

export default function BeneficiaryManager() {
  const { user } = useAuth();
  const isManager = user?.role === "admin" || user?.role === "super_admin";
  const lockedRegion = user?.role === "admin_wilayah" ? user.region : "";
  const activeLetterRef = useRef(null);
  const proofRef = useRef(null);
  const [items, setItems] = useState([]);
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [region, setRegion] = useState("all");
  const [detail, setDetail] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [proofStage, setProofStage] = useState("1");
  const [reviewMapping, setReviewMapping] = useState({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get("/admin/beneficiaries", {
        params: { region: lockedRegion || (region === "all" ? undefined : region) },
      });
      setItems(response.data || []);
      if (isManager) {
        const reviewResponse = await api.get("/admin/beneficiary-reviews");
        setReviews(reviewResponse.data || []);
      }
    } catch (error) {
      toast.error(formatApiError(error.response?.data?.detail));
    } finally {
      setLoading(false);
    }
  }, [isManager, lockedRegion, region]);

  useEffect(() => {
    load();
  }, [load]);

  const visibleItems = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    if (!keyword) return items;
    return items.filter((item) => (
      `${item.name} ${item.nim} ${item.campus} ${item.email}`.toLowerCase().includes(keyword)
    ));
  }, [items, query]);

  const summary = useMemo(() => ({
    total: items.length,
    withLetter: items.filter((item) => item.active_letter_count > 0).length,
    stageOnePaid: items.filter((item) => item.stage_one?.status === "dicairkan").length,
    stageTwoPaid: items.filter((item) => item.stage_two?.status === "dicairkan").length,
  }), [items]);

  const openDetail = async (item) => {
    try {
      const response = await api.get(`/admin/beneficiaries/${item.user_id}`);
      setDetail(response.data);
    } catch (error) {
      toast.error(formatApiError(error.response?.data?.detail));
    }
  };

  const uploadFiles = async (endpoint, files, extras = {}) => {
    if (!files?.length) return;
    setUploading(true);
    const formData = new FormData();
    Object.entries(extras).forEach(([key, value]) => formData.append(key, value));
    Array.from(files).forEach((file) => formData.append("files", file));
    try {
      const response = await api.post(endpoint, formData, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 120000,
      });
      const result = response.data.summary || {};
      toast.success(
        `${result.matched || 0} cocok, ${result.review || 0} perlu ditinjau.`,
      );
      await load();
    } catch (error) {
      toast.error(formatApiError(error.response?.data?.detail));
    } finally {
      setUploading(false);
      if (activeLetterRef.current) activeLetterRef.current.value = "";
      if (proofRef.current) proofRef.current.value = "";
    }
  };

  const resolveReview = async (reviewId) => {
    const userId = reviewMapping[reviewId];
    if (!userId) {
      toast.error("Pilih Penerima Manfaat untuk memetakan item ini.");
      return;
    }
    try {
      await api.post(`/admin/beneficiary-reviews/${reviewId}/resolve`, { user_id: userId });
      toast.success("Item tinjauan berhasil dipetakan.");
      await load();
    } catch (error) {
      toast.error(formatApiError(error.response?.data?.detail));
    }
  };

  return (
    <div className="space-y-7" data-testid="beneficiary-manager">
      <section className="border-l-4 border-[#0B6B3A] bg-[#F0FBF5] px-5 py-4">
        <p className="text-xs font-bold uppercase tracking-wide text-[#0B6B3A]">
          Penerima Manfaat
        </p>
        <h2 className="mt-1 font-display text-2xl font-extrabold text-[#1F2937]">
          Kelola Data PM dan Pencairan Dana
        </h2>
        <p className="mt-2 max-w-4xl text-sm leading-relaxed text-[#6B7280]">
          Data hanya mencakup mahasiswa yang telah lulus tahap akhir. Bukti dan hasil AI tetap
          memerlukan persetujuan operasional Admin Provinsi atau Super Admin.
        </p>
      </section>

      {lockedRegion && (
        <div
          className="inline-flex items-center gap-2 rounded-lg border border-[#B7E4C7] bg-white px-4 py-2.5 text-sm font-bold text-[#0B6B3A]"
          data-testid="beneficiary-regional-scope"
        >
          <Landmark className="h-4 w-4" />
          Tampilan baca-saja: {lockedRegion}
        </div>
      )}

      <section className="grid grid-cols-2 gap-3 lg:grid-cols-4" data-testid="beneficiary-summary">
        <SummaryCard label="Total PM" value={summary.total} testId="beneficiary-total" />
        <SummaryCard label="Surat Aktif Terpasang" value={summary.withLetter} testId="beneficiary-letter-total" />
        <SummaryCard label="Tahap I Dicairkan" value={summary.stageOnePaid} testId="beneficiary-stage-one-total" />
        <SummaryCard label="Tahap II Dicairkan" value={summary.stageTwoPaid} testId="beneficiary-stage-two-total" />
      </section>

      {isManager && (
        <section className="grid gap-4 border border-gray-100 bg-white p-5 shadow-sm xl:grid-cols-2">
          <UploadPanel
            icon={FileCheck2}
            title="Import Surat Mahasiswa Aktif"
            description="PDF, JPG, JPEG, atau PNG. Satu surat dapat memuat banyak mahasiswa."
            buttonLabel={uploading ? "Memproses..." : "Pilih Surat Aktif"}
            testId="upload-active-letters-button"
            inputTestId="active-letters-input"
            inputRef={activeLetterRef}
            disabled={uploading}
            onSelect={(files) => uploadFiles("/admin/beneficiaries/active-letters", files)}
          />
          <UploadPanel
            icon={Banknote}
            title="Import Bukti Transfer"
            description="AI membaca transaksi massal dan menandai kecocokan rekening penerima."
            buttonLabel={uploading ? "Memproses..." : "Pilih Bukti Transfer"}
            testId="upload-transfer-proofs-button"
            inputTestId="transfer-proofs-input"
            inputRef={proofRef}
            disabled={uploading}
            stage={proofStage}
            onStageChange={setProofStage}
            onSelect={(files) => uploadFiles("/admin/beneficiaries/disbursement-proofs", files, {
              stage: proofStage,
            })}
          />
        </section>
      )}

      <section className="space-y-4" data-testid="beneficiary-table-section">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <div className="relative w-full sm:max-w-md">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Cari nama, NIM, kampus, atau email..."
              data-testid="beneficiary-search-input"
              className="w-full rounded-lg border border-gray-200 bg-white py-2.5 pl-9 pr-4 text-sm outline-none focus:border-[#27AE60] focus:ring-2 focus:ring-[#27AE60]/20"
            />
          </div>
          {!lockedRegion && (
            <select
              value={region}
              onChange={(event) => setRegion(event.target.value)}
              data-testid="beneficiary-region-filter"
              className="rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-sm font-semibold text-[#1F2937] outline-none focus:border-[#27AE60]"
            >
              <option value="all">Keseluruhan Wilayah</option>
              {REGIONS.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          )}
        </div>

        <div className="overflow-x-auto rounded-xl border border-gray-100 bg-white shadow-sm">
          <table className="w-full min-w-[72rem] text-left text-sm" data-testid="beneficiaries-table">
            <thead className="border-b border-gray-100 bg-[#F9FAFB] text-xs text-[#6B7280]">
              <tr>
                <th className="px-4 py-3 font-semibold">Penerima Manfaat</th>
                <th className="px-4 py-3 font-semibold">NIM / Kampus</th>
                <th className="px-4 py-3 font-semibold">Wilayah</th>
                <th className="px-4 py-3 font-semibold">Surat Aktif</th>
                <th className="px-4 py-3 font-semibold">Tahap I</th>
                <th className="px-4 py-3 font-semibold">Tahap II</th>
                <th className="px-4 py-3 text-right font-semibold">Aksi</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} className="px-5 py-12 text-center" data-testid="beneficiary-loading-state">
                    <Loader2 className="mx-auto h-5 w-5 animate-spin text-[#27AE60]" />
                  </td>
                </tr>
              ) : visibleItems.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-5 py-12 text-center text-sm text-[#6B7280]" data-testid="beneficiary-empty-state">
                    Belum ada Penerima Manfaat yang sesuai.
                  </td>
                </tr>
              ) : visibleItems.map((item) => (
                <tr key={item.user_id} className="border-b border-gray-50 last:border-0">
                  <td className="px-4 py-3.5">
                    <p className="font-bold text-[#1F2937]">{item.name}</p>
                    <p className="mt-0.5 text-xs text-[#6B7280]">{item.cpm_id}</p>
                  </td>
                  <td className="px-4 py-3.5 text-[#6B7280]">
                    <p>{item.nim}</p>
                    <p className="mt-0.5 text-xs">{item.campus}</p>
                  </td>
                  <td className="px-4 py-3.5 text-[#6B7280]">{item.region}</td>
                  <td className="px-4 py-3.5">
                    <span className="font-bold text-[#0B6B3A]">{item.active_letter_count} berkas</span>
                  </td>
                  <td className="px-4 py-3.5"><StageTag stage={item.stage_one} /></td>
                  <td className="px-4 py-3.5"><StageTag stage={item.stage_two} /></td>
                  <td className="px-4 py-3.5 text-right">
                    <button
                      type="button"
                      onClick={() => openDetail(item)}
                      data-testid={`view-beneficiary-${item.user_id}`}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-[#E8F6EE] px-3 py-2 text-xs font-bold text-[#0B6B3A] hover:bg-[#D3EFDF]"
                    >
                      <Eye className="h-3.5 w-3.5" />
                      Detail
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {isManager && reviews.length > 0 && (
        <ReviewPanel
          reviews={reviews}
          beneficiaries={items}
          mapping={reviewMapping}
          onMappingChange={(reviewId, userId) => setReviewMapping((current) => ({
            ...current,
            [reviewId]: userId,
          }))}
          onResolve={resolveReview}
        />
      )}

      {detail && (
        <BeneficiaryDetail
          detail={detail}
          isManager={isManager}
          onClose={() => setDetail(null)}
          onSaved={async () => {
            await load();
            const response = await api.get(`/admin/beneficiaries/${detail.user_id}`);
            setDetail(response.data);
          }}
        />
      )}
    </div>
  );
}

function SummaryCard({ label, value, testId }) {
  return (
    <div className="border border-gray-100 bg-white p-4 shadow-sm" data-testid={testId}>
      <p className="text-xs text-[#6B7280]">{label}</p>
      <p className="mt-1 font-display text-2xl font-extrabold text-[#0B6B3A]">{value}</p>
    </div>
  );
}

function StageTag({ stage }) {
  const status = stage?.status || "belum_diproses";
  const label = DISBURSEMENT_STATUSES.find(([value]) => value === status)?.[1] || status;
  const color = status === "dicairkan"
    ? "bg-[#E8F6EE] text-[#0B6B3A]"
    : status === "perlu_tinjau" || status === "ditunda"
      ? "bg-[#FEF3C7] text-[#92400E]"
      : "bg-[#F3F4F6] text-[#6B7280]";
  return <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${color}`}>{label}</span>;
}

function UploadPanel({
  icon: Icon,
  title,
  description,
  buttonLabel,
  testId,
  inputTestId,
  inputRef,
  disabled,
  stage,
  onStageChange,
  onSelect,
}) {
  return (
    <div className="flex flex-col gap-4 border border-gray-100 bg-[#FAFAFA] p-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[#E8F6EE] text-[#0B6B3A]">
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <h3 className="font-bold text-[#1F2937]">{title}</h3>
          <p className="mt-1 text-sm text-[#6B7280]">{description}</p>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {stage && (
          <select
            value={stage}
            onChange={(event) => onStageChange(event.target.value)}
            data-testid="transfer-proof-stage-select"
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-semibold text-[#1F2937]"
          >
            <option value="1">Tahap I</option>
            <option value="2">Tahap II</option>
          </select>
        )}
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={disabled}
          data-testid={testId}
          className="inline-flex items-center gap-2 rounded-lg bg-[#0B6B3A] px-4 py-2.5 text-sm font-bold text-white hover:bg-[#07532d] disabled:opacity-60"
        >
          {disabled ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
          {buttonLabel}
        </button>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.jpg,.jpeg,.png"
          className="hidden"
          data-testid={inputTestId}
          onChange={(event) => onSelect(event.target.files)}
        />
      </div>
    </div>
  );
}

function ReviewPanel({ reviews, beneficiaries, mapping, onMappingChange, onResolve }) {
  return (
    <section className="border border-[#FDE68A] bg-[#FFFBEB] p-5" data-testid="beneficiary-review-panel">
      <div className="flex items-center gap-2">
        <ShieldAlert className="h-5 w-5 text-[#B45309]" />
        <h3 className="font-display text-lg font-bold text-[#1F2937]">Daftar Tinjauan PM</h3>
      </div>
      <div className="mt-4 space-y-3">
        {reviews.map((review) => (
          <div key={review.id} className="border border-[#FDE68A] bg-white p-4" data-testid={`beneficiary-review-${review.id}`}>
            <p className="text-sm font-bold text-[#1F2937]">{review.reason}</p>
            <p className="mt-1 text-xs text-[#6B7280]">
              {review.payload?.name || "Tanpa nama"} · {review.payload?.nim || "Tanpa NIM"}
            </p>
            <div className="mt-3 flex flex-col gap-2 sm:flex-row">
              <select
                value={mapping[review.id] || ""}
                onChange={(event) => onMappingChange(review.id, event.target.value)}
                data-testid={`review-recipient-select-${review.id}`}
                className="min-w-0 flex-1 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
              >
                <option value="">Pilih Penerima Manfaat untuk konfirmasi</option>
                {beneficiaries.map((item) => (
                  <option key={item.user_id} value={item.user_id}>
                    {item.name} · {item.nim}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => onResolve(review.id)}
                data-testid={`resolve-beneficiary-review-${review.id}`}
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-[#B45309] px-4 py-2 text-sm font-bold text-white hover:bg-[#92400E]"
              >
                <CheckCircle2 className="h-4 w-4" />
                Konfirmasi
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function BeneficiaryDetail({ detail, isManager, onClose, onSaved }) {
  const [bank, setBank] = useState({
    bank_name: detail.bank?.bank_name || "",
    account_number: "",
  });
  const [stages, setStages] = useState(() => Object.fromEntries(
    [1, 2].map((stage) => {
      const existing = detail.disbursements?.find((item) => item.stage === stage);
      return [stage, { ...emptyStageDraft(stage), ...existing, amount: existing?.amount || "" }];
    }),
  ));
  const [saving, setSaving] = useState(false);
  const [audit, setAudit] = useState([]);

  const saveBank = async () => {
    setSaving(true);
    try {
      await api.put(`/admin/beneficiaries/${detail.user_id}/bank`, bank);
      toast.success("Data rekening disimpan.");
      await onSaved();
    } catch (error) {
      toast.error(formatApiError(error.response?.data?.detail));
    } finally {
      setSaving(false);
    }
  };

  const saveStage = async (stage) => {
    setSaving(true);
    const value = stages[stage];
    try {
      await api.put(`/admin/beneficiaries/${detail.user_id}/disbursements/${stage}`, {
        ...value,
        amount: value.amount === "" ? null : Number(value.amount),
      });
      toast.success(`${stageLabel(stage)} diperbarui.`);
      await onSaved();
    } catch (error) {
      toast.error(formatApiError(error.response?.data?.detail));
    } finally {
      setSaving(false);
    }
  };

  const loadAudit = async () => {
    try {
      const response = await api.get(`/admin/beneficiaries/${detail.user_id}/audit`);
      setAudit(response.data || []);
    } catch (error) {
      toast.error(formatApiError(error.response?.data?.detail));
    }
  };

  const downloadSource = async (sourceId, filename) => {
    try {
      const response = await api.get(`/admin/beneficiary-files/${sourceId}`, { responseType: "blob" });
      const url = window.URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      toast.error(formatApiError(error.response?.data?.detail));
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" data-testid="beneficiary-detail-modal">
      <div className="max-h-[92vh] w-full max-w-5xl overflow-y-auto rounded-xl bg-white shadow-2xl">
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-gray-100 bg-white px-6 py-4">
          <div>
            <h3 className="font-display text-xl font-bold text-[#1F2937]">{detail.name}</h3>
            <p className="mt-1 text-sm text-[#6B7280]">{detail.nim} · {detail.campus} · {detail.region}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            data-testid="close-beneficiary-detail"
            className="rounded-lg p-2 text-[#6B7280] hover:bg-gray-100"
            aria-label="Tutup detail Penerima Manfaat"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="space-y-6 p-6">
          <section className="grid gap-4 md:grid-cols-3">
            <InfoItem label="ID CPM" value={detail.cpm_id} />
            <InfoItem label="Program Studi" value={detail.study_program} />
            <InfoItem label="Semester" value={detail.semester} />
          </section>

          <section className="border border-gray-100 bg-[#FAFAFA] p-5" data-testid="beneficiary-bank-panel">
            <div className="flex items-center gap-2">
              <Landmark className="h-5 w-5 text-[#0B6B3A]" />
              <h4 className="font-display text-lg font-bold text-[#1F2937]">Rekening Penerima</h4>
            </div>
            {isManager ? (
              <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_1fr_auto]">
                <input
                  value={bank.bank_name}
                  onChange={(event) => setBank((current) => ({ ...current, bank_name: event.target.value }))}
                  placeholder="Nama bank"
                  data-testid="beneficiary-bank-name-input"
                  className="rounded-lg border border-gray-300 px-3 py-2.5 text-sm"
                />
                <input
                  value={bank.account_number}
                  onChange={(event) => setBank((current) => ({ ...current, account_number: event.target.value }))}
                  placeholder={`Nomor rekening baru (${detail.bank?.account_number_masked || "belum ada"})`}
                  data-testid="beneficiary-account-number-input"
                  className="rounded-lg border border-gray-300 px-3 py-2.5 text-sm"
                />
                <button
                  type="button"
                  onClick={saveBank}
                  disabled={saving}
                  data-testid="save-beneficiary-bank-button"
                  className="rounded-lg bg-[#0B6B3A] px-4 py-2.5 text-sm font-bold text-white hover:bg-[#07532d] disabled:opacity-60"
                >
                  Simpan Rekening
                </button>
              </div>
            ) : (
              <p className="mt-3 text-sm text-[#6B7280]" data-testid="beneficiary-bank-readonly">
                {detail.bank?.bank_name || "Bank belum dicatat"} · {detail.bank?.account_number_masked}
              </p>
            )}
          </section>

          <section className="border border-gray-100 bg-white p-5">
            <div className="flex items-center gap-2">
              <FileCheck2 className="h-5 w-5 text-[#0B6B3A]" />
              <h4 className="font-display text-lg font-bold text-[#1F2937]">Surat Mahasiswa Aktif</h4>
            </div>
            {detail.active_letters?.length ? (
              <div className="mt-4 space-y-2">
                {detail.active_letters.map((letter) => (
                  <div key={letter.source_id} className="flex flex-col gap-2 border-b border-gray-100 pb-3 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <p className="text-sm font-bold text-[#1F2937]">{letter.original_filename}</p>
                      <p className="mt-1 text-xs text-[#6B7280]">NIM terbaca: {letter.matched_nim}</p>
                    </div>
                    {isManager && (
                      <button
                        type="button"
                        onClick={() => downloadSource(letter.source_id, letter.original_filename)}
                        data-testid={`download-active-letter-${letter.source_id}`}
                        className="inline-flex items-center gap-2 text-sm font-bold text-[#0B6B3A] hover:underline"
                      >
                        <Download className="h-4 w-4" />
                        Buka Berkas
                      </button>
                    )}
                  </div>
                ))}
              </div>
            ) : <p className="mt-3 text-sm text-[#6B7280]">Belum ada surat aktif yang cocok.</p>}
          </section>

          <section className="grid gap-4 lg:grid-cols-2" data-testid="beneficiary-disbursement-panel">
            {[1, 2].map((stage) => (
              <DisbursementCard
                key={stage}
                stage={stage}
                value={stages[stage]}
                isManager={isManager}
                saving={saving}
                onChange={(field, value) => setStages((current) => ({
                  ...current,
                  [stage]: { ...current[stage], [field]: value },
                }))}
                onSave={() => saveStage(stage)}
              />
            ))}
          </section>

          <section className="border-t border-gray-100 pt-5" data-testid="beneficiary-audit-panel">
            <button
              type="button"
              onClick={loadAudit}
              data-testid="load-beneficiary-audit-button"
              className="inline-flex items-center gap-2 text-sm font-bold text-[#0B6B3A] hover:underline"
            >
              <FileUp className="h-4 w-4" />
              Lihat Riwayat Aktivitas
            </button>
            {audit.length > 0 && (
              <div className="mt-3 space-y-2">
                {audit.map((entry) => (
                  <p key={entry.id} className="border-l-2 border-[#B7E4C7] pl-3 text-xs text-[#6B7280]">
                    {entry.created_at} · {entry.actor_name} · {entry.action}
                  </p>
                ))}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

function DisbursementCard({ stage, value, isManager, saving, onChange, onSave }) {
  return (
    <div className="border border-gray-100 bg-[#FAFAFA] p-5" data-testid={`disbursement-stage-${stage}`}>
      <div className="flex items-center justify-between">
        <h4 className="font-display text-lg font-bold text-[#1F2937]">{stageLabel(stage)}</h4>
        <StageTag stage={value} />
      </div>
      {isManager ? (
        <div className="mt-4 space-y-3">
          <select
            value={value.status}
            onChange={(event) => onChange("status", event.target.value)}
            data-testid={`disbursement-status-${stage}`}
            className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm"
          >
            {DISBURSEMENT_STATUSES.map(([status, label]) => (
              <option key={status} value={status}>{label}</option>
            ))}
          </select>
          <input
            type="number"
            min="0"
            value={value.amount}
            onChange={(event) => onChange("amount", event.target.value)}
            placeholder="Nominal pencairan"
            data-testid={`disbursement-amount-${stage}`}
            className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm"
          />
          <input
            type="date"
            value={value.disbursed_at || ""}
            onChange={(event) => onChange("disbursed_at", event.target.value)}
            data-testid={`disbursement-date-${stage}`}
            className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm"
          />
          <input
            value={value.reference || ""}
            onChange={(event) => onChange("reference", event.target.value)}
            placeholder="Nomor referensi"
            data-testid={`disbursement-reference-${stage}`}
            className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm"
          />
          <textarea
            value={value.notes || ""}
            onChange={(event) => onChange("notes", event.target.value)}
            placeholder="Catatan pencairan"
            data-testid={`disbursement-notes-${stage}`}
            className="min-h-20 w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm"
          />
          <button
            type="button"
            onClick={onSave}
            disabled={saving}
            data-testid={`save-disbursement-${stage}`}
            className="w-full rounded-lg bg-[#27AE60] py-2.5 text-sm font-bold text-white hover:bg-[#0B6B3A] disabled:opacity-60"
          >
            Simpan {stageLabel(stage)}
          </button>
        </div>
      ) : (
        <div className="mt-4 space-y-2 text-sm text-[#6B7280]">
          <p>{money(value.amount)}</p>
          <p>{value.disbursed_at || "Tanggal belum dicatat"}</p>
          <p>{value.reference || "Referensi belum dicatat"}</p>
          <p>{value.proofs?.length || 0} bukti transfer terhubung</p>
        </div>
      )}
    </div>
  );
}

function InfoItem({ label, value }) {
  return (
    <div>
      <p className="text-xs text-[#6B7280]">{label}</p>
      <p className="mt-1 text-sm font-bold text-[#1F2937]">{value || "-"}</p>
    </div>
  );
}