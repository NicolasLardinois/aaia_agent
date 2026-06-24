// Markiert eine Ansicht als aus Beispielwerten gespeist. Bei isDemo=false rendert es
// nichts -> beim Umstieg auf echte Daten verschwindet das Etikett automatisch (Spec §2.2).
export function DemoBadge({ isDemo }: { isDemo: boolean }) {
  if (!isDemo) return null;
  return (
    <span
      title="Diese Ansicht zeigt Demo-Daten, weil der echte Backend-Endpunkt noch fehlt."
      className="inline-block rounded bg-violet-100 px-2 py-0.5 text-xs font-medium text-violet-700"
    >
      Demo-Daten
    </span>
  );
}
