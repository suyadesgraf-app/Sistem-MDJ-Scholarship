import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import {
  Banknote,
  Building2,
  CheckCircle2,
  FileUp,
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

const STATUSES = [
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

export default function DisbursementManager() {
  const { user } = useAuth();
  const isManager = user?.role === "admin" || user?.role === "super_admin";
  const lockedRegion = user?.role === "admin_wilayah" ? user.region : "";
  const proofInput = useRef(null);
  const [campuses, setCampuses] = useState([]);
  const [reviews, setReviews] = useState([]);
  const [reviewRecipients, setReviewRecipients] = useState([]);
  const [reviewMapping, setReviewMapping] = useState({});
  const [query, setQuery] = useState("");
  const [region, setRegion] = useState("all");
  const [proofStage, setProofStage] = useState("1");
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [detail, setDetail] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = { region: lockedRegion || (region === "all" ? undefined : region) };
      const response = await api.get("/admin/disbursements/campuses", { params });
      setCampuses(response.data || []);
      if (isManager) {
        const [reviewResponse, recipientResponse] = await Promise.all([
          api.get("/admin/beneficiary-reviews"),
          api.get("/admin/beneficiaries"),
        ]);
        setReviews(reviewResponse.data || []);
        setReviewRecipients(recipientResponse.data || []);
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

  const filteredCampuses = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    if (!keyword) return campuses;
    return campuses.filter((item) => item.campus.toLowerCase().includes(keyword));
  }, [campuses, query]);

  const summary = useMemo(() => ({
    campuses: campuses.length,
    recipients: campuses.reduce((total, item) => total + item.recipient_count, 0),
    stageOnePaid: campuses.filter((item) => item.stage_one.status === "dicairkan").length,
    proofs: campuses.reduce((total, item) => total + item.proof_count, 0),
  }), [campuses]);

  const openCampus = async (campus) => {
    try {
      const response = await api.get(`/admin/disbursements/campuses/${campus.campus_key}`);
      setDetail(response.data);
    } catch (error) {
      toast.error(formatApiError(error.response?.data?.detail));
    }
  };

  const upload = async (endpoint, files, extras = {}) => {
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
      toast.success(`${result.matched || 0} transaksi cocok, ${result.review || 0} ditinjau.`);
      await load();
    } catch (error) {
      toast.error(formatApiError(error.response?.data?.detail));
    } finally {
      setUploading(false);
      if (proofInput.current) proofInput.current.value = "";
    }
  };

  const resolveReview = async (reviewId) => {
    const userId = reviewMapping[reviewId];
    if (!userId) {
      toast.error("Pilih mahasiswa penerima untuk menyelesaikan tinjauan.");
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
    <div className="space-y-7" data-testid="disbursement-manager">
      <section className="border-l-4 border-[#0B6B3A] bg-[#F0FBF5] px-5 py-4">
        <p className="text-xs font-bold uppercase tracking-wide text-[#0B6B3A]">Keuangan Program</p>
        <h2 className="mt-1 font-display text-2xl font-extrabold text-[#1F2937]">Pencairan Dana</h2>
        <p className="mt-2 max-w-4xl text-sm leading-relaxed text-[#6B7280]">
          Ringkasan dana dikelompokkan per kampus dan wilayah untuk penerima manfaat yang telah
          lulus tahap akhir. Keputusan status pencairan selalu dilakukan oleh petugas berwenang.
        </p>
      </section>

      {lockedRegion && (
        <div
          className="inline-flex items-center gap-2 rounded-lg border border-[#B7E4C7] bg-white px-4 py-2.5 text-sm font-bold text-[#0B6B3A]"
          data-testid="disbursement-regional-scope"
        >
          <Building2 className="h-4 w-4" />
          Tampilan baca-saja wilayah {lockedRegion}
        </div>
      )}

      <section className="grid grid-cols-2 gap-3 lg:grid-cols-4" data-testid="disbursement-summary">
        <Metric label="Kampus Terlibat" value={summary.campuses} testId="disbursement-campus-total" />
        <Metric label="Penerima Manfaat" value={summary.recipients} testId="disbursement-recipient-total" />
        <Metric label="Kampus Tahap I Cair" value={summary.stageOnePaid} testId="disbursement-stage-one-total" />
        <Metric label="Bukti Terhubung" value={summary.proofs} testId="disbursement-proof-total" />
      </section>

      {isManager && (
        <section className="border border-gray-100 bg-white p-5 shadow-sm">
          <UploadAction
            icon={Banknote}
            title="Unggah Bukti Transfer"
            description="Satu bukti bisa memetakan transaksi ke banyak kampus dan wilayah."
            inputRef={proofInput}
            inputTestId="disbursement-proof-input"
            buttonTestId="upload-disbursement-proof-button"
            buttonLabel={uploading ? "Memproses..." : "Pilih Bukti Transfer"}
            disabled={uploading}
            stage={proofStage}
            onStageChange={setProofStage}
            onSelect={(files) => upload("/admin/disbursements/transfer-proofs", files, {
              stage: proofStage,
            })}
          />
        </section>
      )}

      <section className="space-y-4" data-testid="campus-disbursement-table-section">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <div className="relative w-full sm:max-w-md">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Cari nama kampus..."
              data-testid="campus-disbursement-search-input"
              className="w-full rounded-lg border border-gray-200 bg-white py-2.5 pl-9 pr-4 text-sm outline-none focus:border-[#27AE60] focus:ring-2 focus:ring-[#27AE60]/20"
            />
          </div>
          {!lockedRegion && (
            <select
              value={region}
              onChange={(event) => setRegion(event.target.value)}
              data-testid="campus-disbursement-region-filter"
              className="rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-sm font-semibold text-[#1F2937]"
            >
              <option value="all">Keseluruhan Wilayah</option>
              {REGIONS.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          )}
        </div>

        <div className="overflow-x-auto rounded-xl border border-gray-100 bg-white shadow-sm">
          <table className="w-full min-w-[68rem] text-left text-sm" data-testid="campus-disbursements-table">
            <thead className="border-b border-gray-100 bg-[#F9FAFB] text-xs text-[#6B7280]">
              <tr>
                <th className="px-4 py-3 font-semibold">No.</th>
                <th className="px-4 py-3 font-semibold">Kampus</th>
                <th className="px-4 py-3 font-semibold">Penerima Manfaat</th>
                <th className="px-4 py-3 font-semibold">Wilayah</th>
                <th className="px-4 py-3 font-semibold">Tahap I</th>
                <th className="px-4 py-3 font-semibold">Tahap II</th>
                <th className="px-4 py-3 font-semibold">Bukti Transfer</th>
                <th className="px-4 py-3 text-right font-semibold">Rincian</th>
              </tr>
            </thead>
            <tbody>
              {loading ? <LoadingRow /> : filteredCampuses.length === 0 ? <EmptyRow /> : (
                filteredCampuses.map((campus, index) => (
                  <tr key={campus.campus_key} className="border-b border-gray-50 last:border-0">
                    <td
                      className="px-4 py-3.5 font-semibold text-[#6B7280]"
                      data-testid={`campus-disbursement-row-number-${campus.campus_key}`}
                    >
                      {index + 1}
                    </td>
                    <td className="px-4 py-3.5 font-bold text-[#1F2937]">{campus.campus}</td>
                    <td className="px-4 py-3.5 text-[#6B7280]">{campus.recipient_count} mahasiswa</td>
                    <td className="px-4 py-3.5 text-[#6B7280]">{campus.region_count} wilayah</td>
                    <td className="px-4 py-3.5"><StatusTag value={campus.stage_one} /></td>
                    <td className="px-4 py-3.5"><StatusTag value={campus.stage_two} /></td>
                    <td className="px-4 py-3.5 font-bold text-[#0B6B3A]">{campus.proof_count} berkas</td>
                    <td className="px-4 py-3.5 text-right">
                      <button
                        type="button"
                        onClick={() => openCampus(campus)}
                        data-testid={`view-campus-disbursement-${campus.campus_key}`}
                        className="rounded-lg bg-[#E8F6EE] px-3 py-2 text-xs font-bold text-[#0B6B3A] hover:bg-[#D3EFDF]"
                      >
                        Buka Rincian
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      {isManager && reviews.length > 0 && (
        <ReviewQueue
          reviews={reviews}
          recipients={reviewRecipients}
          mapping={reviewMapping}
          onMappingChange={(reviewId, userId) => setReviewMapping((current) => ({
            ...current,
            [reviewId]: userId,
          }))}
          onResolve={resolveReview}
        />
      )}

      {detail && (
        <CampusDetail
          detail={detail}
          isManager={isManager}
          onClose={() => setDetail(null)}
          onSaved={async () => {
            await load();
            const response = await api.get(`/admin/disbursements/campuses/${detail.campus_key}`);
            setDetail(response.data);
          }}
        />
      )}
    </div>
  );
}

function Metric({ label, value, testId }) {
  return (
    <div className="border border-gray-100 bg-white p-4 shadow-sm" data-testid={testId}>
      <p className="text-xs text-[#6B7280]">{label}</p>
      <p className="mt-1 font-display text-2xl font-extrabold text-[#0B6B3A]">{value}</p>
    </div>
  );
}

function UploadAction({
  icon: Icon,
  title,
  description,
  inputRef,
  inputTestId,
  buttonTestId,
  buttonLabel,
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
            data-testid="campus-proof-stage-select"
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-semibold"
          >
            <option value="1">Tahap I</option>
            <option value="2">Tahap II</option>
          </select>
        )}
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={disabled}
          data-testid={buttonTestId}
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

function StatusTag({ value }) {
  const status = value?.status || "belum_diproses";
  const label = STATUSES.find(([item]) => item === status)?.[1] || "Bervariasi";
  const color = status === "dicairkan"
    ? "bg-[#E8F6EE] text-[#0B6B3A]"
    : status === "perlu_tinjau" || status === "ditunda" || status === "bervariasi"
      ? "bg-[#FEF3C7] text-[#92400E]"
      : "bg-[#F3F4F6] text-[#6B7280]";
  return <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${color}`}>{label}</span>;
}

function LoadingRow() {
  return (
    <tr>
      <td colSpan={8} className="px-5 py-12 text-center" data-testid="campus-disbursement-loading-state">
        <Loader2 className="mx-auto h-5 w-5 animate-spin text-[#27AE60]" />
      </td>
    </tr>
  );
}

function EmptyRow() {
  return (
    <tr>
      <td colSpan={8} className="px-5 py-12 text-center text-sm text-[#6B7280]" data-testid="campus-disbursement-empty-state">
        Belum ada kampus dengan Penerima Manfaat lulus akhir.
      </td>
    </tr>
  );
}

function ReviewQueue({ reviews, recipients, mapping, onMappingChange, onResolve }) {
  return (
    <section className="border border-[#FDE68A] bg-[#FFFBEB] p-5" data-testid="disbursement-review-queue">
      <div className="flex items-center gap-2">
        <ShieldAlert className="h-5 w-5 text-[#B45309]" />
        <h3 className="font-display text-lg font-bold text-[#1F2937]">Tinjauan Pemetaan Transfer</h3>
      </div>
      <div className="mt-4 space-y-3">
        {reviews.map((review) => (
          <div key={review.id} className="border border-[#FDE68A] bg-white p-4">
            <p className="text-sm font-bold text-[#1F2937]">{review.reason}</p>
            <p className="mt-1 text-xs text-[#6B7280]">
              {review.payload?.name || "Tanpa nama"} · {review.payload?.nim || "Tanpa NIM"}
            </p>
            <div className="mt-3 flex flex-col gap-2 sm:flex-row">
              <select
                value={mapping[review.id] || ""}
                onChange={(event) => onMappingChange(review.id, event.target.value)}
                data-testid={`disbursement-review-recipient-${review.id}`}
                className="min-w-0 flex-1 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
              >
                <option value="">Pilih mahasiswa penerima</option>
                {recipients.map((recipient) => (
                  <option key={recipient.user_id} value={recipient.user_id}>
                    {recipient.name} · {recipient.nim} · {recipient.campus}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => onResolve(review.id)}
                data-testid={`resolve-disbursement-review-${review.id}`}
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

function CampusDetail({ detail, isManager, onClose, onSaved }) {
  const [audit, setAudit] = useState([]);

  const loadAudit = async () => {
    try {
      const response = await api.get(`/admin/disbursements/campuses/${detail.campus_key}/audit`);
      setAudit(response.data || []);
    } catch (error) {
      toast.error(formatApiError(error.response?.data?.detail));
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" data-testid="campus-disbursement-detail-modal">
      <div className="max-h-[92vh] w-full max-w-6xl overflow-y-auto rounded-xl bg-white shadow-2xl">
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-gray-100 bg-white px-6 py-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-[#0B6B3A]">Pencairan per Kampus</p>
            <h3 className="mt-1 font-display text-xl font-bold text-[#1F2937]">{detail.campus}</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            data-testid="close-campus-disbursement-detail"
            className="rounded-lg p-2 text-[#6B7280] hover:bg-gray-100"
            aria-label="Tutup rincian pencairan kampus"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="space-y-5 p-6">
          {detail.regions.map((item) => (
            <RegionDetail
              key={item.region}
              item={item}
              campusKey={detail.campus_key}
              isManager={isManager}
              onSaved={onSaved}
            />
          ))}
          <section className="border-t border-gray-100 pt-5" data-testid="campus-disbursement-audit-panel">
            <button
              type="button"
              onClick={loadAudit}
              data-testid="load-campus-disbursement-audit-button"
              className="inline-flex items-center gap-2 text-sm font-bold text-[#0B6B3A] hover:underline"
            >
              <FileUp className="h-4 w-4" />
              Lihat Riwayat Pencairan Kampus
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

function RegionDetail({ item, campusKey, isManager, onSaved }) {
  return (
    <section className="border border-gray-100 bg-[#FAFAFA] p-5" data-testid={`campus-region-${item.region}`}>
      <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
        <div>
          <h4 className="font-display text-lg font-bold text-[#1F2937]">{item.region}</h4>
          <p className="mt-1 text-sm text-[#6B7280]">{item.recipient_count} mahasiswa penerima</p>
        </div>
        <details className="text-sm text-[#0B6B3A]">
          <summary className="cursor-pointer font-bold" data-testid={`view-campus-region-students-${item.region}`}>
            Lihat daftar mahasiswa
          </summary>
          <div className="mt-2 space-y-1 border-l-2 border-[#B7E4C7] pl-3 text-[#6B7280]">
            {item.recipients.map((recipient) => (
              <p key={recipient.user_id}>{recipient.name} · {recipient.nim}</p>
            ))}
          </div>
        </details>
      </div>
      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        {[item.stage_one, item.stage_two].map((stage) => (
          <CampusStageCard
            key={stage.stage}
            stage={stage}
            campusKey={campusKey}
            region={item.region}
            isManager={isManager}
            onSaved={onSaved}
          />
        ))}
      </div>
    </section>
  );
}

function CampusStageCard({ stage, campusKey, region, isManager, onSaved }) {
  const [draft, setDraft] = useState({
    status: stage.status,
    amount: stage.amount ?? "",
    disbursed_at: stage.disbursed_at || "",
    reference: stage.reference || "",
    notes: stage.notes || "",
  });
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      await api.put(
        `/admin/disbursements/campuses/${campusKey}/regions/${encodeURIComponent(region)}/stages/${stage.stage}`,
        { ...draft, amount: draft.amount === "" ? null : Number(draft.amount) },
      );
      toast.success(`${stageLabel(stage.stage)} ${region} diperbarui.`);
      await onSaved();
    } catch (error) {
      toast.error(formatApiError(error.response?.data?.detail));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="border border-gray-100 bg-white p-4" data-testid={`campus-stage-${stage.stage}-${region}`}>
      <div className="flex items-center justify-between gap-3">
        <h5 className="font-display text-base font-bold text-[#1F2937]">{stageLabel(stage.stage)}</h5>
        <StatusTag value={stage} />
      </div>
      {isManager ? (
        <div className="mt-4 space-y-3">
          <select
            value={draft.status}
            onChange={(event) => setDraft((current) => ({ ...current, status: event.target.value }))}
            data-testid={`campus-stage-status-${stage.stage}-${region}`}
            className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm"
          >
            {STATUSES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
          <input
            type="number"
            min="0"
            value={draft.amount}
            onChange={(event) => setDraft((current) => ({ ...current, amount: event.target.value }))}
            placeholder="Nominal kolektif"
            data-testid={`campus-stage-amount-${stage.stage}-${region}`}
            className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm"
          />
          <input
            type="date"
            value={draft.disbursed_at}
            onChange={(event) => setDraft((current) => ({ ...current, disbursed_at: event.target.value }))}
            data-testid={`campus-stage-date-${stage.stage}-${region}`}
            className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm"
          />
          <input
            value={draft.reference}
            onChange={(event) => setDraft((current) => ({ ...current, reference: event.target.value }))}
            placeholder="Nomor referensi"
            data-testid={`campus-stage-reference-${stage.stage}-${region}`}
            className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm"
          />
          <textarea
            value={draft.notes}
            onChange={(event) => setDraft((current) => ({ ...current, notes: event.target.value }))}
            placeholder="Catatan pencairan"
            data-testid={`campus-stage-notes-${stage.stage}-${region}`}
            className="min-h-20 w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm"
          />
          <button
            type="button"
            onClick={save}
            disabled={saving}
            data-testid={`save-campus-stage-${stage.stage}-${region}`}
            className="w-full rounded-lg bg-[#27AE60] py-2.5 text-sm font-bold text-white hover:bg-[#0B6B3A] disabled:opacity-60"
          >
            {saving ? "Menyimpan..." : `Simpan ${stageLabel(stage.stage)}`}
          </button>
        </div>
      ) : (
        <div className="mt-4 space-y-2 text-sm text-[#6B7280]">
          <p>{money(stage.amount)}</p>
          <p>{stage.disbursed_at || "Tanggal belum dicatat"}</p>
          <p>{stage.reference || "Referensi belum dicatat"}</p>
          <p>{stage.proofs?.length || 0} bukti transfer terhubung</p>
        </div>
      )}
      {stage.proofs?.length > 0 && (
        <div className="mt-3 border-t border-gray-100 pt-3 text-xs text-[#6B7280]">
          {stage.proofs.map((proof) => <p key={proof.source_id}>{proof.original_filename}</p>)}
        </div>
      )}
    </div>
  );
}