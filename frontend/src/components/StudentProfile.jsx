import React, { useRef, useState } from "react";
import { toast } from "sonner";
import api from "@/lib/api";
import { DocPreview, docFileUrl } from "@/components/DocPreview";
import CampusSelector from "@/components/CampusSelector";
import {
  User, MapPin, Image as ImageIcon, ShieldCheck,
  ScanLine, Loader2, CheckCircle2, UploadCloud, Info, Trash2, Camera, FileCheck,
} from "lucide-react";

// Field configuration per sub-tab
const PRIBADI = [
  { k: "namaLengkap", l: "Nama Lengkap", req: true, ph: "Masukkan nama lengkap sesuai identitas" },
  { k: "nik", l: "Nomor Induk Kependudukan (NIK)", req: true, digits: true, max: 16, ph: "Masukkan 16 digit NIK", hint: "Hanya menerima 16 digit angka." },
  { k: "noKK", l: "Nomor Kartu Keluarga", req: true, digits: true, max: 16, ph: "Masukkan 16 digit nomor KK" },
  { k: "tempatLahir", l: "Tempat Lahir", req: true, ph: "Masukkan tempat lahir" },
  { k: "tanggalLahir", l: "Tanggal Lahir", req: true, type: "date" },
  { k: "jenisKelamin", l: "Jenis Kelamin", req: true, opts: [["L", "Laki-laki"], ["P", "Perempuan"]] },
  { k: "agama", l: "Agama", req: true, opts: [["islam", "Islam"], ["kristen", "Kristen"], ["katolik", "Katolik"], ["hindu", "Hindu"], ["buddha", "Buddha"], ["konghucu", "Konghucu"]] },
  { k: "statusPerkawinan", l: "Status Perkawinan", req: true, opts: [["belum_kawin", "Belum Kawin"], ["kawin", "Kawin"], ["cerai", "Cerai"]] },
];
const KONTAK = [
  { k: "noTelp", l: "Nomor Telepon Aktif", req: true, ph: "Contoh: 08123456789", hint: "Gunakan awalan 08 atau +62." },
  { k: "email", l: "Alamat Email", req: true, type: "email", ph: "user@example.com", verified: true, hint: "Ubah email dapat dilakukan di tab Pengaturan Akun." },
];
const ALAMAT = [
  { k: "provinsi", l: "Provinsi", req: true, ph: "Masukkan provinsi" },
  { k: "kota", l: "Kota/Kabupaten", req: true, ph: "Masukkan kota/kabupaten" },
  { k: "kecamatan", l: "Kecamatan", ph: "Masukkan kecamatan" },
  { k: "kelurahan", l: "Kelurahan", ph: "Masukkan kelurahan" },
  { k: "rt", l: "RT", digits: true, max: 3, ph: "000" },
  { k: "rw", l: "RW", digits: true, max: 3, ph: "000" },
  { k: "kodePos", l: "Kode Pos", digits: true, max: 5, ph: "00000" },
  { k: "alamatLengkap", l: "Alamat Lengkap", req: true, full: true, area: true, ph: "Nama jalan, nomor rumah, blok, dll." },
];
export const PENDIDIKAN = [
  { k: "jenjang", l: "Jenjang", req: true, opts: [["D3", "D3"], ["D4", "D4"], ["S1", "S1"]] },
  { k: "institusi", l: "Perguruan Tinggi", req: true, campus: true },
  { k: "jurusan", l: "Program Studi", ph: "Masukkan program studi" },
  { k: "nim", l: "NIM", req: true, ph: "Masukkan NIM" },
  { k: "semester", l: "Semester", digits: true, max: 2, ph: "Contoh: 5" },
  { k: "ipk", l: "IPK", ph: "Contoh: 3.50" },
  {
    k: "biayaPendidikanSemester",
    l: "Nominal Biaya Pendidikan / Semester",
    digits: true,
    currency: true,
    ph: "Contoh: 3.500.000",
    hint: "Masukkan total UKT atau biaya kuliah yang dibayarkan setiap semester.",
  },
];

// KTP fields that get auto-locked once filled from the ID
const KTP_LOCKED = ["namaLengkap", "nik", "tempatLahir", "tanggalLahir", "jenisKelamin"];

export const PROFILE_REQUIRED = [...PRIBADI, ...KONTAK, ...ALAMAT, ...PENDIDIKAN].filter((f) => f.req).map((f) => f.k);
export function profileProgress(data = {}) {
  const filled = PROFILE_REQUIRED.filter((k) => data[k] && String(data[k]).trim() !== "");
  return Math.round((filled.length / PROFILE_REQUIRED.length) * 100);
}

const STEPS = [
  { id: "pribadi", label: "Data Pribadi", keys: PRIBADI.map((f) => f.k) },
  { id: "alamat", label: "Kontak & Alamat", keys: [...KONTAK, ...ALAMAT].map((f) => f.k) },
  { id: "foto", label: "Foto Profil", keys: [] },
];

const TABS = [
  { id: "pribadi", label: "Data Pribadi", icon: User },
  { id: "alamat", label: "Alamat", icon: MapPin },
  { id: "foto", label: "Foto Profil", icon: ImageIcon },
];

export default function StudentProfile({
  data,
  set,
  setData,
  docs,
  documentsLocked,
  uploadDoc,
  deleteDoc,
  onDocSaved,
}) {
  const [tab, setTab] = useState("pribadi");
  const progress = profileProgress(data);

  const stepDone = (keys) => {
    const req = [...PRIBADI, ...KONTAK, ...ALAMAT, ...PENDIDIKAN].filter((f) => f.req && keys.includes(f.k)).map((f) => f.k);
    if (req.length === 0) return false;
    return req.every((k) => data[k] && String(data[k]).trim() !== "");
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white border border-gray-100 rounded-2xl p-6 shadow-[0_4px_20px_-2px_rgba(39,174,96,0.05)]">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <h2 className="font-display font-black text-2xl text-[#1F2937]">Profil Saya</h2>
              <span className="px-2.5 py-1 rounded-full bg-[#FEF6E0] text-[#B8860B] text-[11px] font-bold border border-[#F2C94C]/40">Calon Penerima Manfaat</span>
            </div>
            <p className="text-sm text-[#6B7280] mt-1.5">Lengkapi dan pastikan data yang Anda masukkan sesuai dengan dokumen resmi.</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-[#6B7280]">Kelengkapan Profil</p>
            <p className="font-display font-black text-2xl text-[#27AE60]">{progress}%</p>
            <div className="mt-1 h-1.5 w-28 rounded-full bg-gray-100 overflow-hidden"><div className="h-full bg-[#27AE60] transition-all" style={{ width: `${progress}%` }} /></div>
          </div>
        </div>

        {/* Step indicator */}
        <div className="mt-6 flex items-center">
          {STEPS.map((s, i) => {
            const done = stepDone(s.keys);
            return (
              <React.Fragment key={s.id}>
                <button onClick={() => setTab(s.id)} data-testid={`profile-step-${s.id}`} className="flex items-center gap-2 group">
                  <span className={`w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-bold shrink-0 transition-colors ${done ? "bg-[#27AE60] text-white" : tab === s.id ? "bg-[#0B6B3A] text-white" : "bg-gray-100 text-gray-400"}`}>
                    {done ? <CheckCircle2 className="w-3.5 h-3.5" /> : i + 1}
                  </span>
                  <span className={`text-xs font-semibold hidden md:inline ${done || tab === s.id ? "text-[#1F2937]" : "text-gray-400"}`}>{s.label}</span>
                </button>
                {i < STEPS.length - 1 && <div className="flex-1 h-px bg-gray-200 mx-2 min-w-[12px]" />}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 overflow-x-auto border-b border-gray-100">
        {TABS.map((t) => {
          const Icon = t.icon;
          return (
            <button key={t.id} onClick={() => setTab(t.id)} data-testid={`profile-tab-${t.id}`}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-semibold whitespace-nowrap border-b-2 -mb-px transition-colors ${tab === t.id ? "border-[#27AE60] text-[#0B6B3A]" : "border-transparent text-[#6B7280] hover:text-[#1F2937]"}`}>
              <Icon className="w-4 h-4" /> {t.label}
            </button>
          );
        })}
      </div>

      {/* Panels */}
      {tab === "pribadi" && (
        <div className="space-y-6">
          <DocScanUploader
            type="ktp"
            docs={docs}
            locked={documentsLocked}
            setData={setData}
            onDocSaved={onDocSaved}
          />
          <DocScanUploader
            type="kk"
            docs={docs}
            locked={documentsLocked}
            setData={setData}
            onDocSaved={onDocSaved}
          />
          <SectionCard title="Data Pribadi" desc="Isi data sesuai KTP, Kartu Keluarga, atau dokumen identitas resmi.">
            <FieldGrid fields={PRIBADI} data={data} set={set} />
          </SectionCard>
          <SectionCard title="Informasi Kontak">
            <FieldGrid fields={KONTAK} data={data} set={set} />
          </SectionCard>
          <div className="rounded-xl bg-[#EFF6FF] border border-[#BFDBFE] p-4 flex items-start gap-3">
            <Info className="w-5 h-5 text-[#2563EB] shrink-0 mt-0.5" />
            <p className="text-sm text-[#1E40AF]">Data identitas tertentu (Nama, NIK, KK) tidak dapat diubah setelah pendaftaran beasiswa dikirimkan. Pastikan seluruh data sudah benar sesuai dokumen resmi.</p>
          </div>
        </div>
      )}

      {tab === "alamat" && (
        <SectionCard title="Alamat Domisili" desc="Isi alamat tempat tinggal Anda saat ini.">
          <FieldGrid fields={ALAMAT} data={data} set={set} />
        </SectionCard>
      )}

      {tab === "foto" && (
        <PhotoTab
          docs={docs}
          locked={documentsLocked}
          uploadDoc={uploadDoc}
          deleteDoc={deleteDoc}
        />
      )}
    </div>
  );
}

// ---- AI document auto-fill uploader (KTP / KK) ----
const SCAN_DOCS = {
  ktp: { label: "KTP", endpoint: "/profile/extract-ktp", desc: "Unggah foto/PDF KTP, AI akan mengisi data pribadi Anda otomatis dan file langsung tersimpan sebagai dokumen pendaftaran.", testId: "ktp", docType: "KTP DKI Jakarta" },
  kk: { label: "Kartu Keluarga", endpoint: "/profile/extract-kk", desc: "Unggah foto/PDF Kartu Keluarga, AI akan mengisi Nomor KK otomatis dan file langsung tersimpan sebagai dokumen pendaftaran.", testId: "kk", docType: "Kartu Keluarga (KK)" },
};

function DocScanUploader({ type, setData, docs, locked, onDocSaved }) {
  const cfg = SCAN_DOCS[type];
  const inputRef = useRef(null);
  const [loading, setLoading] = useState(false);
  const [filled, setFilled] = useState(0);
  const [savedDoc, setSavedDoc] = useState(null);
  const [open, setOpen] = useState(false);
  const existing = savedDoc || (docs || []).find((d) => d.doc_type === cfg.docType);

  const handle = async (file) => {
    if (!file) return;
    const ext = file.name.split(".").pop().toLowerCase();
    if (!["jpg", "jpeg", "png", "webp", "pdf"].includes(ext)) {
      return toast.error("Format harus JPG, PNG, WEBP, atau PDF.");
    }
    setLoading(true);
    const fd = new FormData();
    fd.append("file", file);
    try {
      const { data: res } = await api.post(cfg.endpoint, fd, { headers: { "Content-Type": "multipart/form-data" }, timeout: 90000 });
      const mapped = res.data || {};
      const count = Object.keys(mapped).length;
      if (count === 0) { toast.error(`Tidak ada data yang terbaca dari ${cfg.label}.`); return; }
      setData((p) => ({ ...p, ...mapped }));
      setFilled(count);
      if (res.document && onDocSaved) { onDocSaved(res.document); setSavedDoc(res.document); }
      toast.success(`Berhasil! ${count} kolom terisi otomatis dari ${cfg.label}${res.document ? " dan file tersimpan di Dokumen Pendaftaran" : ""}.`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || `Gagal membaca ${cfg.label}. Coba lagi dengan foto yang lebih jelas.`);
    } finally {
      setLoading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return (
    <div className="rounded-2xl border-2 border-dashed border-[#27AE60]/40 bg-gradient-to-br from-[#F0FBF5] to-white p-5" data-testid={`${cfg.testId}-scan-card`}>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
        <div className="flex min-w-0 flex-1 items-start gap-3">
          <div className="w-11 h-11 rounded-xl bg-[#E8F6EE] flex items-center justify-center shrink-0"><ScanLine className="w-6 h-6 text-[#27AE60]" /></div>
          <div className="min-w-0">
            <h4 className="font-display font-bold text-[#1F2937] flex items-center gap-2">Isi Otomatis dari {cfg.label} <span className="px-2 py-0.5 rounded-full bg-[#27AE60] text-white text-[10px] font-bold">AI</span></h4>
            <p className="text-sm text-[#6B7280] mt-0.5">{cfg.desc}</p>
            {filled > 0 && !loading && <p className="text-xs text-[#27AE60] font-semibold mt-1 flex items-center gap-1"><CheckCircle2 className="w-3.5 h-3.5" /> {filled} kolom terisi dari {cfg.label} terakhir.</p>}
            {existing && !loading && <button type="button" onClick={() => setOpen(true)} className="text-xs text-[#0B6B3A] hover:underline mt-1 flex items-center gap-1" data-testid={`${cfg.testId}-saved-doc`}><FileCheck className="w-3.5 h-3.5 text-[#27AE60]" /> Dokumen tersimpan: {existing.original_filename}</button>}
            {open && <DocPreview doc={existing} onClose={() => setOpen(false)} />}
          </div>
        </div>
        <button
          onClick={() => inputRef.current?.click()}
          disabled={loading || locked}
          data-testid={`${cfg.testId}-upload-btn`}
          className="flex shrink-0 items-center justify-center gap-2 self-start rounded-xl bg-[#27AE60] px-5 py-2.5 text-sm font-bold text-white transition-colors hover:bg-[#0B6B3A] disabled:opacity-60 sm:self-auto"
        >
          {loading ? (
            <><Loader2 className="w-4 h-4 animate-spin" /> Membaca {cfg.label}...</>
          ) : locked ? (
            <><FileCheck className="w-4 h-4" /> Dokumen Terkunci</>
          ) : (
            <><UploadCloud className="w-4 h-4" /> Unggah {cfg.label}</>
          )}
        </button>
        <input
          ref={inputRef}
          type="file"
          disabled={locked}
          className="hidden"
          accept=".jpg,.jpeg,.png,.webp,.pdf"
          data-testid={`${cfg.testId}-file-input`}
          onChange={(event) => handle(event.target.files[0])}
        />
      </div>
    </div>
  );
}

// ---- Foto Profil tab ----
const PHOTO_DOC = "Pas Foto 3x4";
function PhotoTab({ docs, locked, uploadDoc, deleteDoc }) {
  const inputRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);
  const photo = (docs || []).find((d) => d.doc_type === PHOTO_DOC);
  const previewUrl = photo ? docFileUrl(photo) : null;

  const onFile = async (file) => {
    if (!file) return;
    setBusy(true);
    await uploadDoc(PHOTO_DOC, file);
    setBusy(false);
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <SectionCard title="Foto Profil" desc="Unggah pas foto formal 3x4 dengan latar belakang polos. Format JPG/PNG, maksimal 5MB.">
      <div className="flex flex-col sm:flex-row items-center gap-6">
        <div className="w-32 h-40 rounded-xl border-2 border-gray-200 bg-[#F9FAFB] overflow-hidden flex items-center justify-center shrink-0">
          {previewUrl ? <img src={previewUrl} alt="Pas foto" onClick={() => setOpen(true)} className="w-full h-full object-cover cursor-zoom-in" data-testid="profile-photo-preview" /> : <Camera className="w-10 h-10 text-gray-300" />}
        </div>
        {open && <DocPreview doc={photo} onClose={() => setOpen(false)} />}
        <div className="flex-1 text-center sm:text-left">
          <p className="text-sm text-[#6B7280] mb-3">{photo ? `File saat ini: ${photo.original_filename}` : "Belum ada foto yang diunggah."}</p>
          <div className="flex flex-wrap gap-2 justify-center sm:justify-start">
            <button onClick={() => inputRef.current?.click()} disabled={busy || locked} data-testid="upload-photo-btn"
              className="px-4 py-2 bg-[#27AE60] hover:bg-[#0B6B3A] disabled:opacity-60 text-white text-sm font-bold rounded-xl flex items-center gap-2 transition-colors">
              {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <UploadCloud className="w-4 h-4" />} {photo ? "Ganti Foto" : "Unggah Foto"}
            </button>
            {photo && !locked && (
              <button
                type="button"
                onClick={() => deleteDoc(photo.id)}
                data-testid="delete-photo-btn"
                className="px-4 py-2 border border-gray-300 text-[#DC2626] text-sm font-bold rounded-xl flex items-center gap-2 hover:bg-[#FEE2E2]"
              >
                <Trash2 className="w-4 h-4" /> Hapus
              </button>
            )}
          </div>
          <input
            ref={inputRef}
            type="file"
            disabled={locked}
            className="hidden"
            accept=".jpg,.jpeg,.png"
            data-testid="photo-file-input"
            onChange={(event) => onFile(event.target.files[0])}
          />
        </div>
      </div>
    </SectionCard>
  );
}

// ---- shared bits ----
const inputCls = "w-full px-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#27AE60] focus:border-transparent";
const formatRupiah = (value) => String(value || "").replace(/\B(?=(\d{3})+(?!\d))/g, ".");
const SectionCard = ({ title, desc, children }) => (
  <div className="bg-white border border-gray-100 rounded-2xl p-6 shadow-[0_4px_20px_-2px_rgba(39,174,96,0.05)]">
    <h3 className="font-display font-bold text-lg text-[#1F2937]">{title}</h3>
    {desc && <p className="text-sm text-[#6B7280] mt-1 mb-5">{desc}</p>}
    {!desc && <div className="mb-5" />}
    {children}
  </div>
);
export const FieldGrid = ({ fields, data, set, campuses = [] }) => {
  const [otherCampusFields, setOtherCampusFields] = useState({});
  const campusNames = campuses.map((campus) => campus.name.trim().toLowerCase());

  return (
  <div className="grid sm:grid-cols-2 gap-x-5 gap-y-4">
    {fields.map((f) => (
      <div key={f.k} className={f.full ? "sm:col-span-2" : ""}>
        <div className="flex items-center justify-between mb-1.5">
          <label className="block text-sm font-semibold text-[#1F2937]">{f.l} {f.req && <span className="text-[#DC2626]">*</span>}</label>
          {f.verified && data[f.k] && <span className="px-2 py-0.5 rounded-full bg-[#E8F6EE] text-[#0B6B3A] text-[10px] font-bold flex items-center gap-1"><ShieldCheck className="w-3 h-3" /> Terverifikasi</span>}
        </div>
        {f.opts ? (
          <select value={data[f.k] || ""} onChange={(e) => set(f.k, e.target.value)} data-testid={`field-${f.k}`} className={inputCls + " bg-white"}>
            <option value="">Pilih salah satu...</option>
            {f.opts.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        ) : f.campus ? (
          <CampusField
            field={f}
            data={data}
            set={set}
            campuses={campuses}
            isOther={
              otherCampusFields[f.k] ||
              (!campusNames.includes(String(data[f.k] || "").trim().toLowerCase()) && !!data[f.k])
            }
            setOther={(value) => setOtherCampusFields((previous) => ({
              ...previous,
              [f.k]: value,
            }))}
          />
        ) : f.area ? (
          <textarea value={data[f.k] || ""} onChange={(e) => set(f.k, e.target.value)} data-testid={`field-${f.k}`} rows={2} placeholder={f.ph} className={inputCls} />
        ) : f.currency ? (
          <div className="relative">
            <span
              className="pointer-events-none absolute inset-y-0 left-0 flex items-center px-4 text-sm font-bold text-[#0B6B3A]"
            >
              Rp
            </span>
            <input
              type="text"
              inputMode="numeric"
              value={formatRupiah(data[f.k])}
              placeholder={f.ph}
              onChange={(e) => set(f.k, e.target.value.replace(/\D/g, ""))}
              data-testid={`field-${f.k}`}
              className={inputCls + " pl-11"}
            />
          </div>
        ) : (
          <input type={f.type || "text"} value={data[f.k] || ""} maxLength={f.max} placeholder={f.ph}
            onChange={(e) => set(f.k, f.digits ? e.target.value.replace(/\D/g, "") : e.target.value)}
            data-testid={`field-${f.k}`} className={inputCls} />
        )}
        {f.hint && <p className="text-xs text-[#9CA3AF] mt-1">{f.hint}</p>}
      </div>
    ))}
  </div>
  );
};

function CampusField({ field, data, set, campuses, isOther, setOther }) {
  return (
    <div className="space-y-2">
      <CampusSelector
        campuses={campuses}
        fieldKey={field.k}
        isOther={isOther}
        value={data[field.k] || ""}
        onChange={(value) => {
          setOther(false);
          set(field.k, value);
        }}
        onSelectOther={() => {
          setOther(true);
          set(field.k, "");
        }}
      />
      {isOther && (
        <input
          value={data[field.k] || ""}
          onChange={(event) => set(field.k, event.target.value)}
          placeholder="Masukkan nama kampus"
          data-testid={`field-${field.k}-other`}
          className={inputCls}
        />
      )}
    </div>
  );
}
