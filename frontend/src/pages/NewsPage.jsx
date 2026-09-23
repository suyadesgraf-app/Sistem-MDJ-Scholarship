import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Search } from "lucide-react";
import api from "@/lib/api";

const categories = ["Semua Berita", "Pengumuman", "Informasi", "Kegiatan Program", "Prestasi Awardee", "Kerja Sama", "Liputan Media", "Inspirasi Alumni", "Artikel"];

export default function NewsPage() {
  const [announcements, setAnnouncements] = useState([]);
  const [activeCategory, setActiveCategory] = useState("Semua Berita");
  const [query, setQuery] = useState("");
  useEffect(() => { api.get("/site/content").then((response) => setAnnouncements(response.data.announcements || [])).catch(() => {}); }, []);
  const news = useMemo(() => announcements.filter((item) => {
    const matchesCategory = activeCategory === "Semua Berita" || item.category === activeCategory;
    const haystack = `${item.title || ""} ${item.summary || ""}`.toLowerCase();
    return matchesCategory && haystack.includes(query.toLowerCase());
  }), [announcements, activeCategory, query]);
  return <main className="min-h-screen bg-[#F5F5F2] px-4 py-6 sm:px-6 lg:px-10">
    <div className="mx-auto max-w-7xl">
      <Link to="/" className="inline-flex items-center gap-2 text-sm font-bold text-[#0B6B3A]"><ArrowLeft className="h-4 w-4" />Kembali ke Beranda</Link>
      <div className="mt-5 grid gap-6 lg:grid-cols-[180px_minmax(0,1fr)]" data-testid="news-page">
        <aside className="h-fit rounded-xl bg-white p-4 shadow-sm" data-testid="news-category-filter"><p className="text-sm font-extrabold text-[#1F2937]">Kategori</p><div className="mt-3 space-y-1">{categories.map((category) => <button key={category} type="button" onClick={() => setActiveCategory(category)} data-testid={`news-category-${category.toLowerCase().replaceAll(" ", "-")}`} className={`w-full rounded-md px-3 py-2 text-left text-xs font-semibold ${activeCategory === category ? "bg-[#0B6B3A] text-white" : "text-[#6B7280] hover:bg-[#E8F6EE]"}`}>{category}</button>)}</div></aside>
        <section>
          <div className="flex items-center gap-2 rounded-xl bg-white p-3 shadow-sm"><Search className="h-4 w-4 text-[#6B7280]" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Cari judul berita..." data-testid="news-search-input" className="w-full border-0 text-sm outline-none" /></div>
          <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-3" data-testid="news-grid">{news.map((item, index) => <article key={`${item.title}-${index}`} className="overflow-hidden rounded-xl bg-white shadow-sm" data-testid={`news-card-${index}`}><div className="relative aspect-[1.55] bg-[#E8F6EE]">{item.banner?.url ? <img src={`${process.env.REACT_APP_BACKEND_URL}${item.banner.url}`} alt={item.title} className="h-full w-full object-cover" /> : <div className="flex h-full items-center justify-center px-4 text-center text-xs font-extrabold text-[#0B6B3A]">{item.category || "MDJ Scholarship"}</div>}{item.date && <span className="absolute left-2 top-2 rounded bg-white/95 px-2 py-1 text-[10px] font-extrabold text-[#0B6B3A]">{item.date}</span>}</div><div className="p-4"><span className="text-[10px] font-bold text-[#0B6B3A]">{item.category}</span><h1 className="mt-1 line-clamp-2 font-display text-sm font-extrabold text-[#1F2937]">{item.title}</h1><p className="mt-2 line-clamp-2 text-xs leading-relaxed text-[#6B7280]">{item.summary}</p>{item.link && <a href={item.link} target="_blank" rel="noreferrer" className="mt-3 inline-block text-xs font-bold text-[#0B6B3A]">Baca Selengkapnya →</a>}</div></article>)}</div>
          {!news.length && <p className="mt-8 text-center text-sm text-[#6B7280]" data-testid="news-empty-state">Belum ada berita pada kategori ini.</p>}
        </section>
      </div>
    </div>
  </main>;
}