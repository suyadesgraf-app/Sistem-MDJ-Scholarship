import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Bell, ClipboardList, Loader2, MapPinned, RefreshCw, Send, Users } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

const PROCESS_STAGES = [
  { id: "submitted", label: "Pendaftaran Terkirim" },
  { id: "verifikasi", label: "Verifikasi Administrasi" },
  { id: "lolos_administrasi", label: "Lolos Administrasi" },
  { id: "wawancara", label: "Wawancara Assessment" },
  { id: "verifikasi_faktual", label: "Verifikasi Faktual" },
  { id: "lolos", label: "Pengumuman Penerima" },
];

export default function AdminRegistrationSummary() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [region, setRegion] = useState("all");
  const [error, setError] = useState(false);
  const lockedRegion = user?.role === "admin_wilayah" ? user.region : "";

  const load = useCallback(async (selectedRegion) => {
    setError(false);
    try {
      const response = await api.get("/admin/stats", {
        params: selectedRegion === "all" ? {} : { region: selectedRegion },
      });
      setStats(response.data);
    } catch {
      setError(true);
    }
  }, []);

  useEffect(() => {
    load(lockedRegion || region);
  }, [load, lockedRegion, region]);

  const stageData = useMemo(() => (
    PROCESS_STAGES.map((stage) => ({
      ...stage,
      count: stats?.by_status?.[stage.id] || 0,
    }))
  ), [stats]);

  if (!stats && !error) {
    return <div className="py-16 text-center" data-testid="admin-summary-loading"><Loader2 className="mx-auto h-6 w-6 animate-spin text-[#27AE60]" /></div>;
  }

  if (error) {
    return (
      <div className="border border-[#FECACA] bg-[#FEF2F2] p-6 text-center" data-testid="admin-summary-error">
        <p className="text-sm font-semibold text-[#991B1B]">Data Ringkasan belum dapat dimuat.</p>
        <button type="button" onClick={() => load(region)} data-testid="admin-summary-error-retry" className="mt-3 inline-flex items-center gap-2 text-sm font-bold text-[#B91C1C] hover:underline">
          <RefreshCw className="h-4 w-4" /> Coba lagi
        </button>
      </div>
    );
  }

  const tiles = [
    { id: "total-applicants", label: "Peserta Mendaftar", value: stats.total_registrations || 0, icon: Users },
    { id: "submitted", label: "Pendaftaran Terkirim", value: stats.by_status?.submitted || 0, icon: Send },
    { id: "in-process", label: "Dalam Proses Seleksi", value: stats.pending || 0, icon: ClipboardList },
    { id: "announcements", label: "Pengumuman Aktif", value: stats.announcement_count || 0, icon: Bell },
  ];

  return (
    <div className="space-y-7" data-testid="admin-registration-summary">
      <section className="flex flex-col justify-between gap-4 border-l-4 border-[#0B6B3A] bg-[#F0FBF5] px-5 py-4 sm:flex-row sm:items-center">
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-[#0B6B3A]">Ringkasan Pendaftaran</p>
          <h2 className="mt-1 font-display text-2xl font-extrabold text-[#1F2937]">Proses pendaftaran hingga pengumuman</h2>
        </div>
        {lockedRegion ? (
          <span
            className="inline-flex items-center gap-2 rounded-lg border border-[#B7E4C7] bg-white px-3 py-2 text-sm font-bold text-[#0B6B3A]"
            data-testid="regional-admin-summary-scope"
          >
            <MapPinned className="h-4 w-4" />
            Wilayah kerja: {lockedRegion}
          </span>
        ) : (
          <label className="flex items-center gap-2 text-sm font-semibold text-[#1F2937]">
            <MapPinned className="h-4 w-4 text-[#0B6B3A]" />
            <span className="sr-only">Filter wilayah</span>
            <select
              value={region}
              onChange={(event) => setRegion(event.target.value)}
              data-testid="summary-region-filter"
              className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm outline-none focus:border-[#27AE60]"
            >
              <option value="all">Keseluruhan Wilayah</option>
              {(stats.available_regions || [])
                .filter((item) => item !== "Belum diisi")
                .map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>
        )}
      </section>

      <section className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        {tiles.map((tile) => {
          const Icon = tile.icon;
          return (
            <div key={tile.id} className="border border-gray-100 bg-white p-5 shadow-sm" data-testid={`summary-${tile.id}`}>
              <Icon className="h-5 w-5 text-[#27AE60]" />
              <p className="mt-4 text-xs text-[#6B7280]">{tile.label}</p>
              <p className="mt-1 font-display text-3xl font-extrabold text-[#1F2937]">{tile.value}</p>
            </div>
          );
        })}
      </section>

      <section className="border-y border-gray-100 bg-white py-6" data-testid="summary-selection-stages">
        <h3 className="font-display text-lg font-bold text-[#1F2937]">Tahapan Seleksi</h3>
        <p className="mt-1 text-sm text-[#6B7280]">Jumlah peserta pada setiap proses setelah pendaftaran.</p>
        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          {stageData.map((stage, index) => (
            <div key={stage.id} className="border-l-2 border-gray-200 bg-[#FAFAFA] px-4 py-3" data-testid={`summary-stage-${stage.id}`}>
              <p className="text-xs font-bold text-[#6B7280]">Tahap {index + 1}</p>
              <p className="mt-2 text-sm font-bold leading-snug text-[#1F2937]">{stage.label}</p>
              <p className="mt-2 font-display text-2xl font-extrabold text-[#0B6B3A]">{stage.count}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="border border-gray-100 bg-white p-6 shadow-sm" data-testid="summary-process-chart">
        <h3 className="font-display text-lg font-bold text-[#1F2937]">Infografis Proses Pendaftaran & Seleksi</h3>
        <p className="mt-1 text-sm text-[#6B7280]">Perbandingan peserta pada setiap tahapan yang dipilih.</p>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={stageData} margin={{ top: 20, right: 8, left: -22, bottom: 4 }}>
            <CartesianGrid stroke="#F1F5F9" strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="label" tick={{ fill: "#6B7280", fontSize: 10 }} axisLine={false} tickLine={false} />
            <YAxis allowDecimals={false} tick={{ fill: "#6B7280", fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip cursor={{ fill: "#F0FBF5" }} contentStyle={{ border: "1px solid #E5E7EB", borderRadius: 8 }} />
            <Bar dataKey="count" fill="#0B6B3A" name="Peserta" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </section>
    </div>
  );
}