import React from "react";
import { AlertCircle, FileText, GraduationCap } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export default function PactRequirementsDialog({
  missingDocuments,
  missingEducation,
  onClose,
  open,
}) {
  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent
        data-testid="pakta-incomplete-dialog"
        className="max-w-lg rounded-xl border-0 bg-white p-7"
      >
        <DialogHeader className="text-left">
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-[#FEF2F2]">
            <AlertCircle className="h-6 w-6 text-[#DC2626]" />
          </span>
          <DialogTitle className="pt-3 font-display text-2xl font-extrabold text-[#1F2937]">
            Lengkapi Data Sebelum Pakta Integritas
          </DialogTitle>
          <DialogDescription className="leading-relaxed text-[#6B7280]">
            Formulir Pakta Integritas dapat dibuka setelah seluruh Data Pendidikan dan dokumen
            persyaratan lengkap.
          </DialogDescription>
        </DialogHeader>
        <div className="max-h-64 space-y-4 overflow-y-auto pr-1">
          {missingEducation.length > 0 && (
            <MissingGroup
              icon={GraduationCap}
              items={missingEducation}
              testId="pakta-missing-education"
              title="Data Pendidikan yang Belum Terisi"
            />
          )}
          {missingDocuments.length > 0 && (
            <MissingGroup
              icon={FileText}
              items={missingDocuments}
              testId="pakta-missing-documents"
              title="Dokumen yang Belum Diunggah"
            />
          )}
        </div>
        <DialogFooter>
          <button
            type="button"
            onClick={onClose}
            data-testid="close-pakta-incomplete-dialog"
            className="rounded-lg bg-[#0B6B3A] px-5 py-3 text-sm font-bold text-white"
          >
            Saya Mengerti
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function MissingGroup({ icon: Icon, items, testId, title }) {
  return (
    <section className="border border-[#FDE68A] bg-[#FFFBEB] p-4" data-testid={testId}>
      <h3 className="flex items-center gap-2 text-sm font-bold text-[#7A5C00]">
        <Icon className="h-4 w-4" />
        {title}
      </h3>
      <ul className="mt-2 space-y-1.5 text-sm text-[#4B5563]">
        {items.map((item) => <li key={item}>• {item}</li>)}
      </ul>
    </section>
  );
}