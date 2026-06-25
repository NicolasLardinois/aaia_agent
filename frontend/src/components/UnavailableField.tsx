// Gestreift-graues Feld fuer UNAVAILABLE — eigener Zustand, nie neutral/0 (Spec §5.4).
export function UnavailableField({ reason }: { reason?: string }) {
  return (
    <span
      title={reason ?? "Datenquelle nicht verfügbar"}
      className="inline-block rounded px-2 py-0.5 text-sm text-muted
                 bg-[repeating-linear-gradient(45deg,rgb(var(--line)),rgb(var(--line))_4px,transparent_4px,transparent_8px)]"
    >
      nicht verfügbar
    </span>
  );
}
