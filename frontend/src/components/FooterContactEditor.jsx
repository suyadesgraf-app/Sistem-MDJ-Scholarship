import React from "react";
import { Plus, Save, Trash2 } from "lucide-react";

const SOCIAL_PLATFORM_OPTIONS = [
  ["facebook", "Facebook"],
  ["instagram", "Instagram"],
  ["youtube", "YouTube"],
  ["other", "Lainnya"],
];

const CONTACT_TYPE_OPTIONS = [
  ["address", "Alamat"],
  ["whatsapp", "WhatsApp"],
  ["email", "Email"],
  ["phone", "Telepon"],
  ["other", "Lainnya"],
];

const inputClass = [
  "w-full rounded-xl border border-gray-300 px-4 py-2.5 text-sm",
  "focus:outline-none focus:ring-2 focus:ring-[#27AE60]",
].join(" ");

export function FooterContactEditor({ content, onChange, onSave, saving }) {
  const footer = {
    social_links: content?.social_links || [],
    contact: {
      title: content?.contact?.title || "Hubungi Kami",
      items: content?.contact?.items || [],
    },
  };

  const updateSocial = (index, field, value) => {
    onChange({
      ...footer,
      social_links: footer.social_links.map((item, itemIndex) => (
        itemIndex === index ? { ...item, [field]: value } : item
      )),
    });
  };

  const updateContact = (index, field, value) => {
    onChange({
      ...footer,
      contact: {
        ...footer.contact,
        items: footer.contact.items.map((item, itemIndex) => (
          itemIndex === index ? { ...item, [field]: value } : item
        )),
      },
    });
  };

  return (
    <div className="space-y-6" data-testid="footer-contact-editor">
      <section className="border-l-4 border-[#27AE60] bg-[#F0FBF5] px-4 py-3">
        <p className="text-sm font-bold text-[#1F2937]">Footer Beranda</p>
        <p className="mt-1 text-xs leading-relaxed text-[#6B7280]">
          Atur tautan sosial dan informasi Hubungi Kami yang tampil pada bagian bawah Beranda.
        </p>
      </section>

      <section className="space-y-3" data-testid="footer-social-links-editor">
        <div>
          <h3 className="font-display text-base font-bold text-[#1F2937]">Tautan Sosial</h3>
          <p className="mt-1 text-xs text-[#6B7280]">
            Tautan selalu dibuka pada tab baru saat diklik pengunjung.
          </p>
        </div>
        {footer.social_links.map((item, index) => (
          <div
            key={`${item.platform || "social"}-${index}`}
            className="grid gap-2 border border-gray-100 bg-white p-4 sm:grid-cols-[0.8fr_1fr_1.7fr_auto]"
          >
            <select
              value={item.platform || "other"}
              onChange={(event) => updateSocial(index, "platform", event.target.value)}
              data-testid={`footer-social-platform-${index}`}
              className={inputClass}
            >
              {SOCIAL_PLATFORM_OPTIONS.map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
            <input
              value={item.label || ""}
              onChange={(event) => updateSocial(index, "label", event.target.value)}
              data-testid={`footer-social-label-${index}`}
              placeholder="Label tautan"
              className={inputClass}
            />
            <input
              value={item.url || ""}
              onChange={(event) => updateSocial(index, "url", event.target.value)}
              data-testid={`footer-social-url-${index}`}
              placeholder="https://..."
              className={inputClass}
            />
            <button
              type="button"
              onClick={() => onChange({
                ...footer,
                social_links: footer.social_links.filter((_, itemIndex) => itemIndex !== index),
              })}
              data-testid={`delete-footer-social-${index}`}
              aria-label={`Hapus tautan sosial ${item.label || index + 1}`}
              className="justify-self-end rounded-lg p-2.5 text-[#DC2626] transition-colors hover:bg-[#FEE2E2]"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        ))}
        <button
          type="button"
          onClick={() => onChange({
            ...footer,
            social_links: [
              ...footer.social_links,
              { platform: "other", label: "", url: "" },
            ],
          })}
          data-testid="add-footer-social"
          className="inline-flex items-center gap-2 rounded-lg border-2 border-dashed border-gray-200 px-4 py-2.5 text-sm font-bold text-[#6B7280] transition-colors hover:border-[#27AE60] hover:text-[#27AE60]"
        >
          <Plus className="h-4 w-4" /> Tambah Tautan Sosial
        </button>
      </section>

      <section className="space-y-3" data-testid="footer-contact-items-editor">
        <div>
          <h3 className="font-display text-base font-bold text-[#1F2937]">Hubungi Kami</h3>
          <label className="mt-3 block text-sm font-semibold text-[#1F2937]">
            Judul Bagian
            <input
              value={footer.contact.title}
              onChange={(event) => onChange({
                ...footer,
                contact: { ...footer.contact, title: event.target.value },
              })}
              data-testid="footer-contact-title"
              className={`${inputClass} mt-1.5`}
            />
          </label>
        </div>
        {footer.contact.items.map((item, index) => (
          <div key={`${item.type || "contact"}-${index}`} className="border border-gray-100 bg-white p-4">
            <div className="grid gap-2 sm:grid-cols-[0.8fr_1fr_auto]">
              <select
                value={item.type || "other"}
                onChange={(event) => updateContact(index, "type", event.target.value)}
                data-testid={`footer-contact-type-${index}`}
                className={inputClass}
              >
                {CONTACT_TYPE_OPTIONS.map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
              <input
                value={item.label || ""}
                onChange={(event) => updateContact(index, "label", event.target.value)}
                data-testid={`footer-contact-label-${index}`}
                placeholder="Label, misalnya Hotline Kampus"
                className={inputClass}
              />
              <button
                type="button"
                onClick={() => onChange({
                  ...footer,
                  contact: {
                    ...footer.contact,
                    items: footer.contact.items.filter((_, itemIndex) => itemIndex !== index),
                  },
                })}
                data-testid={`delete-footer-contact-${index}`}
                aria-label={`Hapus kontak ${item.label || index + 1}`}
                className="justify-self-end rounded-lg p-2.5 text-[#DC2626] transition-colors hover:bg-[#FEE2E2]"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
            <textarea
              value={item.value || ""}
              onChange={(event) => updateContact(index, "value", event.target.value)}
              data-testid={`footer-contact-value-${index}`}
              placeholder="Isi informasi kontak"
              rows={2}
              className={`${inputClass} mt-2 resize-y`}
            />
            <label className="mt-2 block text-xs font-semibold text-[#6B7280]">
              Tautan aksi (opsional)
              <input
                value={item.url || ""}
                onChange={(event) => updateContact(index, "url", event.target.value)}
                data-testid={`footer-contact-url-${index}`}
                placeholder="https://..., mailto:..., atau tel:..."
                className={`${inputClass} mt-1.5`}
              />
            </label>
          </div>
        ))}
        <button
          type="button"
          onClick={() => onChange({
            ...footer,
            contact: {
              ...footer.contact,
              items: [
                ...footer.contact.items,
                { type: "other", label: "", value: "", url: "" },
              ],
            },
          })}
          data-testid="add-footer-contact"
          className="inline-flex items-center gap-2 rounded-lg border-2 border-dashed border-gray-200 px-4 py-2.5 text-sm font-bold text-[#6B7280] transition-colors hover:border-[#27AE60] hover:text-[#27AE60]"
        >
          <Plus className="h-4 w-4" /> Tambah Kontak
        </button>
      </section>

      <button
        type="button"
        onClick={onSave}
        disabled={saving}
        data-testid="save-footer-contact-content"
        className="inline-flex items-center gap-2 rounded-xl bg-[#27AE60] px-5 py-3 text-sm font-bold text-white transition-colors hover:bg-[#0B6B3A] disabled:opacity-60"
      >
        <Save className="h-4 w-4" />
        {saving ? "Menyimpan..." : "Simpan Footer & Kontak"}
      </button>
    </div>
  );
}