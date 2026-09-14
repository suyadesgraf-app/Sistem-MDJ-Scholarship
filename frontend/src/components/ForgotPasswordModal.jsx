import React, { useState } from "react";
import { Loader2, Mail, X } from "lucide-react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";

export default function ForgotPasswordModal({ onClose }) {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    try {
      const response = await api.post("/auth/forgot-password", { email });
      setSubmitted(true);
      toast.success(response.data.message);
    } catch (error) {
      toast.error(formatApiError(error.response?.data?.detail));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-[#1F2937]/55 p-4"
      data-testid="forgot-password-overlay"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-xl bg-white p-6 shadow-2xl"
        data-testid="forgot-password-modal"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="font-display text-xl font-extrabold text-[#1F2937]">Atur Ulang Kata Sandi</h2>
            <p className="mt-2 text-sm leading-relaxed text-[#6B7280]">
              Masukkan email akun Anda. Kami akan mengirim tautan aman untuk membuat kata sandi baru.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            data-testid="close-forgot-password-modal"
            className="rounded-lg p-2 text-[#6B7280] hover:bg-gray-100"
            aria-label="Tutup dialog lupa kata sandi"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {submitted ? (
          <div className="mt-6 border-l-4 border-[#27AE60] bg-[#F0FBF5] p-4 text-sm leading-relaxed text-[#0B6B3A]" data-testid="forgot-password-success">
            Jika email terdaftar, tautan reset telah dikirim. Silakan periksa kotak masuk dan folder spam.
          </div>
        ) : (
          <form className="mt-6 space-y-4" onSubmit={submit}>
            <label className="block text-xs font-bold uppercase tracking-wide text-[#6B7280]">
              Email Terdaftar
              <span className="relative mt-1.5 block">
                <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="nama@email.com"
                  required
                  autoFocus
                  data-testid="forgot-password-email-input"
                  className="w-full rounded-lg border border-gray-300 py-3 pl-10 pr-4 text-sm outline-none focus:border-transparent focus:ring-2 focus:ring-[#27AE60]"
                />
              </span>
            </label>
            <button
              type="submit"
              disabled={submitting}
              data-testid="forgot-password-submit-button"
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#27AE60] py-3 text-sm font-bold text-white transition-colors hover:bg-[#0B6B3A] disabled:opacity-60"
            >
              {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
              Kirim Tautan Reset
            </button>
          </form>
        )}
      </div>
    </div>
  );
}