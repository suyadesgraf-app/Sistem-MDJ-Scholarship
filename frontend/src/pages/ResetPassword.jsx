import React, { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowLeft, CheckCircle2, Eye, EyeOff, Loader2, Lock, XCircle } from "lucide-react";
import api, { formatApiError } from "@/lib/api";

export default function ResetPassword() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [state, setState] = useState({ status: "idle", message: "" });

  const submit = async (event) => {
    event.preventDefault();
    if (!token) {
      setState({ status: "error", message: "Tautan reset tidak valid." });
      return;
    }
    if (password !== confirmation) {
      setState({ status: "error", message: "Konfirmasi kata sandi baru belum sama." });
      return;
    }
    setState({ status: "loading", message: "" });
    try {
      const response = await api.post("/auth/reset-password", {
        token,
        new_password: password,
      });
      setState({ status: "success", message: response.data.message });
    } catch (error) {
      setState({ status: "error", message: formatApiError(error.response?.data?.detail) });
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#F0FBF5] p-4">
      <main className="w-full max-w-md rounded-xl bg-white p-7 shadow-xl shadow-[#0B6B3A]/10" data-testid="reset-password-card">
        <Link
          to="/login"
          data-testid="reset-password-back-login"
          className="inline-flex items-center gap-2 text-sm font-semibold text-[#0B6B3A] hover:underline"
        >
          <ArrowLeft className="h-4 w-4" />
          Kembali ke Masuk
        </Link>
        {state.status === "success" ? (
          <div className="py-10 text-center" data-testid="reset-password-success">
            <CheckCircle2 className="mx-auto h-12 w-12 text-[#27AE60]" />
            <h1 className="mt-5 font-display text-2xl font-extrabold text-[#1F2937]">Kata Sandi Diperbarui</h1>
            <p className="mt-3 text-sm leading-relaxed text-[#6B7280]">{state.message}</p>
            <button
              type="button"
              onClick={() => navigate("/login", { replace: true })}
              data-testid="reset-password-to-login-button"
              className="mt-6 rounded-lg bg-[#27AE60] px-5 py-3 text-sm font-bold text-white hover:bg-[#0B6B3A]"
            >
              Masuk dengan Kata Sandi Baru
            </button>
          </div>
        ) : (
          <>
            <h1 className="mt-6 font-display text-2xl font-extrabold text-[#1F2937]">Buat Kata Sandi Baru</h1>
            <p className="mt-2 text-sm leading-relaxed text-[#6B7280]">
              Gunakan minimal 8 karakter. Tautan ini hanya dapat digunakan satu kali.
            </p>
            {state.status === "error" && (
              <div className="mt-5 flex gap-2 border-l-4 border-[#DC2626] bg-[#FEF2F2] p-3 text-sm text-[#B91C1C]" data-testid="reset-password-error">
                <XCircle className="h-5 w-5 shrink-0" />
                <span>{state.message}</span>
              </div>
            )}
            <form className="mt-6 space-y-4" onSubmit={submit}>
              <PasswordField
                label="Kata Sandi Baru"
                value={password}
                setValue={setPassword}
                visible={showPassword}
                setVisible={setShowPassword}
                testId="reset-password-new-input"
              />
              <PasswordField
                label="Konfirmasi Kata Sandi Baru"
                value={confirmation}
                setValue={setConfirmation}
                visible={showConfirmation}
                setVisible={setShowConfirmation}
                testId="reset-password-confirmation-input"
              />
              <button
                type="submit"
                disabled={state.status === "loading" || !token}
                data-testid="reset-password-submit-button"
                className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#27AE60] py-3 text-sm font-bold text-white hover:bg-[#0B6B3A] disabled:opacity-60"
              >
                {state.status === "loading" && <Loader2 className="h-4 w-4 animate-spin" />}
                Simpan Kata Sandi Baru
              </button>
            </form>
          </>
        )}
      </main>
    </div>
  );
}

function PasswordField({ label, value, setValue, visible, setVisible, testId }) {
  return (
    <label className="block text-xs font-bold uppercase tracking-wide text-[#6B7280]">
      {label}
      <span className="relative mt-1.5 block">
        <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
        <input
          type={visible ? "text" : "password"}
          value={value}
          onChange={(event) => setValue(event.target.value)}
          minLength={8}
          required
          data-testid={testId}
          className="w-full rounded-lg border border-gray-300 py-3 pl-10 pr-11 text-sm outline-none focus:border-transparent focus:ring-2 focus:ring-[#27AE60]"
        />
        <button
          type="button"
          onClick={() => setVisible(!visible)}
          data-testid={`${testId}-visibility-button`}
          aria-label={visible ? "Sembunyikan kata sandi" : "Tampilkan kata sandi"}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
        >
          {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </span>
    </label>
  );
}