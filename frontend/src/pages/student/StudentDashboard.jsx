import React, { useEffect, useState, useMemo } from "react";
import { toast } from "sonner";
import api, { API } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import DashboardShell, { StatusBadge, STATUS_META } from "@/components/DashboardShell";
import StudentProfile, { profileProgress } from "@/components/StudentProfile";
import {
  Home, User, FileText, Activity, Megaphone, Settings, Save, Loader2,
  UploadCloud, CheckCircle2, Clock, Trash2, FileCheck, AlertCircle, Eye,
} from "lucide-react";

const MENU = [
  { id: "ringkasan", label: "Ringkasan", icon: Home },
  { id: "profil", label: "Profil Saya", icon: User },
  { id: "daftar", label: "Pendaftaran", icon: FileText },
  { id: "dokumen", label: "Dokumen", icon: FileCheck },
  { id: "status", label: "Status Seleksi", icon: Activity },
  { id: "pengumuman", label: "Pengumuman", icon: Megaphone },
  { id: "pengaturan", label: "Pengaturan", icon: Settings },
];

const DOC_TYPES = [
  "KTP DKI Jakarta", "Kartu Keluarga (KK)", "Pas Foto 3x4", "Kartu Tanda Mahasiswa (KTM)",
  "Surat Keterangan Mahasiswa Aktif", "SKTM / Surat Rekomendasi", "Surat Persetujuan Orang Tua",
  "Surat Keterangan Tidak Menerima Beasiswa Lain", "Pakta Integritas",
];

const CATEGORY_OPTS = ["Mahasiswa Sarjana (S1)", "Mahasiswa Vokasi", "Koordinator Akademik", "Volunteer / Relawan"];

export default function StudentDashboard() {
  const { user } = useAuth();
  const [active, setActive] = useState("ringkasan");
  const [data, setData] = useState({});
  const [reg, setReg] = useState({});
  const [docs, setDocs] = useState([]);
  const [content, setContent] = useState({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.get("/profile").then((r) => setData(r.data.data || {}));
    api.get("/registration").then((r) => setReg(r.data || {}));
    api.get("/documents").then((r) => setDocs(r.data));
    api.get("/site/content").then((r) => setContent(r.data));
  }, []);

  const progress = useMemo(() => profileProgress(data), [data]);

  const set = (k, v) => setData((p) => ({ ...p, [k]: v }));

  const saveProfile = async () => {
    setSaving(true);
    try { await api.put("/profile", { data }); toast.success("Profil berhasil disimpan."); }
    catch { toast.error("Gagal menyimpan profil."); }
    finally { setSaving(false); }
  };

  const uploadDoc = async (docType, file) => {
    if (!file) return;
    const fd = new FormData();
    fd.append("doc_type", docType);
    fd.append("file", file);
    try {
      await api.post("/documents", fd, { headers: { "Content-Type": "multipart/form-data" } });
      const r = await api.get("/documents");
      setDocs(r.data);
      toast.success(`${docType} berhasil diunggah.`);
    } catch { toast.error("Gagal mengunggah dokumen."); }
  };

  const deleteDoc = async (id) => {
    await api.delete(`/documents/${id}`);
    setDocs((p) => p.filter((d) => d.id !== id));
    toast.success("Dokumen dihapus.");
  };

  const submitRegistration = async (action) => {
    if (!reg.category) return toast.error("Pilih kategori program terlebih dahulu.");
    if (action === "submit" && progress < 100) return toast.error("Lengkapi seluruh data wajib pada Profil sebelum mengirim.");
    try {
      const { data: r } = await api.post("/registration", { category: reg.category, action });
      setReg(r);
      toast.success(action === "submit" ? "Pendaftaran berhasil dikirim!" : "Draft pendaftaran disimpan.");
    } catch (e) { toast.error("Gagal memproses pendaftaran."); }
  };

  const timeline = content.timeline || [];
  const statusOrder = ["submitted", "verifikasi", "lolos_administrasi", "wawancara", "verifikasi_faktual", "lolos"];
  const currentIdx = statusOrder.indexOf(reg.status);

  return (
    <DashboardShell menu={MENU} active={active} onSelect={setActive} brandLabel="Portal Pendaftar"
      title={MENU.find((m) => m.id === active)?.label} subtitle="Program Masa Depan Jakarta 2026"
      actions={active === "profil" && <button onClick={saveProfile} disabled={saving} data-testid="save-profile-btn" className="px-4 py-2 bg-[#27AE60] hover:bg-[#0B6B3A] text-white text-sm font-bold rounded-xl flex items-center gap-2 transition-colors">{saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Simpan</button>}>

      {active === "ringkasan" && (
        <div className="space-y-6">
          <Card className="bg-gradient-to-r from-[#0B6B3A] to-[#27AE60] text-white">
            <p className="text-white/80 text-sm">Assalamualaikum,</p>
            <h2 className="font-display font-black text-2xl mt-1">{user?.name}</h2>
            <p className="text-white/80 text-sm mt-2">Lengkapi profil dan berkas Anda untuk melanjutkan pendaftaran MDJ Scholarship.</p>
          </Card>
          <div className="grid sm:grid-cols-3 gap-4">
            <StatTile icon={User} label="Kelengkapan Profil" value={`${progress}%`} />
            <StatTile icon={FileCheck} label="Dokumen Diunggah" value={`${docs.length}/${DOC_TYPES.length}`} />
            <StatTile icon={Activity} label="Status" value={STATUS_META[reg.status || "draft"].label} />
          </div>
          <Card>
            <div className="flex items-center justify-between mb-2"><h3 className="font-display font-bold text-[#1F2937]">Kelengkapan Profil</h3><span className="text-sm font-bold text-[#27AE60]">{progress}%</span></div>
            <div className="h-3 rounded-full bg-gray-100 overflow-hidden"><div className="h-full bg-[#27AE60] transition-all" style={{ width: `${progress}%` }} /></div>
            <p className="text-sm text-[#6B7280] mt-3">Isi seluruh data wajib pada menu Profil Saya, unggah dokumen, lalu kirim pendaftaran Anda.</p>
          </Card>
        </div>
      )}

      {active === "profil" && (
        <StudentProfile data={data} set={set} setData={setData} docs={docs} uploadDoc={uploadDoc} deleteDoc={deleteDoc} />
      )}

      {active === "daftar" && (
        <div className="space-y-6">
          <Card>
            <h3 className="font-display font-bold text-lg text-[#1F2937] mb-2">Formulir Pendaftaran Beasiswa</h3>
            <p className="text-sm text-[#6B7280] mb-5">Pilih kategori program yang sesuai dengan profil Anda.</p>
            <label className="block text-sm font-semibold text-[#1F2937] mb-1.5">Kategori Program <span className="text-[#DC2626]">*</span></label>
            <select value={reg.category || ""} onChange={(e) => setReg((p) => ({ ...p, category: e.target.value }))} data-testid="reg-category-select" className={selectCls} disabled={reg.status && reg.status !== "draft"}>
              <option value="">Pilih kategori...</option>
              {CATEGORY_OPTS.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            <div className="mt-5 rounded-xl bg-[#F9FAFB] p-4 flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-[#F2C94C] shrink-0 mt-0.5" />
              <p className="text-sm text-[#6B7280]">Kelengkapan profil saat ini <b className="text-[#1F2937]">{progress}%</b>. Data wajib harus 100% dan dokumen lengkap sebelum pendaftaran dapat dikirim.</p>
            </div>
            {(!reg.status || reg.status === "draft") ? (
              <div className="flex gap-3 mt-5">
                <button onClick={() => submitRegistration("draft")} data-testid="save-draft-btn" className="px-5 py-2.5 border border-gray-300 text-[#1F2937] text-sm font-bold rounded-xl hover:bg-gray-50">Simpan Draft</button>
                <button onClick={() => submitRegistration("submit")} data-testid="submit-registration-btn" className="px-5 py-2.5 bg-[#27AE60] hover:bg-[#0B6B3A] text-white text-sm font-bold rounded-xl transition-colors">Kirim Pendaftaran</button>
              </div>
            ) : (
              <div className="mt-5 flex items-center gap-3 rounded-xl bg-[#E8F6EE] p-4"><CheckCircle2 className="w-5 h-5 text-[#27AE60]" /><span className="text-sm font-semibold text-[#0B6B3A]">Pendaftaran Anda telah dikirim. Pantau perkembangan di menu Status Seleksi.</span></div>
            )}
          </Card>
        </div>
      )}

      {active === "dokumen" && (
        <div className="space-y-4">
          <Card>
            <h3 className="font-display font-bold text-lg text-[#1F2937] mb-1">Unggah Berkas Persyaratan</h3>
            <p className="text-sm text-[#6B7280] mb-5">Format PDF/JPG/PNG. Ukuran maksimal 5MB per file.</p>
            <div className="space-y-3">
              {DOC_TYPES.map((dt) => {
                const doc = docs.find((d) => d.doc_type === dt);
                return (
                  <div key={dt} className="flex items-center justify-between gap-3 p-3.5 rounded-xl border border-gray-100 bg-[#F9FAFB]">
                    <div className="flex items-center gap-3 min-w-0">
                      {doc ? <CheckCircle2 className="w-5 h-5 text-[#27AE60] shrink-0" /> : <Clock className="w-5 h-5 text-gray-400 shrink-0" />}
                      <div className="min-w-0"><p className="text-sm font-semibold text-[#1F2937] truncate">{dt}</p>{doc && <p className="text-xs text-[#6B7280] truncate">{doc.original_filename}</p>}</div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {doc && <button onClick={() => deleteDoc(doc.id)} data-testid={`delete-doc-${DOC_TYPES.indexOf(dt)}`} className="p-2 text-[#DC2626] hover:bg-[#FEE2E2] rounded-lg" aria-label="Hapus"><Trash2 className="w-4 h-4" /></button>}
                      <label className="px-3.5 py-2 bg-white border border-gray-300 hover:bg-gray-50 text-[#1F2937] text-xs font-bold rounded-lg cursor-pointer flex items-center gap-2">
                        <UploadCloud className="w-4 h-4" /> {doc ? "Ganti" : "Unggah"}
                        <input type="file" className="hidden" accept=".pdf,.jpg,.jpeg,.png" data-testid={`upload-doc-${DOC_TYPES.indexOf(dt)}`} onChange={(e) => uploadDoc(dt, e.target.files[0])} />
                      </label>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>
      )}

      {active === "status" && (
        <Card>
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-display font-bold text-lg text-[#1F2937]">Status Seleksi</h3>
            <StatusBadge status={reg.status || "draft"} />
          </div>
          {!reg.status || reg.status === "draft" ? (
            <p className="text-sm text-[#6B7280]">Anda belum mengirim pendaftaran. Lengkapi profil & dokumen, lalu kirim di menu Pendaftaran.</p>
          ) : (
            <div className="relative pl-8 border-l-2 border-gray-100 space-y-6">
              {["Pendaftaran Terkirim", "Verifikasi Administrasi", "Lolos Administrasi", "Wawancara Assessment", "Verifikasi Faktual", "Penerima Manfaat"].map((s, i) => {
                const done = reg.status === "ditolak" ? false : i <= currentIdx;
                const isCurrent = i === currentIdx;
                return (
                  <div key={s} className="relative" data-testid={`selection-step-${i}`}>
                    <div className={`absolute -left-[41px] w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${done ? "bg-[#27AE60] text-white" : isCurrent ? "bg-[#F2C94C] text-[#0B6B3A]" : "bg-gray-100 text-gray-400"}`}>{done ? <CheckCircle2 className="w-4 h-4" /> : i + 1}</div>
                    <p className={`font-semibold ${done || isCurrent ? "text-[#1F2937]" : "text-gray-400"}`}>{s}</p>
                  </div>
                );
              })}
              {reg.status === "ditolak" && <div className="rounded-xl bg-[#FEE2E2] p-4 text-sm text-[#DC2626] ml-[-8px]">Mohon maaf, Anda belum lolos pada tahap ini. Terima kasih atas partisipasinya.</div>}
            </div>
          )}
          {(reg.history || []).length > 0 && (
            <div className="mt-8 pt-6 border-t border-gray-100">
              <p className="font-semibold text-sm text-[#1F2937] mb-3">Riwayat</p>
              <div className="space-y-2">
                {[...reg.history].reverse().map((h, i) => (
                  <div key={i} className="flex items-start gap-3 text-sm"><div className="w-2 h-2 rounded-full bg-[#27AE60] mt-1.5" /><div><span className="font-semibold text-[#1F2937]">{STATUS_META[h.status]?.label || h.status}</span>{h.note && <span className="text-[#6B7280]"> — {h.note}</span>}<span className="block text-xs text-gray-400">{new Date(h.at).toLocaleString("id-ID")}</span></div></div>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}

      {active === "pengumuman" && (
        <div className="space-y-4">
          {(content.announcements || []).map((a, i) => (
            <Card key={i}>
              <div className="flex items-center justify-between mb-2"><span className="px-2.5 py-1 rounded-full bg-[#E8F6EE] text-[#0B6B3A] text-[11px] font-bold">{a.category}</span><span className="text-xs text-[#6B7280]">{a.date}</span></div>
              <h3 className="font-display font-bold text-[#1F2937]">{a.title}</h3>
              <p className="text-sm text-[#6B7280] mt-1">{a.summary}</p>
            </Card>
          ))}
        </div>
      )}

      {active === "pengaturan" && (
        <Card>
          <h3 className="font-display font-bold text-lg text-[#1F2937] mb-4">Informasi Akun</h3>
          <div className="space-y-3 text-sm">
            <Row label="Nama" value={user?.name} />
            <Row label="Email" value={user?.email} />
            <Row label="Metode Login" value={user?.auth_provider === "google" ? "Google" : "Email & Kata Sandi"} />
            <Row label="Peran" value="Mahasiswa Pendaftar" />
          </div>
        </Card>
      )}
    </DashboardShell>
  );
}

const inputCls = "w-full px-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#27AE60] focus:border-transparent";
const selectCls = inputCls + " bg-white";
const Card = ({ children, className = "" }) => <div className={`bg-white border border-gray-100 rounded-2xl p-6 shadow-[0_4px_20px_-2px_rgba(39,174,96,0.05)] ${className}`}>{children}</div>;
const StatTile = ({ icon: Icon, label, value }) => (
  <div className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm"><div className="w-10 h-10 rounded-xl bg-[#E8F6EE] flex items-center justify-center mb-3"><Icon className="w-5 h-5 text-[#27AE60]" /></div><p className="text-xs text-[#6B7280]">{label}</p><p className="font-display font-extrabold text-xl text-[#1F2937] mt-0.5">{value}</p></div>
);
const Row = ({ label, value }) => <div className="flex items-center justify-between py-2 border-b border-gray-50"><span className="text-[#6B7280]">{label}</span><span className="font-semibold text-[#1F2937]">{value}</span></div>;
