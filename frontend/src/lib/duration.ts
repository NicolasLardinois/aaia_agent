// Zinsrisiko aus Modified Duration (= ungefaehre %-Kursaenderung je 1 %-Punkt Renditeaenderung).
// Lueckenlose Baender: <3 J = niedrig, [3,7) = mittel, >=7 = hoch (laengere Duration -> hoehere
// Zinssensitivitaet). null = UNAVAILABLE (nie 0). Quelle: Bond-Duration (Macaulay/Modified).
export function durationRisk(
  modifiedDuration: number | null,
): { level: "niedrig" | "mittel" | "hoch" | "unbekannt"; note: string } {
  if (modifiedDuration === null) return { level: "unbekannt", note: "Duration nicht verfügbar" };
  if (modifiedDuration < 3) return { level: "niedrig", note: "geringe Zinssensitivität" };
  if (modifiedDuration < 7) return { level: "mittel", note: "moderate Zinssensitivität" };
  return { level: "hoch", note: "hohe Zinssensitivität" };
}
