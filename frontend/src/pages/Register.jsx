import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";
import { formatApiError } from "@/lib/api";
import { AuthSide, GoogleIcon } from "@/pages/Login";
import { Eye, EyeOff, Mail, Lock, User, Phone, Loader2, ArrowLeft } from "lucide-react";

export default function Register() {
  const navigate = useNavigate();
  const { register } = useAuth();
  const [form, setForm] = useState({ name: "", email: "", phone: "", password: "", confirm: "" });
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);
  const set = (k) => (e) => setForm((p) => ({ ...p, [k]: e.target.value }));

  const googleRegister = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    window.location.href = `${process.env.REACT_APP_BACKEND_URL}/api/auth/google/login?redirect_origin=${encodeURIComponent(window.location.origin)}`;
  };

  const submit = async (e) => {
    e.preventDefault();
    if (form.password.length < 8) return toast.error("Kata sandi minimal 8 karakter.");
    if (form.password !== form.confirm) return toast.error("Konfirmasi kata sandi tidak cocok.");
    setLoading(true);
    try {
      await register({
        name: form.name,
        email: form.email,
        password: form.password,
        phone: form.phone,
      });
      toast.success("Akun berhasil dibuat!");
      navigate("/dashboard", { replace: true });
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail) || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-[#F9FAFB]">
      <AuthSide />
      <div className="flex items-center justify-center p-6 sm:p-12 overflow-y-auto">
        <div className="w-full max-w-md">
          <Link
            to="/"
            data-testid="register-home-link"
            className="mb-6 inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-semibold text-[#6B7280] transition-colors hover:border-[#8FE2B4] hover:bg-[#F0FBF5] hover:text-[#0B6B3A]"
          >
            <ArrowLeft className="h-4 w-4" />
            Kembali ke Beranda
          </Link>
          <h1 className="font-display font-extrabold text-3xl tracking-tight text-[#1F2937] mb-2">Buat Akun Pendaftar</h1>
          <p className="text-sm text-[#6B7280] mb-8">Daftar untuk memulai proses pendaftaran MDJ Scholarship.</p>
          <form onSubmit={submit} className="space-y-4">
            <Field label="Nama Lengkap" icon={User} required><input value={form.name} onChange={set("name")} required data-testid="reg-name-input" placeholder="Nama sesuai KTP" className={inputCls} /></Field>
            <Field label="Email" icon={Mail} required><input type="email" value={form.email} onChange={set("email")} required data-testid="reg-email-input" placeholder="email@contoh.com" className={inputCls} /></Field>
            <Field label="No. Telepon" icon={Phone}>
              <input
                value={form.phone}
                onChange={set("phone")}
                data-testid="reg-phone-input"
                placeholder="08xxxx"
                className={inputCls}
              />
            </Field>
            <Field label="Kata Sandi" icon={Lock} required>
              <input type={show ? "text" : "password"} value={form.password} onChange={set("password")} required data-testid="reg-password-input" placeholder="Min. 8 karakter" className={inputCls} />
              <button type="button" onClick={() => setShow(!show)} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">{show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}</button>
            </Field>
            <Field label="Konfirmasi Kata Sandi" icon={Lock} required><input type={show ? "text" : "password"} value={form.confirm} onChange={set("confirm")} required data-testid="reg-confirm-input" placeholder="Ulangi kata sandi" className={inputCls} /></Field>
            <button type="submit" disabled={loading} data-testid="register-submit-button"
              className="w-full py-3 bg-[#27AE60] hover:bg-[#0B6B3A] text-white font-bold rounded-xl transition-colors flex items-center justify-center gap-2 disabled:opacity-60">
              {loading ? <><Loader2 className="w-4 h-4 animate-spin" /> Memproses...</> : "Buat Akun"}
            </button>
          </form>
          <div className="my-6 flex items-center gap-3" data-testid="register-google-divider">
            <span className="h-px flex-1 bg-gray-200" />
            <span className="text-xs font-medium text-gray-400">ATAU</span>
            <span className="h-px flex-1 bg-gray-200" />
          </div>
          <button
            type="button"
            onClick={googleRegister}
            data-testid="register-google-button"
            className={[
              "flex w-full items-center justify-center gap-3 rounded-lg border border-gray-300 py-3",
              "text-sm font-semibold text-[#1F2937] transition-colors duration-200 hover:bg-gray-50",
            ].join(" ")}
          >
            <GoogleIcon />
            Daftar dengan akun Google
          </button>
          <p className="mt-3 text-center text-[11px] leading-relaxed text-[#9CA3AF]">
            Gunakan akun Google untuk membuat akun pendaftar secara praktis dan aman.
          </p>
          <p className="text-sm text-center text-[#6B7280] mt-6">Sudah punya akun? <Link to="/login" className="font-bold text-[#27AE60] hover:text-[#0B6B3A]" data-testid="to-login-link">Masuk di sini</Link></p>
        </div>
      </div>
    </div>
  );
}

const inputCls = "w-full pl-11 pr-11 py-3 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#27AE60] focus:border-transparent";

const Field = ({ label, icon: Icon, required, children }) => (
  <div>
    <label className="block text-sm font-semibold text-[#1F2937] mb-1.5">{label} {required && <span className="text-[#DC2626]">*</span>}</label>
    <div className="relative"><Icon className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />{children}</div>
  </div>
);
