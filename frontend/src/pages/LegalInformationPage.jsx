import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, FileText } from "lucide-react";
import api from "@/lib/api";

const DEFAULT_PAGES = {
  privacy: { title: "Kebijakan Privasi", content: "Kebijakan privasi Sistem Registrasi BAZNAS untuk layanan MDJ Scholarship." },
  terms: { title: "Syarat dan Ketentuan", content: "Syarat dan ketentuan penggunaan layanan MDJ Scholarship." },
  guide: { title: "Pedoman Program", content: "Pedoman program Masa Depan Jakarta Scholarship BAZNAS (BAZIS) DKI Jakarta." },
};

export default function LegalInformationPage({ pageKey }) {
  const [page, setPage] = useState(DEFAULT_PAGES[pageKey]);
  useEffect(() => {
    api.get("/site/content").then((response) => {
      setPage(response.data.legal_information?.[pageKey] || DEFAULT_PAGES[pageKey]);
    }).catch(() => {});
  }, [pageKey]);
  return <main className="min-h-screen bg-[#F4F6F3] px-4 py-8 sm:px-6 lg:py-14">
    <section className="mx-auto max-w-4xl" data-testid={`legal-page-${pageKey}`}>
      <Link to="/" className="inline-flex items-center gap-2 text-sm font-bold text-[#0B6B3A]"><ArrowLeft className="h-4 w-4" />Kembali ke Beranda</Link>
      <article className="mt-8 border-l-4 border-[#27AE60] bg-white px-6 py-8 shadow-sm sm:px-10">
        <FileText className="h-7 w-7 text-[#0B6B3A]" />
        <p className="mt-5 text-xs font-bold uppercase tracking-wide text-[#0B6B3A]">Informasi Legal</p>
        <h1 className="mt-2 font-display text-4xl font-extrabold text-[#1F2937] sm:text-5xl">{page.title}</h1>
        <p className="mt-6 whitespace-pre-wrap text-sm leading-7 text-[#4B5563]" data-testid="legal-page-content">{page.content}</p>
      </article>
    </section>
  </main>;
}