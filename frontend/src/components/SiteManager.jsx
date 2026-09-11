import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import api from "@/lib/api";
import { API } from "@/lib/api";
import { Loader2, Plus, Trash2, UploadCloud, Save, Image as ImageIcon } from "lucide-react";

const TABS = [
  ["umum", "Umum & Banner"], ["timeline", "Timeline"], ["pengumuman", "Pengumuman"],
  ["statistik", "Statistik"], ["persyaratan", "Persyaratan"], ["faq", "FAQ"],
];

export default function SiteManager() {
  const [c, setC] = useState(null);
  const [tab, setTab] = useState("umum");
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);

  useEffect(() => { api.get("/site/content").then((r) => setC(r.data)); }, []);
  if (!c) return <div className="py-12 text-center"><Loader2 className="w-6 h-6 animate-spin inline text-[#27AE60]" /></div>;

  const save = async (partial) => {
    setSaving(true);
    try {
      const { data } = await api.put("/site/content", { content: partial });
      setC(data);
      toast.success("Konten website diperbarui.");
    } catch { toast.error("Gagal menyimpan konten."); }
    finally { setSaving(false); }
  };

  const uploadBanner = async (file) => {
    if (!file) return;
    setUploading(true);
    const fd = new FormData(); fd.append("file", file);
    try {
      const { data } = await api.post("/site/banner", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setC((p) => ({ ...p, banner_url: data.banner_url }));
      toast.success("Banner berhasil diunggah.");
    } catch { toast.error("Gagal mengunggah banner."); }
    finally { setUploading(false); }
  };

  const setField = (path, value) => setC((p) => ({ ...p, [path]: value }));
  const setSetting = (k, v) => setC((p) => ({ ...p, settings: { ...p.settings, [k]: v } }));
  const setHero = (k, v) => setC((p) => ({ ...p, hero: { ...p.hero, [k]: v } }));

  const bannerSrc = c.banner_url ? `${API.replace("/api", "")}${c.banner_url}` : null;

  return (
    <div className="space-y-4">
      <div className="flex gap-1.5 overflow-x-auto pb-1 mdj-scrollbar">
        {TABS.map(([v, l]) => (
          <button key={v} onClick={() => setTab(v)} data-testid={`site-tab-${v}`} className={`px-3.5 py-2 rounded-lg text-xs font-bold whitespace-nowrap transition-colors ${tab === v ? "bg-[#27AE60] text-white" : "bg-white border border-gray-200 text-[#6B7280] hover:bg-gray-50"}`}>{l}</button>
        ))}
      </div>

      {tab === "umum" && (
        <div className="space-y-4">
          <Panel title="Banner Hero">
            {bannerSrc && <img src={bannerSrc} alt="Banner" className="w-full h-40 object-cover rounded-xl mb-4" />}
            <label className="inline-flex items-center gap-2 px-4 py-2.5 bg-white border border-gray-300 hover:bg-gray-50 text-sm font-bold rounded-xl cursor-pointer">
              {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <UploadCloud className="w-4 h-4" />} Unggah Banner
              <input type="file" accept="image/*" className="hidden" data-testid="upload-banner-input" onChange={(e) => uploadBanner(e.target.files[0])} />
            </label>
            <p className="text-xs text-[#6B7280] mt-2">Rekomendasi rasio lebar (16:9). Format JPG/PNG.</p>
          </Panel>
          <Panel title="Periode & Status Pendaftaran">
            <label className="flex items-center gap-3 mb-4 cursor-pointer">
              <input type="checkbox" checked={!!c.settings?.registration_open} onChange={(e) => setSetting("registration_open", e.target.checked)} data-testid="reg-open-toggle" className="w-5 h-5 accent-[#27AE60]" />
              <span className="text-sm font-semibold text-[#1F2937]">Pendaftaran Dibuka</span>
            </label>
            <div className="grid sm:grid-cols-2 gap-4">
              <Fld label="Tanggal Mulai"><input value={c.settings?.period_start || ""} onChange={(e) => setSetting("period_start", e.target.value)} data-testid="period-start-input" className={ic} /></Fld>
              <Fld label="Tanggal Selesai"><input value={c.settings?.period_end || ""} onChange={(e) => setSetting("period_end", e.target.value)} data-testid="period-end-input" className={ic} /></Fld>
              <Fld label="Tanggal Pengumuman"><input value={c.settings?.announcement_date || ""} onChange={(e) => setSetting("announcement_date", e.target.value)} data-testid="announcement-date-input" className={ic} /></Fld>
              <Fld label="Tahun Program"><input value={c.settings?.year || ""} onChange={(e) => setSetting("year", e.target.value)} className={ic} /></Fld>
            </div>
          </Panel>
          <Panel title="Teks Hero">
            <Fld label="Judul"><input value={c.hero?.title || ""} onChange={(e) => setHero("title", e.target.value)} data-testid="hero-title-input" className={ic} /></Fld>
            <div className="mt-4"><Fld label="Subjudul"><textarea rows={3} value={c.hero?.subtitle || ""} onChange={(e) => setHero("subtitle", e.target.value)} data-testid="hero-subtitle-input" className={ic} /></Fld></div>
          </Panel>
          <SaveBar onSave={() => save({ settings: c.settings, hero: c.hero })} saving={saving} />
        </div>
      )}

      {tab === "timeline" && (
        <ArrayEditor items={c.timeline || []} onChange={(v) => setField("timeline", v)} onSave={() => save({ timeline: c.timeline })} saving={saving}
          template={{ title: "", desc: "" }} testid="timeline"
          render={(it, upd, idx) => (<>
            <input value={it.title} onChange={(e) => upd("title", e.target.value)} placeholder="Judul tahap" data-testid={`timeline-title-${idx}`} className={ic + " mb-2 font-semibold"} />
            <textarea value={it.desc} onChange={(e) => upd("desc", e.target.value)} placeholder="Deskripsi" rows={2} className={ic} />
          </>)} />
      )}

      {tab === "pengumuman" && (
        <ArrayEditor items={c.announcements || []} onChange={(v) => setField("announcements", v)} onSave={() => save({ announcements: c.announcements })} saving={saving}
          template={{ date: "", category: "Informasi", title: "", summary: "" }} testid="announcement"
          render={(it, upd, idx) => (<>
            <div className="grid grid-cols-2 gap-2 mb-2">
              <input value={it.date} onChange={(e) => upd("date", e.target.value)} placeholder="Tanggal" data-testid={`announcement-date-${idx}`} className={ic} />
              <input value={it.category} onChange={(e) => upd("category", e.target.value)} placeholder="Kategori" className={ic} />
            </div>
            <input value={it.title} onChange={(e) => upd("title", e.target.value)} placeholder="Judul" data-testid={`announcement-title-${idx}`} className={ic + " mb-2 font-semibold"} />
            <textarea value={it.summary} onChange={(e) => upd("summary", e.target.value)} placeholder="Ringkasan" rows={2} className={ic} />
          </>)} />
      )}

      {tab === "statistik" && (
        <ArrayEditor items={c.stats || []} onChange={(v) => setField("stats", v)} onSave={() => save({ stats: c.stats })} saving={saving}
          template={{ label: "", value: "" }} testid="stat"
          render={(it, upd, idx) => (<div className="grid grid-cols-2 gap-2">
            <input value={it.value} onChange={(e) => upd("value", e.target.value)} placeholder="Nilai" data-testid={`stat-value-${idx}`} className={ic + " font-bold"} />
            <input value={it.label} onChange={(e) => upd("label", e.target.value)} placeholder="Label" className={ic} />
          </div>)} />
      )}

      {tab === "persyaratan" && (
        <StringListEditor items={c.requirements || []} onChange={(v) => setField("requirements", v)} onSave={() => save({ requirements: c.requirements })} saving={saving} testid="requirement" />
      )}

      {tab === "faq" && (
        <ArrayEditor items={c.faqs || []} onChange={(v) => setField("faqs", v)} onSave={() => save({ faqs: c.faqs })} saving={saving}
          template={{ q: "", a: "" }} testid="faq"
          render={(it, upd, idx) => (<>
            <input value={it.q} onChange={(e) => upd("q", e.target.value)} placeholder="Pertanyaan" data-testid={`faq-q-${idx}`} className={ic + " mb-2 font-semibold"} />
            <textarea value={it.a} onChange={(e) => upd("a", e.target.value)} placeholder="Jawaban" rows={2} className={ic} />
          </>)} />
      )}
    </div>
  );
}

function ArrayEditor({ items, onChange, onSave, saving, template, render, testid }) {
  const upd = (idx, k, v) => onChange(items.map((it, i) => (i === idx ? { ...it, [k]: v } : it)));
  const add = () => onChange([...items, { ...template }]);
  const del = (idx) => onChange(items.filter((_, i) => i !== idx));
  return (
    <div className="space-y-3">
      {items.map((it, idx) => (
        <div key={idx} className="bg-white border border-gray-100 rounded-2xl p-4 shadow-sm relative">
          <button onClick={() => del(idx)} data-testid={`del-${testid}-${idx}`} className="absolute top-3 right-3 p-1.5 text-[#DC2626] hover:bg-[#FEE2E2] rounded-lg"><Trash2 className="w-4 h-4" /></button>
          <div className="pr-8">{render(it, (k, v) => upd(idx, k, v), idx)}</div>
        </div>
      ))}
      <button onClick={add} data-testid={`add-${testid}`} className="w-full py-3 border-2 border-dashed border-gray-200 rounded-xl text-sm font-bold text-[#6B7280] hover:border-[#27AE60] hover:text-[#27AE60] flex items-center justify-center gap-2 transition-colors"><Plus className="w-4 h-4" /> Tambah</button>
      <SaveBar onSave={onSave} saving={saving} />
    </div>
  );
}

function StringListEditor({ items, onChange, onSave, saving, testid }) {
  return (
    <div className="space-y-3">
      {items.map((it, idx) => (
        <div key={idx} className="flex gap-2 items-center">
          <input value={it} onChange={(e) => onChange(items.map((v, i) => (i === idx ? e.target.value : v)))} data-testid={`${testid}-${idx}`} className={ic} />
          <button onClick={() => onChange(items.filter((_, i) => i !== idx))} className="p-2.5 text-[#DC2626] hover:bg-[#FEE2E2] rounded-lg shrink-0"><Trash2 className="w-4 h-4" /></button>
        </div>
      ))}
      <button onClick={() => onChange([...items, ""])} data-testid={`add-${testid}`} className="w-full py-3 border-2 border-dashed border-gray-200 rounded-xl text-sm font-bold text-[#6B7280] hover:border-[#27AE60] hover:text-[#27AE60] flex items-center justify-center gap-2 transition-colors"><Plus className="w-4 h-4" /> Tambah Persyaratan</button>
      <SaveBar onSave={onSave} saving={saving} />
    </div>
  );
}

const SaveBar = ({ onSave, saving }) => (
  <button onClick={onSave} disabled={saving} data-testid="save-site-content-btn" className="px-5 py-2.5 bg-[#27AE60] hover:bg-[#0B6B3A] text-white text-sm font-bold rounded-xl flex items-center gap-2 transition-colors">{saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Simpan Perubahan</button>
);
const Panel = ({ title, children }) => <div className="bg-white border border-gray-100 rounded-2xl p-6 shadow-sm"><h3 className="font-display font-bold text-[#1F2937] mb-4">{title}</h3>{children}</div>;
const ic = "w-full px-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#27AE60]";
const Fld = ({ label, children }) => <div><label className="block text-sm font-semibold text-[#1F2937] mb-1.5">{label}</label>{children}</div>;
