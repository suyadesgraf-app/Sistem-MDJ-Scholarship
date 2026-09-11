import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { GraduationCap, Menu, X, LogOut, ChevronDown } from "lucide-react";

const STATUS_META = {
  draft: { label: "Draft", cls: "bg-gray-100 text-gray-600" },
  submitted: { label: "Terkirim", cls: "bg-blue-50 text-blue-700" },
  verifikasi: { label: "Verifikasi Administrasi", cls: "bg-[#FEF9E7] text-[#7a5c00]" },
  lolos_administrasi: { label: "Lolos Administrasi", cls: "bg-[#E8F6EE] text-[#0B6B3A]" },
  wawancara: { label: "Wawancara", cls: "bg-purple-50 text-purple-700" },
  verifikasi_faktual: { label: "Verifikasi Faktual", cls: "bg-orange-50 text-orange-700" },
  lolos: { label: "Lolos / Penerima", cls: "bg-[#E8F6EE] text-[#0B6B3A]" },
  ditolak: { label: "Tidak Lolos", cls: "bg-[#FEE2E2] text-[#DC2626]" },
};

export function StatusBadge({ status }) {
  const m = STATUS_META[status] || STATUS_META.draft;
  return <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold ${m.cls}`} data-testid={`status-badge-${status}`}>{m.label}</span>;
}
export { STATUS_META };

export default function DashboardShell({ menu, active, onSelect, title, subtitle, actions, children, brandLabel }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  const doLogout = async () => { await logout(); navigate("/", { replace: true }); };

  const Sidebar = () => (
    <div className="flex flex-col h-full">
      <div className="h-16 flex items-center gap-2.5 px-5 border-b border-gray-100">
        <div className="w-9 h-9 rounded-xl bg-[#27AE60] flex items-center justify-center"><GraduationCap className="w-5 h-5 text-white" /></div>
        <div className="leading-tight">
          <p className="font-display font-extrabold text-sm text-[#1F2937]">MDJ Scholarship</p>
          <p className="text-[10px] font-semibold text-[#6B7280]">{brandLabel}</p>
        </div>
      </div>
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto mdj-scrollbar">
        {menu.map((m) => {
          const isActive = active === m.id;
          return (
            <button key={m.id} onClick={() => { onSelect(m.id); setOpen(false); }} data-testid={`menu-${m.id}`}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-semibold transition-colors ${isActive ? "bg-[#E8F6EE] text-[#0B6B3A] border-l-4 border-[#27AE60]" : "text-[#6B7280] hover:bg-gray-50 hover:text-[#1F2937] border-l-4 border-transparent"}`}>
              <m.icon className="w-5 h-5 shrink-0" /> {m.label}
            </button>
          );
        })}
      </nav>
      <div className="p-3 border-t border-gray-100">
        <button onClick={doLogout} data-testid="logout-btn" className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-semibold text-[#DC2626] hover:bg-[#FEE2E2] transition-colors"><LogOut className="w-5 h-5" /> Keluar</button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#F9FAFB] flex">
      <aside className="hidden lg:flex w-64 bg-white border-r border-gray-100 fixed inset-y-0 left-0 z-30"><Sidebar /></aside>
      {open && <div className="lg:hidden fixed inset-0 z-40 bg-black/40" onClick={() => setOpen(false)} />}
      <aside className={`lg:hidden fixed inset-y-0 left-0 z-50 w-64 bg-white transform transition-transform ${open ? "translate-x-0" : "-translate-x-full"}`}><Sidebar /></aside>

      <div className="flex-1 lg:ml-64 min-w-0">
        <header className="h-16 bg-white/90 backdrop-blur-xl border-b border-gray-100 sticky top-0 z-20 flex items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-3 min-w-0">
            <button className="lg:hidden p-2 -ml-2" onClick={() => setOpen(true)} data-testid="sidebar-toggle" aria-label="Buka menu"><Menu className="w-6 h-6 text-[#1F2937]" /></button>
            <div className="min-w-0">
              <h1 className="font-display font-bold text-lg text-[#1F2937] truncate">{title}</h1>
              {subtitle && <p className="text-xs text-[#6B7280] truncate">{subtitle}</p>}
            </div>
          </div>
          <div className="flex items-center gap-3">
            {actions}
            <div className="flex items-center gap-2 pl-3 border-l border-gray-200">
              <div className="w-9 h-9 rounded-full bg-[#E8F6EE] flex items-center justify-center text-[#0B6B3A] font-bold text-sm">{(user?.name || "?").charAt(0).toUpperCase()}</div>
              <div className="hidden sm:block leading-tight"><p className="text-sm font-semibold text-[#1F2937] max-w-[140px] truncate">{user?.name}</p><p className="text-[11px] text-[#6B7280] capitalize">{(user?.role || "").replace("_", " ")}</p></div>
            </div>
          </div>
        </header>
        <main className="p-4 sm:p-6 lg:p-8 max-w-6xl mx-auto">{children}</main>
      </div>
    </div>
  );
}
