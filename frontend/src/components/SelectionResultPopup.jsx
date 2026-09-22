import React, { useEffect, useState } from "react";
import { ArrowRight, CheckCircle2, PartyPopper, XCircle } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export default function SelectionResultPopup({ announcement, onMarkSeen, onDismiss }) {
  const [showResult, setShowResult] = useState(false);
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    setShowResult(false);
    setProcessing(false);
  }, [announcement?.id]);

  if (!announcement) {
    return null;
  }

  const isPassed = announcement.result === "passed";
  const isBeneficiary = announcement.stage === "beneficiary";

  const markSeen = async () => {
    setProcessing(true);
    try {
      await onMarkSeen(announcement.id);
    } finally {
      setProcessing(false);
    }
  };

  const viewResult = async () => {
    await markSeen();
    setShowResult(true);
  };

  const dismiss = async () => {
    if (processing) {
      return;
    }
    setProcessing(true);
    try {
      await onDismiss(announcement.id);
    } finally {
      setProcessing(false);
    }
  };

  return (
    <Dialog open onOpenChange={(open) => !open && dismiss()}>
      <DialogContent
        data-testid="selection-announcement-popup"
        className="max-w-md rounded-xl border-0 bg-white p-7"
      >
        {showResult ? (
          <SelectionResultDetail isPassed={isPassed} isBeneficiary={isBeneficiary} onDismiss={dismiss} processing={processing} />
        ) : (
          <>
            <DialogHeader className="text-left">
              <span className="flex h-12 w-12 items-center justify-center rounded-full bg-[#E8F6EE]">
                <CheckCircle2 className="h-6 w-6 text-[#27AE60]" />
              </span>
              <DialogTitle
                data-testid="selection-announcement-popup-title"
                className="pt-3 font-display text-2xl font-extrabold text-[#1F2937]"
              >
                Pengumuman Hasil Seleksi
              </DialogTitle>
              <DialogDescription className="leading-relaxed text-[#6B7280]">
                Pengumuman hasil seleksi telah diterbitkan oleh Admin. Silakan cek
                status Anda.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter className="mt-3">
              <button
                type="button"
                onClick={dismiss}
                disabled={processing}
                data-testid="dismiss-selection-announcement-button"
                className="rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-bold text-[#4B5563]"
              >
                Tutup
              </button>
              <button
                type="button"
                onClick={viewResult}
                disabled={processing}
                data-testid="view-selection-result-button"
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-[#27AE60] px-4 py-2.5 text-sm font-bold text-white disabled:opacity-60"
              >
                Lihat Hasil Seleksi
                <ArrowRight className="h-4 w-4" />
              </button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

function SelectionResultDetail({ isPassed, isBeneficiary, onDismiss, processing }) {
  const iconClass = isPassed ? "bg-[#E8F6EE] text-[#27AE60]" : "bg-[#FEF2F2] text-[#DC2626]";
  const title = isPassed
    ? `Selamat! Anda dinyatakan ${isBeneficiary ? "LOLOS MENJADI PENERIMA MANFAAT" : "LOLOS ADMINISTRASI"}.`
    : "Mohon maaf, Anda belum lolos pada tahapan ini.";
  const message = isPassed
    ? (isBeneficiary ? "Selamat menjadi Penerima Manfaat Masa Depan Jakarta Scholarship." : "Pantau akun MDJ Scholarship secara berkala terkait jadwal wawancara.")
    : "Terima kasih atas partisipasi Anda. Tetap semangat dan terus persiapkan diri untuk kesempatan berikutnya.";

  return (
    <div className="py-4 text-center" data-testid="selection-result-detail">
      <span className={`mx-auto flex h-16 w-16 items-center justify-center rounded-full ${iconClass}`}>
        {isPassed ? <PartyPopper className="h-8 w-8" /> : <XCircle className="h-8 w-8" />}
      </span>
      <h2
        data-testid={isPassed ? "selection-result-passed" : "selection-result-failed"}
        className="mt-5 font-display text-2xl font-extrabold leading-snug text-[#1F2937]"
      >
        {title}
      </h2>
      <p className="mt-3 text-sm leading-relaxed text-[#6B7280]">{message}</p>
      <button
        type="button"
        onClick={onDismiss}
        disabled={processing}
        data-testid="close-selection-result-button"
        className="mt-7 rounded-lg bg-[#0B6B3A] px-5 py-3 text-sm font-bold text-white disabled:opacity-60"
      >
        Selesai
      </button>
    </div>
  );
}