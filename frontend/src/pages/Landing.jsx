import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { API } from "@/lib/api";
import axios from "axios";
import RegistrationFlow from "@/components/RegistrationFlow";
import {
  GraduationCap, User, Award, Shield, Menu, X, CheckCircle2, ArrowRight,
  School, BookOpen, Star, Calendar, ChevronDown, Sparkles, ShieldCheck,
  Download, MapPin, Megaphone, Facebook, Instagram, Youtube, Phone, Mail,
} from "lucide-react";

const HERO_IMG = "https://images.unsplash.com/photo-1555899434-94d1368aa7af?auto=format&fit=crop&w=1600&q=60";
const ABOUT_IMG = "https://images.unsplash.com/photo-1522202176988-66273c2fd55f?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2OTF8MHwxfHNlYXJjaHwxfHx1bml2ZXJzaXR5JTIwc3R1ZGVudHMlMjBzbWlsaW5nJTIwc3R1ZHlpbmd8ZW58MHx8fHwxNzg5MTU2MTM5fDA&ixlib=rb-4.1.0&q=85";

const NAV_LINKS = [
  { name: "Beranda", href: "#beranda" },
  { name: "Tentang", href: "#tentang" },
  { name: "Persyaratan", href: "#persyaratan" },
  { name: "Alur", href: "#alur" },
  { name: "Pengumuman", href: "#pengumuman" },
  { name: "FAQ", href: "#faq" },
];

const BENEFITS = [
  { title: "Bantuan Biaya UKT", desc: "Meringankan biaya pendidikan melalui bantuan Uang Kuliah Tunggal (UKT).", icon: GraduationCap },
  { title: "Pembentukan Karakter", desc: "Pembinaan soft skill, kepemimpinan, integritas, dan etika melalui Kaderisasi MDJ.", icon: User },
  { title: "Pelatihan Hardskill & Vokasi", desc: "Pelatihan bersertifikasi (Data Analyst, Digital Marketing, Urban Farming, dll).", icon: Award },
  { title: "Kerelawanan & Pengabdian", desc: "Mendorong kontribusi sosial nyata bagi Jakarta melalui program MDJ Mengabdi.", icon: Shield },
];

const CATEGORIES = [
  { title: "Mahasiswa Sarjana (S1)", desc: "Bantuan biaya pendidikan untuk mahasiswa S1 ber-KTP atau kampus di wilayah DKI Jakarta.", icon: School },
  { title: "Mahasiswa Vokasi", desc: "Program link & match industri untuk mahasiswa vokasi dengan dukungan Super Tax Deduction.", icon: BookOpen },
  { title: "Koordinator Akademik", desc: "Jalur kepemimpinan bagi penerima manfaat untuk menjadi penggerak komunitas di tiap kota.", icon: Star },
  { title: "Volunteer / Relawan", desc: "Kesempatan berkontribusi dalam event sosial dan ke-BAZNAS-an.", icon: User },
];

const Logo = ({ light, logoUrl }) => (
  <div className="flex items-center gap-2.5" data-testid="mdj-logo">
    <div className="h-10 w-10 overflow-hidden rounded-lg bg-[#27AE60] shadow-md shadow-[#27AE60]/30">
      {logoUrl ? (
        <img
          src={logoUrl}
          alt="Logo MDJ Scholarship"
          className="h-full w-full object-contain"
          data-testid="mdj-header-logo-image"
        />
      ) : (
        <span className="flex h-full w-full items-center justify-center text-xs font-black text-white">
          MDJ
        </span>
      )}
    </div>
    <div className="leading-tight">
      <p className={`font-display font-extrabold text-base ${light ? "text-white" : "text-[#1F2937]"}`}>MDJ Scholarship</p>
      <p className={`text-[10px] font-semibold ${light ? "text-white/70" : "text-[#6B7280]"}`}>BAZNAS (BAZIS) DKI Jakarta</p>
    </div>
  </div>
);

const Navbar = ({ onNavigate, logoUrl }) => {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const h = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", h);
    return () => window.removeEventListener("scroll", h);
  }, []);
  return (
    <nav className={`fixed top-0 inset-x-0 z-50 transition-all ${scrolled ? "bg-white/90 backdrop-blur-xl border-b border-gray-100 shadow-sm" : "bg-transparent"}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 lg:h-20">
          <Logo light={!scrolled} logoUrl={logoUrl} />
          <div className="hidden lg:flex items-center gap-1">
            {NAV_LINKS.map((l) => (
              <a key={l.name} href={l.href} data-testid={`nav-${l.name.toLowerCase()}`}
                className={`px-3.5 py-2 text-sm font-semibold rounded-lg transition-colors ${scrolled ? "text-[#6B7280] hover:text-[#0B6B3A] hover:bg-[#E8F6EE]" : "text-white/90 hover:text-white hover:bg-white/10"}`}>
                {l.name}
              </a>
            ))}
          </div>
          <div className="hidden lg:flex items-center gap-3">
            <button
              onClick={() => onNavigate("/login")}
              data-testid="nav-login-btn"
              className={`px-4 py-2 text-sm font-bold transition-colors ${scrolled ? "text-[#0B6B3A] hover:bg-[#E8F6EE]" : "text-white hover:bg-white/10"}`}
            >
              Masuk
            </button>
            <button
              onClick={() => onNavigate("/register")}
              data-testid="nav-register-btn"
              className="rounded-xl bg-[#27AE60] px-5 py-2.5 text-sm font-bold text-white shadow-md shadow-[#0B6B3A]/20 transition-[background-color,transform] duration-200 hover:-translate-y-0.5 hover:bg-[#0B6B3A] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F2C94C] focus-visible:ring-offset-2"
            >
              Daftar
            </button>
          </div>
          <button className={`lg:hidden p-2 rounded-lg ${scrolled ? "text-[#1F2937]" : "text-white"}`} onClick={() => setOpen(!open)} data-testid="nav-mobile-toggle">
            {open ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>
      {open && (
        <div className="lg:hidden bg-white border-t border-gray-100 px-4 py-4 space-y-1">
          {NAV_LINKS.map((l) => (
            <a key={l.name} href={l.href} onClick={() => setOpen(false)} className="block px-3 py-2.5 text-sm font-semibold text-[#1F2937] rounded-lg hover:bg-[#E8F6EE]">{l.name}</a>
          ))}
          <div className="grid grid-cols-2 gap-2 pt-2">
            <button
              onClick={() => onNavigate("/login")}
              data-testid="nav-mobile-login-btn"
              className="w-full rounded-xl border border-gray-200 px-4 py-2.5 text-sm font-bold text-[#0B6B3A]"
            >
              Masuk
            </button>
            <button
              onClick={() => onNavigate("/register")}
              data-testid="nav-mobile-register-btn"
              className="w-full rounded-xl bg-[#27AE60] px-4 py-2.5 text-sm font-bold text-white"
            >
              Daftar
            </button>
          </div>
        </div>
      )}
    </nav>
  );
};

export default function Landing() {
  const navigate = useNavigate();
  const [content, setContent] = useState(null);
  const [faqOpen, setFaqOpen] = useState(0);
  const go = (p) => navigate(p);

  useEffect(() => {
    axios.get(`${API}/site/content`).then((r) => setContent(r.data)).catch(() => setContent({}));
  }, []);

  const c = content || {};
  const settings = c.settings || {};
  const stats = c.stats || [];
  const registrationFlow = c.registration_flow || [];
  const announcements = c.announcements || [];
  const requirements = c.eligibility_requirements || c.requirements || [];
  const requiredDocuments = c.required_documents || [];
  const faqs = c.faqs || [];
  const hero = c.hero || {};
  const bannerBg = c.banner_url ? `${API.replace("/api", "")}${c.banner_url}` : HERO_IMG;
  const aboutBg = c.about_url ? `${API.replace("/api", "")}${c.about_url}` : ABOUT_IMG;
  const logoUrl = c.logo_url ? `${API.replace("/api", "")}${c.logo_url}` : null;

  return (
    <div className="min-h-screen bg-white font-sans">
      <Navbar onNavigate={go} logoUrl={logoUrl} />

      {/* HERO */}
      <section id="beranda" className="relative min-h-[620px] flex items-center pt-20 overflow-hidden">
        <div className="absolute inset-0 bg-[#0B6B3A]">
          <img src={bannerBg} alt="Jakarta" fetchpriority="high" decoding="async" onError={(e) => { if (e.currentTarget.src !== HERO_IMG) e.currentTarget.src = HERO_IMG; }} className="w-full h-full object-cover" data-testid="hero-banner-img" />
          <div className="absolute inset-0 bg-gradient-to-r from-[#0B3D1F]/95 via-[#0B6B3A]/85 to-[#27AE60]/60" />
        </div>
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full grid lg:grid-cols-2 gap-10 items-center py-16">
          <div className="text-white animate-fade-up">
            <span className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/15 backdrop-blur text-xs font-bold border border-white/20 mb-6">
              <Sparkles className="w-3.5 h-3.5 text-[#F2C94C]" /> Program Beasiswa Pendidikan DKI Jakarta
            </span>
            <h1 className="font-display font-black text-4xl sm:text-5xl lg:text-6xl tracking-tight leading-[1.05] mb-5">
              {hero.title || "Wujudkan Pendidikan dan Masa Depan Terbaikmu"}
            </h1>
            <p className="text-base lg:text-lg text-white/85 leading-relaxed max-w-xl mb-8">
              {hero.subtitle || "Program Masa Depan Jakarta (MDJ) hadir sebagai wujud nyata dukungan BAZNAS (BAZIS) Provinsi DKI Jakarta. Muda dengan Zakat, Bahagia dengan Manfaat."}
            </p>
            <div className="flex flex-wrap gap-3">
              <button onClick={() => go("/login")} data-testid="hero-register-btn"
                className="px-8 py-3.5 text-base font-bold text-[#0B6B3A] bg-[#F2C94C] rounded-full hover:bg-[#D4AC2B] shadow-lg shadow-black/20 transition-colors flex items-center gap-2">
                Daftar Beasiswa <ArrowRight className="w-5 h-5" />
              </button>
              <a href="#tentang" className="px-8 py-3.5 text-base font-bold text-white bg-white/10 border border-white/30 rounded-full hover:bg-white/20 transition-colors">Pelajari Program</a>
            </div>
            <div className="flex flex-wrap gap-x-6 gap-y-2 mt-8 text-sm text-white/80">
              <span className="flex items-center gap-2"><CheckCircle2 className="w-4 h-4 text-[#F2C94C]" /> Gratis & transparan</span>
              <span className="flex items-center gap-2"><ShieldCheck className="w-4 h-4 text-[#F2C94C]" /> Terverifikasi & akuntabel</span>
            </div>
          </div>
          <div className="hidden lg:flex justify-end animate-fade-up" style={{ animationDelay: "0.15s" }}>
            <div className="bg-white/95 backdrop-blur-xl rounded-2xl p-6 w-full max-w-sm shadow-2xl border border-white/50">
              <p className="font-display font-extrabold text-lg text-[#1F2937]">Masa Depan Jakarta {settings.year || "2026"}</p>
              <p className="text-sm text-[#6B7280] mt-1 mb-5">Mewujudkan SDM Jakarta yang Terdidik, Unggul, dan Berakhlak Mulia.</p>
              <div className="rounded-xl bg-[#E8F6EE] p-4 flex items-center gap-3">
                <div className={`w-2.5 h-2.5 rounded-full ${settings.registration_open ? "bg-[#27AE60] animate-pulse" : "bg-[#DC2626]"}`} />
                <div>
                  <p className="text-xs text-[#6B7280]">Status Pendaftaran</p>
                  <p className="font-bold text-[#0B6B3A] text-sm">{settings.registration_open ? "Sedang Dibuka" : "Ditutup"}</p>
                </div>
              </div>
              <div className="mt-4 space-y-2.5 text-sm">
                <div className="flex items-center justify-between"><span className="text-[#6B7280] flex items-center gap-2"><Calendar className="w-4 h-4" /> Periode</span><span className="font-semibold text-[#1F2937]">{settings.period_start} - {settings.period_end}</span></div>
                <div className="flex items-center justify-between"><span className="text-[#6B7280] flex items-center gap-2"><Megaphone className="w-4 h-4" /> Pengumuman</span><span className="font-semibold text-[#1F2937]">{settings.announcement_date}</span></div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* STATS */}
      <section className="bg-[#0B6B3A] py-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 grid grid-cols-2 lg:grid-cols-4 gap-6">
          {stats.map((s, i) => (
            <div key={i} className="text-center" data-testid={`stat-${i}`}>
              <p className="font-display font-black text-3xl lg:text-5xl text-[#F2C94C]">{s.value}</p>
              <p className="text-xs lg:text-sm text-white/80 mt-1">{s.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ABOUT */}
      <section id="tentang" className="py-20 lg:py-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid lg:grid-cols-2 gap-12 items-center mb-16">
          <div>
            <h2 className="font-display font-extrabold text-3xl lg:text-4xl tracking-tight text-[#1F2937] mb-4">Tentang Program Masa Depan Jakarta</h2>
            <p className="text-[#6B7280] leading-relaxed">Program Masa Depan Jakarta (MDJ) adalah inisiatif pemberdayaan dan bantuan biaya pendidikan (UKT) yang dikelola oleh BAZNAS (BAZIS) Provinsi DKI Jakarta. Lebih dari sekadar beasiswa, kami membangun karakter, kompetensi vokasi, dan kepemimpinan generasi muda Jakarta.</p>
            <div className="flex flex-wrap gap-2 mt-6">
              {["Berilmu", "Berakhlak", "Berdaya", "Berkontribusi"].map((t) => (
                <span key={t} className="px-3.5 py-1.5 rounded-full bg-[#E8F6EE] text-[#0B6B3A] text-xs font-bold">{t}</span>
              ))}
            </div>
          </div>
          <img
            src={aboutBg}
            alt="Mahasiswa berkolaborasi"
            className="rounded-2xl w-full h-72 object-cover shadow-lg"
            data-testid="about-program-image"
          />
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {BENEFITS.map((b, i) => (
            <div key={i} className="bg-white border border-gray-100 rounded-2xl p-6 shadow-[0_4px_20px_-2px_rgba(39,174,96,0.06)] hover:-translate-y-1 transition-transform">
              <div className="w-12 h-12 rounded-xl bg-[#E8F6EE] flex items-center justify-center mb-4"><b.icon className="w-6 h-6 text-[#27AE60]" /></div>
              <h3 className="font-display font-bold text-lg text-[#1F2937] mb-2">{b.title}</h3>
              <p className="text-sm text-[#6B7280] leading-relaxed">{b.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CATEGORIES */}
      <section className="py-20 lg:py-24 bg-[#0B3D1F]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="font-display font-extrabold text-3xl lg:text-4xl tracking-tight text-white text-center mb-3">Pilih Kategori Program</h2>
          <p className="text-white/70 text-center max-w-2xl mx-auto mb-12">Jalur kepesertaan disesuaikan dengan jenjang pendidikan dan fokus pengembangan.</p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {CATEGORIES.map((cat, i) => (
              <div key={i} className="bg-white/5 border border-white/10 rounded-2xl p-6 flex flex-col hover:bg-white/10 transition-colors">
                <div className="w-12 h-12 rounded-xl bg-[#F2C94C]/20 flex items-center justify-center mb-4"><cat.icon className="w-6 h-6 text-[#F2C94C]" /></div>
                <h3 className="font-display font-bold text-lg text-white mb-2">{cat.title}</h3>
                <p className="text-sm text-white/70 leading-relaxed mb-4">{cat.desc}</p>
                <button onClick={() => go("/register")} className="text-sm font-bold text-[#F2C94C] flex items-center gap-2 hover:gap-3 transition-all mt-auto w-fit">Lihat Persyaratan <ArrowRight className="w-4 h-4" /></button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* REQUIREMENTS */}
      <section id="persyaratan" className="py-20 lg:py-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid lg:grid-cols-3 gap-10">
          <div className="lg:col-span-1">
            <h2 className="font-display font-extrabold text-3xl lg:text-4xl tracking-tight text-[#1F2937] mb-4">Syarat & Kelengkapan Berkas</h2>
            <p className="text-[#6B7280] leading-relaxed mb-6">Pastikan Anda memenuhi ketentuan dan menyiapkan dokumen sebelum memulai pendaftaran.</p>
            <div className="rounded-2xl bg-[#FEF9E7] border border-[#F2C94C]/40 p-4 text-sm text-[#7a5c00]">Dokumen tidak lengkap dapat menyebabkan pendaftaran tidak dapat diproses.</div>
          </div>
          <div className="lg:col-span-2 grid gap-6 md:grid-cols-2">
            <RequirementList title="Syarat (Kriteria / Ketentuan Pendaftar)" items={requirements} testId="eligibility-requirements" />
            <RequirementList title="Kelengkapan Berkas (Dokumen yang Harus Disiapkan)" items={requiredDocuments} testId="required-documents" />
          </div>
        </div>
      </section>

      <RegistrationFlow steps={registrationFlow} />

      {/* ANNOUNCEMENTS */}
      <section id="pengumuman" className="py-20 lg:py-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <h2 className="font-display font-extrabold text-3xl lg:text-4xl tracking-tight text-[#1F2937] text-center mb-3">Pengumuman Terbaru</h2>
        <p className="text-[#6B7280] text-center mb-12">Informasi dan berita terkini seputar MDJ Scholarship.</p>
        <div className="grid md:grid-cols-3 gap-6">
          {announcements.map((a, i) => (
            <div key={i} className="bg-white border border-gray-100 rounded-2xl p-6 shadow-[0_4px_20px_-2px_rgba(39,174,96,0.06)] hover:-translate-y-1 transition-transform">
              <div className="flex items-center justify-between mb-3">
                <span className="px-2.5 py-1 rounded-full bg-[#E8F6EE] text-[#0B6B3A] text-[11px] font-bold">{a.category}</span>
                <span className="text-xs text-[#6B7280]">{a.date}</span>
              </div>
              <h3 className="font-display font-bold text-lg text-[#1F2937] mb-2">{a.title}</h3>
              <p className="text-sm text-[#6B7280] leading-relaxed">{a.summary}</p>
            </div>
          ))}
        </div>
      </section>

      {/* FAQ */}
      <section id="faq" className="py-20 lg:py-24 bg-[#F9FAFB]">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="font-display font-extrabold text-3xl lg:text-4xl tracking-tight text-[#1F2937] text-center mb-3">Pertanyaan yang Sering Diajukan</h2>
          <p className="text-[#6B7280] text-center mb-10">Temukan jawaban untuk pertanyaan umum seputar program.</p>
          <div className="space-y-3">
            {faqs.map((f, i) => (
              <div key={i} className="bg-white rounded-xl border border-gray-100 overflow-hidden">
                <button onClick={() => setFaqOpen(faqOpen === i ? -1 : i)} data-testid={`faq-${i}`}
                  className="w-full flex items-center justify-between gap-4 p-5 text-left">
                  <span className="font-semibold text-[#1F2937]">{f.q}</span>
                  <ChevronDown className={`w-5 h-5 text-[#27AE60] shrink-0 transition-transform ${faqOpen === i ? "rotate-180" : ""}`} />
                </button>
                {faqOpen === i && <div className="px-5 pb-5 text-sm text-[#6B7280] leading-relaxed">{f.a}</div>}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-b-2 border-[#27AE60] bg-[#08743D] py-16 sm:py-20">
        <div className="mx-auto max-w-3xl px-4 text-center">
          <h2 className="font-display mb-4 text-3xl font-black leading-[1.04] text-white sm:text-4xl">
            Siap Mengambil Langkah untuk Masa Depanmu?
          </h2>
          <p className="mx-auto mb-8 max-w-2xl text-sm leading-relaxed text-white/90 sm:text-base">
            Persiapkan dokumenmu, lengkapi pendaftaran, dan jadilah bagian dari Kader Akademia
            Program Masa Depan Jakarta.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <button
              onClick={() => go("/register")}
              data-testid="cta-register-btn"
              className="rounded-xl bg-[#F2C94C] px-7 py-3 text-sm font-bold text-[#0B6B3A] shadow-lg
                shadow-black/10 transition-colors duration-200 hover:bg-[#D4AC2B]
                focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white
                focus-visible:ring-offset-2 focus-visible:ring-offset-[#08743D]"
            >
              Daftar Sekarang
            </button>
            <a
              href="#persyaratan"
              data-testid="cta-requirements-link"
              className="rounded-xl border border-white/30 px-7 py-3 text-sm font-bold text-white
                transition-colors duration-200 hover:bg-white/10 focus-visible:outline-none
                focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2
                focus-visible:ring-offset-[#08743D]"
            >
              Cek Persyaratan
            </a>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="bg-[#111827] py-14 text-white/65 sm:py-16">
        <div className="mx-auto grid max-w-6xl gap-10 px-4 sm:px-6 md:grid-cols-2 lg:grid-cols-4 lg:gap-12">
          <div>
            <p className="font-display text-base font-extrabold uppercase text-white">
              Masa Depan Jakarta Scholarship
            </p>
            <p className="mt-0.5 text-[10px] font-medium text-white/50">
              BAZNAS (BAZIS) Provinsi DKI Jakarta
            </p>
            <p className="mt-5 max-w-xs text-sm leading-relaxed">
              Program beasiswa dan pembinaan komprehensif bagi mahasiswa DKI Jakarta dan keluarga
              prasejahtera untuk membangun generasi berilmu, berakhlak, berdaya, dan berkontribusi.
            </p>
            <div className="mt-6 flex items-center gap-3">
              <a
                href="https://www.facebook.com/baznasbazisdki"
                target="_blank"
                rel="noreferrer"
                aria-label="Facebook BAZNAS BAZIS DKI Jakarta"
                data-testid="footer-facebook-link"
                className="text-white/60 transition-colors duration-200 hover:text-[#F2C94C]"
              >
                <Facebook className="h-5 w-5" />
              </a>
              <a
                href="https://www.instagram.com/baznasbazisdki/"
                target="_blank"
                rel="noreferrer"
                aria-label="Instagram BAZNAS BAZIS DKI Jakarta"
                data-testid="footer-instagram-link"
                className="text-white/60 transition-colors duration-200 hover:text-[#F2C94C]"
              >
                <Instagram className="h-5 w-5" />
              </a>
              <a
                href="https://www.youtube.com/@baznasbazisdki"
                target="_blank"
                rel="noreferrer"
                aria-label="YouTube BAZNAS BAZIS DKI Jakarta"
                data-testid="footer-youtube-link"
                className="text-white/60 transition-colors duration-200 hover:text-[#F2C94C]"
              >
                <Youtube className="h-5 w-5" />
              </a>
            </div>
          </div>

          <div>
            <p className="font-display text-sm font-bold text-white">Tautan Cepat</p>
            <ul className="mt-5 space-y-3 text-sm">
              {NAV_LINKS.slice(1).map((link) => (
                <li key={link.name}>
                  <a
                    href={link.href}
                    data-testid={`footer-link-${link.name.toLowerCase()}`}
                    className="transition-colors duration-200 hover:text-white"
                  >
                    {link.name === "Tentang" ? "Tentang Program" : link.name}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <p className="font-display text-sm font-bold text-white">Informasi Legal</p>
            <ul className="mt-5 space-y-3 text-sm">
              <li>
                <a
                  href="#kebijakan-privasi"
                  data-testid="footer-privacy-link"
                  className="transition-colors duration-200 hover:text-white"
                >
                  Kebijakan Privasi
                </a>
              </li>
              <li>
                <a
                  href="#syarat-ketentuan"
                  data-testid="footer-terms-link"
                  className="transition-colors duration-200 hover:text-white"
                >
                  Syarat dan Ketentuan
                </a>
              </li>
              <li>
                <a
                  href="#pedoman-program"
                  data-testid="footer-guide-link"
                  className="transition-colors duration-200 hover:text-white"
                >
                  Pedoman Program
                </a>
              </li>
            </ul>
          </div>

          <div>
            <p className="font-display text-sm font-bold text-white">Hubungi Kami</p>
            <div className="mt-5 space-y-3 text-sm leading-relaxed">
              <p className="flex items-start gap-3">
                <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-[#27AE60]" />
                <span>
                  Gedung Graha Mental Spiritual Lt.5, Jl. Awaludin II, Kebon Melati, Tanah Abang,
                  Jakarta Pusat
                </span>
              </p>
              <a
                href="tel:+62213199456"
                data-testid="footer-phone-link"
                className="flex items-center gap-3 transition-colors duration-200 hover:text-white"
              >
                <Phone className="h-4 w-4 shrink-0 text-[#27AE60]" />
                <span>[Nomor Telepon BAZNAS]</span>
              </a>
              <a
                href="mailto:pendaftaranmdj@baznasbazisdki.id"
                data-testid="footer-email-link"
                className="flex items-center gap-3 break-all transition-colors duration-200 hover:text-white"
              >
                <Mail className="h-4 w-4 shrink-0 text-[#27AE60]" />
                <span>pendaftaranmdj@baznasbazisdki.id</span>
              </a>
            </div>
          </div>
        </div>
        <div className="mx-auto mt-12 max-w-6xl border-t border-white/10 px-4 pt-6 sm:px-6">
          <div className="flex flex-col justify-between gap-2 text-xs sm:flex-row sm:items-center">
            <p data-testid="footer-copyright">
              © {new Date().getFullYear()} BAZNAS (BAZIS) Provinsi DKI Jakarta. Seluruh hak dilindungi.
            </p>
            <p data-testid="footer-tagline">Muda dengan Zakat, Bahagia dengan Manfaat.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

function RequirementList({ title, items, testId }) {
  return <section className="border border-gray-100 bg-white p-5 shadow-sm" data-testid={testId}>
    <h3 className="font-display text-lg font-extrabold text-[#1F2937]">{title}</h3>
    <div className="mt-4 space-y-3">
      {items.map((item, index) => <div key={`${item}-${index}`} className="flex items-start gap-3"><CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-[#27AE60]" /><span className="text-sm leading-relaxed text-[#1F2937]">{item}</span></div>)}
    </div>
  </section>;
}
