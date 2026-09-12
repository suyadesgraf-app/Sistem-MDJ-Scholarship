import React, { useEffect, useMemo, useState } from "react";
import {
  Award,
  CheckCircle2,
  ClipboardCheck,
  Loader2,
  MapPinned,
  Users,
} from "lucide-react";
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

const STAGES = [
  { id: "submitted", label: "Pendaftaran Terkirim" },
  { id: "verifikasi", label: "Verifikasi Administrasi" },
  { id: "lolos_administrasi", label: "Lolos Administrasi" },
  { id: "wawancara", label: "Wawancara Assessment" },
  { id: "verifikasi_faktual", label: "Verifikasi Faktual" },
  { id: "lolos", label: "Penerima Manfaat" },
];

export default function AdminSelectionDashboard() {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    api.get("/admin/stats")
      .then((response) => setStats(response.data))
      .catch(() => setStats({}));
  }, []);

  const passedRate = useMemo(() => {
    const total = stats?.total_registrations || 0;
    const passed = stats?.verified || 0;
    return total ? Math.round((passed / total) * 100) : 0;
  }, [stats]);

  if (!stats) {
    return (
      <div className="py-16 text-center" data-testid="admin-dashboard-loading">
        <Loader2 className="mx-auto h-6 w-6 animate-spin text-[#27AE60]" />
      </div>
    );
  }

  const tiles = [
    {
      id: "total-applicants",
      label: "Total Pendaftar",
      value: stats.total_registrations || 0,
      icon: Users,
      color: "#27AE60",
    },
    {
      id: "in-progress",
      label: "Dalam Proses Seleksi",
      value: stats.pending || 0,
      icon: ClipboardCheck,
      color: "#D99A00",
    },
    {
      id: "passed-students",
      label: "Mahasiswa Lulus",
      value: stats.verified || 0,
      icon: Award,
      color: "#0B6B3A",
    },
    {
      id: "passed-regions",
      label: "Wilayah Mahasiswa Lulus",
      value: (stats.passed_by_region || []).length,
      icon: MapPinned,
      color: "#2563EB",
    },
  ];

  return (
    <div className="space-y-7" data-testid="admin-selection-dashboard">
      <section>
        <p className="text-sm text-[#6B7280]">
          Pantau tahapan penerimaan Calon Penerima Manfaat Program MDJ hingga kelulusan.
        </p>
        <div className="mt-4 grid grid-cols-2 gap-4 xl:grid-cols-4">
          {tiles.map((tile) => {
            const Icon = tile.icon;
            return (
              <div
                key={tile.id}
                className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm"
                data-testid={`dashboard-${tile.id}`}
              >
                <div
                  className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg"
                  style={{ backgroundColor: `${tile.color}1a` }}
                >
                  <Icon className="h-5 w-5" style={{ color: tile.color }} />
                </div>
                <p className="text-xs text-[#6B7280]">{tile.label}</p>
                <p className="mt-0.5 font-display text-2xl font-extrabold text-[#1F2937]">
                  {tile.value}
                </p>
              </div>
            );
          })}
        </div>
      </section>

      <section className="border-y border-gray-100 bg-white py-6" data-testid="selection-stages">
        <div className="mb-5 flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
          <div>
            <h3 className="font-display text-lg font-bold text-[#1F2937]">
              Tahapan Seleksi Calon Penerima Manfaat
            </h3>
            <p className="mt-1 text-sm text-[#6B7280]">Jumlah mahasiswa pada setiap proses seleksi.</p>
          </div>
          <span className="inline-flex items-center gap-1.5 text-xs font-bold text-[#0B6B3A]">
            <CheckCircle2 className="h-4 w-4" />
            Kelulusan: {passedRate}%
          </span>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          {STAGES.map((stage, index) => {
            const count = stats.by_status?.[stage.id] || 0;
            const isFinal = stage.id === "lolos";
            return (
              <div
                key={stage.id}
                className={[
                  "relative min-h-28 border-l-2 px-4 py-3",
                  isFinal ? "border-[#27AE60] bg-[#F0FBF5]" : "border-gray-200 bg-[#FAFAFA]",
                ].join(" ")}
                data-testid={`selection-stage-${stage.id}`}
              >
                <span className="text-xs font-bold text-[#6B7280]">Tahap {index + 1}</span>
                <p className="mt-2 text-sm font-bold leading-snug text-[#1F2937]">{stage.label}</p>
                <p className="mt-2 font-display text-2xl font-extrabold text-[#0B6B3A]">{count}</p>
              </div>
            );
          })}
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
        <div className="border border-gray-100 bg-white p-6 shadow-sm" data-testid="passed-summary">
          <p className="text-sm font-semibold text-[#6B7280]">Kelulusan Keseluruhan</p>
          <p className="mt-3 font-display text-5xl font-black text-[#0B6B3A]" data-testid="passed-rate">
            {passedRate}%
          </p>
          <p className="mt-2 text-sm text-[#6B7280]">
            {stats.verified || 0} mahasiswa lulus dari {stats.total_registrations || 0} pendaftar.
          </p>
          <div className="mt-5 h-3 overflow-hidden rounded-full bg-[#E8F6EE]">
            <div
              className="h-full rounded-full bg-[#27AE60] transition-[width] duration-500"
              style={{ width: `${passedRate}%` }}
              data-testid="passed-rate-bar"
            />
          </div>
        </div>

        <div className="border border-gray-100 bg-white p-6 shadow-sm" data-testid="passed-region-chart">
          <h3 className="font-display text-lg font-bold text-[#1F2937]">
            Infografis Mahasiswa Lulus per Wilayah
          </h3>
          <p className="mt-1 text-sm text-[#6B7280]">Berdasarkan kota/kabupaten domisili.</p>
          {(stats.passed_by_region || []).length === 0 ? (
            <div className="flex h-60 items-center justify-center text-center" data-testid="passed-region-empty">
              <p className="max-w-xs text-sm text-[#6B7280]">
                Belum ada mahasiswa yang lulus untuk ditampilkan per wilayah.
              </p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={stats.passed_by_region} margin={{ top: 18, right: 4, left: -20, bottom: 4 }}>
                <CartesianGrid stroke="#F1F5F9" strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="region"
                  tick={{ fill: "#6B7280", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  allowDecimals={false}
                  tick={{ fill: "#6B7280", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  cursor={{ fill: "#F0FBF5" }}
                  contentStyle={{ border: "1px solid #E5E7EB", borderRadius: 8 }}
                />
                <Bar dataKey="count" fill="#27AE60" name="Mahasiswa lulus" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </section>
    </div>
  );
}