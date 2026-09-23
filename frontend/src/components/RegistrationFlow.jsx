import React, { useEffect, useState } from "react";
import { ArrowDown, ArrowRight } from "lucide-react";

const getDesktopPosition = (index) => {
  const row = Math.floor(index / 3);
  const positionInRow = index % 3;
  const column = row % 2 === 0 ? positionInRow : 2 - positionInRow;
  return {
    row,
    column,
    order: row * 3 + column + 1,
  };
};

const getDesktopDirection = (index) => {
  const current = getDesktopPosition(index);
  const next = getDesktopPosition(index + 1);
  if (next.row > current.row) return "down";
  return next.column > current.column ? "right" : "left";
};

const getTrailingPlaceholderOrders = (stepCount) => {
  if (!stepCount || stepCount % 3 === 0) return [];
  const row = Math.floor((stepCount - 1) / 3);
  if (row % 2 === 0) return [];
  const usedColumns = stepCount % 3;
  return Array.from(
    { length: 3 - usedColumns },
    (_, index) => row * 3 + index + 1,
  );
};

export default function RegistrationFlow({ steps = [] }) {
  const [isMobile, setIsMobile] = useState(() => window.innerWidth < 1024);
  const [activeIndex, setActiveIndex] = useState(() => (
    window.innerWidth < 1024 ? 0 : null
  ));

  useEffect(() => {
    const query = window.matchMedia("(max-width: 1023px)");
    const syncLayout = () => {
      setIsMobile(query.matches);
      if (query.matches) {
        setActiveIndex((current) => (
          current === null || current >= steps.length ? 0 : current
        ));
      }
    };
    syncLayout();
    query.addEventListener("change", syncLayout);
    return () => query.removeEventListener("change", syncLayout);
  }, [steps.length]);

  if (!steps.length) return null;

  const trailingPlaceholderOrders = getTrailingPlaceholderOrders(steps.length);

  return (
    <section id="alur" className="overflow-hidden bg-[#08743D] py-20 lg:py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-3xl text-center">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#F2C94C]">
            Proses Program
          </p>
          <h2 className="mt-3 font-display text-3xl font-extrabold text-white lg:text-4xl">
            Alur Pendaftaran
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-white/75 sm:text-base">
            Ikuti setiap tahapan Program Masa Depan Jakarta Scholarship secara berurutan.
          </p>
        </div>

        <div className="mt-12 grid gap-x-12 gap-y-12 lg:grid-cols-3" data-testid="registration-flow-grid">
          {steps.map((step, index) => {
            const isLast = index === steps.length - 1;
            const isActive = activeIndex === index;
            const direction = isLast ? null : getDesktopDirection(index);
            const desktopPosition = getDesktopPosition(index);
            return (
              <div
                key={`${step.title}-${index}`}
                style={{ "--desktop-order": desktopPosition.order }}
                className="relative lg:order-[var(--desktop-order)]"
                onMouseLeave={() => {
                  if (!isMobile) setActiveIndex(null);
                }}
              >
                <div className="relative">
                  <button
                    type="button"
                    onMouseEnter={() => setActiveIndex(index)}
                    onFocus={() => setActiveIndex(index)}
                    onClick={() => setActiveIndex(index)}
                    data-testid={`registration-flow-step-${index + 1}`}
                    aria-expanded={isActive}
                    className={`group relative min-h-28 w-full overflow-hidden rounded-2xl border px-6 py-6 text-left shadow-lg transition-[background-color,border-color,transform] duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F2C94C] focus-visible:ring-offset-2 focus-visible:ring-offset-[#08743D] ${isActive ? "border-[#F2C94C]/80 bg-[#2E965D] -translate-y-1" : "border-white/25 bg-white/10 hover:bg-white/15 hover:-translate-y-1"}`}
                  >
                    <span className="absolute right-5 top-2 font-display text-5xl font-black text-white/10 sm:text-6xl">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <span className="relative block max-w-[80%] font-display text-lg font-bold leading-snug text-white">
                      {step.title}
                    </span>
                    {isActive && (
                      <span
                        id={`registration-flow-dropdown-${index + 1}`}
                        className="relative mt-4 block border-t border-white/30 pt-4 text-sm leading-relaxed text-white animate-fade-up"
                        data-testid={`registration-flow-dropdown-${index + 1}`}
                        aria-live="polite"
                      >
                        {step.desc || "Keterangan tahapan akan diperbarui melalui Kelola Website."}
                      </span>
                    )}
                  </button>

                  {!isLast && direction !== "down" && (
                    <span
                      className={`absolute top-1/2 z-10 hidden h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full border border-[#F2C94C]/60 bg-[#08743D] text-[#F2C94C] lg:flex ${direction === "left" ? "-left-10" : "-right-10"}`}
                      aria-hidden="true"
                      data-testid={`registration-flow-arrow-${index + 1}`}
                    >
                      <ArrowRight className={`h-4 w-4 ${direction === "left" ? "rotate-180" : ""}`} />
                    </span>
                  )}
                </div>

                {!isLast && (
                  <span
                    className="absolute bottom-[-36px] left-1/2 z-10 flex h-8 w-8 -translate-x-1/2 items-center justify-center rounded-full border border-[#F2C94C]/60 bg-[#08743D] text-[#F2C94C] lg:hidden"
                    aria-hidden="true"
                    data-testid={`registration-flow-mobile-arrow-${index + 1}`}
                  >
                    <ArrowDown className="h-4 w-4" />
                  </span>
                )}
                {!isLast && direction === "down" && (
                  <span
                    className="absolute bottom-[-36px] left-1/2 z-10 hidden h-8 w-8 -translate-x-1/2 items-center justify-center rounded-full border border-[#F2C94C]/60 bg-[#08743D] text-[#F2C94C] lg:flex"
                    aria-hidden="true"
                    data-testid={`registration-flow-arrow-${index + 1}`}
                  >
                    <ArrowDown className="h-4 w-4" />
                  </span>
                )}
              </div>
            );
          })}
          {trailingPlaceholderOrders.map((order) => (
            <div
              key={`registration-flow-placeholder-${order}`}
              aria-hidden="true"
              style={{ "--desktop-order": order }}
              className="hidden lg:block lg:order-[var(--desktop-order)]"
            />
          ))}
        </div>
      </div>
    </section>
  );
}