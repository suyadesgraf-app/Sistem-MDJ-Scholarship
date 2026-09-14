import React, { useEffect, useMemo, useRef, useState } from "react";
import { Building2, Check, ChevronsUpDown, Search } from "lucide-react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

export default function CampusSelector({
  campuses,
  fieldKey,
  isOther,
  onChange,
  onSelectOther,
  value,
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const searchInputRef = useRef(null);

  const selectedCampus = campuses.find((campus) => (
    campus.name.trim().toLowerCase() === String(value || "").trim().toLowerCase()
  ));

  const filteredCampuses = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) {
      return campuses;
    }
    return campuses.filter((campus) => (
      `${campus.name} ${campus.code || ""}`.toLowerCase().includes(normalizedQuery)
    ));
  }, [campuses, query]);

  useEffect(() => {
    if (open) {
      window.setTimeout(() => searchInputRef.current?.focus(), 0);
      return;
    }
    setQuery("");
  }, [open]);

  const selectCampus = (campus) => {
    onChange(campus.name);
    setOpen(false);
  };

  const selectOther = () => {
    onSelectOther();
    setOpen(false);
  };

  const triggerLabel = isOther
    ? (value || "Kampus Lainnya")
    : (selectedCampus
      ? `${selectedCampus.name}${selectedCampus.code ? ` — ${selectedCampus.code}` : ""}`
      : "Pilih kampus terdaftar...");

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          data-testid={`field-${fieldKey}`}
          aria-expanded={open}
          className={[
            "flex w-full items-center justify-between gap-3 rounded-xl border border-gray-300",
            "bg-white px-4 py-2.5 text-left text-sm outline-none transition-colors",
            "focus:border-transparent focus:ring-2 focus:ring-[#27AE60]",
          ].join(" ")}
        >
          <span
            className={[
              "min-w-0 truncate",
              selectedCampus || isOther ? "text-[#1F2937]" : "text-[#9CA3AF]",
            ].join(" ")}
          >
            {triggerLabel}
          </span>
          <ChevronsUpDown className="h-4 w-4 shrink-0 text-[#0B6B3A]" />
        </button>
      </PopoverTrigger>
      <PopoverContent
        align="start"
        sideOffset={6}
        data-testid={`field-${fieldKey}-campus-popover`}
        className={[
          "w-[var(--radix-popover-trigger-width)] min-w-[18rem] overflow-hidden rounded-xl",
          "border border-[#B7E8CA] bg-white p-0 shadow-xl shadow-[#0B6B3A]/10",
        ].join(" ")}
      >
        <div className="border-b border-gray-100 p-3">
          <label className="sr-only" htmlFor={`field-${fieldKey}-campus-search`}>
            Cari kampus terdaftar
          </label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#6B7280]" />
            <input
              ref={searchInputRef}
              id={`field-${fieldKey}-campus-search`}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              data-testid={`field-${fieldKey}-campus-search`}
              placeholder="Cari nama atau kode kampus..."
              className={[
                "w-full rounded-lg border border-gray-200 py-2.5 pl-9 pr-3 text-sm outline-none",
                "focus:border-transparent focus:ring-2 focus:ring-[#27AE60]",
              ].join(" ")}
            />
          </div>
        </div>
        <div
          data-testid={`field-${fieldKey}-campus-options`}
          className="max-h-56 overflow-y-auto p-1.5"
        >
          {filteredCampuses.length ? (
            filteredCampuses.map((campus) => {
              const selected = selectedCampus?.id === campus.id && !isOther;
              const label = `${campus.name}${campus.code ? ` — ${campus.code}` : ""}`;

              return (
                <button
                  key={campus.id}
                  type="button"
                  onClick={() => selectCampus(campus)}
                  data-testid={`field-${fieldKey}-campus-option-${campus.id}`}
                  className={[
                    "flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2.5 " +
                    "text-left",
                    "text-sm transition-colors hover:bg-[#F0FBF5] focus:bg-[#F0FBF5]",
                    selected ? "bg-[#E8F6EE] font-semibold text-[#0B6B3A]" : "text-[#1F2937]",
                  ].join(" ")}
                >
                  <span className="min-w-0 truncate">{label}</span>
                  {selected && <Check className="h-4 w-4 shrink-0" />}
                </button>
              );
            })
          ) : (
            <p
              data-testid={`field-${fieldKey}-campus-empty-state`}
              className="px-3 py-7 text-center text-sm text-[#6B7280]"
            >
              Kampus tidak ditemukan.
            </p>
          )}
        </div>
        <div className="border-t border-gray-100 bg-white p-1.5">
          <button
            type="button"
            onClick={selectOther}
            data-testid={`field-${fieldKey}-other-option`}
            className={[
              "flex w-full items-center gap-3 rounded-lg bg-[#F0FBF5] px-3 py-2.5 text-left",
              "text-sm font-bold text-[#0B6B3A] transition-colors hover:bg-[#DDF8E8]",
              "focus:bg-[#DDF8E8]",
            ].join(" ")}
          >
            <Building2 className="h-4 w-4 shrink-0" />
            Kampus Lainnya
          </button>
        </div>
      </PopoverContent>
    </Popover>
  );
}