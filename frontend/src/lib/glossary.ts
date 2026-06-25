// Pure Begriff→Erklärung-Quelle. Eine Quelle für InfoTip-Tooltips und eine
// spätere Glossar-Seite (Teil-Projekt B). Erklärungen kurz + auf Deutsch.
const ENTRIES: Record<string, string> = {
  "Top-Down": "Analyse von oben nach unten: zuerst das große Bild (Konjunktur, Zinsen, Inflation), das den Rahmen für einzelne Anlagen setzt.",
  "Bottom-Up": "Analyse von unten nach oben: die Tiefenprüfung eines einzelnen Titels (Bewertung, Qualität, Bilanz) unabhängig vom Gesamtmarkt.",
  "Regime": "Die aktuelle Großwetterlage am Markt (z. B. Aufschwung, Abschwung, Rezession), abgeleitet aus Makro-Daten.",
  "Urteil": "Die Zusammenführung von Top-Down und Bottom-Up zu einer Gesamteinschätzung pro Anlage.",
  "Demo-Daten": "Beispielwerte, die echte Daten nachstellen, solange die echte Quelle noch nicht angebunden ist — am Etikett erkennbar.",
  "Exposure": "Wie stark dein Kapital insgesamt im Markt steckt (brutto = Summe aller Positionen, netto = long minus short).",
};

export function glossaryLookup(term: string): string | null {
  return ENTRIES[term] ?? null;
}
