import React from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Database, LockKeyhole, ShieldCheck } from "lucide-react";

const SECTIONS = [
  {
    icon: Database,
    title: "Pengumpulan Data Pengguna",
    body: "Sistem Registrasi BAZNAS mengumpulkan data yang Anda berikan saat membuat akun dan mendaftar, seperti nama, alamat email, nomor telepon, data identitas, data pendidikan, dokumen persyaratan, serta informasi yang diperlukan untuk proses seleksi dan penyaluran bantuan.",
  },
  {
    icon: ShieldCheck,
    title: "Penggunaan Data",
    body: "Data digunakan untuk verifikasi pendaftaran, penilaian kelayakan, komunikasi program, pengelolaan dokumen, proses seleksi, serta administrasi penyaluran bantuan pendidikan. Data tidak digunakan untuk tujuan yang tidak berkaitan dengan layanan MDJ Scholarship dan Sistem Registrasi BAZNAS.",
  },
  {
    icon: LockKeyhole,
    title: "Keamanan Data",
    body: "Kami menerapkan pembatasan akses berdasarkan peran, autentikasi akun, serta pengamanan pada penyimpanan dokumen dan data aplikasi. Hanya petugas yang berwenang dapat mengakses data sesuai kebutuhan tugasnya. Pengguna juga bertanggung jawab menjaga kerahasiaan kata sandi akun.",
  },
];

export default function PrivacyPolicy() {
  return (
    <main className="min-h-screen bg-[#F4F6F3] px-4 py-8 sm:px-6 lg:py-14">
      <section className="mx-auto max-w-4xl" data-testid="privacy-policy-page">
        <Link
          to="/"
          data-testid="privacy-policy-back-link"
          className="inline-flex items-center gap-2 text-sm font-bold text-[#0B6B3A] transition-colors hover:text-[#27AE60]"
        >
          <ArrowLeft className="h-4 w-4" />
          Kembali ke Beranda
        </Link>
        <header className="mt-8 border-l-4 border-[#27AE60] bg-white px-6 py-8 shadow-sm sm:px-10">
          <p className="text-xs font-bold uppercase tracking-wide text-[#0B6B3A]">BAZNAS (BAZIS) DKI Jakarta</p>
          <h1 className="mt-3 font-display text-4xl font-extrabold text-[#1F2937] sm:text-5xl">Privacy Policy</h1>
          <p className="mt-4 max-w-2xl text-sm leading-relaxed text-[#4B5563]" data-testid="privacy-policy-intro">
            Kebijakan privasi Sistem Registrasi BAZNAS untuk layanan MDJ Scholarship.
          </p>
        </header>
        <div className="mt-6 space-y-4">
          {SECTIONS.map(({ icon: Icon, title, body }, index) => (
            <article key={title} className="border border-gray-200 bg-white p-6 shadow-sm sm:p-8" data-testid={`privacy-policy-section-${index + 1}`}>
              <div className="flex items-start gap-4">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-[#E8F6EE] text-[#0B6B3A]">
                  <Icon className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="font-display text-xl font-extrabold text-[#1F2937]">{title}</h2>
                  <p className="mt-3 text-sm leading-7 text-[#4B5563]">{body}</p>
                </div>
              </div>
            </article>
          ))}
        </div>
        <p className="mt-8 text-center text-xs leading-relaxed text-[#6B7280]" data-testid="privacy-policy-updated-date">
          Terakhir diperbarui: September 2026
        </p>
      </section>
    </main>
  );
}