// Einheitlicher Karten-Container (die "ausgewogene" Designsprache an einem Ort).
import type { ReactNode } from "react";

export function SectionCard({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
      <h3 className="text-base font-semibold">{title}</h3>
      {subtitle && <p className="mt-0.5 text-sm text-slate-500">{subtitle}</p>}
      <div className="mt-3">{children}</div>
    </section>
  );
}
