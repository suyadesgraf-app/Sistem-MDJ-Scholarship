import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import api, { formatApiError } from "@/lib/api";
import { CheckCircle2, XCircle, Loader2, ArrowRight } from "lucide-react";

export default function VerifyEmail() {
  const [params] = useSearchParams();
  const [state, setState] = useState({ status: "loading", message: "" });

  useEffect(() => {
    const token = params.get("token");
    if (!token) { setState({ status: "error", message: "Tautan tidak valid." }); return; }
    api.post("/auth/email/verify", { token })
      .then(({ data }) => setState({ status: "success", message: data.message || "Email berhasil diperbarui.", email: data.email }))
      .catch((e) => setState({ status: "error", message: formatApiError(e?.response?.data?.detail) }));
  }, [params]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#F0FBF5] p-4">
      <div className="bg-white rounded-2xl shadow-[0_10px_40px_-10px_rgba(39,174,96,0.2)] p-8 max-w-md w-full text-center" data-testid="verify-email-card">
        {state.status === "loading" && (
          <>
            <Loader2 className="w-12 h-12 text-[#27AE60] animate-spin mx-auto" />
            <p className="mt-4 text-[#6B7280]">Memverifikasi email Anda...</p>
          </>
        )}
        {state.status === "success" && (
          <>
            <div className="w-16 h-16 rounded-full bg-[#E8F6EE] flex items-center justify-center mx-auto"><CheckCircle2 className="w-9 h-9 text-[#27AE60]" /></div>
            <h1 className="font-display font-black text-2xl text-[#1F2937] mt-5">Email Terverifikasi</h1>
            <p className="text-[#6B7280] mt-2">{state.message}</p>
            {state.email && <p className="text-sm font-semibold text-[#0B6B3A] mt-1">{state.email}</p>}
            <Link to="/login" data-testid="verify-to-login" className="mt-6 inline-flex items-center gap-2 px-5 py-2.5 bg-[#27AE60] hover:bg-[#0B6B3A] text-white text-sm font-bold rounded-xl transition-colors">Masuk ke Akun <ArrowRight className="w-4 h-4" /></Link>
          </>
        )}
        {state.status === "error" && (
          <>
            <div className="w-16 h-16 rounded-full bg-[#FEE2E2] flex items-center justify-center mx-auto"><XCircle className="w-9 h-9 text-[#DC2626]" /></div>
            <h1 className="font-display font-black text-2xl text-[#1F2937] mt-5">Verifikasi Gagal</h1>
            <p className="text-[#6B7280] mt-2">{state.message}</p>
            <Link to="/dashboard" data-testid="verify-to-dashboard" className="mt-6 inline-flex items-center gap-2 px-5 py-2.5 border border-gray-300 text-[#1F2937] text-sm font-bold rounded-xl hover:bg-gray-50 transition-colors">Kembali ke Dashboard</Link>
          </>
        )}
      </div>
    </div>
  );
}
