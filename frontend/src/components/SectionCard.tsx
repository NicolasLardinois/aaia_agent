// Einheitlicher Karten-Container (die "ausgewogene" Designsprache an einem Ort).
// Optionaler "eyebrow" = kleine Versal-Markierung über dem Titel (Struktur als Information).
import type { ReactNode } from "react";

export function SectionCard({
  title, subtitle, eyebrow, children,
}: { title: string; subtitle?: string; eyebrow?: string; children: ReactNode }) {
  return (
    <section className="rounded-panel border border-line bg-surface p-4 shadow-panel">
      {eyebrow && (
        <div className="mb-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-brand">{eyebrow}</div>
      )}
      <h3 className="font-display text-base font-semibold">{title}</h3>
      {subtitle && <p className="mt-0.5 text-sm text-muted">{subtitle}</p>}
      <div className="mt-3">{children}</div>
    </section>
  );
}
