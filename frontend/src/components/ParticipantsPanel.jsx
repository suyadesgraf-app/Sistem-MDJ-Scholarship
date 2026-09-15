import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import api from "@/lib/api";
import { StatusBadge, STATUS_META } from "@/components/DashboardShell";
import { useAuth } from "@/context/AuthContext";
import { Search, Eye, X, FileText, Download, Loader2, Building2, Phone, Mail, GraduationCap } from "lucide-react";
import { DocPreview } from "@/components/DocPreview";

const STATUS_FILTERS = [
  ["all", "Semua"], ["submitted", "Terkirim"], ["verifikasi", "Verifikasi"],
  ["lolos_administrasi", "Lolos Adm."], ["wawancara", "Wawancara"],
  ["verifikasi_faktual", "Verif. Faktual"], ["lolos", "Penerima"], ["ditolak", "Tidak Lolos"],
];
const STATUS_OPTS = ["submitted", "verifikasi", "lolos_administrasi", "wawancara", "verifikasi_faktual", "lolos", "ditolak"];

export default function ParticipantsPanel() {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [status, setStatus] = useState("all");
  const [region, setRegion] = useState("all");
  const [regions, setRegions] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [detail, setDetail] = useState(null);
  const lockedRegion = user?.role === "admin_wilayah" ? user.region : "";

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/admin/participants", {
        params: {
          status,
          region: lockedRegion || (region === "all" ? undefined : region),
          search: search || undefined,
        },
      });
      setItems(data);
    } catch { toast.error("Gagal memuat data peserta."); }
    finally { setLoading(false); }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, region]);
  useEffect(() => {
    if (lockedRegion) {
      setRegions([lockedRegion]);
      setRegion(lockedRegion);
      return;
    }
    api.get("/admin/stats")
      .then((response) => setRegions(response.data.available_regions || []))
      .catch(() => setRegions([]));
  }, [lockedRegion]);

  const exportExcel = async () => {
    setExporting(true);
    try {
      const response = await api.get("/admin/participants/export.xlsx", {
        params: {
          status,
          region: lockedRegion || (region === "all" ? undefined : region),
          search: search || undefined,
        },
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = "data-peserta-mdj.xlsx";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success("Data peserta berhasil diekspor ke Excel.");
    } catch {
      toast.error("Gagal mengekspor data peserta.");
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3">
        <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
          <p className="text-sm font-bold text-[#1F2937]" data-testid="participant-total">
            Jumlah Mahasiswa: {items.length} peserta
          </p>
          <div className="flex flex-wrap items-center gap-2">
            {lockedRegion ? (
              <span
                className="rounded-lg border border-[#B7E4C7] bg-[#F0FBF5] px-3 py-2 text-sm font-bold text-[#0B6B3A]"
                data-testid="regional-admin-participant-scope"
              >
                Wilayah kerja: {lockedRegion}
              </span>
            ) : (
              <label className="flex items-center gap-2 text-sm font-semibold text-[#6B7280]">
                Wilayah
                <select
                  value={region}
                  onChange={(event) => setRegion(event.target.value)}
                  data-testid="participant-region-filter"
                  className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-[#1F2937] outline-none focus:border-[#27AE60]"
                >
                  <option value="all">Keseluruhan Wilayah</option>
                  {regions.map((item) => <option key={item} value={item}>{item}</option>)}
                </select>
              </label>
            )}
            <button
              type="button"
              onClick={exportExcel}
              disabled={exporting}
              data-testid="export-participants-excel-button"
              className="inline-flex items-center gap-2 rounded-lg bg-[#0B6B3A] px-4 py-2.5 text-sm font-bold text-white transition-colors hover:bg-[#07532d] disabled:opacity-60"
            >
              {exporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
              {exporting ? "Mengekspor..." : "Export Excel"}
            </button>
          </div>
        </div>
        <div className="flex flex-col sm:flex-row gap-3 sm:items-center justify-between">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input value={search} onChange={(e) => setSearch(e.target.value)} onKeyDown={(e) => e.key === "Enter" && load()} data-testid="participant-search"
            placeholder="Cari nama, email, kampus..." className="w-full pl-11 pr-4 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#27AE60]" />
        </div>
        <div className="flex gap-1.5 overflow-x-auto pb-1 mdj-scrollbar">
          {STATUS_FILTERS.map(([v, l]) => (
            <button key={v} onClick={() => setStatus(v)} data-testid={`filter-${v}`}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold whitespace-nowrap transition-colors ${status === v ? "bg-[#27AE60] text-white" : "bg-white border border-gray-200 text-[#6B7280] hover:bg-gray-50"}`}>{l}</button>
          ))}
        </div>
        </div>
      </div>

      <div className="bg-white border border-gray-100 rounded-2xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto mdj-scrollbar">
          <table className="w-full text-sm" data-testid="participants-table">
            <thead><tr className="text-left text-xs text-[#6B7280] border-b border-gray-100 bg-[#F9FAFB]">
              <th className="px-4 py-3 font-semibold">No.</th>
              <th className="px-4 py-3 font-semibold">Nama</th>
              <th className="px-4 py-3 font-semibold">Kampus</th>
              <th className="px-4 py-3 font-semibold">Wilayah</th>
              <th className="px-4 py-3 font-semibold">Dok.</th>
              <th className="px-4 py-3 font-semibold">Status</th>
              <th className="px-4 py-3 font-semibold text-right">Aksi</th>
            </tr></thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={7} className="px-4 py-12 text-center text-gray-400"><Loader2 className="w-5 h-5 animate-spin inline" /></td></tr>
              ) : items.length === 0 ? (
                <tr><td colSpan={7} className="px-4 py-12 text-center text-gray-400">Belum ada pendaftar.</td></tr>
              ) : items.map((p, index) => (
                <tr key={p.user_id} className="border-b border-gray-50 hover:bg-[#F9FAFB] transition-colors">
                  <td className="px-4 py-3 text-sm font-semibold text-[#6B7280]" data-testid={`participant-sequence-${p.user_id}`}>
                    {index + 1}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-semibold text-[#1F2937]">{p.name}</p>
                      {p.is_test_data && (
                        <span
                          className="rounded-full bg-[#FEF3C7] px-2 py-0.5 text-[10px] font-bold text-[#92400E]"
                          data-testid={`test-data-badge-${p.user_id}`}
                        >
                          Data Uji MDJ
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-[#6B7280]">{p.email}</p>
                  </td>
                  <td className="px-4 py-3 text-[#6B7280]">{p.institusi} <span className="block text-xs">{p.jenjang}</span></td>
                  <td className="px-4 py-3 text-[#6B7280]" data-testid={`participant-region-${p.user_id}`}>
                    {p.wilayah}
                  </td>
                  <td className="px-4 py-3 text-[#6B7280]">{p.doc_count}</td>
                  <td className="px-4 py-3"><StatusBadge status={p.status} /></td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={() => setDetail(p.user_id)} data-testid={`view-participant-${p.user_id}`} className="px-3 py-1.5 bg-[#E8F6EE] text-[#0B6B3A] text-xs font-bold rounded-lg hover:bg-[#d3efdf] inline-flex items-center gap-1.5"><Eye className="w-3.5 h-3.5" /> Detail</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {detail && (
        <DetailModal
          userId={detail}
          onClose={() => setDetail(null)}
          onUpdated={load}
          canManageDocuments={user?.role !== "admin_wilayah"}
        />
      )}
    </div>
  );
}

function DetailModal({ userId, onClose, onUpdated, canManageDocuments }) {
  const [data, setData] = useState(null);
  const [newStatus, setNewStatus] = useState("");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [updatingDocumentPermission, setUpdatingDocumentPermission] = useState(false);

  useEffect(() => {
    api.get(`/admin/participants/${userId}`).then((r) => { setData(r.data); setNewStatus(r.data.registration?.status || "submitted"); });
  }, [userId]);

  const [preview, setPreview] = useState(null);
  const viewFile = (doc) => setPreview(doc);

  const updateStatus = async () => {
    setSaving(true);
    try {
      await api.put(`/admin/participants/${userId}/status`, { status: newStatus, note });
      toast.success("Status peserta diperbarui.");
      setNote("");
      const r = await api.get(`/admin/participants/${userId}`); setData(r.data);
      onUpdated();
    } catch { toast.error("Gagal memperbarui status."); }
    finally { setSaving(false); }
  };

  const updateDocumentPermission = async (allowed) => {
    setUpdatingDocumentPermission(true);
    try {
      const response = await api.put(
        `/admin/participants/${userId}/document-editing-permission`,
        { allowed },
      );
      setData((previous) => ({ ...previous, registration: response.data }));
      toast.success(allowed ? "Izin edit dokumen diberikan." : "Izin edit dokumen dikunci kembali.");
      onUpdated();
    } catch {
      toast.error("Izin edit dokumen belum dapat diperbarui.");
    } finally {
      setUpdatingDocumentPermission(false);
    }
  };

  const p = data?.profile || {};
  return (
    <div className="fixed inset-0 z-50 bg-[#1F2937]/50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto mdj-scrollbar" onClick={(e) => e.stopPropagation()} data-testid="participant-detail-modal">
        <div className="sticky top-0 bg-white border-b border-gray-100 px-6 py-4 flex items-center justify-between">
          <h3 className="font-display font-bold text-lg text-[#1F2937]">Detail Peserta</h3>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg" data-testid="close-detail-modal"><X className="w-5 h-5" /></button>
        </div>
        {!data ? <div className="p-12 text-center"><Loader2 className="w-6 h-6 animate-spin inline text-[#27AE60]" /></div> : (
          <div className="p-6 space-y-6">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-full bg-[#E8F6EE] flex items-center justify-center text-[#0B6B3A] font-bold text-xl">{(data.account?.name || "?").charAt(0)}</div>
              <div><p className="font-display font-bold text-lg text-[#1F2937]">{data.account?.name}</p><div className="mt-1"><StatusBadge status={data.registration?.status || "draft"} /></div></div>
            </div>
            <Grid>
              <Info icon={Mail} label="Email" value={data.account?.email} />
              <Info icon={Phone} label="Telepon" value={p.noTelp} />
              <Info icon={GraduationCap} label="Jenjang" value={p.jenjang} />
              <Info icon={Building2} label="Kampus" value={p.institusi} />
              <Info label="Program Studi" value={p.jurusan} />
              <Info label="NIM" value={p.nim} />
              <Info label="NIK" value={p.nik} />
              <Info label="IPK" value={p.ipk} />
              <Info label="Kategori" value={data.registration?.category} />
              <Info label="Alamat" value={p.alamatLengkap} full />
            </Grid>

            <div>
              <p className="font-semibold text-sm text-[#1F2937] mb-2">Dokumen ({data.documents?.length || 0})</p>
              {(data.documents || []).length === 0 ? <p className="text-sm text-gray-400">Belum ada dokumen diunggah.</p> : (
                <div className="grid sm:grid-cols-2 gap-2">
                  {data.documents.map((d) => (
                    <button key={d.id} onClick={() => viewFile(d)} data-testid={`view-file-${d.id}`} className="flex items-center gap-3 p-3 rounded-xl border border-gray-100 bg-[#F9FAFB] hover:bg-[#E8F6EE] text-left transition-colors">
                      <FileText className="w-5 h-5 text-[#27AE60] shrink-0" />
                      <div className="min-w-0 flex-1"><p className="text-xs font-semibold text-[#1F2937] truncate">{d.doc_type}</p><p className="text-[11px] text-[#6B7280] truncate">{d.original_filename}</p></div>
                      <Eye className="w-4 h-4 text-[#6B7280]" />
                    </button>
                  ))}
                </div>
              )}
              <DocPreview doc={preview} onClose={() => setPreview(null)} />
            </div>

            {canManageDocuments && (
              <div className="border-t border-gray-100 pt-5">
                <p className="font-semibold text-sm text-[#1F2937] mb-3">Izin Edit Dokumen</p>
                <div
                  className="flex flex-wrap items-center justify-between gap-3 border border-[#FDE68A] bg-[#FFFBEB] p-4"
                  data-testid="document-editing-permission-panel"
                >
                  <p className="max-w-lg text-sm leading-relaxed text-[#5E4A00]">
                    {data.registration?.documents_editing_allowed
                      ? "Mahasiswa saat ini diizinkan memperbaiki dokumen pendaftarannya."
                      : "Dokumen terkunci setelah pendaftaran dikirim. Berikan izin bila perlu diperbaiki."}
                  </p>
                  <button
                    type="button"
                    onClick={() => updateDocumentPermission(!data.registration?.documents_editing_allowed)}
                    disabled={updatingDocumentPermission}
                    data-testid="toggle-document-editing-permission"
                    className={[
                      "rounded-lg px-4 py-2.5 text-sm font-bold text-white transition-colors",
                      data.registration?.documents_editing_allowed
                        ? "bg-[#B8860B] hover:bg-[#936C00]"
                        : "bg-[#0B6B3A] hover:bg-[#07532D]",
                      "disabled:cursor-wait disabled:opacity-60",
                    ].join(" ")}
                  >
                    {updatingDocumentPermission
                      ? "Memperbarui..."
                      : data.registration?.documents_editing_allowed
                        ? "Kunci Kembali Dokumen"
                        : "Izinkan Edit Dokumen"}
                  </button>
                </div>
              </div>
            )}

            <div className="border-t border-gray-100 pt-5">
              <p className="font-semibold text-sm text-[#1F2937] mb-3">Perbarui Status Seleksi</p>
              <div className="space-y-3">
                <select value={newStatus} onChange={(e) => setNewStatus(e.target.value)} data-testid="status-select" className="w-full px-4 py-2.5 border border-gray-300 rounded-xl text-sm bg-white focus:outline-none focus:ring-2 focus:ring-[#27AE60]">
                  {STATUS_OPTS.map((s) => <option key={s} value={s}>{STATUS_META[s].label}</option>)}
                </select>
                <input value={note} onChange={(e) => setNote(e.target.value)} data-testid="status-note-input" placeholder="Catatan (opsional)" className="w-full px-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#27AE60]" />
                <button onClick={updateStatus} disabled={saving} data-testid="update-status-btn" className="w-full py-2.5 bg-[#27AE60] hover:bg-[#0B6B3A] text-white text-sm font-bold rounded-xl flex items-center justify-center gap-2 transition-colors">{saving ? <Loader2 className="w-4 h-4 animate-spin" /> : null} Simpan Status</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

const Grid = ({ children }) => <div className="grid sm:grid-cols-2 gap-x-4 gap-y-3">{children}</div>;
const Info = ({ icon: Icon, label, value, full }) => (
  <div className={full ? "sm:col-span-2" : ""}>
    <p className="text-xs text-[#6B7280] flex items-center gap-1.5">{Icon && <Icon className="w-3.5 h-3.5" />}{label}</p>
    <p className="text-sm font-semibold text-[#1F2937] mt-0.5">{value || "-"}</p>
  </div>
);
