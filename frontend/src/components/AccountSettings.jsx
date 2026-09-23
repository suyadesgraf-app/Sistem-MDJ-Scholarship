import React, { useState } from "react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import {
  Mail, Phone, ShieldCheck, AlertTriangle, Loader2, Lock, Eye, EyeOff, X, KeyRound,
} from "lucide-react";

const Card = ({ children }) => (
  <div className="bg-white border border-gray-100 rounded-2xl p-6 shadow-[0_4px_20px_-2px_rgba(39,174,96,0.05)]">{children}</div>
);
const inputCls = "w-full px-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#27AE60] focus:border-transparent";

function passwordStrength(pw) {
  if (!pw) return { score: 0, label: "", color: "#E5E7EB" };
  let score = 0;
  if (pw.length >= 8) score++;
  if (pw.length >= 12) score++;
  if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) score++;
  if (/\d/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  const levels = [
    { label: "Sangat Lemah", color: "#DC2626" },
    { label: "Lemah", color: "#DC2626" },
    { label: "Sedang", color: "#F2C94C" },
    { label: "Cukup Kuat", color: "#3B82F6" },
    { label: "Kuat", color: "#27AE60" },
    { label: "Sangat Kuat", color: "#27AE60" },
  ];
  return { score, ...levels[score] };
}

export default function AccountSettings() {
  const { user, checkAuth } = useAuth();
  const [modal, setModal] = useState(null); // "email" | "phone"
  const isGoogle = user?.auth_provider === "google";

  return (
    <div className="space-y-6" data-testid="account-settings">
      {/* Informasi Akun */}
      <Card>
        <h3 className="font-display font-bold text-lg text-[#1F2937] mb-5">Informasi Akun</h3>
        <div className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-xl border border-gray-100 bg-[#F9FAFB]">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-[#E8F6EE] flex items-center justify-center shrink-0"><Mail className="w-5 h-5 text-[#27AE60]" /></div>
              <div>
                <p className="text-sm font-semibold text-[#1F2937]">Email Akun</p>
                <p className="text-sm text-[#6B7280] flex items-center gap-2 mt-0.5" data-testid="account-email-value">
                  {user?.email}
                  <span className="px-2 py-0.5 rounded-full bg-[#E8F6EE] text-[#0B6B3A] text-[10px] font-bold flex items-center gap-1"><ShieldCheck className="w-3 h-3" /> Terverifikasi</span>
                </p>
              </div>
            </div>
            {!isGoogle && (
              <button onClick={() => setModal("email")} data-testid="change-email-btn" className="px-4 py-2 border border-gray-300 text-[#1F2937] text-sm font-bold rounded-xl hover:bg-white transition-colors">Ubah Email</button>
            )}
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-xl border border-gray-100 bg-[#F9FAFB]">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-[#E8F6EE] flex items-center justify-center shrink-0"><Phone className="w-5 h-5 text-[#27AE60]" /></div>
              <div>
                <p className="text-sm font-semibold text-[#1F2937]">Nomor Telepon / WhatsApp</p>
                <p className="text-sm text-[#6B7280] flex items-center gap-2 mt-0.5" data-testid="account-phone-value">
                  {user?.phone || "Belum diatur"}
                  {user?.phone_verified
                    ? <span className="px-2 py-0.5 rounded-full bg-[#E8F6EE] text-[#0B6B3A] text-[10px] font-bold flex items-center gap-1"><ShieldCheck className="w-3 h-3" /> Terverifikasi</span>
                    : <span className="px-2 py-0.5 rounded-full bg-[#FEF6E0] text-[#B8860B] text-[10px] font-bold flex items-center gap-1"><AlertTriangle className="w-3 h-3" /> Belum Terverifikasi</span>}
                </p>
              </div>
            </div>
            <button onClick={() => setModal("phone")} data-testid="change-phone-btn" className="px-4 py-2 border border-gray-300 text-[#1F2937] text-sm font-bold rounded-xl hover:bg-white transition-colors">Ubah Nomor</button>
          </div>
        </div>
      </Card>

      {/* Keamanan Akun */}
      {isGoogle ? (
        <Card>
          <h3 className="font-display font-bold text-lg text-[#1F2937]">Keamanan Akun</h3>
          <p className="text-sm text-[#6B7280] mt-2">Akun Anda masuk menggunakan Google, sehingga kata sandi dikelola oleh akun Google Anda.</p>
        </Card>
      ) : (
        <ChangePasswordCard />
      )}

      {modal === "email" && <ChangeEmailModal onClose={() => setModal(null)} />}
      {modal === "phone" && <ChangePhoneModal onClose={() => setModal(null)} onDone={checkAuth} />}
    </div>
  );
}

function ChangePasswordCard() {
  const [cur, setCur] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const strength = passwordStrength(next);

  const submit = async () => {
    if (next.length < 8) return toast.error("Kata sandi baru minimal 8 karakter.");
    if (next !== confirm) return toast.error("Konfirmasi kata sandi tidak cocok.");
    setBusy(true);
    try {
      await api.post("/auth/change-password", { current_password: cur, new_password: next });
      toast.success("Kata sandi berhasil diperbarui.");
      setCur(""); setNext(""); setConfirm("");
    } catch (e) {
      toast.error(formatApiError(e?.response?.data?.detail));
    } finally { setBusy(false); }
  };

  return (
    <Card>
      <h3 className="font-display font-bold text-lg text-[#1F2937]">Keamanan Akun</h3>
      <p className="text-sm text-[#6B7280] mt-1 mb-5">Ganti kata sandi secara berkala untuk menjaga keamanan akun Anda.</p>
      <div className="space-y-4">
        <div className="max-w-md">
          <label className="block text-sm font-semibold text-[#1F2937] mb-1.5">Kata Sandi Saat Ini <span className="text-[#DC2626]">*</span></label>
          <div className="relative">
            <input type={show ? "text" : "password"} value={cur} onChange={(e) => setCur(e.target.value)} placeholder="Masukkan kata sandi saat ini" data-testid="current-password-input" className={inputCls + " pr-10"} />
            <button type="button" onClick={() => setShow((s) => !s)} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400" aria-label="Toggle">{show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}</button>
          </div>
        </div>
        <div className="grid sm:grid-cols-2 gap-x-5 gap-y-4">
          <div>
            <label className="block text-sm font-semibold text-[#1F2937] mb-1.5">Kata Sandi Baru <span className="text-[#DC2626]">*</span></label>
            <input type={show ? "text" : "password"} value={next} onChange={(e) => setNext(e.target.value)} placeholder="Minimal 8 karakter" data-testid="new-password-input" className={inputCls} />
            {next && (
              <>
                <div className="mt-2 flex gap-1">
                  {[0, 1, 2, 3, 4].map((i) => <div key={i} className="h-1.5 flex-1 rounded-full transition-colors" style={{ background: i < strength.score ? strength.color : "#E5E7EB" }} />)}
                </div>
                <p className="text-xs mt-1 font-medium" style={{ color: strength.color }} data-testid="password-strength">Kekuatan: {strength.label}</p>
              </>
            )}
          </div>
          <div>
            <label className="block text-sm font-semibold text-[#1F2937] mb-1.5">Konfirmasi Kata Sandi Baru <span className="text-[#DC2626]">*</span></label>
            <input type={show ? "text" : "password"} value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="Ulangi kata sandi baru" data-testid="confirm-password-input" className={inputCls} />
            {confirm && next !== confirm && <p className="text-xs mt-1 text-[#DC2626]">Kata sandi tidak cocok.</p>}
          </div>
        </div>
        <button onClick={submit} disabled={busy || !cur || !next || !confirm} data-testid="submit-change-password-btn" className="px-5 py-2.5 bg-[#27AE60] hover:bg-[#0B6B3A] disabled:opacity-60 text-white text-sm font-bold rounded-xl flex items-center gap-2 transition-colors">
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <KeyRound className="w-4 h-4" />} Perbarui Kata Sandi
        </button>
      </div>
    </Card>
  );
}

function ModalShell({ title, icon: Icon, onClose, children }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40" onClick={onClose}>
      <div className="bg-white rounded-2xl w-full max-w-md p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-display font-bold text-lg text-[#1F2937] flex items-center gap-2"><Icon className="w-5 h-5 text-[#27AE60]" /> {title}</h3>
          <button onClick={onClose} data-testid="modal-close-btn" className="p-1 text-gray-400 hover:text-gray-600"><X className="w-5 h-5" /></button>
        </div>
        {children}
      </div>
    </div>
  );
}

function ChangeEmailModal({ onClose }) {
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/auth/email/change-request", { new_email: email, password: pw });
      toast.success(data.message || "Tautan verifikasi telah dikirim.");
      onClose();
    } catch (e) { toast.error(formatApiError(e?.response?.data?.detail)); }
    finally { setBusy(false); }
  };
  return (
    <ModalShell title="Ubah Email" icon={Mail} onClose={onClose}>
      <p className="text-sm text-[#6B7280] mb-4">Kami akan mengirim tautan verifikasi ke email baru Anda. Email hanya berubah setelah Anda mengeklik tautan tersebut.</p>
      <div className="space-y-3">
        <div>
          <label className="block text-sm font-semibold text-[#1F2937] mb-1.5">Email Baru</label>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="email.baru@example.com" data-testid="new-email-input" className={inputCls} />
        </div>
        <div>
          <label className="block text-sm font-semibold text-[#1F2937] mb-1.5">Kata Sandi Saat Ini</label>
          <input type="password" value={pw} onChange={(e) => setPw(e.target.value)} placeholder="Konfirmasi dengan kata sandi" data-testid="email-password-input" className={inputCls} />
        </div>
        <button onClick={submit} disabled={busy || !email || !pw} data-testid="submit-change-email-btn" className="w-full px-5 py-2.5 bg-[#27AE60] hover:bg-[#0B6B3A] disabled:opacity-60 text-white text-sm font-bold rounded-xl flex items-center justify-center gap-2 transition-colors">
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Mail className="w-4 h-4" />} Kirim Tautan Verifikasi
        </button>
      </div>
    </ModalShell>
  );
}

function ChangePhoneModal({ onClose, onDone }) {
  const [step, setStep] = useState(1);
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const sendOtp = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/auth/phone/send-otp", { phone });
      toast.success(data.message || "Kode OTP dikirim.");
      setStep(2);
    } catch (e) { toast.error(formatApiError(e?.response?.data?.detail)); }
    finally { setBusy(false); }
  };
  const verifyOtp = async () => {
    setBusy(true);
    try {
      await api.post("/auth/phone/verify-otp", { phone, code });
      toast.success("Nomor telepon berhasil diverifikasi.");
      if (onDone) await onDone();
      onClose();
    } catch (e) { toast.error(formatApiError(e?.response?.data?.detail)); }
    finally { setBusy(false); }
  };
  return (
    <ModalShell title="Ubah Nomor Telepon" icon={Phone} onClose={onClose}>
      {step === 1 ? (
        <div className="space-y-3">
          <p className="text-sm text-[#6B7280]">Masukkan nomor telepon dalam format internasional. Kami akan mengirim kode OTP via SMS.</p>
          <div>
            <label className="block text-sm font-semibold text-[#1F2937] mb-1.5">Nomor Telepon</label>
            <input type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+6281234567890" data-testid="new-phone-input" className={inputCls} />
          </div>
          <button onClick={sendOtp} disabled={busy || !phone} data-testid="send-otp-btn" className="w-full px-5 py-2.5 bg-[#27AE60] hover:bg-[#0B6B3A] disabled:opacity-60 text-white text-sm font-bold rounded-xl flex items-center justify-center gap-2 transition-colors">
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Phone className="w-4 h-4" />} Kirim Kode OTP
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-sm text-[#6B7280]">Masukkan 6 digit kode OTP yang dikirim ke <b>{phone}</b>.</p>
          <div>
            <label className="block text-sm font-semibold text-[#1F2937] mb-1.5">Kode OTP</label>
            <input type="text" inputMode="numeric" maxLength={6} value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} placeholder="000000" data-testid="otp-input" className={inputCls + " tracking-[0.4em] text-center font-bold"} />
          </div>
          <button onClick={verifyOtp} disabled={busy || code.length < 4} data-testid="verify-otp-btn" className="w-full px-5 py-2.5 bg-[#27AE60] hover:bg-[#0B6B3A] disabled:opacity-60 text-white text-sm font-bold rounded-xl flex items-center justify-center gap-2 transition-colors">
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />} Verifikasi
          </button>
          <button onClick={() => setStep(1)} className="w-full text-sm text-[#6B7280] hover:text-[#1F2937]">Ubah nomor</button>
        </div>
      )}
    </ModalShell>
  );
}
