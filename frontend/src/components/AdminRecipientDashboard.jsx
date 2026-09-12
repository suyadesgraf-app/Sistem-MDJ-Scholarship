import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Award, Loader2, MapPinned, RefreshCw, Users } from "lucide-react";
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

export default function AdminRecipientDashboard() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(false);

  const load = useCallback(async () => {
    setError(false);
    try {
      const response = await api.get("/admin/stats");
      setStats(response.data);
    } catch {
      setError(true);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const regionTotal = useMemo(
    () => (stats?.passed_by_region || []).reduce((total, item) => total + item.count, 0),
    [stats],
  );

  if (!stats && !error) {
    return <LoadingState testId="recipient-dashboard-loading" />;
  }

  if (error) {
    return <ErrorState onRetry={load} testId="recipient-dashboard-error" />;
  }

  const passed = stats.verified || 0;
  const tiles = [
    { id: "recipient-total", label: "Total Penerima Manfaat", value: passed, icon: Award },
    {
      id: "recipient-regions",
      label: "Wilayah Penerima Manfaat",
      value: (stats.passed_by_region || []).length,
      icon: MapPinned,
    },
    { id: "recipient-distributed", label: "Data Terpetakan", value: regionTotal, icon: Users },
  ];

  return (
    <div className="space-y-7" data-testid="recipient-dashboard">
      <section className="border-l-4 border-[#27AE60] bg-[#F0FBF5] px-5 py-4">
        <p className="text-xs font-bold uppercase tracking-wide text-[#0B6B3A]">
          Penerima Manfaat MDJ
        </p>
        <h2 className="mt-1 font-display text-2xl font-extrabold text-[#1F2937]">
          Mahasiswa yang dinyatakan lulus seluruh tahap seleksi
        </h2>
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        {tiles.map((tile) => {
          const Icon = tile.icon;
          return (
            <div
              key={tile.id}
              className="border border-gray-100 bg-white p-5 shadow-sm"
              data-testid={`dashboard-${tile.id}`}
            >
              <Icon className="h-5 w-5 text-[#27AE60]" />
              <p className="mt-4 text-xs text-[#6B7280]">{tile.label}</p>
              <p className="mt-1 font-display text-3xl font-extrabold text-[#0B6B3A]">
                {tile.value}
              </p>
            </div>
          );
        })}
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.25fr_0.75fr]">
        <div className="border border-gray-100 bg-white p-6 shadow-sm" data-testid="recipient-region-chart">
          <h3 className="font-display text-lg font-bold text-[#1F2937]">
            Infografis Penerima Manfaat per Wilayah
          </h3>
          <p className="mt-1 text-sm text-[#6B7280]">Berdasarkan kota/kabupaten domisili mahasiswa.</p>
          {(stats.passed_by_region || []).length === 0 ? (
            <div className="flex h-64 items-center justify-center text-center" data-testid="recipient-region-empty">
              <p className="max-w-xs text-sm text-[#6B7280]">
                Belum ada penerima manfaat yang lulus seluruh tahap untuk dipetakan per wilayah.
              </p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart
                data={stats.passed_by_region}
                margin={{ top: 20, right: 8, left: -22, bottom: 4 }}
              >
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
                <Bar dataKey="count" fill="#27AE60" name="Penerima manfaat" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="border border-gray-100 bg-white p-6 shadow-sm" data-testid="recipient-region-list">
          <h3 className="font-display text-lg font-bold text-[#1F2937]">Sebaran Wilayah</h3>
          <div className="mt-4 space-y-3">
            {(stats.passed_by_region || []).length === 0 ? (
              <p className="text-sm text-[#6B7280]">Data wilayah akan tampil setelah ada kelulusan.</p>
            ) : (
              stats.passed_by_region.map((item) => (
                <div
                  key={item.region}
                  className="flex items-center justify-between border-b border-gray-100 pb-3 last:border-0"
                  data-testid={`recipient-region-${item.region}`}
                >
                  <span className="text-sm font-semibold text-[#1F2937]">{item.region}</span>
                  <span className="text-sm font-bold text-[#0B6B3A]">{item.count}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

export function LoadingState({ testId }) {
  return (
    <div className="py-16 text-center" data-testid={testId}>
      <Loader2 className="mx-auto h-6 w-6 animate-spin text-[#27AE60]" />
    </div>
  );
}

export function ErrorState({ onRetry, testId }) {
  return (
    <div className="border border-[#FECACA] bg-[#FEF2F2] p-6 text-center" data-testid={testId}>
      <p className="text-sm font-semibold text-[#991B1B]">Data Dashboard belum dapat dimuat.</p>
      <button
        type="button"
        onClick={onRetry}
        data-testid={`${testId}-retry`}
        className="mt-3 inline-flex items-center gap-2 text-sm font-bold text-[#B91C1C] hover:underline"
      >
        <RefreshCw className="h-4 w-4" />
        Coba lagi
      </button>
    </div>
  );
}