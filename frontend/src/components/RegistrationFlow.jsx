import React, { useEffect, useState } from "react";
import { ArrowDown, ArrowRight } from "lucide-react";

export default function RegistrationFlow({ steps = [] }) {
  const [activeIndex, setActiveIndex] = useState(0);
  const safeIndex = Math.min(activeIndex, Math.max(steps.length - 1, 0));
  const activeStep = steps[safeIndex];

  useEffect(() => {
    if (activeIndex >= steps.length) setActiveIndex(0);
  }, [activeIndex, steps.length]);

  if (!steps.length) return null;

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
            const rowEnd = (index + 1) % 3 === 0;
            const isActive = safeIndex === index;
            return (
              <div key={`${step.title}-${index}`} className="relative">
                <button
                  type="button"
                  onMouseEnter={() => setActiveIndex(index)}
                  onFocus={() => setActiveIndex(index)}
                  onClick={() => setActiveIndex(index)}
                  data-testid={`registration-flow-step-${index + 1}`}
                  aria-pressed={isActive}
                  className={`group relative min-h-28 w-full overflow-hidden rounded-2xl border px-6 py-6 text-left shadow-lg transition-[background-color,border-color,transform] duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F2C94C] focus-visible:ring-offset-2 focus-visible:ring-offset-[#08743D] ${isActive ? "border-[#F2C94C]/80 bg-[#2E965D] -translate-y-1" : "border-white/25 bg-white/10 hover:bg-white/15 hover:-translate-y-1"}`}
                >
                  <span className="absolute right-5 top-2 font-display text-5xl font-black text-white/10 sm:text-6xl">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <span className="relative block max-w-[80%] font-display text-lg font-bold leading-snug text-white">
                    {step.title}
                  </span>
                </button>

                {!isLast && !rowEnd && (
                  <span
                    className="absolute left-1/2 top-full z-10 flex h-8 w-8 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-[#F2C94C]/60 bg-[#08743D] text-[#F2C94C] lg:left-auto lg:-right-10 lg:top-1/2 lg:translate-x-0"
                    aria-hidden="true"
                    data-testid={`registration-flow-arrow-${index + 1}`}
                  >
                    <ArrowDown className="h-4 w-4 lg:hidden" />
                    <ArrowRight className="hidden h-4 w-4 lg:block" />
                  </span>
                )}
                {!isLast && rowEnd && (
                  <span
                    className="absolute bottom-[-36px] left-1/2 z-10 flex h-8 w-8 -translate-x-1/2 items-center justify-center rounded-full border border-[#F2C94C]/60 bg-[#08743D] text-[#F2C94C]"
                    aria-hidden="true"
                    data-testid={`registration-flow-arrow-${index + 1}`}
                  >
                    <ArrowDown className="h-4 w-4" />
                  </span>
                )}
              </div>
            );
          })}
        </div>

        <div
          className="mt-12 min-h-28 border-t border-white/20 bg-[#065F32] px-6 py-6 text-left shadow-inner transition-[opacity,transform] duration-200 sm:px-8"
          data-testid="registration-flow-description"
          aria-live="polite"
        >
          <div className="flex flex-col gap-2 sm:flex-row sm:items-baseline sm:gap-4">
            <p className="shrink-0 text-xs font-bold uppercase tracking-[0.16em] text-[#F2C94C]">
              Tahap {String(safeIndex + 1).padStart(2, "0")}
            </p>
            <h3 className="font-display text-xl font-bold text-white">{activeStep.title}</h3>
          </div>
          <p className="mt-3 max-w-5xl text-sm leading-relaxed text-white/80 sm:text-base">
            {activeStep.desc || "Keterangan tahapan akan diperbarui melalui Kelola Website."}
          </p>
        </div>
      </div>
    </section>
  );
}