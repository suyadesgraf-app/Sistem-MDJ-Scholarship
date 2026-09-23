import React, { useState } from "react";
import { ArrowRight, Megaphone } from "lucide-react";
import { API } from "@/lib/api";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export default function SiteAnnouncementPopup({
  announcement,
  onDismiss,
  onView,
  variant = "student",
}) {
  const [processing, setProcessing] = useState(false);

  if (!announcement) {
    return null;
  }

  const testIdPrefix = variant === "landing" ? "landing-announcement" : "site-announcement";
  const imageUrl = announcement.banner?.url
    ? `${API.replace("/api", "")}${announcement.banner.url}`
    : null;
  const message = announcement.message || announcement.summary || "Ada pengumuman baru dari Admin MDJ.";

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
        data-testid={`${testIdPrefix}-popup`}
        className="max-w-md rounded-xl border-0 bg-white p-7"
      >
        <DialogHeader className="text-left">
          {imageUrl && (
            <img
              src={imageUrl}
              alt={`Banner ${announcement.title}`}
              className="mb-3 aspect-[1.8] w-full rounded-lg object-cover"
              data-testid={`${testIdPrefix}-banner`}
            />
          )}
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-[#E8F6EE]">
            <Megaphone className="h-6 w-6 text-[#0B6B3A]" />
          </span>
          <DialogTitle
            data-testid={`${testIdPrefix}-popup-title`}
            className="pt-3 font-display text-2xl font-extrabold text-[#1F2937]"
          >
            {announcement.title || "Pengumuman MDJ Scholarship"}
          </DialogTitle>
          <DialogDescription
            data-testid={`${testIdPrefix}-popup-message`}
            className="leading-relaxed text-[#6B7280]"
          >
            {message}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="mt-3">
          <button
            type="button"
            onClick={() => dismiss(false)}
            disabled={processing}
            data-testid={`dismiss-${testIdPrefix}-popup`}
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
            data-testid={`view-${testIdPrefix}-button`}
            className={
              "inline-flex items-center justify-center gap-2 rounded-lg bg-[#0B6B3A] px-4 py-2.5 " +
              "text-sm font-bold text-white disabled:opacity-60"
            }
          >
            {variant === "landing" ? "Baca Selengkapnya" : "Lihat Pengumuman"}
            <ArrowRight className="h-4 w-4" />
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}