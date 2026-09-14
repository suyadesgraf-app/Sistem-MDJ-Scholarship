import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { toast } from "sonner";
import { useAuth, dashboardPath } from "@/context/AuthContext";
import { formatApiError } from "@/lib/api";
import {
  ArrowLeft,
  CheckCircle2,
  Eye,
  EyeOff,
  Loader2,
  Lock,
  Mail,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

const GoogleIcon = () => (
  <svg className="h-5 w-5" viewBox="0 0 24 24" aria-hidden="true">
    <path
      fill="#4285F4"
      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1Z"
    />
    <path
      fill="#34A853"
      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23Z"
    />
    <path
      fill="#FBBC05"
      d="M5.84 14.1a6.6 6.6 0 0 1 0-4.2V7.06H2.18a11 11 0 0 0 0 9.88l3.66-2.84Z"
    />
    <path
      fill="#EA4335"
      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84C6.71 7.31 9.14 5.38 12 5.38Z"
    />
  </svg>
);

const DEMO_ACCOUNTS = [
  {
    label: "Super Admin",
    email: process.env.REACT_APP_DEMO_SUPER_ADMIN_EMAIL,
    password: process.env.REACT_APP_DEMO_SUPER_ADMIN_PASSWORD,
    testId: "demo-account-super-admin-button",
  },
  {
    label: "Admin Provinsi",
    email: process.env.REACT_APP_DEMO_ADMIN_EMAIL,
    password: process.env.REACT_APP_DEMO_ADMIN_PASSWORD,
    testId: "demo-account-admin-button",
  },
  {
    label: "Mahasiswa",
    email: process.env.REACT_APP_DEMO_STUDENT_EMAIL,
    password: process.env.REACT_APP_DEMO_STUDENT_PASSWORD,
    testId: "demo-account-student-button",
  },
];

export const AuthSide = () => (
  <aside className="hidden bg-gradient-to-br from-[#08743D] via-[#08713B] to-[#198447] lg:block">
    <div className="flex h-full min-h-[720px] flex-col justify-between p-12 text-white xl:p-16">
      <div>
        <span className="inline-flex items-center gap-2 rounded-full border border-[#F2C94C]/45 bg-[#0E8A4A]/40 px-3 py-1 text-xs font-bold text-[#F7D867]">
          <Sparkles className="h-3.5 w-3.5" />
          Program Beasiswa Pendidikan
        </span>
        <h2 className="font-display mt-7 max-w-lg text-4xl font-black leading-[1.06] text-white">
          Lanjutkan Langkahmu Menuju Masa Depan yang Lebih Baik
        </h2>
        <p className="mt-7 max-w-md text-base leading-relaxed text-white/90">
          Masuk ke akun MDJ Scholarship untuk melengkapi data diri.
        </p>
        <div className="mt-8 space-y-4">
          {[
            "Lengkapi data diri anda dengan lengkap.",
            "Pantau proses verifikasi secara berkala.",
            "Dapatkan informasi dan pengumuman terbaru.",
          ].map((text) => (
            <p key={text} className="flex items-center gap-3 text-sm font-medium text-white/95">
              <CheckCircle2 className="h-5 w-5 shrink-0 text-[#F2C94C]" />
              {text}
            </p>
          ))}
        </div>
      </div>
      <p className="border-t border-white/20 pt-5 text-sm text-white/90">
        <ShieldCheck className="mr-2 inline h-4 w-4 text-[#F2C94C]" />
        Seluruh proses pendaftaran MDJ Scholarship tidak dipungut biaya.
      </p>
    </div>
  </aside>
);

export default function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [remember, setRemember] = useState(false);
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const user = await login(email, password);
      toast.success("Berhasil masuk!");
      navigate(dashboardPath(user.role), { replace: true });
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail) || err.message);
    } finally {
      setLoading(false);
    }
  };

  const googleLogin = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + "/dashboard";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  const loginWithDemoAccount = async (account) => {
    setEmail(account.email);
    setPassword(account.password);
    setShow(false);
    setLoading(true);
    try {
      const user = await login(account.email, account.password);
      toast.success(`Berhasil masuk sebagai ${account.label}.`);
      navigate(dashboardPath(user.role), { replace: true });
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail) || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F4F6F3] p-4 lg:p-6">
      <main
        className="mx-auto grid min-h-[calc(100vh-2rem)] max-w-[1240px] overflow-hidden bg-white shadow-xl
          shadow-[#0B6B3A]/10 lg:min-h-[720px] lg:grid-cols-2 lg:rounded-xl"
      >
        <AuthSide />
        <div className="flex items-center justify-center px-6 py-12 sm:px-12 lg:p-16">
          <div className="w-full max-w-md">
            <Link
              to="/"
              data-testid="login-home-link"
              className="mb-7 inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-semibold text-[#6B7280] transition-colors hover:border-[#8FE2B4] hover:bg-[#F0FBF5] hover:text-[#0B6B3A]"
            >
              <ArrowLeft className="h-4 w-4" />
              Kembali ke Beranda
            </Link>
            <h1 className="font-display text-3xl font-extrabold tracking-tight text-[#1F2937]">
              Masuk ke Akun Anda
            </h1>
            <p className="mb-7 mt-2 text-sm leading-relaxed text-[#6B7280]">
              Gunakan akun yang telah terdaftar untuk mengakses layanan MDJ Scholarship.
            </p>
          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-semibold text-[#1F2937]">
                Email atau NIK <span className="text-[#DC2626]">*</span>
              </label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  data-testid="login-email-input"
                  required
                  placeholder="Masukkan email atau NIK Anda"
                  className="w-full rounded-lg border border-gray-300 py-3 pl-11 pr-4 text-sm outline-none
                    transition-colors focus:border-transparent focus:ring-2 focus:ring-[#27AE60]"
                />
              </div>
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-semibold text-[#1F2937]">
                Kata Sandi <span className="text-[#DC2626]">*</span>
              </label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <input
                  type={show ? "text" : "password"}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  data-testid="login-password-input"
                  required
                  placeholder="Masukkan kata sandi"
                  className="w-full rounded-lg border border-gray-300 py-3 pl-11 pr-11 text-sm outline-none
                    transition-colors focus:border-transparent focus:ring-2 focus:ring-[#27AE60]"
                />
                <button
                  type="button"
                  onClick={() => setShow(!show)}
                  data-testid="login-password-visibility-button"
                  aria-label={show ? "Sembunyikan kata sandi" : "Tampilkan kata sandi"}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-gray-400 transition-colors
                    hover:text-gray-600"
                >
                  {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>
            <div className="flex items-center justify-between gap-4 pt-0.5 text-xs">
              <label className="flex cursor-pointer items-center gap-2 text-[#6B7280]">
                <input
                  type="checkbox"
                  checked={remember}
                  onChange={(event) => setRemember(event.target.checked)}
                  data-testid="login-remember-checkbox"
                  className="h-3.5 w-3.5 rounded border-gray-300 accent-[#27AE60]"
                />
                Ingat saya
              </label>
              <span className="font-semibold text-[#0B6B3A]">Lupa kata sandi?</span>
            </div>
            <button
              type="submit"
              disabled={loading}
              data-testid="login-submit-button"
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#27AE60] py-3 text-sm
                font-bold text-white transition-colors duration-200 hover:bg-[#0B6B3A] disabled:opacity-60"
            >
              {loading ? <><Loader2 className="h-4 w-4 animate-spin" /> Memproses...</> : "Masuk"}
            </button>
          </form>
          <div className="my-6 flex items-center gap-3">
            <div className="h-px flex-1 bg-gray-200" />
            <span className="text-xs font-medium text-gray-400">ATAU</span>
            <div className="h-px flex-1 bg-gray-200" />
          </div>
          <button
            onClick={googleLogin}
            data-testid="login-google-button"
            className="flex w-full items-center justify-center gap-3 rounded-lg border border-gray-300 py-3 text-sm
              font-semibold text-[#1F2937] transition-colors duration-200 hover:bg-gray-50"
          >
            <GoogleIcon />
            Login dengan akun Gmail
          </button>
          <p className="mt-3 text-center text-[11px] leading-relaxed text-[#9CA3AF]">
            Gunakan akun Gmail yang terdaftar untuk masuk secara praktis dan aman.
          </p>
          <div className="mt-6 border-t border-gray-100 pt-5">
            <p className="text-xs font-bold uppercase tracking-wide text-[#9CA3AF]">
              Akun Demo (Klik untuk Mengisi)
            </p>
            <div className="mt-3 flex flex-wrap gap-2.5">
              {DEMO_ACCOUNTS.map((account) => (
                <button
                  key={account.label}
                  type="button"
                  onClick={() => loginWithDemoAccount(account)}
                  data-testid={account.testId}
                  disabled={loading}
                  className="rounded-full border border-[#8FE2B4] bg-[#F2FFF7] px-4 py-2 text-sm font-bold
                    text-[#08743D] transition-colors duration-200 hover:bg-[#DDF8E8] focus-visible:outline-none
                    focus-visible:ring-2 focus-visible:ring-[#27AE60] focus-visible:ring-offset-2
                    disabled:cursor-wait disabled:opacity-60"
                >
                  {account.label}
                </button>
              ))}
            </div>
          </div>
          <p className="mt-6 text-center text-sm text-[#6B7280]">
            Belum punya akun? {" "}
            <Link
              to="/register"
              className="font-bold text-[#27AE60] transition-colors duration-200 hover:text-[#0B6B3A]"
              data-testid="to-register-link"
            >
              Daftar sekarang
            </Link>
          </p>
        </div>
        </div>
      </main>
    </div>
  );
}
