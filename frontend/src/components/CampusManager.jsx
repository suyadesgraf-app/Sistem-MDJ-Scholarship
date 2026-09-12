import React, { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import {
  Building2,
  FileSpreadsheet,
  Loader2,
  Pencil,
  Plus,
  Search,
  Trash2,
  X,
} from "lucide-react";
import api from "@/lib/api";

const emptyForm = { name: "", code: "" };

export default function CampusManager() {
  const importRef = useRef(null);
  const [campuses, setCampuses] = useState([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [importing, setImporting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [editing, setEditing] = useState(null);
  const [deleting, setDeleting] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const response = await api.get("/campuses");
      setCampuses(response.data || []);
    } catch {
      toast.error("Data kampus belum dapat dimuat.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    if (!keyword) return campuses;
    return campuses.filter((campus) => (
      `${campus.name} ${campus.code || ""}`.toLowerCase().includes(keyword)
    ));
  }, [campuses, query]);

  const resetForm = () => {
    setForm(emptyForm);
    setEditing(null);
  };

  const submit = async (event) => {
    event.preventDefault();
    setSaving(true);
    try {
      if (editing) {
        await api.put(`/campuses/${editing.id}`, form);
        toast.success("Data kampus diperbarui.");
      } else {
        await api.post("/campuses", form);
        toast.success("Kampus baru ditambahkan.");
      }
      resetForm();
      await load();
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Gagal menyimpan data kampus.");
    } finally {
      setSaving(false);
    }
  };

  const importFile = async (file) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".xlsx")) {
      toast.error("Pilih file Excel berformat XLSX.");
      return;
    }
    setImporting(true);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const response = await api.post("/campuses/import", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast.success(
        `${response.data.inserted} kampus ditambahkan, ${response.data.updated} diperbarui.`,
      );
      await load();
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Gagal mengimpor file kampus.");
    } finally {
      setImporting(false);
      if (importRef.current) importRef.current.value = "";
    }
  };

  const confirmDelete = async () => {
    if (!deleting) return;
    try {
      await api.delete(`/campuses/${deleting.id}`);
      setCampuses((previous) => previous.filter((campus) => campus.id !== deleting.id));
      toast.success("Data kampus dihapus.");
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Gagal menghapus data kampus.");
    } finally {
      setDeleting(null);
    }
  };

  return (
    <div className="space-y-6" data-testid="campus-manager">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-sm text-[#6B7280]">
            Kelola daftar kampus yang menjadi pilihan mahasiswa saat mendaftar.
          </p>
          <p className="mt-1 text-xs font-semibold text-[#0B6B3A]" data-testid="campus-total">
            {campuses.length} kampus terdaftar
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => importRef.current?.click()}
            disabled={importing}
            data-testid="import-campuses-button"
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm font-bold text-[#1F2937] transition-colors hover:bg-gray-50 disabled:opacity-60"
          >
            {importing ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileSpreadsheet className="h-4 w-4" />}
            {importing ? "Mengimpor..." : "Impor Excel"}
          </button>
          <button
            type="button"
            onClick={resetForm}
            data-testid="add-campus-button"
            className="inline-flex items-center gap-2 rounded-lg bg-[#27AE60] px-4 py-2.5 text-sm font-bold text-white transition-colors hover:bg-[#0B6B3A]"
          >
            <Plus className="h-4 w-4" />
            Tambah Kampus
          </button>
          <input
            ref={importRef}
            type="file"
            accept=".xlsx"
            className="hidden"
            data-testid="campus-import-input"
            onChange={(event) => importFile(event.target.files[0])}
          />
        </div>
      </div>

      <form
        onSubmit={submit}
        className="grid gap-3 rounded-xl border border-gray-100 bg-white p-4 shadow-sm md:grid-cols-[1fr_12rem_auto]"
        data-testid="campus-form"
      >
        <input
          required
          value={form.name}
          onChange={(event) => setForm((previous) => ({ ...previous, name: event.target.value }))}
          placeholder="Nama kampus"
          data-testid="campus-name-input"
          className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm outline-none focus:border-[#27AE60] focus:ring-2 focus:ring-[#27AE60]/20"
        />
        <input
          value={form.code}
          onChange={(event) => setForm((previous) => ({ ...previous, code: event.target.value }))}
          placeholder="Kode kampus (opsional)"
          data-testid="campus-code-input"
          className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm outline-none focus:border-[#27AE60] focus:ring-2 focus:ring-[#27AE60]/20"
        />
        <div className="flex gap-2">
          <button
            type="submit"
            disabled={saving}
            data-testid="save-campus-button"
            className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg bg-[#0B6B3A] px-4 py-2.5 text-sm font-bold text-white hover:bg-[#07532d] disabled:opacity-60"
          >
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            {editing ? "Simpan" : "Tambah"}
          </button>
          {editing && (
            <button
              type="button"
              onClick={resetForm}
              data-testid="cancel-edit-campus-button"
              className="rounded-lg border border-gray-300 px-3 text-[#6B7280] hover:bg-gray-50"
              aria-label="Batal edit kampus"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      </form>

      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Cari nama atau kode kampus..."
          data-testid="campus-search-input"
          className="w-full rounded-lg border border-gray-200 bg-white py-2.5 pl-9 pr-4 text-sm outline-none focus:border-[#27AE60] focus:ring-2 focus:ring-[#27AE60]/20"
        />
      </div>

      <div className="overflow-x-auto rounded-xl border border-gray-100 bg-white shadow-sm">
        <table className="w-full min-w-[44rem] text-left">
          <thead className="border-b border-gray-100 bg-[#F9FAFB] text-xs text-[#6B7280]">
            <tr>
              <th className="w-16 px-5 py-3 font-semibold">No.</th>
              <th className="px-5 py-3 font-semibold">Nama Kampus</th>
              <th className="px-5 py-3 font-semibold">Kode Kampus</th>
              <th className="px-5 py-3 text-right font-semibold">Aksi</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan="4" className="px-5 py-10 text-center" data-testid="campus-loading-state">
                  <Loader2 className="mx-auto h-5 w-5 animate-spin text-[#27AE60]" />
                </td>
              </tr>
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan="4" className="px-5 py-10 text-center text-sm text-[#6B7280]" data-testid="campus-empty-state">
                  Belum ada kampus yang sesuai.
                </td>
              </tr>
            ) : (
              filtered.map((campus, index) => (
                <tr
                  key={campus.id}
                  className="border-b border-gray-50 last:border-0"
                  data-testid={`campus-row-${campus.id}`}
                >
                  <td
                    className="px-5 py-3.5 text-sm font-semibold text-[#6B7280]"
                    data-testid={`campus-sequence-${campus.id}`}
                  >
                    {index + 1}
                  </td>
                  <td className="px-5 py-3.5 text-sm font-semibold text-[#1F2937]">{campus.name}</td>
                  <td className="px-5 py-3.5 text-sm text-[#6B7280]">{campus.code || "—"}</td>
                  <td className="px-5 py-3.5">
                    <div className="flex justify-end gap-1">
                      <button
                        type="button"
                        title="Edit kampus"
                        onClick={() => {
                          setEditing(campus);
                          setForm({ name: campus.name, code: campus.code || "" });
                        }}
                        data-testid={`edit-campus-${campus.id}`}
                        className="rounded-lg p-2 text-[#0B6B3A] hover:bg-[#E8F6EE]"
                      >
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button
                        type="button"
                        title="Hapus kampus"
                        onClick={() => setDeleting(campus)}
                        data-testid={`delete-campus-${campus.id}`}
                        className="rounded-lg p-2 text-[#DC2626] hover:bg-[#FEE2E2]"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {deleting && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          data-testid="delete-campus-dialog"
        >
          <div className="w-full max-w-sm rounded-xl bg-white p-6 shadow-2xl">
            <Building2 className="h-8 w-8 text-[#DC2626]" />
            <h3 className="mt-3 font-display text-lg font-bold text-[#1F2937]">Hapus kampus?</h3>
            <p className="mt-2 text-sm text-[#6B7280]">
              {deleting.name} akan dihapus dari pilihan kampus mahasiswa.
            </p>
            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setDeleting(null)}
                data-testid="cancel-delete-campus-button"
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-bold text-[#1F2937] hover:bg-gray-50"
              >
                Batal
              </button>
              <button
                type="button"
                onClick={confirmDelete}
                data-testid="confirm-delete-campus-button"
                className="rounded-lg bg-[#DC2626] px-4 py-2 text-sm font-bold text-white hover:bg-[#B91C1C]"
              >
                Hapus
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}