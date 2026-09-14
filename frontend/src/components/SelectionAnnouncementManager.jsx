import React, { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { BellRing, CheckCircle2, Clock3, Send, UserCheck, UserX } from "lucide-react";
import api from "@/lib/api";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export default function SelectionAnnouncementManager() {
  const [category, setCategory] = useState("all");
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [publishOpen, setPublishOpen] = useState(false);
  const [publishing, setPublishing] = useState(false);

  const loadSummary = useCallback(async (selectedCategory) => {
    setLoading(true);
    try {
      const response = await api.get("/admin/selection-announcements/summary", {
        params: { category: selectedCategory },
      });
      setSummary(response.data);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Ringkasan pengumuman belum dapat dimuat.");
      setSummary(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSummary(category);
  }, [category, loadSummary]);

  const publishAnnouncement = async () => {
    setPublishing(true);
    try {
      const response = await api.post("/admin/selection-announcements/publish", { category });
      toast.success(response.data.message);
      setPublishOpen(false);
      await loadSummary(category);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Pengumuman belum berhasil dikirim.");
    } finally {
      setPublishing(false);
    }
  };

  const recipientCount = summary?.recipient_count || 0;
  const selectedCategoryLabel = category === "all" ? "Semua Kategori" : category;

  return (
    <div className="space-y-7" data-testid="selection-announcement-manager">
      <section className="border-l-4 border-[#0B6B3A] bg-[#F0FBF5] px-5 py-5">
        <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-[#0B6B3A]">
              Broadcast Hasil Seleksi
            </p>
            <h2 className="mt-1 font-display text-2xl font-extrabold text-[#1F2937]">
              Pengumuman Seleksi Berkas
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[#4B5563]">
              Kirim hasil seleksi kepada mahasiswa yang statusnya sudah ditetapkan.
            </p>
          </div>
          <label className="flex flex-col gap-1.5 text-sm font-bold text-[#1F2937]">
            Sasaran Pengumuman
            <select
              value={category}
              onChange={(event) => setCategory(event.target.value)}
              data-testid="selection-announcement-category-select"
              className="min-w-64 rounded-lg border border-[#B7E4C7] bg-white px-3 py-2.5 text-sm"
            >
              <option value="all">Semua Kategori</option>
              {(summary?.categories || []).map((item) => (
                <option key={item} value={item}>{item}</option>
              ))}
            </select>
          </label>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-3" data-testid="selection-announcement-summary">
        <SummaryMetric
          icon={UserCheck}
          label="Mahasiswa Lolos"
          testId="selection-announcement-passed-count"
          tone="green"
          value={summary?.passed_count || 0}
        />
        <SummaryMetric
          icon={UserX}
          label="Mahasiswa Tidak Lolos"
          testId="selection-announcement-failed-count"
          tone="red"
          value={summary?.failed_count || 0}
        />
        <SummaryMetric
          icon={Clock3}
          label="Masih Dalam Proses"
          testId="selection-announcement-pending-count"
          tone="gold"
          value={summary?.pending_count || 0}
        />
      </section>

      <section className="border border-gray-100 bg-white p-6 shadow-sm">
        <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-center">
          <div>
            <h3 className="font-display text-lg font-bold text-[#1F2937]">
              Siapkan Pengumuman
            </h3>
            <p className="mt-1 text-sm leading-relaxed text-[#6B7280]">
              {loading
                ? "Menyiapkan ringkasan penerima..."
                : `${recipientCount} mahasiswa siap menerima pengumuman untuk ${selectedCategoryLabel}.`}
            </p>
            {summary?.latest_publication && (
              <p
                className="mt-2 inline-flex items-center gap-1.5 text-xs font-bold text-[#0B6B3A]"
                data-testid="selection-announcement-latest-publication"
              >
                <CheckCircle2 className="h-4 w-4" />
                Broadcast terakhir sudah Published.
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={() => setPublishOpen(true)}
            disabled={loading || recipientCount === 0}
            data-testid="open-selection-announcement-dialog"
            className={[
              "inline-flex items-center justify-center gap-2 rounded-lg bg-[#0B6B3A] px-5 py-3",
              "text-sm font-bold text-white transition-colors hover:bg-[#07532D]",
              "disabled:cursor-not-allowed disabled:opacity-50",
            ].join(" ")}
          >
            <BellRing className="h-4 w-4" />
            Kirim Pengumuman Seleksi
          </button>
        </div>
      </section>

      <Dialog open={publishOpen} onOpenChange={setPublishOpen}>
        <DialogContent
          data-testid="selection-announcement-confirmation-dialog"
          className="max-w-lg rounded-xl border-0 bg-white p-7"
        >
          <DialogHeader className="text-left">
            <DialogTitle className="font-display text-2xl font-extrabold text-[#1F2937]">
              Publikasikan Hasil Seleksi?
            </DialogTitle>
            <DialogDescription className="leading-relaxed text-[#6B7280]">
              Notifikasi hanya akan dikirim kepada mahasiswa dengan hasil seleksi yang sudah ditetapkan.
            </DialogDescription>
          </DialogHeader>
          <div className="grid grid-cols-2 gap-3 py-2">
            <ConfirmationCount
              label="Lolos"
              testId="selection-announcement-confirm-passed"
              value={summary?.passed_count || 0}
            />
            <ConfirmationCount
              label="Tidak Lolos"
              testId="selection-announcement-confirm-failed"
              value={summary?.failed_count || 0}
            />
          </div>
          <p
            className="border-l-4 border-[#F2C94C] bg-[#FEF9E7] px-3 py-2.5 text-sm text-[#7A5C00]"
            data-testid="selection-announcement-confirm-category"
          >
            Sasaran: <strong>{selectedCategoryLabel}</strong>. Total penerima: {recipientCount} mahasiswa.
          </p>
          <DialogFooter>
            <button
              type="button"
              onClick={() => setPublishOpen(false)}
              disabled={publishing}
              data-testid="cancel-selection-announcement-button"
              className="rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-bold text-[#4B5563]"
            >
              Batal
            </button>
            <button
              type="button"
              onClick={publishAnnouncement}
              disabled={publishing}
              data-testid="confirm-selection-announcement-button"
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-[#27AE60] px-4 py-2.5 text-sm font-bold text-white disabled:opacity-60"
            >
              <Send className="h-4 w-4" />
              {publishing ? "Mengirim..." : "Publikasikan Pengumuman"}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function SummaryMetric({ icon: Icon, label, testId, tone, value }) {
  const tones = {
    green: "border-[#B7E4C7] bg-[#F0FBF5] text-[#0B6B3A]",
    red: "border-[#FECACA] bg-[#FEF2F2] text-[#B91C1C]",
    gold: "border-[#FDE68A] bg-[#FEF9E7] text-[#7A5C00]",
  };

  return (
    <div className={`border p-5 ${tones[tone]}`} data-testid={testId}>
      <Icon className="h-5 w-5" />
      <p className="mt-4 text-xs font-bold">{label}</p>
      <p className="mt-1 font-display text-3xl font-extrabold">{value}</p>
    </div>
  );
}

function ConfirmationCount({ label, testId, value }) {
  return (
    <div className="border border-gray-100 bg-[#FAFAFA] p-4" data-testid={testId}>
      <p className="text-xs font-bold text-[#6B7280]">{label}</p>
      <p className="mt-1 font-display text-2xl font-extrabold text-[#1F2937]">{value}</p>
    </div>
  );
}