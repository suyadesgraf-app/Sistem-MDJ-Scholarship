import React, { useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Eye,
  Clock,
  FileCheck,
  FileText,
  GraduationCap,
  Save,
  Trash2,
  UploadCloud,
} from "lucide-react";
import { FieldGrid, PENDIDIKAN } from "@/components/StudentProfile";
import { DocPreview } from "@/components/DocPreview";
import EducationDocumentScan from "@/components/EducationDocumentScan";

const DOC_TYPES = [
  "KTP DKI Jakarta",
  "Kartu Keluarga (KK)",
  "Pas Foto 3x4",
  "Kartu Tanda Mahasiswa (KTM)",
  "KRS / KHS / Transkrip Nilai",
  "Surat Keterangan Mahasiswa Aktif",
  "SKTM / Surat Rekomendasi",
  "Surat Persetujuan Orang Tua",
  "Surat Keterangan Tidak Menerima Beasiswa Lain",
  "Pakta Integritas",
];

const CATEGORY_OPTS = [
  "Mahasiswa Sarjana (S1)",
  "Mahasiswa Vokasi",
  "Koordinator Akademik",
  "Volunteer / Relawan",
];

const SUBMENU = [
  { id: "pendidikan", label: "Data Pendidikan", icon: GraduationCap },
  { id: "dokumen", label: "Dokumen", icon: FileCheck },
  { id: "formulir", label: "Formulir Pakta Integritas", icon: FileText },
];

const inputCls =
  "w-full px-4 py-2.5 border border-gray-300 rounded-xl text-sm " +
  "focus:outline-none focus:ring-2 focus:ring-[#27AE60] focus:border-transparent";

const Card = ({ children, className = "" }) => (
  <div
    className={[
      "bg-white border border-gray-100 rounded-2xl p-6",
      "shadow-[0_4px_20px_-2px_rgba(39,174,96,0.05)]",
      className,
    ].join(" ")}
  >
    {children}
  </div>
);

export default function RegistrationSections({
  data,
  setData,
  docs,
  reg,
  setReg,
  progress,
  saving,
  onSaveProfile,
  onUploadDoc,
  onDeleteDoc,
  onDocumentSaved,
  onSubmitRegistration,
}) {
  const [tab, setTab] = useState("pendidikan");
  const [preview, setPreview] = useState(null);
  const set = (key, value) => setData((previous) => ({ ...previous, [key]: value }));

  return (
    <div className="space-y-6" data-testid="registration-sections">
      <div className="flex gap-1 overflow-x-auto border-b border-gray-100">
        {SUBMENU.map((item) => {
          const Icon = item.icon;
          const selected = tab === item.id;

          return (
            <button
              key={item.id}
              type="button"
              onClick={() => setTab(item.id)}
              data-testid={`registration-tab-${item.id}`}
              aria-current={selected ? "page" : undefined}
              className={[
                "flex items-center gap-2 px-4 py-3 text-sm font-semibold whitespace-nowrap",
                "border-b-2 -mb-px transition-colors",
                  selected
                    ? "border-[#27AE60] text-[#0B6B3A]"
                    : "border-transparent text-[#6B7280] hover:text-[#1F2937]",
              ].join(" ")}
            >
              <Icon className="w-4 h-4" />
              {item.label}
            </button>
          );
        })}
      </div>

      {tab === "formulir" && (
        <Card>
          <h3 className="font-display font-bold text-lg text-[#1F2937] mb-2">
            Formulir Pendaftaran Beasiswa
          </h3>
          <p className="text-sm text-[#6B7280] mb-5">
            Pilih kategori program yang sesuai dengan profil Anda.
          </p>
          <label className="block text-sm font-semibold text-[#1F2937] mb-1.5">
            Kategori Program <span className="text-[#DC2626]">*</span>
          </label>
          <select
            value={reg.category || ""}
            onChange={(event) => setReg((previous) => ({
              ...previous,
              category: event.target.value,
            }))}
            data-testid="reg-category-select"
            className={inputCls + " bg-white"}
            disabled={reg.status && reg.status !== "draft"}
          >
            <option value="">Pilih kategori...</option>
            {CATEGORY_OPTS.map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>
          <div className="mt-5 rounded-xl bg-[#F9FAFB] p-4 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-[#B8860B] shrink-0 mt-0.5" />
            <p className="text-sm text-[#6B7280]" data-testid="registration-progress-note">
              Kelengkapan profil saat ini <b className="text-[#1F2937]">{progress}%</b>.
              Data wajib harus 100% dan dokumen lengkap sebelum pendaftaran dapat dikirim.
            </p>
          </div>
          {(!reg.status || reg.status === "draft") ? (
            <div className="flex flex-wrap gap-3 mt-5">
              <button
                type="button"
                onClick={() => onSubmitRegistration("draft")}
                data-testid="save-draft-btn"
                className={[
                  "px-5 py-2.5 border border-gray-300 text-[#1F2937] text-sm font-bold",
                  "rounded-xl hover:bg-gray-50",
                ].join(" ")}
              >
                Simpan Draft
              </button>
              <button
                type="button"
                onClick={() => onSubmitRegistration("submit")}
                data-testid="submit-registration-btn"
                className={[
                  "px-5 py-2.5 bg-[#27AE60] hover:bg-[#0B6B3A] text-white text-sm",
                  "font-bold rounded-xl transition-colors",
                ].join(" ")}
              >
                Kirim Pendaftaran
              </button>
            </div>
          ) : (
            <div
              className="mt-5 flex items-center gap-3 rounded-xl bg-[#E8F6EE] p-4"
              data-testid="registration-submitted-confirmation"
            >
              <CheckCircle2 className="w-5 h-5 text-[#27AE60]" />
              <span className="text-sm font-semibold text-[#0B6B3A]">
                Pendaftaran Anda telah dikirim. Pantau perkembangan di menu Status Seleksi.
              </span>
            </div>
          )}
        </Card>
      )}

      {tab === "pendidikan" && (
        <Card>
          <h3 className="font-display font-bold text-lg text-[#1F2937]">
            Data Pendidikan
          </h3>
          <p className="text-sm text-[#6B7280] mt-1 mb-5">
            Isi data perguruan tinggi tempat Anda menempuh studi.
          </p>
          <EducationDocumentScan
            docs={docs}
            setData={setData}
            onDocumentSaved={onDocumentSaved}
          />
          <p className="mt-5 text-xs leading-relaxed text-[#6B7280]">
            Tinjau hasil AI, perbaiki bila perlu, lalu simpan data pendidikan.
          </p>
          <FieldGrid fields={PENDIDIKAN} data={data} set={set} />
          <div className="mt-6 flex justify-end">
            <button
              type="button"
              onClick={onSaveProfile}
              disabled={saving}
              data-testid="save-education-btn"
              className={[
                "px-5 py-2.5 bg-[#27AE60] hover:bg-[#0B6B3A] disabled:opacity-60",
                "text-white text-sm font-bold rounded-xl flex items-center gap-2",
                "transition-colors",
              ].join(" ")}
            >
              <Save className="w-4 h-4" />
              {saving ? "Menyimpan..." : "Simpan Data Pendidikan"}
            </button>
          </div>
        </Card>
      )}

      {tab === "dokumen" && (
        <Card>
          <h3 className="font-display font-bold text-lg text-[#1F2937] mb-1">
            Unggah Berkas Persyaratan
          </h3>
          <p className="text-sm text-[#6B7280] mb-5">
            Format PDF/JPG/PNG. Ukuran maksimal 5MB per file.
          </p>
          <div className="space-y-3">
            {DOC_TYPES.map((docType, index) => {
              const document = docs.find((item) => item.doc_type === docType);

              return (
                <div
                  key={docType}
                  className={[
                    "flex flex-wrap items-center justify-between gap-3 p-3.5 rounded-xl",
                    "border border-gray-100 bg-[#F9FAFB]",
                  ].join(" ")}
                  data-testid={`document-row-${index}`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    {document ? (
                      <CheckCircle2 className="w-5 h-5 text-[#27AE60] shrink-0" />
                    ) : (
                      <Clock className="w-5 h-5 text-gray-400 shrink-0" />
                    )}
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-[#1F2937] truncate">
                        {docType}
                      </p>
                      {document && (
                        <button
                          type="button"
                          onClick={() => setPreview(document)}
                          data-testid={`preview-document-${index}`}
                          className="text-xs text-[#0B6B3A] hover:underline truncate max-w-[260px] flex items-center gap-1"
                        >
                          <Eye className="w-3.5 h-3.5 shrink-0" /> {document.original_filename}
                        </button>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {document && (
                      <button
                        type="button"
                        onClick={() => onDeleteDoc(document.id)}
                        data-testid={`delete-document-${index}`}
                        aria-label={`Hapus ${docType}`}
                        className="p-2 text-[#DC2626] hover:bg-[#FEE2E2] rounded-lg"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                    <label
                      data-testid={`document-upload-trigger-${index}`}
                      className={[
                        "px-3.5 py-2 bg-white border border-gray-300 hover:bg-gray-50",
                        "text-[#1F2937] text-xs font-bold rounded-lg cursor-pointer",
                        "flex items-center gap-2",
                      ].join(" ")}
                    >
                      <UploadCloud className="w-4 h-4" />
                      {document ? "Ganti" : "Unggah"}
                      <input
                        type="file"
                        className="hidden"
                        accept=".pdf,.jpg,.jpeg,.png"
                        data-testid={`upload-document-${index}`}
                        onChange={(event) => onUploadDoc(docType, event.target.files[0])}
                      />
                    </label>
                  </div>
                </div>
              );
            })}
          </div>
          <DocPreview doc={preview} onClose={() => setPreview(null)} />
        </Card>
      )}
    </div>
  );
}