// Markiert eine Ansicht als aus Beispielwerten gespeist. Bei isDemo=false rendert es
// nichts -> beim Umstieg auf echte Daten verschwindet das Etikett automatisch (Spec §2.2).
export function DemoBadge({ isDemo }: { isDemo: boolean }) {
  if (!isDemo) return null;
  return (
    <span
      title="Diese Ansicht zeigt Demo-Daten, weil der echte Backend-Endpunkt noch fehlt."
      className="inline-flex items-center gap-1.5 rounded-full border border-line bg-surface-2 px-2 py-0.5 text-[11px] font-medium text-muted"
    >
      <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-brand" />
      Demo-Daten
    </span>
  );
}
