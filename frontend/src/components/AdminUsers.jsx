import React, { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Loader2, Power, ShieldCheck, Trash2, UserPlus, X } from "lucide-react";
import api, { formatApiError } from "@/lib/api";

const REGIONS = [
  "Jakarta Pusat",
  "Jakarta Utara",
  "Jakarta Barat",
  "Jakarta Selatan",
  "Jakarta Timur",
  "Kepulauan Seribu",
];

const INPUT_CLASS = (
  "w-full rounded-xl border border-gray-300 px-4 py-2.5 text-sm "
  + "focus:outline-none focus:ring-2 focus:ring-[#27AE60]"
);

function emptyForm(canManageProvincial) {
  return {
    name: "",
    email: "",
    password: "",
    role: canManageProvincial ? "admin" : "admin_wilayah",
    region: "",
  };
}

function roleLabel(role) {
  if (role === "super_admin") return "Super Admin";
  if (role === "admin_wilayah") return "Admin Wilayah";
  return "Admin/PIC Provinsi";
}

export default function AdminUsers({ canManageProvincial = false }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState(() => emptyForm(canManageProvincial));
  const [saving, setSaving] = useState(false);

  const roleOptions = useMemo(() => (
    canManageProvincial
      ? [
        ["admin", "Admin/PIC Provinsi"],
        ["admin_wilayah", "Admin Wilayah"],
        ["super_admin", "Super Admin"],
      ]
      : [["admin_wilayah", "Admin Wilayah"]]
  ), [canManageProvincial]);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/admin/users", { params: { role: "all" } });
      setUsers(data);
    } catch (error) {
      toast.error(formatApiError(error.response?.data?.detail));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const create = async (event) => {
    event.preventDefault();
    if (form.password.length < 8) {
      toast.error("Kata sandi minimal 8 karakter.");
      return;
    }
    if (form.role === "admin_wilayah" && !form.region) {
      toast.error("Pilih wilayah kerja untuk Admin Wilayah.");
      return;
    }
    setSaving(true);
    try {
      await api.post("/admin/users", form);
      toast.success("Akun admin berhasil dibuat.");
      setShowCreate(false);
      setForm(emptyForm(canManageProvincial));
      await load();
    } catch (error) {
      toast.error(formatApiError(error.response?.data?.detail));
    } finally {
      setSaving(false);
    }
  };

  const toggle = async (account) => {
    try {
      await api.put(`/admin/users/${account.user_id}`, { is_active: !account.is_active });
      toast.success("Status akun diperbarui.");
      await load();
    } catch (error) {
      toast.error(formatApiError(error.response?.data?.detail));
    }
  };

  const remove = async (account) => {
    if (!window.confirm(`Hapus akun ${account.name}?`)) return;
    try {
      await api.delete(`/admin/users/${account.user_id}`);
      toast.success("Akun dihapus.");
      await load();
    } catch (error) {
      toast.error(formatApiError(error.response?.data?.detail));
    }
  };

  return (
    <div className="space-y-4" data-testid="admin-users-manager">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <p className="text-sm text-[#6B7280]" data-testid="admin-user-total">
          {users.length} akun pengelola
        </p>
        <button
          type="button"
          onClick={() => setShowCreate(true)}
          data-testid="create-admin-btn"
          className="flex items-center gap-2 rounded-xl bg-[#27AE60] px-4 py-2.5 text-sm font-bold text-white transition-colors hover:bg-[#0B6B3A]"
        >
          <UserPlus className="h-4 w-4" />
          Buat Akun Admin
        </button>
      </div>

      <div className="overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-sm">
        <div className="overflow-x-auto mdj-scrollbar">
          <table className="w-full text-sm" data-testid="admins-table">
            <thead>
              <tr className="border-b border-gray-100 bg-[#F9FAFB] text-left text-xs text-[#6B7280]">
                <th className="px-4 py-3 font-semibold">Nama</th>
                <th className="px-4 py-3 font-semibold">Email</th>
                <th className="px-4 py-3 font-semibold">Peran</th>
                <th className="px-4 py-3 font-semibold">Wilayah</th>
                <th className="px-4 py-3 font-semibold">Status</th>
                <th className="px-4 py-3 text-right font-semibold">Aksi</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center text-gray-400">
                    <Loader2 className="inline h-5 w-5 animate-spin" />
                  </td>
                </tr>
              ) : users.map((account) => (
                <tr key={account.user_id} className="border-b border-gray-50 hover:bg-[#F9FAFB]">
                  <td className="px-4 py-3 font-semibold text-[#1F2937]">{account.name}</td>
                  <td className="px-4 py-3 text-[#6B7280]">{account.email}</td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center gap-1 rounded-full bg-[#E8F6EE] px-2.5 py-1 text-xs font-bold text-[#0B6B3A]">
                      <ShieldCheck className="h-3 w-3" />
                      {roleLabel(account.role)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-[#6B7280]">{account.region || "Provinsi DKI"}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-bold ${account.is_active ? "bg-[#E8F6EE] text-[#0B6B3A]" : "bg-[#FEE2E2] text-[#DC2626]"}`}>
                      {account.is_active ? "Aktif" : "Nonaktif"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    {account.role !== "super_admin" && (
                      <div className="inline-flex gap-1.5">
                        <button
                          type="button"
                          onClick={() => toggle(account)}
                          data-testid={`toggle-user-${account.user_id}`}
                          className="rounded-lg p-2 text-[#6B7280] hover:bg-gray-100"
                          aria-label="Aktif atau nonaktifkan akun"
                        >
                          <Power className="h-4 w-4" />
                        </button>
                        <button
                          type="button"
                          onClick={() => remove(account)}
                          data-testid={`delete-user-${account.user_id}`}
                          className="rounded-lg p-2 text-[#DC2626] hover:bg-[#FEE2E2]"
                          aria-label="Hapus akun"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {showCreate && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-[#1F2937]/50 p-4"
          onClick={() => setShowCreate(false)}
          data-testid="create-admin-overlay"
        >
          <div
            className="w-full max-w-md rounded-2xl bg-white p-6"
            onClick={(event) => event.stopPropagation()}
            data-testid="create-admin-modal"
          >
            <div className="mb-5 flex items-center justify-between">
              <h3 className="font-display text-lg font-bold text-[#1F2937]">
                Buat Akun Admin
              </h3>
              <button
                type="button"
                onClick={() => setShowCreate(false)}
                data-testid="close-create-admin-modal"
                className="rounded-lg p-2 hover:bg-gray-100"
                aria-label="Tutup formulir akun admin"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <form onSubmit={create} className="space-y-4">
              <Field label="Nama Lengkap">
                <input
                  value={form.name}
                  onChange={(event) => setForm((current) => ({
                    ...current,
                    name: event.target.value,
                  }))}
                  required
                  data-testid="admin-name-input"
                  className={INPUT_CLASS}
                />
              </Field>
              <Field label="Email">
                <input
                  type="email"
                  value={form.email}
                  onChange={(event) => setForm((current) => ({
                    ...current,
                    email: event.target.value,
                  }))}
                  required
                  data-testid="admin-email-input"
                  className={INPUT_CLASS}
                />
              </Field>
              <Field label="Kata Sandi">
                <input
                  type="text"
                  value={form.password}
                  onChange={(event) => setForm((current) => ({
                    ...current,
                    password: event.target.value,
                  }))}
                  required
                  placeholder="Min. 8 karakter"
                  data-testid="admin-password-input"
                  className={INPUT_CLASS}
                />
              </Field>
              <Field label="Peran">
                <select
                  value={form.role}
                  onChange={(event) => setForm((current) => ({
                    ...current,
                    role: event.target.value,
                    region: event.target.value === "admin_wilayah" ? current.region : "",
                  }))}
                  data-testid="admin-role-select"
                  className={`${INPUT_CLASS} bg-white`}
                >
                  {roleOptions.map(([value, label]) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </Field>
              {form.role === "admin_wilayah" && (
                <Field label="Wilayah Kerja">
                  <select
                    value={form.region}
                    onChange={(event) => setForm((current) => ({
                      ...current,
                      region: event.target.value,
                    }))}
                    required
                    data-testid="admin-region-select"
                    className={`${INPUT_CLASS} bg-white`}
                  >
                    <option value="">Pilih wilayah</option>
                    {REGIONS.map((region) => <option key={region} value={region}>{region}</option>)}
                  </select>
                </Field>
              )}
              <button
                type="submit"
                disabled={saving}
                data-testid="submit-admin-btn"
                className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#27AE60] py-2.5 font-bold text-white transition-colors hover:bg-[#0B6B3A] disabled:opacity-60"
              >
                {saving && <Loader2 className="h-4 w-4 animate-spin" />}
                Buat Akun
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

function Field({ label, children }) {
  return (
    <div>
      <label className="mb-1.5 block text-sm font-semibold text-[#1F2937]">{label}</label>
      {children}
    </div>
  );
}
