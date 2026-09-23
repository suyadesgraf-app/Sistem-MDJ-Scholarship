import React, { useState } from "react";
import { toast } from "sonner";
import { Loader2, UserPlus, X } from "lucide-react";
import api from "@/lib/api";

const INPUT_CLASS = [
  "mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm",
  "outline-none focus:border-[#27AE60] focus:ring-2 focus:ring-[#27AE60]/20",
].join(" ");

const EMPTY_FORM = {
  name: "",
  nik: "",
  email: "",
  phone: "",
  campus: "",
  nim: "",
};

export default function ManualParticipantDialog({ onClose, onCreated }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);

  const setField = (field, value) => {
    setForm((previous) => ({ ...previous, [field]: value }));
  };

  const submit = async (event) => {
    event.preventDefault();
    setSaving(true);
    try {
      const response = await api.post("/admin/participants/manual", form);
      if (response.data.campus_warning) {
        toast.warning(response.data.campus_warning);
      } else {
        toast.success("Pendaftar baru berhasil ditambahkan.");
      }
      onCreated();
      onClose();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Gagal menambahkan pendaftar.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-[#1F2937]/50 p-4"
      data-testid="manual-participant-dialog"
      onClick={onClose}
    >
      <form
        className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white shadow-2xl"
        onSubmit={submit}
        onClick={(event) => event.stopPropagation()}
      >
        <div
          className="sticky top-0 z-10 flex items-start justify-between border-b bg-white px-6 py-5"
        >
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-[#0B6B3A]">Data Peserta</p>
            <h2 className="mt-1 font-display text-xl font-extrabold text-[#1F2937]">
              Tambah Pendaftar
            </h2>
            <p className="mt-1 text-sm text-[#6B7280]">
              Pendaftar dibuat dengan status Terkirim tanpa berkas. Kampus baru dibuat otomatis
              bila belum ada.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            data-testid="close-manual-participant-dialog"
            className="rounded-lg p-2 text-[#6B7280] transition-colors hover:bg-gray-100"
            aria-label="Tutup tambah pendaftar"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="grid gap-5 p-6 sm:grid-cols-2">
          <Field label="Nama Lengkap" htmlFor="manual-participant-name">
            <input
              id="manual-participant-name"
              value={form.name}
              onChange={(event) => setField("name", event.target.value)}
              data-testid="manual-participant-name"
              className={INPUT_CLASS}
              required
            />
          </Field>
          <Field label="NIK" htmlFor="manual-participant-nik">
            <input
              id="manual-participant-nik"
              inputMode="numeric"
              maxLength={16}
              value={form.nik}
              onChange={(event) => setField("nik", event.target.value.replace(/\D/g, ""))}
              data-testid="manual-participant-nik"
              className={INPUT_CLASS}
              required
            />
          </Field>
          <Field label="Email" htmlFor="manual-participant-email">
            <input
              id="manual-participant-email"
              type="email"
              value={form.email}
              onChange={(event) => setField("email", event.target.value)}
              data-testid="manual-participant-email"
              className={INPUT_CLASS}
              required
            />
          </Field>
          <Field label="Nomor HP" htmlFor="manual-participant-phone">
            <input
              id="manual-participant-phone"
              inputMode="tel"
              value={form.phone}
              onChange={(event) => setField("phone", event.target.value)}
              data-testid="manual-participant-phone"
              className={INPUT_CLASS}
              required
            />
          </Field>
          <Field label="Kampus" htmlFor="manual-participant-campus">
            <input
              id="manual-participant-campus"
              value={form.campus}
              onChange={(event) => setField("campus", event.target.value)}
              data-testid="manual-participant-campus"
              className={INPUT_CLASS}
              required
            />
          </Field>
          <Field label="NIM" htmlFor="manual-participant-nim">
            <input
              id="manual-participant-nim"
              value={form.nim}
              onChange={(event) => setField("nim", event.target.value)}
              data-testid="manual-participant-nim"
              className={INPUT_CLASS}
              required
            />
          </Field>
        </div>

        <div className="flex justify-end border-t bg-[#F9FAFB] px-6 py-4">
          <button
            type="submit"
            disabled={saving}
            data-testid="submit-manual-participant"
            className={[
              "inline-flex items-center gap-2 rounded-lg bg-[#27AE60] px-5 py-3 text-sm",
              "font-bold text-white transition-colors hover:bg-[#0B6B3A] disabled:opacity-60",
            ].join(" ")}
          >
            {saving ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <UserPlus className="h-4 w-4" />
            )}
            {saving ? "Menyimpan..." : "Tambah Pendaftar"}
          </button>
        </div>
      </form>
    </div>
  );
}

function Field({ label, htmlFor, children }) {
  return (
    <label htmlFor={htmlFor} className="text-sm font-bold text-[#1F2937]">
      {label} <span className="text-[#DC2626]">*</span>
      {children}
    </label>
  );
}