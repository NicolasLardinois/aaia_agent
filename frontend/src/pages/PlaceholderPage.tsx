// Generische Platzhalter-Seite fuer Bereiche, die spaetere Slices fuellen.
export function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="rounded-lg border border-dashed border-slate-300 p-8 text-center text-slate-500 dark:border-slate-700">
      <h2 className="text-lg font-semibold">{title}</h2>
      <p className="mt-1 text-sm">Dieser Bereich wird in einem folgenden Slice gebaut.</p>
    </div>
  );
}
