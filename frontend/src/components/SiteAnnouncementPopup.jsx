import React, { useState } from "react";
import { ArrowRight, Megaphone } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export default function SiteAnnouncementPopup({ announcement, onDismiss, onView }) {
  const [processing, setProcessing] = useState(false);

  if (!announcement) {
    return null;
  }

  const dismiss = async (viewAnnouncement) => {
    if (processing) {
      return;
    }
    setProcessing(true);
    try {
      await onDismiss(announcement.id);
      if (viewAnnouncement) {
        onView();
      }
    } finally {
      setProcessing(false);
    }
  };

  return (
    <Dialog open onOpenChange={(isOpen) => !isOpen && dismiss(false)}>
      <DialogContent
        data-testid="site-announcement-popup"
        className="max-w-md rounded-xl border-0 bg-white p-7"
      >
        <DialogHeader className="text-left">
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-[#E8F6EE]">
            <Megaphone className="h-6 w-6 text-[#0B6B3A]" />
          </span>
          <DialogTitle
            data-testid="site-announcement-popup-title"
            className="pt-3 font-display text-2xl font-extrabold text-[#1F2937]"
          >
            {announcement.title || "Pengumuman MDJ Scholarship"}
          </DialogTitle>
          <DialogDescription
            data-testid="site-announcement-popup-message"
            className="leading-relaxed text-[#6B7280]"
          >
            {announcement.message || "Ada pengumuman baru dari Admin MDJ."}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="mt-3">
          <button
            type="button"
            onClick={() => dismiss(false)}
            disabled={processing}
            data-testid="dismiss-site-announcement-popup"
            className={
              "rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-bold " +
              "text-[#4B5563]"
            }
          >
            Tutup
          </button>
          <button
            type="button"
            onClick={() => dismiss(true)}
            disabled={processing}
            data-testid="view-site-announcement-button"
            className={
              "inline-flex items-center justify-center gap-2 rounded-lg bg-[#0B6B3A] px-4 py-2.5 " +
              "text-sm font-bold text-white disabled:opacity-60"
            }
          >
            Lihat Pengumuman
            <ArrowRight className="h-4 w-4" />
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}