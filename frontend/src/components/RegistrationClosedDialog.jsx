import React from "react";
import { CalendarX } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export default function RegistrationClosedDialog({ open, onClose }) {
  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent
        data-testid="registration-closed-dialog"
        className="max-w-md rounded-xl border-0 bg-white p-7"
      >
        <DialogHeader className="text-left">
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-[#FEF9E7]">
            <CalendarX className="h-6 w-6 text-[#B8860B]" />
          </span>
          <DialogTitle
            data-testid="registration-closed-dialog-title"
            className="pt-3 font-display text-2xl font-extrabold text-[#1F2937]"
          >
            Masa Pendaftaran Belum Dibuka
          </DialogTitle>
          <DialogDescription
            data-testid="registration-closed-dialog-message"
            className="leading-relaxed text-[#6B7280]"
          >
            Masa pendaftaran belum dibuka. Silakan pantau pengumuman MDJ Scholarship secara
            berkala.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="mt-3">
          <button
            type="button"
            onClick={onClose}
            data-testid="close-registration-closed-dialog"
            className={
              "rounded-lg bg-[#0B6B3A] px-5 py-3 text-sm font-bold text-white " +
              "transition-colors hover:bg-[#07532D]"
            }
          >
            Tutup
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}