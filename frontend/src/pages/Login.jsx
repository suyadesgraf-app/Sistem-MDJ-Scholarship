import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { toast } from "sonner";
import { useAuth, dashboardPath } from "@/context/AuthContext";
import { formatApiError } from "@/lib/api";
import { GraduationCap, Eye, EyeOff, Mail, Lock, Loader2, ArrowLeft, CheckCircle2 } from "lucide-react";

const AUTH_IMG = "https://images.unsplash.com/photo-1758270705518-b61b40527e76?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2OTF8MHwxfHNlYXJjaHw0fHx1bml2ZXJzaXR5JTIwc3R1ZGVudHMlMjBzbWlsaW5nJTIwc3R1ZHlpbmd8ZW58MHx8fHwxNzg5MTU2MTM5fDA&ixlib=rb-4.1.0&q=85";

const GoogleIcon = () => (
  <svg className="w-5 h-5" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1Z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23Z"/><path fill="#FBBC05" d="M5.84 14.1a6.6 6.6 0 0 1 0-4.2V7.06H2.18a11 11 0 0 0 0 9.88l3.66-2.84Z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84C6.71 7.31 9.14 5.38 12 5.38Z"/></svg>
);

export const AuthSide = () => (
  <div className="hidden lg:block relative">
    <img src={AUTH_IMG} alt="Mahasiswa" className="absolute inset-0 w-full h-full object-cover" />
    <div className="absolute inset-0 bg-gradient-to-br from-[#0B6B3A]/95 to-[#27AE60]/80" />
    <div className="relative h-full flex flex-col justify-between p-12 text-white">
      <Link to="/" className="flex items-center gap-2.5 w-fit" data-testid="auth-home-link">
        <div className="w-10 h-10 rounded-xl bg-white/15 backdrop-blur flex items-center justify-center"><GraduationCap className="w-6 h-6 text-white" /></div>
        <span className="font-display font-extrabold">MDJ Scholarship</span>
      </Link>
      <div>
        <h2 className="font-display font-black text-4xl tracking-tight leading-tight mb-4">Lanjutkan Langkahmu Menuju Masa Depan yang Lebih Baik</h2>
        <div className="space-y-3 mt-8">
          {["Lengkapi data diri Anda dengan lengkap.", "Pantau proses verifikasi secara berkala.", "Dapatkan informasi dan pengumuman terbaru."].map((t) => (
            <p key={t} className="flex items-center gap-3 text-white/90"><CheckCircle2 className="w-5 h-5 text-[#F2C94C]" /> {t}</p>
          ))}
        </div>
      </div>
      <p className="text-sm text-white/70">Seluruh proses pendaftaran MDJ Scholarship <span className="font-bold text-[#F2C94C]">tidak dipungut biaya</span>.</p>
    </div>
  </div>
);

export default function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
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

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-[#F9FAFB]">
      <AuthSide />
      <div className="flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-md">
          <Link to="/" className="lg:hidden flex items-center gap-2 text-sm text-[#6B7280] mb-6"><ArrowLeft className="w-4 h-4" /> Kembali ke Beranda</Link>
          <h1 className="font-display font-extrabold text-3xl tracking-tight text-[#1F2937] mb-2">Masuk ke Akun Anda</h1>
          <p className="text-sm text-[#6B7280] mb-8">Gunakan akun terdaftar untuk mengakses dashboard pendaftar.</p>
          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="block text-sm font-semibold text-[#1F2937] mb-1.5">Email <span className="text-[#DC2626]">*</span></label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input type="text" value={email} onChange={(e) => setEmail(e.target.value)} data-testid="login-email-input" required
                  placeholder="Masukkan email Anda" className="w-full pl-11 pr-4 py-3 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#27AE60] focus:border-transparent" />
              </div>
            </div>
            <div>
              <label className="block text-sm font-semibold text-[#1F2937] mb-1.5">Kata Sandi <span className="text-[#DC2626]">*</span></label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input type={show ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)} data-testid="login-password-input" required
                  placeholder="Masukkan kata sandi" className="w-full pl-11 pr-11 py-3 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#27AE60] focus:border-transparent" />
                <button type="button" onClick={() => setShow(!show)} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">{show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}</button>
              </div>
            </div>
            <button type="submit" disabled={loading} data-testid="login-submit-button"
              className="w-full py-3 bg-[#27AE60] hover:bg-[#0B6B3A] text-white font-bold rounded-xl transition-colors flex items-center justify-center gap-2 disabled:opacity-60">
              {loading ? <><Loader2 className="w-4 h-4 animate-spin" /> Memproses...</> : "Masuk ke Dashboard"}
            </button>
          </form>
          <div className="flex items-center gap-3 my-6"><div className="flex-1 h-px bg-gray-200" /><span className="text-xs text-gray-400 font-medium">ATAU</span><div className="flex-1 h-px bg-gray-200" /></div>
          <button onClick={googleLogin} data-testid="login-google-button" className="w-full py-3 border border-gray-300 rounded-xl font-semibold text-sm text-[#1F2937] hover:bg-gray-50 flex items-center justify-center gap-3 transition-colors"><GoogleIcon /> Login dengan akun Google</button>
          <p className="text-sm text-center text-[#6B7280] mt-6">Belum punya akun? <Link to="/register" className="font-bold text-[#27AE60] hover:text-[#0B6B3A]" data-testid="to-register-link">Daftar sekarang</Link></p>
        </div>
      </div>
    </div>
  );
}
