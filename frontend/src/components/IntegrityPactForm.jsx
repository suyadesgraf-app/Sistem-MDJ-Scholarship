import React, { useState } from "react";
import { CheckCircle2, FileLock2, Send, ShieldCheck } from "lucide-react";
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

const PACT_POINTS = [
  "Seluruh data, informasi, jawaban, dan dokumen yang saya input atau unggah dalam " +
    "sistem pendaftaran Masa Depan Jakarta Scholarship adalah benar, lengkap, sah, dan " +
    "dapat dipertanggungjawabkan.",
  "Saya tidak melakukan pemalsuan, manipulasi, pengubahan, penggunaan dokumen palsu, " +
    "maupun penyampaian informasi yang tidak sesuai dengan kondisi sebenarnya.",
  "Saya bersedia apabila panitia melakukan verifikasi, klarifikasi, dan pengecekan atas " +
    "data maupun dokumen yang saya sampaikan.",
  "Apabila di kemudian hari ditemukan ketidaksesuaian data, informasi tidak benar, atau " +
    "pemalsuan dokumen, saya bersedia menerima konsekuensi sesuai ketentuan program.",
  "Saya menyetujui seluruh ketentuan program dan bersedia menerima keputusan panitia " +
    "terkait hasil verifikasi serta seleksi.",
];

const CONSEQUENCES = [
  "Didiskualifikasi dari seluruh tahapan seleksi.",
  "Dibatalkan statusnya apabila telah dinyatakan sebagai penerima manfaat.",
  "Dicoret dari daftar calon penerima manfaat Masa Depan Jakarta Scholarship.",
  "Dilarang mengikuti program pada periode berikutnya sesuai ketentuan yang berlaku.",
];

export default function IntegrityPactForm({ onSubmit, reg, submitting }) {
  const [agreed, setAgreed] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const resubmission = Boolean(reg.revision_requested);
  const submitted = reg.status && reg.status !== "draft" && !resubmission;

  const confirmSubmission = async () => {
    setConfirmOpen(false);
    await onSubmit("submit", true);
  };

  if (submitted) {
    return (
      <section
        data-testid="pakta-submitted-state"
        className="border border-[#B7E4C7] bg-[#F0FBF5] p-6"
      >
        <FileLock2 className="h-7 w-7 text-[#0B6B3A]" />
        <h2 className="mt-3 font-display text-xl font-extrabold text-[#0B6B3A]">
          Pakta Integritas Telah Disetujui
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-[#245A3A]">
          Data dan dokumen telah dikirim kepada panitia seleksi. Dokumen hanya dapat diubah jika
          panitia memberikan izin edit kembali.
        </p>
      </section>
    );
  }

  if (resubmission) {
    return (
      <RevisionResubmission
        note={reg.revision_note}
        submitting={submitting}
        onSubmit={onSubmit}
      />
    );
  }

  return (
    <div className="space-y-6" data-testid="pakta-integritas-form">
      <section
        className="border-l-4 border-[#0B6B3A] bg-[#F0FBF5] px-5 py-5"
      >
        <p className="text-xs font-bold uppercase tracking-wide text-[#0B6B3A]">
          Masa Depan Jakarta Scholarship
        </p>
        <h2 className="mt-1 font-display text-2xl font-extrabold text-[#1F2937]">
          Pakta Integritas Pendaftar
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-[#4B5563]">
          Saya menyatakan dengan sebenar-benarnya bahwa:
        </p>
      </section>

      <ol className="space-y-4" data-testid="pakta-integritas-points">
        {PACT_POINTS.map((point, index) => (
          <li
            key={point}
            className={
              "flex gap-4 border-b border-gray-100 pb-4 text-sm leading-relaxed " +
              "text-[#374151]"
            }
          >
            <span
              className={
                "flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#E8F6EE] " +
                "text-xs font-extrabold text-[#0B6B3A]"
              }
            >
              {index + 1}
            </span>
            <span>{point}</span>
          </li>
        ))}
      </ol>

      <section className="border border-[#FDE68A] bg-[#FFFBEB] p-5">
        <h3 className="font-display text-base font-extrabold text-[#7A5C00]">
          Konsekuensi Ketidaksesuaian Data
        </h3>
        <ul className="mt-3 space-y-2 text-sm leading-relaxed text-[#5E4A00]">
          {CONSEQUENCES.map((item) => <li key={item}>• {item}</li>)}
        </ul>
      </section>

      <section className="border border-[#B7E4C7] bg-white p-5">
        <label className="flex cursor-pointer items-start gap-3">
          <input
            type="checkbox"
            checked={agreed}
            onChange={(event) => setAgreed(event.target.checked)}
            data-testid="pakta-agreement-checkbox"
            className="mt-0.5 h-5 w-5 accent-[#27AE60]"
          />
          <span className="text-sm leading-relaxed text-[#374151]">
            Dengan mencentang pernyataan ini, saya menyatakan telah membaca, memahami, dan
            menyetujui Pakta Integritas ini tanpa paksaan dari pihak mana pun.
            <strong className="mt-1 block text-[#1F2937]">
              Saya menyetujui Pakta Integritas Pendaftar Masa Depan Jakarta Scholarship.
            </strong>
          </span>
        </label>
      </section>

      <button
        type="button"
        onClick={() => setConfirmOpen(true)}
        disabled={!agreed || submitting}
        data-testid="open-pakta-submit-confirmation"
        className={[
          "inline-flex w-full items-center justify-center gap-2 rounded-lg bg-[#0B6B3A] px-5 py-3",
          "text-sm font-bold text-white transition-colors hover:bg-[#07532D]",
          "disabled:cursor-not-allowed disabled:opacity-50",
        ].join(" ")}
      >
        <Send className="h-4 w-4" />
        {submitting ? "Mengirim Data..." : "Kirim Data untuk Pendaftaran"}
      </button>

      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogContent
          data-testid="pakta-submit-confirmation-dialog"
          className="max-w-lg rounded-xl border-0 bg-white p-7"
        >
          <AlertDialogHeader className="text-left">
            <span className="flex h-12 w-12 items-center justify-center rounded-full bg-[#E8F6EE]">
              <ShieldCheck className="h-6 w-6 text-[#0B6B3A]" />
            </span>
            <AlertDialogTitle className="pt-3 font-display text-2xl font-extrabold text-[#1F2937]">
              Kirim Data Pendaftaran?
            </AlertDialogTitle>
            <AlertDialogDescription className="leading-relaxed text-[#6B7280]">
              Data dan dokumen yang dikirim ke panitia seleksi tidak dapat diedit kembali,
              kecuali tim panitia mengizinkan untuk diedit kembali.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="cancel-pakta-submit-button">
              Tidak, Kembali
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmSubmission}
              data-testid="confirm-pakta-submit-button"
              className="bg-[#27AE60] text-white hover:bg-[#0B6B3A]"
            >
              <CheckCircle2 className="mr-2 h-4 w-4" />
              Ya, Kirim Data
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

function RevisionResubmission({ note, onSubmit, submitting }) {
  const [confirmOpen, setConfirmOpen] = useState(false);

  const confirmResubmission = async () => {
    setConfirmOpen(false);
    await onSubmit("submit", true);
  };

  return (
    <div className="space-y-6" data-testid="pakta-resubmission-state">
      <section className="border-l-4 border-[#B8860B] bg-[#FFFBEB] px-5 py-5">
        <p className="text-xs font-bold uppercase tracking-wide text-[#7A5C00]">
          Perbaikan Berkas
        </p>
        <h2 className="mt-1 font-display text-2xl font-extrabold text-[#1F2937]">
          Perbaiki dan Kirim Ulang Berkas
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-[#5E4A00]">
          Lengkapi dokumen sesuai arahan panitia, kemudian kirim ulang untuk verifikasi kembali.
        </p>
      </section>
      <section
        data-testid="pakta-resubmission-note"
        className="border border-[#FDE68A] bg-white p-5"
      >
        <p className="text-xs font-bold uppercase tracking-wide text-[#7A5C00]">
          Catatan Panitia
        </p>
        <p className="mt-2 text-sm leading-relaxed text-[#374151]">
          {note || "Periksa kembali data dan dokumen sebelum mengirim ulang."}
        </p>
      </section>
      <button
        type="button"
        onClick={() => setConfirmOpen(true)}
        disabled={submitting}
        data-testid="open-pakta-resubmit-confirmation"
        className={[
          "inline-flex w-full items-center justify-center gap-2 rounded-lg bg-[#B8860B] px-5 py-3",
          "text-sm font-bold text-white transition-colors hover:bg-[#936C00]",
          "disabled:cursor-not-allowed disabled:opacity-50",
        ].join(" ")}
      >
        <Send className="h-4 w-4" />
        {submitting ? "Mengirim Ulang..." : "Kirim Ulang Berkas"}
      </button>
      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogContent
          data-testid="pakta-resubmit-confirmation-dialog"
          className="max-w-lg rounded-xl border-0 bg-white p-7"
        >
          <AlertDialogHeader className="text-left">
            <AlertDialogTitle className="font-display text-2xl font-extrabold text-[#1F2937]">
              Kirim Ulang Berkas Perbaikan?
            </AlertDialogTitle>
            <AlertDialogDescription className="leading-relaxed text-[#6B7280]">
              Berkas perbaikan akan dikirim kepada panitia untuk verifikasi ulang dan dikunci kembali.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="cancel-pakta-resubmit-button">
              Tidak, Kembali
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmResubmission}
              data-testid="confirm-pakta-resubmit-button"
              className="bg-[#B8860B] text-white hover:bg-[#936C00]"
            >
              Ya, Kirim Ulang
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}