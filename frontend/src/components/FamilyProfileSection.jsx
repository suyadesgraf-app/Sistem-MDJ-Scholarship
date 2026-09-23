import React from "react";
import { UsersRound } from "lucide-react";

const INPUT_CLASS = [
  "w-full rounded-xl border border-gray-300 px-4 py-2.5 text-sm",
  "focus:border-transparent focus:outline-none focus:ring-2 focus:ring-[#27AE60]",
].join(" ");

const PARENT_STATUS_OPTIONS = [
  ["hidup", "Hidup"],
  ["meninggal", "Meninggal"],
];

const JOB_OPTIONS = [
  "PNS",
  "TNI / Polri",
  "Pegawai Swasta",
  "Wiraswasta",
  "Buruh",
  "Petani / Nelayan",
  "Ibu Rumah Tangga",
  "Tidak Bekerja",
  "Pensiunan",
  "Lainnya",
];

const RELATION_OPTIONS = [
  "Kakak",
  "Adik",
  "Kakek / Nenek",
  "Paman / Bibi",
  "Saudara Lainnya",
];

const EDUCATION_OPTIONS = [
  "Tidak / Belum Sekolah",
  "SD",
  "SMP",
  "SMA / SMK",
  "D1 / D2 / D3",
  "D4 / S1",
  "S2",
  "S3",
];

const ELECTRICITY_OPTIONS = [
  "450 VA",
  "900 VA",
  "1.300 VA",
  "2.200 VA",
  "3.500 VA",
  "> 3.500 VA",
];

const PARENT_FIELDS = [
  ["name", "Nama Lengkap"],
  ["nik", "NIK"],
  ["status", "Status Orang Tua"],
  ["phone", "Nomor HP"],
  ["job", "Pekerjaan"],
  ["income", "Penghasilan / Bulan"],
];

const MEMBER_FIELDS = [
  ["name", "Nama Lengkap"],
  ["nik", "NIK"],
  ["relationship", "Hubungan"],
  ["education", "Pendidikan Terakhir"],
  ["job", "Pekerjaan"],
  ["income", "Penghasilan / Bulan"],
];

const EMPTY_PARENT = {
  name: "",
  nik: "",
  status: "",
  phone: "",
  job: "",
  income: "",
};

const EMPTY_MEMBER = {
  name: "",
  nik: "",
  relationship: "",
  education: "",
  job: "",
  income: "",
};

const hasValue = (value) => String(value ?? "").trim() !== "";

export const parseFamilyCount = (value) => {
  const parsed = Number.parseInt(String(value ?? ""), 10);
  if (Number.isNaN(parsed)) return 0;
  return Math.max(0, Math.min(parsed, 15));
};

export const normalizeFamilyState = (family) => {
  const source = family && typeof family === "object" ? family : {};
  const count = parseFamilyCount(source.otherMemberCount);
  const members = Array.isArray(source.otherMembers) ? source.otherMembers : [];
  return {
    father: { ...EMPTY_PARENT, ...(source.father || {}) },
    mother: { ...EMPTY_PARENT, ...(source.mother || {}) },
    otherMemberCount: source.otherMemberCount ?? "",
    otherMembers: Array.from(
      { length: count },
      (_, index) => ({ ...EMPTY_MEMBER, ...(members[index] || {}) }),
    ),
    electricityPower: source.electricityPower || "",
  };
};

export const getMissingFamilyFields = (data = {}) => {
  const family = normalizeFamilyState(data.family);
  const missing = [];
  [
    ["father", "Ayah"],
    ["mother", "Ibu"],
  ].forEach(([parentKey, parentLabel]) => {
    PARENT_FIELDS.forEach(([key, label]) => {
      if (!hasValue(family[parentKey][key])) {
        missing.push({ k: `family.${parentKey}.${key}`, l: `${label} ${parentLabel}` });
      }
    });
  });
  if (!hasValue(family.otherMemberCount)) {
    missing.push({ k: "family.otherMemberCount", l: "Jumlah Anggota Keluarga Lain" });
  }
  family.otherMembers.forEach((member, index) => {
    MEMBER_FIELDS.forEach(([key, label]) => {
      if (!hasValue(member[key])) {
        missing.push({
          k: `family.otherMembers.${index}.${key}`,
          l: `${label} Anggota Keluarga ${index + 1}`,
        });
      }
    });
  });
  if (!hasValue(family.electricityPower)) {
    missing.push({ k: "family.electricityPower", l: "Daya Listrik Rumah" });
  }
  return missing;
};

export const getFamilyRequiredFieldCount = (data = {}) => {
  const count = parseFamilyCount(data.family?.otherMemberCount);
  return (PARENT_FIELDS.length * 2) + 2 + (MEMBER_FIELDS.length * count);
};

const formatRupiah = (value) => String(value || "").replace(/\B(?=(\d{3})+(?!\d))/g, ".");

function FieldLabel({ children, htmlFor }) {
  return (
    <label htmlFor={htmlFor} className="mb-1.5 block text-sm font-semibold text-[#1F2937]">
      {children} <span className="text-[#DC2626]">*</span>
    </label>
  );
}

function ParentForm({ id, label, value, onChange }) {
  const prefix = `family-${id}`;
  const setField = (key, nextValue) => onChange({ ...value, [key]: nextValue });
  return (
    <div
      className="rounded-xl border border-gray-100 bg-[#F9FAFB] p-5"
      data-testid={`${prefix}-card`}
    >
      <h4 className="font-display text-base font-bold text-[#1F2937]">Data {label}</h4>
      <div className="mt-4 grid gap-x-5 gap-y-4 sm:grid-cols-2">
        <div>
          <FieldLabel htmlFor={`${prefix}-name`}>Nama Lengkap</FieldLabel>
          <input
            id={`${prefix}-name`}
            value={value.name}
            onChange={(event) => setField("name", event.target.value)}
            placeholder={`Nama lengkap ${label.toLowerCase()}`}
            data-testid={`${prefix}-name`}
            className={INPUT_CLASS}
          />
        </div>
        <div>
          <FieldLabel htmlFor={`${prefix}-nik`}>NIK</FieldLabel>
          <input
            id={`${prefix}-nik`}
            inputMode="numeric"
            maxLength={16}
            value={value.nik}
            onChange={(event) => setField("nik", event.target.value.replace(/\D/g, ""))}
            placeholder="16 digit NIK"
            data-testid={`${prefix}-nik`}
            className={INPUT_CLASS}
          />
        </div>
        <div>
          <FieldLabel htmlFor={`${prefix}-status`}>Status Orang Tua</FieldLabel>
          <select
            id={`${prefix}-status`}
            value={value.status}
            onChange={(event) => setField("status", event.target.value)}
            data-testid={`${prefix}-status`}
            className={`${INPUT_CLASS} bg-white`}
          >
            <option value="">Pilih status...</option>
            {PARENT_STATUS_OPTIONS.map(([optionValue, optionLabel]) => (
              <option key={optionValue} value={optionValue}>{optionLabel}</option>
            ))}
          </select>
        </div>
        <div>
          <FieldLabel htmlFor={`${prefix}-phone`}>Nomor HP</FieldLabel>
          <input
            id={`${prefix}-phone`}
            inputMode="tel"
            value={value.phone}
            onChange={(event) => setField("phone", event.target.value)}
            placeholder="Contoh: 08123456789"
            data-testid={`${prefix}-phone`}
            className={INPUT_CLASS}
          />
        </div>
        <div>
          <FieldLabel htmlFor={`${prefix}-job`}>Pekerjaan</FieldLabel>
          <select
            id={`${prefix}-job`}
            value={value.job}
            onChange={(event) => setField("job", event.target.value)}
            data-testid={`${prefix}-job`}
            className={`${INPUT_CLASS} bg-white`}
          >
            <option value="">Pilih pekerjaan...</option>
            {JOB_OPTIONS.map((option) => <option key={option} value={option}>{option}</option>)}
          </select>
        </div>
        <div>
          <FieldLabel htmlFor={`${prefix}-income`}>Penghasilan / Bulan</FieldLabel>
          <div className="relative">
            <span
              className={[
                "pointer-events-none absolute inset-y-0 left-0 flex items-center px-4 text-sm",
                "font-bold text-[#0B6B3A]",
              ].join(" ")}
            >
              Rp
            </span>
            <input
              id={`${prefix}-income`}
              inputMode="numeric"
              value={formatRupiah(value.income)}
              onChange={(event) => {
                setField("income", event.target.value.replace(/\D/g, ""));
              }}
              placeholder="0"
              data-testid={`${prefix}-income`}
              className={`${INPUT_CLASS} pl-11`}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function OtherMemberForm({ index, value, onChange }) {
  const prefix = `family-member-${index}`;
  const setField = (key, nextValue) => onChange({ ...value, [key]: nextValue });
  return (
    <div className="border border-gray-100 bg-white p-4" data-testid={`${prefix}-card`}>
      <p className="mb-4 text-sm font-bold text-[#1F2937]">Anggota Keluarga {index + 1}</p>
      <div className="grid gap-x-5 gap-y-4 sm:grid-cols-2 lg:grid-cols-3">
        <div>
          <FieldLabel htmlFor={`${prefix}-name`}>Nama Lengkap</FieldLabel>
          <input
            id={`${prefix}-name`}
            value={value.name}
            onChange={(event) => setField("name", event.target.value)}
            data-testid={`${prefix}-name`}
            className={INPUT_CLASS}
          />
        </div>
        <div>
          <FieldLabel htmlFor={`${prefix}-nik`}>NIK</FieldLabel>
          <input
            id={`${prefix}-nik`}
            inputMode="numeric"
            maxLength={16}
            value={value.nik}
            onChange={(event) => setField("nik", event.target.value.replace(/\D/g, ""))}
            data-testid={`${prefix}-nik`}
            className={INPUT_CLASS}
          />
        </div>
        <div>
          <FieldLabel htmlFor={`${prefix}-relationship`}>Hubungan</FieldLabel>
          <select
            id={`${prefix}-relationship`}
            value={value.relationship}
            onChange={(event) => setField("relationship", event.target.value)}
            data-testid={`${prefix}-relationship`}
            className={`${INPUT_CLASS} bg-white`}
          >
            <option value="">Pilih hubungan...</option>
            {RELATION_OPTIONS.map((option) => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
        </div>
        <div>
          <FieldLabel htmlFor={`${prefix}-education`}>Pendidikan Terakhir</FieldLabel>
          <select
            id={`${prefix}-education`}
            value={value.education}
            onChange={(event) => setField("education", event.target.value)}
            data-testid={`${prefix}-education`}
            className={`${INPUT_CLASS} bg-white`}
          >
            <option value="">Pilih pendidikan...</option>
            {EDUCATION_OPTIONS.map((option) => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
        </div>
        <div>
          <FieldLabel htmlFor={`${prefix}-job`}>Pekerjaan</FieldLabel>
          <select
            id={`${prefix}-job`}
            value={value.job}
            onChange={(event) => setField("job", event.target.value)}
            data-testid={`${prefix}-job`}
            className={`${INPUT_CLASS} bg-white`}
          >
            <option value="">Pilih pekerjaan...</option>
            {JOB_OPTIONS.map((option) => <option key={option} value={option}>{option}</option>)}
          </select>
        </div>
        <div>
          <FieldLabel htmlFor={`${prefix}-income`}>Penghasilan / Bulan</FieldLabel>
          <div className="relative">
            <span
              className={[
                "pointer-events-none absolute inset-y-0 left-0 flex items-center px-4 text-sm",
                "font-bold text-[#0B6B3A]",
              ].join(" ")}
            >
              Rp
            </span>
            <input
              id={`${prefix}-income`}
              inputMode="numeric"
              value={formatRupiah(value.income)}
              onChange={(event) => {
                setField("income", event.target.value.replace(/\D/g, ""));
              }}
              placeholder="0"
              data-testid={`${prefix}-income`}
              className={`${INPUT_CLASS} pl-11`}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default function FamilyProfileSection({ data, setData }) {
  const family = normalizeFamilyState(data.family);

  const updateFamily = (updater) => {
    setData((previous) => ({
      ...previous,
      family: updater(normalizeFamilyState(previous.family)),
    }));
  };

  const setParent = (parentKey, parent) => updateFamily((current) => ({
    ...current,
    [parentKey]: parent,
  }));

  const setMember = (index, member) => updateFamily((current) => ({
    ...current,
    otherMembers: current.otherMembers.map((item, itemIndex) => (
      itemIndex === index ? member : item
    )),
  }));

  const setMemberCount = (rawValue) => {
    const count = parseFamilyCount(rawValue);
    updateFamily((current) => ({
      ...current,
      otherMemberCount: rawValue,
      otherMembers: Array.from(
        { length: count },
        (_, index) => ({ ...EMPTY_MEMBER, ...(current.otherMembers[index] || {}) }),
      ),
    }));
  };

  return (
    <div className="space-y-6" data-testid="family-profile-section">
      <div className="flex items-start gap-3 border-l-4 border-[#27AE60] bg-[#F0FBF5] px-4 py-4">
        <UsersRound className="mt-0.5 h-5 w-5 shrink-0 text-[#0B6B3A]" />
        <div>
          <h3 className="font-display text-lg font-bold text-[#1F2937]">Data Keluarga</h3>
          <p className="mt-1 text-sm text-[#6B7280]">
            Isi data keluarga berdasarkan informasi terakhir yang diketahui. Semua kolom bertanda
            bintang wajib diisi.
          </p>
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <ParentForm
          id="father"
          label="Ayah"
          value={family.father}
          onChange={(parent) => setParent("father", parent)}
        />
        <ParentForm
          id="mother"
          label="Ibu"
          value={family.mother}
          onChange={(parent) => setParent("mother", parent)}
        />
      </div>

      <div className="bg-white p-6 shadow-[0_4px_20px_-2px_rgba(39,174,96,0.05)]">
        <div className="max-w-sm">
          <FieldLabel htmlFor="family-other-member-count">Jumlah Anggota Keluarga Lain</FieldLabel>
          <input
            id="family-other-member-count"
            type="number"
            min="0"
            max="15"
            inputMode="numeric"
            value={family.otherMemberCount}
            onChange={(event) => setMemberCount(event.target.value.replace(/\D/g, ""))}
            placeholder="Contoh: 2"
            data-testid="family-other-member-count"
            className={INPUT_CLASS}
          />
          <p className="mt-1 text-xs text-[#9CA3AF]">Maksimal 15 anggota selain ayah dan ibu.</p>
        </div>

        {family.otherMembers.length > 0 && (
          <div className="mt-6 space-y-4" data-testid="family-other-members-list">
            <h4 className="font-display text-base font-bold text-[#1F2937]">
              Anggota Keluarga Lain
            </h4>
            {family.otherMembers.map((member, index) => (
              <OtherMemberForm
                key={index}
                index={index}
                value={member}
                onChange={(nextMember) => setMember(index, nextMember)}
              />
            ))}
          </div>
        )}
      </div>

      <div className="max-w-md bg-white p-6 shadow-[0_4px_20px_-2px_rgba(39,174,96,0.05)]">
        <FieldLabel htmlFor="family-electricity-power">Daya Listrik Rumah</FieldLabel>
        <select
          id="family-electricity-power"
          value={family.electricityPower}
          onChange={(event) => updateFamily((current) => ({
            ...current,
            electricityPower: event.target.value,
          }))}
          data-testid="family-electricity-power"
          className={`${INPUT_CLASS} bg-white`}
        >
          <option value="">Pilih daya listrik...</option>
          {ELECTRICITY_OPTIONS.map((option) => (
            <option key={option} value={option}>{option}</option>
          ))}
        </select>
      </div>
    </div>
  );
}