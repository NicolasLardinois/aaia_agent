// Konfidenz (0..1) als ganze Prozent fuer die Anzeige; defensiv geclamped.
export function formatConfidence(value: number): string {
  const clamped = Math.max(0, Math.min(1, value));
  return `${Math.round(clamped * 100)} %`;
}

// Deutsche Zahlenformatierung (AGENTS.md §0: UI durchgehend Deutsch): Komma als Dezimal-,
// Punkt als Tausendertrenner (z. B. 30.5 -> "30,5", 238000 -> "238.000"). Ohne fractionDigits
// werden bis zu 3 Nachkommastellen ohne unnoetige Nullen gezeigt; mit fractionDigits exakt diese
// Anzahl (z. B. Hebel auf 1 Stelle: formatNumber(33.27, 1) -> "33,3").
export function formatNumber(value: number, fractionDigits?: number): string {
  const opts: Intl.NumberFormatOptions =
    fractionDigits === undefined
      ? { maximumFractionDigits: 3 }
      : { minimumFractionDigits: fractionDigits, maximumFractionDigits: fractionDigits };
  return new Intl.NumberFormat("de-DE", opts).format(value);
}

// Vorzeichenbehaftete Anzeige (Roll-Yield, Saisonalitaet): Vorzeichen explizit als ASCII +/-
// (deterministisch, locale-unabhaengig), Betrag deutsch formatiert. 0 ohne Vorzeichen.
// Beispiel: formatSigned(-3.1) -> "-3,1", formatSigned(1.2) -> "+1,2".
export function formatSigned(value: number, fractionDigits?: number): string {
  const sign = value > 0 ? "+" : value < 0 ? "-" : "";
  return `${sign}${formatNumber(Math.abs(value), fractionDigits)}`;
}
