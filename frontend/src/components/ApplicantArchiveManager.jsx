import React, { useCallback, useEffect, useState } from "react";
import { Archive, ArchiveRestore, ShieldAlert, Users } from "lucide-react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

export default function ApplicantArchiveManager() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [archiving, setArchiving] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [archiveDialogOpen, setArchiveDialogOpen] = useState(false);
  const [restoreDialogOpen, setRestoreDialogOpen] = useState(false);

  const loadSummary = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get("/super-admin/applicant-archive/summary");
      setSummary(response.data);
    } catch (error) {
      toast.error(formatApiError(error.response?.data?.detail));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSummary();
  }, [loadSummary]);

  const archiveAllApplicants = async () => {
    setArchiving(true);
    try {
      const response = await api.post("/super-admin/applicant-archive");
      toast.success(response.data.message);
      setArchiveDialogOpen(false);
      await loadSummary();
    } catch (error) {
      toast.error(formatApiError(error.response?.data?.detail));
    } finally {
      setArchiving(false);
    }
  };

  const restoreLatestBatch = async () => {
    const batchId = summary?.restorable_batch?.id;
    if (!batchId) {
      return;
    }
    setRestoring(true);
    try {
      const response = await api.post(`/super-admin/applicant-archive/${batchId}/restore`);
      toast.success(response.data.message);
      setRestoreDialogOpen(false);
      await loadSummary();
    } catch (error) {
      toast.error(formatApiError(error.response?.data?.detail));
    } finally {
      setRestoring(false);
    }
  };

  const batch = summary?.restorable_batch;
  const activeCount = summary?.active_applicant_count || 0;
  const archivedCount = summary?.archived_applicant_count || 0;

  return (
    <div className="space-y-7" data-testid="applicant-archive-manager">
      <section className="border-l-4 border-[#B91C1C] bg-[#FEF2F2] px-5 py-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-[#B91C1C]">
              Pengelolaan Data Sensitif
            </p>
            <h2 className="mt-1 font-display text-2xl font-extrabold text-[#1F2937]">
              Arsip Data Pendaftar
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[#7F1D1D]">
              Arsipkan seluruh data mahasiswa pendaftar tanpa menghapusnya secara permanen.
              Hanya Super Admin yang dapat memulihkan batch arsip.
            </p>
          </div>
          <ShieldAlert className="h-8 w-8 shrink-0 text-[#B91C1C]" />
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2" data-testid="applicant-archive-summary">
        <ArchiveMetric
          icon={Users}
          label="Pendaftar Aktif"
          testId="active-applicant-count"
          tone="green"
          value={loading ? "…" : activeCount}
        />
        <ArchiveMetric
          icon={Archive}
          label="Pendaftar Diarsipkan"
          testId="archived-applicant-count"
          tone="red"
          value={loading ? "…" : archivedCount}
        />
      </section>

      <section className="border border-gray-100 bg-white p-6 shadow-sm">
        <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-center">
          <div>
            <h3 className="font-display text-lg font-bold text-[#1F2937]">
              Arsipkan Seluruh Data Pendaftar
            </h3>
            <p className="mt-1 max-w-2xl text-sm leading-relaxed text-[#6B7280]">
              Akun mahasiswa, profil, pendaftaran, dokumen, notifikasi, dan sesi aktif akan
              diarsipkan sebagai satu batch yang dapat dipulihkan.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setArchiveDialogOpen(true)}
            disabled={loading || activeCount === 0 || archiving}
            data-testid="open-archive-all-applicants-dialog"
            className={[
              "inline-flex items-center justify-center gap-2 rounded-lg bg-[#B91C1C] px-5 py-3",
              "text-sm font-bold text-white transition-colors hover:bg-[#991B1B]",
              "disabled:cursor-not-allowed disabled:opacity-50",
            ].join(" ")}
          >
            <Archive className="h-4 w-4" />
            Arsipkan Semua Pendaftar
          </button>
        </div>
      </section>

      {batch && (
        <section
          data-testid="restorable-archive-batch"
          className="border border-[#B7E4C7] bg-[#F0FBF5] p-6"
        >
          <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-center">
            <div>
              <p className="text-xs font-bold uppercase tracking-wide text-[#0B6B3A]">
                Batch Arsip Terakhir
              </p>
              <h3 className="mt-1 font-display text-lg font-bold text-[#1F2937]">
                {batch.applicant_count || 0} pendaftar dapat dipulihkan
              </h3>
              <p className="mt-1 text-sm leading-relaxed text-[#245A3A]">
                {batch.profile_count || 0} profil, {batch.document_count || 0} dokumen, dan
                {batch.registration_count || 0} pendaftaran tersimpan dalam batch ini.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setRestoreDialogOpen(true)}
              disabled={restoring}
              data-testid="open-restore-applicants-dialog"
              className={
                "inline-flex items-center justify-center gap-2 rounded-lg bg-[#0B6B3A] " +
                "px-5 py-3 text-sm font-bold text-white"
              }
            >
              <ArchiveRestore className="h-4 w-4" />
              Pulihkan Batch
            </button>
          </div>
        </section>
      )}

      <ArchiveConfirmation
        open={archiveDialogOpen}
        loading={archiving}
        onConfirm={archiveAllApplicants}
        onOpenChange={setArchiveDialogOpen}
        applicantCount={activeCount}
      />
      <RestoreConfirmation
        open={restoreDialogOpen}
        loading={restoring}
        onConfirm={restoreLatestBatch}
        onOpenChange={setRestoreDialogOpen}
        applicantCount={batch?.applicant_count || 0}
      />
    </div>
  );
}

function ArchiveMetric({ icon: Icon, label, testId, tone, value }) {
  const styles = {
    green: "border-[#B7E4C7] bg-[#F0FBF5] text-[#0B6B3A]",
    red: "border-[#FECACA] bg-[#FEF2F2] text-[#B91C1C]",
  };

  return (
    <div className={`border p-5 ${styles[tone]}`} data-testid={testId}>
      <Icon className="h-5 w-5" />
      <p className="mt-4 text-xs font-bold">{label}</p>
      <p className="mt-1 font-display text-3xl font-extrabold">{value}</p>
    </div>
  );
}

function ArchiveConfirmation({ applicantCount, loading, onConfirm, onOpenChange, open }) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent data-testid="archive-all-applicants-dialog" className="max-w-lg">
        <AlertDialogHeader className="text-left">
          <AlertDialogTitle className="font-display text-2xl font-extrabold text-[#B91C1C]">
            Arsipkan Semua Data Pendaftar?
          </AlertDialogTitle>
          <AlertDialogDescription className="leading-relaxed text-[#6B7280]">
            Sebanyak {applicantCount} akun mahasiswa beserta profil, pendaftaran, dokumen, dan
            notifikasinya akan dinonaktifkan dari data aktif. Data tidak dihapus permanen dan dapat
            dipulihkan oleh Super Admin.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel data-testid="cancel-archive-all-applicants-button">
            Tidak, Kembali
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={onConfirm}
            disabled={loading}
            data-testid="confirm-archive-all-applicants-button"
            className="bg-[#B91C1C] text-white hover:bg-[#991B1B]"
          >
            {loading ? "Mengarsipkan..." : "Ya, Arsipkan Semua Data"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

function RestoreConfirmation({ applicantCount, loading, onConfirm, onOpenChange, open }) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent data-testid="restore-applicants-dialog" className="max-w-lg">
        <AlertDialogHeader className="text-left">
          <AlertDialogTitle className="font-display text-2xl font-extrabold text-[#0B6B3A]">
            Pulihkan Data Pendaftar?
          </AlertDialogTitle>
          <AlertDialogDescription className="leading-relaxed text-[#6B7280]">
            Sebanyak {applicantCount} akun mahasiswa akan dikembalikan ke data aktif.
            Mahasiswa dapat masuk kembali dengan kredensial yang sama.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel data-testid="cancel-restore-applicants-button">
            Tidak, Kembali
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={onConfirm}
            disabled={loading}
            data-testid="confirm-restore-applicants-button"
            className="bg-[#0B6B3A] text-white hover:bg-[#07532D]"
          >
            {loading ? "Memulihkan..." : "Ya, Pulihkan Data"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}