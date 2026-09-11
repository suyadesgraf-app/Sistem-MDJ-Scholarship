import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { STATUS_META } from "@/components/DashboardShell";
import { Users, UserCheck, Clock, Shield, Loader2 } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

export default function StatsOverview({ showAdmins }) {
  const [stats, setStats] = useState(null);
  useEffect(() => { api.get("/admin/stats").then((r) => setStats(r.data)).catch(() => setStats({})); }, []);
  if (!stats) return <div className="py-12 text-center"><Loader2 className="w-6 h-6 animate-spin inline text-[#27AE60]" /></div>;

  const tiles = [
    { icon: Users, label: "Total Pendaftar", value: stats.total_registrations || 0, color: "#27AE60" },
    { icon: UserCheck, label: "Penerima (Lolos)", value: stats.verified || 0, color: "#0B6B3A" },
    { icon: Clock, label: "Menunggu Verifikasi", value: stats.pending || 0, color: "#F2C94C" },
    { icon: Shield, label: showAdmins ? "Total Admin" : "Total Mahasiswa", value: showAdmins ? stats.total_admins : stats.total_students, color: "#6B7280" },
  ];
  const trend = (stats.trend || []).map((t) => ({ month: t.month, count: t.count }));
  const byStatus = Object.entries(stats.by_status || {}).map(([k, v]) => ({ label: STATUS_META[k]?.label || k, value: v }));

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {tiles.map((t, i) => (
          <div key={i} className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm" data-testid={`stat-tile-${i}`}>
            <div className="w-10 h-10 rounded-xl flex items-center justify-center mb-3" style={{ backgroundColor: `${t.color}1a` }}><t.icon className="w-5 h-5" style={{ color: t.color }} /></div>
            <p className="text-xs text-[#6B7280]">{t.label}</p>
            <p className="font-display font-extrabold text-2xl text-[#1F2937] mt-0.5">{t.value}</p>
          </div>
        ))}
      </div>
      <div className="bg-white border border-gray-100 rounded-2xl p-6 shadow-sm">
        <h3 className="font-display font-bold text-[#1F2937] mb-4">Tren Pendaftaran per Bulan</h3>
        {trend.length === 0 ? <p className="text-sm text-gray-400 py-8 text-center">Belum ada data pendaftaran.</p> : (
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={trend}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
              <XAxis dataKey="month" tick={{ fontSize: 12, fill: "#6B7280" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 12, fill: "#6B7280" }} axisLine={false} tickLine={false} allowDecimals={false} />
              <Tooltip cursor={{ fill: "#E8F6EE" }} contentStyle={{ borderRadius: 12, border: "1px solid #eee" }} />
              <Bar dataKey="count" fill="#27AE60" radius={[6, 6, 0, 0]} name="Pendaftar" />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
      {byStatus.length > 0 && (
        <div className="bg-white border border-gray-100 rounded-2xl p-6 shadow-sm">
          <h3 className="font-display font-bold text-[#1F2937] mb-4">Distribusi Status Seleksi</h3>
          <div className="flex flex-wrap gap-3">
            {byStatus.map((s, i) => (
              <div key={i} className="px-4 py-3 rounded-xl bg-[#F9FAFB] border border-gray-100"><p className="font-display font-extrabold text-xl text-[#27AE60]">{s.value}</p><p className="text-xs text-[#6B7280]">{s.label}</p></div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
