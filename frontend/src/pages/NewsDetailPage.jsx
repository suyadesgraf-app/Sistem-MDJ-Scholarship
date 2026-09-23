import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, CalendarDays, Eye } from "lucide-react";
import api from "@/lib/api";

const slugify = (value = "") => value.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");

export default function NewsDetailPage() {
  const { slug } = useParams();
  const [item, setItem] = useState(null);
  useEffect(() => { api.get("/site/content").then((response) => setItem((response.data.announcements || []).find((entry) => slugify(entry.title) === slug) || null)).catch(() => setItem(null)); }, [slug]);
  if (!item) return <main className="min-h-screen bg-[#F5F5F2] px-4 py-16 text-center"><Link to="/berita" className="font-bold text-[#0B6B3A]">← Kembali ke daftar berita</Link><p className="mt-6 text-sm text-[#6B7280]">Berita tidak ditemukan.</p></main>;
  const imageUrl = item.banner?.url ? `${process.env.REACT_APP_BACKEND_URL}${item.banner.url}` : null;
  return <main className="min-h-screen bg-[#F5F5F2] px-4 py-6 sm:px-6 lg:px-10"><article className="mx-auto max-w-4xl" data-testid="news-detail-page"><div className="flex items-center gap-3 text-xs font-bold text-[#0B6B3A]"><Link to="/berita" data-testid="back-to-news-link" className="inline-flex items-center gap-1"><ArrowLeft className="h-3 w-3" />Kembali ke daftar berita</Link><span>{item.category}</span></div><h1 className="mt-5 font-display text-3xl font-extrabold leading-tight text-[#111827] sm:text-5xl">{item.title}</h1><div className="mt-4 flex flex-wrap gap-4 text-xs text-[#6B7280]"><span className="inline-flex items-center gap-1"><CalendarDays className="h-3.5 w-3.5" />{item.date || "Informasi MDJ"}</span><span className="inline-flex items-center gap-1"><Eye className="h-3.5 w-3.5" />MDJ Scholarship</span></div>{imageUrl && <img src={imageUrl} alt={item.title} className="mt-6 w-full rounded-xl object-cover" data-testid="news-detail-banner" />}<div className="mt-6 border-l-4 border-[#0B6B3A] bg-white p-5 text-sm italic leading-7 text-[#6B7280]">{item.summary}</div><div className="mt-7 whitespace-pre-wrap text-sm leading-8 text-[#374151]" data-testid="news-detail-content">{item.content || item.summary}</div>{item.attachment?.url && <a href={`${process.env.REACT_APP_BACKEND_URL}${item.attachment.url}`} target="_blank" rel="noreferrer" className="mt-8 inline-block rounded-lg bg-[#0B6B3A] px-4 py-3 text-sm font-bold text-white">Lihat Lampiran</a>}{item.link && <a href={item.link} target="_blank" rel="noreferrer" className="mt-8 ml-3 inline-block rounded-lg border border-[#0B6B3A] px-4 py-3 text-sm font-bold text-[#0B6B3A]">Sumber Informasi</a>}</article></main>;
}