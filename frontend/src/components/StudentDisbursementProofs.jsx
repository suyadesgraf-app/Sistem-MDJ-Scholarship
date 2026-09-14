import React, { useCallback, useEffect, useState } from "react";
import { Eye, FileCheck2, Loader2 } from "lucide-react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";

const stageLabel = (stage) => `Tahap ${stage === 1 ? "I" : "II"}`;

export default function StudentDisbursementProofs() {
  const [proofs, setProofs] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get("/student/disbursement-proofs");
      setProofs(response.data || []);
    } catch (error) {
      toast.error(formatApiError(error.response?.data?.detail));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const preview = async (proof) => {
    try {
      const response = await api.get(`/student/disbursement-proofs/${proof.source_id}`, {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(response.data);
      window.open(url, "_blank", "noopener,noreferrer");
      window.setTimeout(() => window.URL.revokeObjectURL(url), 60000);
    } catch (error) {
      toast.error(formatApiError(error.response?.data?.detail));
    }
  };

  return (
    <div className="space-y-5" data-testid="student-disbursement-proofs">
      <section className="border-l-4 border-[#0B6B3A] bg-[#F0FBF5] px-5 py-4">
        <p className="text-xs font-bold uppercase tracking-wide text-[#0B6B3A]">Pencairan Beasiswa</p>
        <h2 className="mt-1 font-display text-2xl font-extrabold text-[#1F2937]">
          Bukti Transfer Saya
        </h2>
        <p className="mt-2 text-sm text-[#6B7280]">
          Bukti transfer yang diterbitkan untuk kampus dan wilayah Anda akan tersedia di sini.
        </p>
      </section>

      {loading ? (
        <div className="py-12 text-center" data-testid="student-proof-loading-state">
          <Loader2 className="mx-auto h-5 w-5 animate-spin text-[#27AE60]" />
        </div>
      ) : proofs.length === 0 ? (
        <div className="border border-gray-100 bg-white p-8 text-center text-sm text-[#6B7280]" data-testid="student-proof-empty-state">
          Belum ada bukti transfer yang diterbitkan untuk Anda.
        </div>
      ) : (
        <div className="space-y-3">
          {proofs.map((proof, index) => (
            <article
              key={proof.source_id}
              className="flex flex-col justify-between gap-4 border border-gray-100 bg-white p-5 shadow-sm sm:flex-row sm:items-center"
              data-testid={`student-proof-${proof.source_id}`}
            >
              <div className="flex gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[#E8F6EE] text-[#0B6B3A]">
                  <FileCheck2 className="h-5 w-5" />
                </div>
                <div>
                  <p className="font-bold text-[#1F2937]">Bukti TF {index + 1}</p>
                  <p className="mt-1 text-sm text-[#6B7280]">{proof.filename}</p>
                  <p className="mt-1 text-xs text-[#6B7280]">
                    {proof.campuses.map((item) => (
                      `${item.campus} · ${item.region} · ${stageLabel(item.stage)}`
                    )).join(" | ")}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => preview(proof)}
                data-testid={`preview-student-proof-${proof.source_id}`}
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-[#E8F6EE] px-4 py-2.5 text-sm font-bold text-[#0B6B3A] hover:bg-[#D3EFDF]"
              >
                <Eye className="h-4 w-4" />
                Lihat Bukti TF
              </button>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}