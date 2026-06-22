// Konfidenz (0..1) als ganze Prozent fuer die Anzeige; defensiv geclamped.
export function formatConfidence(value: number): string {
  const clamped = Math.max(0, Math.min(1, value));
  return `${Math.round(clamped * 100)} %`;
}
