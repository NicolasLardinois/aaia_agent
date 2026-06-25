// Generische Platzhalter-Seite fuer Bereiche, die spaetere Slices fuellen.
export function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="rounded-lg border border-dashed border-line p-8 text-center text-muted">
      <h2 className="text-lg font-semibold">{title}</h2>
      <p className="mt-1 text-sm">Dieser Bereich wird in einem folgenden Slice gebaut.</p>
    </div>
  );
}
