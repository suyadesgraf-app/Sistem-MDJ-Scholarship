import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { UserPlus, Loader2, Trash2, Power, X, ShieldCheck, User } from "lucide-react";

export default function AdminUsers() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "admin" });
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    try { const { data } = await api.get("/admin/users", { params: { role: "all" } }); setUsers(data); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const admins = users.filter((u) => u.role === "admin" || u.role === "super_admin");

  const create = async (e) => {
    e.preventDefault();
    if (form.password.length < 8) return toast.error("Kata sandi minimal 8 karakter.");
    setSaving(true);
    try {
      await api.post("/admin/users", form);
      toast.success("Akun admin berhasil dibuat.");
      setShowCreate(false); setForm({ name: "", email: "", password: "", role: "admin" });
      load();
    } catch (err) { toast.error(formatApiError(err.response?.data?.detail)); }
    finally { setSaving(false); }
  };

  const toggle = async (u) => {
    try { await api.put(`/admin/users/${u.user_id}`, { is_active: !u.is_active }); toast.success("Status akun diperbarui."); load(); }
    catch (err) { toast.error(formatApiError(err.response?.data?.detail)); }
  };
  const remove = async (u) => {
    if (!window.confirm(`Hapus akun ${u.name}?`)) return;
    try { await api.delete(`/admin/users/${u.user_id}`); toast.success("Akun dihapus."); load(); }
    catch (err) { toast.error(formatApiError(err.response?.data?.detail)); }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-[#6B7280]">{admins.length} akun pengelola</p>
        <button onClick={() => setShowCreate(true)} data-testid="create-admin-btn" className="px-4 py-2.5 bg-[#27AE60] hover:bg-[#0B6B3A] text-white text-sm font-bold rounded-xl flex items-center gap-2 transition-colors"><UserPlus className="w-4 h-4" /> Buat Akun Admin</button>
      </div>
      <div className="bg-white border border-gray-100 rounded-2xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto mdj-scrollbar">
          <table className="w-full text-sm" data-testid="admins-table">
            <thead><tr className="text-left text-xs text-[#6B7280] border-b border-gray-100 bg-[#F9FAFB]">
              <th className="px-4 py-3 font-semibold">Nama</th><th className="px-4 py-3 font-semibold">Email</th>
              <th className="px-4 py-3 font-semibold">Peran</th><th className="px-4 py-3 font-semibold">Status</th>
              <th className="px-4 py-3 font-semibold text-right">Aksi</th>
            </tr></thead>
            <tbody>
              {loading ? <tr><td colSpan={5} className="px-4 py-12 text-center text-gray-400"><Loader2 className="w-5 h-5 animate-spin inline" /></td></tr> :
                admins.map((u) => (
                  <tr key={u.user_id} className="border-b border-gray-50 hover:bg-[#F9FAFB]">
                    <td className="px-4 py-3 font-semibold text-[#1F2937]">{u.name}</td>
                    <td className="px-4 py-3 text-[#6B7280]">{u.email}</td>
                    <td className="px-4 py-3"><span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold ${u.role === "super_admin" ? "bg-[#FEF9E7] text-[#7a5c00]" : "bg-[#E8F6EE] text-[#0B6B3A]"}`}>{u.role === "super_admin" ? <ShieldCheck className="w-3 h-3" /> : <User className="w-3 h-3" />}{u.role === "super_admin" ? "Super Admin" : "Admin"}</span></td>
                    <td className="px-4 py-3"><span className={`inline-flex px-2.5 py-1 rounded-full text-xs font-bold ${u.is_active ? "bg-[#E8F6EE] text-[#0B6B3A]" : "bg-[#FEE2E2] text-[#DC2626]"}`}>{u.is_active ? "Aktif" : "Nonaktif"}</span></td>
                    <td className="px-4 py-3 text-right">
                      {u.role !== "super_admin" && (
                        <div className="inline-flex gap-1.5">
                          <button onClick={() => toggle(u)} data-testid={`toggle-user-${u.user_id}`} className="p-2 text-[#6B7280] hover:bg-gray-100 rounded-lg" aria-label="Aktif/Nonaktif"><Power className="w-4 h-4" /></button>
                          <button onClick={() => remove(u)} data-testid={`delete-user-${u.user_id}`} className="p-2 text-[#DC2626] hover:bg-[#FEE2E2] rounded-lg" aria-label="Hapus"><Trash2 className="w-4 h-4" /></button>
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
        <div className="fixed inset-0 z-50 bg-[#1F2937]/50 flex items-center justify-center p-4" onClick={() => setShowCreate(false)}>
          <div className="bg-white rounded-2xl w-full max-w-md p-6" onClick={(e) => e.stopPropagation()} data-testid="create-admin-modal">
            <div className="flex items-center justify-between mb-5"><h3 className="font-display font-bold text-lg text-[#1F2937]">Buat Akun Admin</h3><button onClick={() => setShowCreate(false)} className="p-2 hover:bg-gray-100 rounded-lg"><X className="w-5 h-5" /></button></div>
            <form onSubmit={create} className="space-y-4">
              <F label="Nama Lengkap"><input value={form.name} onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))} required data-testid="admin-name-input" className={ic} /></F>
              <F label="Email"><input type="email" value={form.email} onChange={(e) => setForm((p) => ({ ...p, email: e.target.value }))} required data-testid="admin-email-input" className={ic} /></F>
              <F label="Kata Sandi"><input type="text" value={form.password} onChange={(e) => setForm((p) => ({ ...p, password: e.target.value }))} required data-testid="admin-password-input" placeholder="Min. 8 karakter" className={ic} /></F>
              <F label="Peran"><select value={form.role} onChange={(e) => setForm((p) => ({ ...p, role: e.target.value }))} data-testid="admin-role-select" className={ic + " bg-white"}><option value="admin">Admin Pendaftaran</option><option value="super_admin">Super Admin</option></select></F>
              <button type="submit" disabled={saving} data-testid="submit-admin-btn" className="w-full py-2.5 bg-[#27AE60] hover:bg-[#0B6B3A] text-white font-bold rounded-xl flex items-center justify-center gap-2 transition-colors">{saving ? <Loader2 className="w-4 h-4 animate-spin" /> : null} Buat Akun</button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
const ic = "w-full px-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#27AE60]";
const F = ({ label, children }) => <div><label className="block text-sm font-semibold text-[#1F2937] mb-1.5">{label}</label>{children}</div>;
