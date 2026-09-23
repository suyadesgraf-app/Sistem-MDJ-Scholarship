import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import api from "@/lib/api";
import { API } from "@/lib/api";
import {
  ChevronDown,
  ChevronUp,
  Image as ImageIcon,
  Loader2,
  Plus,
  Save,
  Trash2,
  UploadCloud,
} from "lucide-react";

const TABS = [
  ["umum", "Umum & Banner"],
  ["alur", "Alur Pendaftaran"],
  ["pengumuman", "Pengumuman"],
  ["statistik", "Statistik"],
  ["persyaratan", "Syarat Pendaftar"],
  ["berkas", "Kelengkapan Berkas"],
  ["legal", "Informasi Legal"],
  ["faq", "FAQ"],
];

let newsCategoryItemSequence = 0;

const automaticAnnouncementDate = () => new Intl.DateTimeFormat("id-ID", {
  day: "numeric",
  month: "long",
  year: "numeric",
  timeZone: "Asia/Jakarta",
}).format(new Date());

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
    const fd = new FormData();
    fd.append("file", file);
    try {
      const { data } = await api.post("/site/banner", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setC((p) => ({ ...p, banner_url: data.banner_url }));
      toast.success("Banner berhasil diunggah.");
    } catch { toast.error("Gagal mengunggah banner."); }
    finally { setUploading(false); }
  };

  const uploadAboutImage = async (file) => {
    if (!file) return;
    setUploading(true);
    const fd = new FormData(); fd.append("file", file);
    try {
      const { data } = await api.post("/site/about-image", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setC((p) => ({ ...p, about_url: data.about_url }));
      toast.success("Gambar Tentang berhasil diunggah.");
    } catch { toast.error("Gagal mengunggah gambar Tentang."); }
    finally { setUploading(false); }
  };

  const uploadLogo = async (file) => {
    if (!file) return;
    setUploading(true);
    const fd = new FormData();
    fd.append("file", file);
    try {
      const { data } = await api.post("/site/logo", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setC((previous) => ({ ...previous, logo_url: data.logo_url }));
      toast.success("Logo MDJ berhasil diunggah.");
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Gagal mengunggah logo MDJ.");
    } finally {
      setUploading(false);
    }
  };

  const setField = (path, value) => setC((p) => ({ ...p, [path]: value }));
  const setSetting = (k, v) => setC((p) => ({ ...p, settings: { ...p.settings, [k]: v } }));
  const setHero = (k, v) => setC((p) => ({ ...p, hero: { ...p.hero, [k]: v } }));
  const setAnnouncementPopup = (index, field, enabled) => {
    setC((previous) => ({
      ...previous,
      announcements: (previous.announcements || []).map((announcement, announcementIndex) => {
        if (announcementIndex === index) {
          return { ...announcement, [field]: enabled };
        }
        return enabled ? { ...announcement, [field]: false } : announcement;
      }),
    }));
  };
  const saveAnnouncements = () => {
    const announcements = (c.announcements || []).map((announcement) => ({
      ...announcement,
      date: announcement.date || automaticAnnouncementDate(),
    }));
    setField("announcements", announcements);
    save({ announcements });
  };

  const bannerSrc = c.banner_url ? `${API.replace("/api", "")}${c.banner_url}` : null;
  const aboutSrc = c.about_url ? `${API.replace("/api", "")}${c.about_url}` : null;
  const logoSrc = c.logo_url ? `${API.replace("/api", "")}${c.logo_url}` : null;

  return (
    <div className="space-y-4">
      <div className="flex gap-1.5 overflow-x-auto pb-1 mdj-scrollbar">
        {TABS.map(([v, l]) => (
          <button key={v} onClick={() => setTab(v)} data-testid={`site-tab-${v}`} className={`px-3.5 py-2 rounded-lg text-xs font-bold whitespace-nowrap transition-colors ${tab === v ? "bg-[#27AE60] text-white" : "bg-white border border-gray-200 text-[#6B7280] hover:bg-gray-50"}`}>{l}</button>
        ))}
      </div>

      {tab === "umum" && (
        <div className="space-y-4">
          <Panel title="Logo MDJ Scholarship">
            {logoSrc && (
              <img
                src={logoSrc}
                alt="Logo MDJ Scholarship"
                className="mb-4 h-24 w-24 rounded-lg object-contain"
                data-testid="site-logo-preview"
              />
            )}
            <label className="inline-flex cursor-pointer items-center gap-2 rounded-xl border border-gray-300 bg-white px-4 py-2.5 text-sm font-bold hover:bg-gray-50">
              {uploading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <ImageIcon className="h-4 w-4" />
              )}
              Unggah Logo
              <input
                type="file"
                accept=".jpg,.jpeg,.png,.webp"
                className="hidden"
                data-testid="upload-site-logo-input"
                onChange={(event) => uploadLogo(event.target.files[0])}
              />
            </label>
            <p className="mt-2 text-xs text-[#6B7280]">
              Gunakan logo persegi dengan latar yang sesuai identitas MDJ.
            </p>
          </Panel>
          <Panel title="Banner Hero">
            {bannerSrc && <img src={bannerSrc} alt="Banner" className="w-full h-40 object-cover rounded-xl mb-4" />}
            <label className="inline-flex items-center gap-2 px-4 py-2.5 bg-white border border-gray-300 hover:bg-gray-50 text-sm font-bold rounded-xl cursor-pointer">
              {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <UploadCloud className="w-4 h-4" />} Unggah Banner
              <input type="file" accept="image/*" className="hidden" data-testid="upload-banner-input" onChange={(e) => uploadBanner(e.target.files[0])} />
            </label>
            <p className="text-xs text-[#6B7280] mt-2">Rekomendasi rasio lebar (16:9). Format JPG/PNG.</p>
          </Panel>
          <Panel title="Gambar Tentang Program">
            {aboutSrc && (
              <img
                src={aboutSrc}
                alt="Tentang Program"
                className="w-full h-40 object-cover rounded-xl mb-4"
                data-testid="about-image-preview"
              />
            )}
            <label className="inline-flex items-center gap-2 px-4 py-2.5 bg-white border border-gray-300 hover:bg-gray-50 text-sm font-bold rounded-xl cursor-pointer">
              {uploading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <ImageIcon className="w-4 h-4" />
              )}
              Unggah Gambar Tentang
              <input
                type="file"
                accept="image/*"
                className="hidden"
                data-testid="upload-about-image-input"
                onChange={(e) => uploadAboutImage(e.target.files[0])}
              />
            </label>
            <p className="text-xs text-[#6B7280] mt-2">Pilih gambar mahasiswa atau kegiatan program dengan rasio lebar.</p>
          </Panel>
          <Panel title="Periode & Status Pendaftaran">
            <label className="flex items-center gap-3 mb-4 cursor-pointer">
              <input type="checkbox" checked={!!c.settings?.registration_open} onChange={(e) => setSetting("registration_open", e.target.checked)} data-testid="reg-open-toggle" className="w-5 h-5 accent-[#27AE60]" />
              <span className="text-sm font-semibold text-[#1F2937]">Pendaftaran Dibuka</span>
            </label>
            <div className={`grid sm:grid-cols-2 gap-4 ${!c.settings?.registration_open ? "opacity-50" : ""}`}>
              <Fld label="Tanggal & Jam Mulai"><input type="datetime-local" disabled={!c.settings?.registration_open} value={c.settings?.registration_start_at || ""} onChange={(e) => setSetting("registration_start_at", e.target.value)} data-testid="period-start-input" className={ic} /></Fld>
              <Fld label="Tanggal & Jam Selesai"><input type="datetime-local" disabled={!c.settings?.registration_open} value={c.settings?.registration_end_at || ""} onChange={(e) => setSetting("registration_end_at", e.target.value)} data-testid="period-end-input" className={ic} /></Fld>
              <Fld label="Tanggal Pengumuman"><input type="date" disabled={!c.settings?.registration_open} value={c.settings?.announcement_date || ""} onChange={(e) => setSetting("announcement_date", e.target.value)} data-testid="announcement-date-input" className={ic} /></Fld>
              <Fld label="Tahun Program"><input type="number" disabled={!c.settings?.registration_open} value={c.settings?.year || ""} onChange={(e) => setSetting("year", e.target.value)} className={ic} /></Fld>
              <Fld label="Kuota Penerima">
                <input
                  type="number"
                  min="1"
                  step="1"
                  value={c.settings?.recipient_quota || ""}
                  onChange={(event) => setSetting("recipient_quota", event.target.value)}
                  data-testid="recipient-quota-input"
                  placeholder="Contoh: 3600"
                  className={ic}
                />
              </Fld>
            </div>
          </Panel>
          <Panel title="Teks Hero">
            <Fld label="Judul"><input value={c.hero?.title || ""} onChange={(e) => setHero("title", e.target.value)} data-testid="hero-title-input" className={ic} /></Fld>
            <div className="mt-4"><Fld label="Subjudul"><textarea rows={3} value={c.hero?.subtitle || ""} onChange={(e) => setHero("subtitle", e.target.value)} data-testid="hero-subtitle-input" className={ic} /></Fld></div>
          </Panel>
          <SaveBar onSave={() => save({ settings: c.settings, hero: c.hero })} saving={saving} />
        </div>
      )}

      {tab === "alur" && (
        <RegistrationFlowEditor
          items={c.registration_flow || []}
          onChange={(value) => setField("registration_flow", value)}
          onSave={() => save({ registration_flow: c.registration_flow })}
          saving={saving}
        />
      )}

      {tab === "pengumuman" && (
        <div className="space-y-6">
          <NewsCategoryEditor
            categories={c.news_categories || []}
            onSave={(news_categories, news_category_renames) => save({
              news_categories,
              news_category_renames,
            })}
            saving={saving}
          />
          <ArrayEditor
            items={c.announcements || []}
            onChange={(value) => setField("announcements", value)}
            onSave={saveAnnouncements}
            saving={saving}
            template={{
              date: automaticAnnouncementDate(),
              category: c.news_categories?.[0] || "Informasi",
              title: "",
              summary: "",
              content: "",
              link: "",
            }}
            testid="announcement"
            render={(item, update, index) => (
              <>
                <div className="mb-2 grid grid-cols-2 gap-2">
                  <div
                    data-testid={`announcement-created-date-${index}`}
                    className="flex min-h-11 items-center rounded-xl border border-gray-200 bg-[#F9FAFB]
                      px-3 text-sm text-[#4B5563]"
                  >
                    Dibuat: {item.date || automaticAnnouncementDate()}
                  </div>
                  <select
                    value={item.category || c.news_categories?.[0] || ""}
                    onChange={(event) => update("category", event.target.value)}
                    data-testid={`announcement-category-${index}`}
                    className={ic}
                  >
                    {(c.news_categories || []).map((category) => (
                      <option key={category} value={category}>{category}</option>
                    ))}
                  </select>
                </div>
                <div className="mb-3 flex flex-wrap gap-x-5 gap-y-2">
                  <label className="flex cursor-pointer items-center gap-2 text-xs font-semibold text-[#374151]">
                    <input
                      type="checkbox"
                      checked={item.show_student_popup === true}
                      onChange={(event) => setAnnouncementPopup(
                        index,
                        "show_student_popup",
                        event.target.checked,
                      )}
                      data-testid={`announcement-student-popup-${index}`}
                      className="h-4 w-4 rounded border-gray-300 accent-[#27AE60]"
                    />
                    Popup Akun Mahasiswa
                  </label>
                  <label className="flex cursor-pointer items-center gap-2 text-xs font-semibold text-[#374151]">
                    <input
                      type="checkbox"
                      checked={item.show_landing_popup === true}
                      onChange={(event) => setAnnouncementPopup(
                        index,
                        "show_landing_popup",
                        event.target.checked,
                      )}
                      data-testid={`announcement-landing-popup-${index}`}
                      className="h-4 w-4 rounded border-gray-300 accent-[#27AE60]"
                    />
                    Popup Beranda
                  </label>
                </div>
                <input
                  value={item.title}
                  onChange={(event) => update("title", event.target.value)}
                  placeholder="Judul"
                  data-testid={`announcement-title-${index}`}
                  className={`${ic} mb-2 font-semibold`}
                />
                <textarea
                  value={item.summary}
                  onChange={(event) => update("summary", event.target.value)}
                  placeholder="Ringkasan"
                  rows={2}
                  data-testid={`announcement-summary-${index}`}
                  className={ic}
                />
                <textarea
                  value={item.content || ""}
                  onChange={(event) => update("content", event.target.value)}
                  placeholder="Isi detail berita"
                  rows={5}
                  data-testid={`announcement-content-${index}`}
                  className={`${ic} mt-2`}
                />
                <input
                  value={item.link || ""}
                  onChange={(event) => update("link", event.target.value)}
                  placeholder="Tautan pengumuman (opsional)"
                  data-testid={`announcement-link-${index}`}
                  className={`${ic} mt-2`}
                />
                <AnnouncementUpload onUpload={(attachment) => update(
                  attachment.content_type.startsWith("image/") ? "banner" : "attachment",
                  attachment,
                )} index={index} />
                {item.banner && (
                  <p className="mt-2 text-xs text-[#0B6B3A]">Banner: {item.banner.name}</p>
                )}
                {item.attachment && (
                  <p className="mt-2 text-xs text-[#0B6B3A]">
                    Dokumen: {item.attachment.name}
                  </p>
                )}
              </>
            )}
          />
        </div>
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
        <StringListEditor items={c.eligibility_requirements || []} onChange={(v) => setField("eligibility_requirements", v)} onSave={() => save({ eligibility_requirements: c.eligibility_requirements })} saving={saving} testid="eligibility-requirement" addLabel="Tambah Syarat" />
      )}

      {tab === "berkas" && (
        <StringListEditor items={c.required_documents || []} onChange={(v) => setField("required_documents", v)} onSave={() => save({ required_documents: c.required_documents })} saving={saving} testid="required-document" addLabel="Tambah Berkas" />
      )}

      {tab === "legal" && <LegalEditor content={c.legal_information || {}} onSave={(legal_information) => save({ legal_information })} saving={saving} />}

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

function LegalEditor({ content, onSave, saving }) {
  const [legal, setLegal] = useState({
    privacy: content.privacy || { title: "Kebijakan Privasi", content: "" },
    terms: content.terms || { title: "Syarat dan Ketentuan", content: "" },
    guide: content.guide || { title: "Pedoman Program", content: "" },
  });
  const update = (key, field, value) => setLegal((previous) => ({ ...previous, [key]: { ...previous[key], [field]: value } }));
  const importFile = async (key, file) => {
    if (!file) return;
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await api.post("/super-admin/legal-information/import", formData, { headers: { "Content-Type": "multipart/form-data" } });
      update(key, "content", response.data.content);
      toast.success("Isi berkas berhasil dimasukkan ke editor.");
    } catch (error) { toast.error(error.response?.data?.detail || "Berkas legal gagal diimpor."); }
  };
  return <div className="space-y-5">
    {[['privacy', 'Kebijakan Privasi'], ['terms', 'Syarat dan Ketentuan'], ['guide', 'Pedoman Program']].map(([key, label]) => <div key={key} className="rounded-xl border border-gray-100 bg-white p-5"><p className="font-display font-extrabold text-[#1F2937]">{label}</p><input value={legal[key].title} onChange={(e) => update(key, 'title', e.target.value)} className={ic + " mt-3"} /><label className="mt-3 inline-flex cursor-pointer items-center gap-2 text-xs font-bold text-[#0B6B3A]">Import PDF/DOC<input type="file" accept=".pdf,.doc,.docx" className="sr-only" data-testid={`legal-import-${key}`} onChange={(event) => importFile(key, event.target.files?.[0])} /></label><textarea value={legal[key].content} onChange={(e) => update(key, 'content', e.target.value)} rows={7} className={ic + " mt-3"} placeholder="Isi halaman..." /></div>)}
    <button onClick={() => onSave(legal)} disabled={saving} data-testid="save-legal-information" className="rounded-lg bg-[#0B6B3A] px-5 py-3 text-sm font-bold text-white">{saving ? "Menyimpan..." : "Simpan Informasi Legal"}</button>
  </div>;
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

function StringListEditor({ items, onChange, onSave, saving, testid, addLabel = "Tambah" }) {
  return (
    <div className="space-y-3">
      {items.map((it, idx) => (
        <div key={idx} className="flex gap-2 items-center">
          <input value={it} onChange={(e) => onChange(items.map((v, i) => (i === idx ? e.target.value : v)))} data-testid={`${testid}-${idx}`} className={ic} />
          <button onClick={() => onChange(items.filter((_, i) => i !== idx))} className="p-2.5 text-[#DC2626] hover:bg-[#FEE2E2] rounded-lg shrink-0"><Trash2 className="w-4 h-4" /></button>
        </div>
      ))}
      <button onClick={() => onChange([...items, ""])} data-testid={`add-${testid}`} className="w-full py-3 border-2 border-dashed border-gray-200 rounded-xl text-sm font-bold text-[#6B7280] hover:border-[#27AE60] hover:text-[#27AE60] flex items-center justify-center gap-2 transition-colors"><Plus className="w-4 h-4" /> {addLabel}</button>
      <SaveBar onSave={onSave} saving={saving} />
    </div>
  );
}

function AnnouncementUpload({ onUpload, index }) {
  const [uploading, setUploading] = useState(false);

  const upload = async (file) => {
    if (!file) return;
    setUploading(true);
    try {
      const data = new FormData();
      data.append("file", file);
      const response = await api.post("/super-admin/site-announcements/upload", data, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      onUpload(response.data);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Lampiran gagal diunggah.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <label className="mt-2 inline-flex cursor-pointer items-center gap-2 text-xs font-bold text-[#0B6B3A]">
      {uploading ? "Mengunggah..." : "Unggah banner/dokumen"}
      <input
        type="file"
        accept=".jpg,.jpeg,.png,.pdf,.doc,.docx,.xls,.xlsx"
        className="sr-only"
        onChange={(event) => upload(event.target.files?.[0])}
        data-testid={`announcement-upload-${index}`}
      />
    </label>
  );
}

function NewsCategoryEditor({ categories, onSave, saving }) {
  const makeItems = (values) => values.map((value) => ({
    id: newsCategoryItemSequence++,
    original: value,
    value,
  }));
  const [items, setItems] = useState(() => makeItems(categories));

  useEffect(() => {
    setItems(makeItems(categories));
  }, [categories]);

  const update = (index, value) => {
    setItems((previous) => previous.map((item, itemIndex) => (
      itemIndex === index ? { ...item, value } : item
    )));
  };

  const remove = (index) => {
    if (items.length === 1) {
      toast.error("Minimal satu kategori berita harus tersedia.");
      return;
    }
    setItems((previous) => previous.filter((_, itemIndex) => itemIndex !== index));
  };

  const saveCategories = () => {
    const categoryRenames = {};
    items.forEach((item) => {
      const next = item.value.trim();
      if (item.original && next && item.original !== next) {
        categoryRenames[item.original] = next;
      }
    });
    onSave(items.map((item) => item.value.trim()), categoryRenames);
  };

  return (
    <div className="space-y-4" data-testid="news-category-editor">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <p className="text-sm font-bold text-[#1F2937]">Kategori Berita</p>
          <p className="mt-1 text-xs text-[#6B7280]">
            Tambahkan atau ubah pilihan kategori untuk berita di bawah.
          </p>
        </div>
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        {items.map((item, index) => (
          <div key={item.id} className="flex items-center gap-2">
            <input
              value={item.value}
              onChange={(event) => update(index, event.target.value)}
              data-testid={`news-category-input-${index}`}
              className={ic}
            />
            <button
              type="button"
              onClick={() => remove(index)}
              data-testid={`delete-news-category-${index}`}
              className="shrink-0 rounded-lg p-2.5 text-[#DC2626] hover:bg-[#FEE2E2]"
              aria-label={`Hapus kategori ${item.value || index + 1}`}
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => setItems((previous) => [
            ...previous,
            { id: newsCategoryItemSequence++, original: "", value: "" },
          ])}
          data-testid="add-news-category"
          className="inline-flex items-center gap-2 rounded-lg border-2 border-dashed border-gray-200
            px-4 py-2.5 text-sm font-bold text-[#6B7280] transition-colors hover:border-[#27AE60]
            hover:text-[#27AE60]"
        >
          <Plus className="h-4 w-4" /> Tambah Kategori
        </button>
        <button
          type="button"
          onClick={saveCategories}
          disabled={saving}
          data-testid="save-news-categories"
          className="flex items-center gap-2 rounded-lg bg-[#27AE60] px-5 py-2.5 text-sm font-bold
            text-white transition-colors hover:bg-[#0B6B3A] disabled:opacity-60"
        >
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          Simpan Kategori
        </button>
      </div>
    </div>
  );
}

function RegistrationFlowEditor({ items, onChange, onSave, saving }) {
  const updateField = (index, field, value) => {
    onChange(items.map((item, itemIndex) => (
      itemIndex === index ? { ...item, [field]: value } : item
    )));
  };

  const move = (index, direction) => {
    const targetIndex = index + direction;
    if (targetIndex < 0 || targetIndex >= items.length) return;
    const reordered = [...items];
    [reordered[index], reordered[targetIndex]] = [reordered[targetIndex], reordered[index]];
    onChange(reordered);
  };

  const remove = (index) => onChange(items.filter((_, itemIndex) => itemIndex !== index));

  return (
    <div className="space-y-4" data-testid="registration-flow-editor">
      <div className="border-l-4 border-[#27AE60] bg-[#F0FBF5] px-4 py-3">
        <p className="text-sm font-bold text-[#1F2937]">Alur Pendaftaran di Beranda</p>
        <p className="mt-1 text-xs leading-relaxed text-[#6B7280]">
          Tambahkan, ubah, susun ulang, atau hapus tahapan. Judul dan keterangan akan tampil di
          Beranda.
        </p>
      </div>
      {!items.length && (
        <p
          className="border border-dashed border-gray-200 bg-[#F9FAFB] p-4 text-sm text-[#6B7280]"
          data-testid="registration-flow-empty-state"
        >
          Belum ada tahap alur. Tambahkan tahap pertama untuk ditampilkan di Beranda.
        </p>
      )}
      {items.map((item, index) => (
        <div key={index} className="border border-gray-100 bg-white p-4 shadow-sm">
          <div className="flex items-start gap-3">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#0B6B3A] text-xs font-bold text-white">
              {String(index + 1).padStart(2, "0")}
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex items-start gap-2">
                <label className="min-w-0 flex-1 text-xs font-bold uppercase tracking-wide text-[#6B7280]">
                  Judul Tahap
                  <input
                    value={item.title || ""}
                    onChange={(event) => updateField(index, "title", event.target.value)}
                    placeholder="Contoh: Pendaftaran Online"
                    data-testid={`registration-flow-title-input-${index + 1}`}
                    className={`${ic} mt-1.5 font-semibold normal-case`}
                  />
                </label>
                <div className="flex shrink-0 items-center gap-1 pt-5">
                  <button
                    type="button"
                    onClick={() => move(index, -1)}
                    disabled={index === 0}
                    data-testid={`move-registration-flow-up-${index + 1}`}
                    title="Pindahkan ke atas"
                    className="rounded-lg p-2 text-[#0B6B3A] transition-colors hover:bg-[#E8F6EE]
                      disabled:cursor-not-allowed disabled:opacity-30"
                  >
                    <ChevronUp className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => move(index, 1)}
                    disabled={index === items.length - 1}
                    data-testid={`move-registration-flow-down-${index + 1}`}
                    title="Pindahkan ke bawah"
                    className="rounded-lg p-2 text-[#0B6B3A] transition-colors hover:bg-[#E8F6EE]
                      disabled:cursor-not-allowed disabled:opacity-30"
                  >
                    <ChevronDown className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => remove(index)}
                    data-testid={`delete-registration-flow-${index + 1}`}
                    title="Hapus tahap"
                    className="rounded-lg p-2 text-[#DC2626] transition-colors hover:bg-[#FEE2E2]"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
              <label className="mt-3 block text-xs font-bold uppercase tracking-wide text-[#6B7280]">
                Keterangan Tahap
                <textarea
                  value={item.desc || ""}
                  onChange={(event) => updateField(index, "desc", event.target.value)}
                  placeholder="Masukkan keterangan yang muncul saat tahap dipilih..."
                  rows={3}
                  data-testid={`registration-flow-description-input-${index + 1}`}
                  className={`${ic} mt-1.5 resize-y`}
                />
              </label>
            </div>
          </div>
        </div>
      ))}
      <button
        type="button"
        onClick={() => onChange([...items, { title: "", desc: "" }])}
        data-testid="add-registration-flow-step"
        className="flex w-full items-center justify-center gap-2 rounded-xl border-2 border-dashed border-gray-200
          py-3 text-sm font-bold text-[#6B7280] transition-colors hover:border-[#27AE60]
          hover:text-[#27AE60]"
      >
        <Plus className="h-4 w-4" /> Tambah Tahap
      </button>
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
