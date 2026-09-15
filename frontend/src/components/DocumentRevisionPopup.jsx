import React, { useState } from "react";
import { ClipboardPenLine, FileWarning } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export default function DocumentRevisionPopup({ revision, onDismiss, onRepair }) {
  const [processing, setProcessing] = useState(false);

  if (!revision) {
    return null;
  }

  const dismiss = async (action) => {
    if (processing) {
      return;
    }
    setProcessing(true);
    try {
      await onDismiss(revision.id);
      if (action === "repair") {
        onRepair();
      }
    } finally {
      setProcessing(false);
    }
  };

  return (
    <Dialog open onOpenChange={(isOpen) => !isOpen && dismiss("close")}>
      <DialogContent
        data-testid="document-revision-popup"
        className="max-w-md rounded-xl border-0 bg-white p-7"
      >
        <DialogHeader className="text-left">
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-[#FFFBEB]">
            <FileWarning className="h-6 w-6 text-[#B8860B]" />
          </span>
          <DialogTitle
            data-testid="document-revision-popup-title"
            className="pt-3 font-display text-2xl font-extrabold text-[#1F2937]"
          >
            Berkas Perlu Dilengkapi
          </DialogTitle>
          <DialogDescription className="leading-relaxed text-[#6B7280]">
            Panitia seleksi telah mengembalikan berkas Anda untuk diperbaiki. Periksa dan
            lengkapi data maupun dokumen sesuai catatan berikut.
          </DialogDescription>
        </DialogHeader>
        <section
          data-testid="document-revision-popup-note"
          className="border-l-4 border-[#F2C94C] bg-[#FFFBEB] px-4 py-3"
        >
          <p className="text-xs font-bold uppercase tracking-wide text-[#7A5C00]">
            Catatan Panitia
          </p>
          <p className="mt-1 text-sm leading-relaxed text-[#5E4A00]">
            {revision.revision_note || revision.message}
          </p>
        </section>
        <DialogFooter className="mt-3">
          <button
            type="button"
            onClick={() => dismiss("close")}
            disabled={processing}
            data-testid="dismiss-document-revision-popup"
            className="rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-bold text-[#4B5563]"
          >
            Tutup
          </button>
          <button
            type="button"
            onClick={() => dismiss("repair")}
            disabled={processing}
            data-testid="repair-document-revision-button"
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-[#B8860B] px-4 py-2.5 text-sm font-bold text-white disabled:opacity-60"
          >
            <ClipboardPenLine className="h-4 w-4" />
            Perbaiki Berkas
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}