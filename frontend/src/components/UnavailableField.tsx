// Gestreift-graues Feld fuer UNAVAILABLE — eigener Zustand, nie neutral/0 (Spec §5.4).
export function UnavailableField({ reason }: { reason?: string }) {
  return (
    <span
      title={reason ?? "Datenquelle nicht verfügbar"}
      className="inline-block rounded px-2 py-0.5 text-sm text-slate-500
                 bg-[repeating-linear-gradient(45deg,#e2e8f0,#e2e8f0_4px,#f1f5f9_4px,#f1f5f9_8px)]"
    >
      nicht verfügbar
    </span>
  );
}
