// Pure Begriff→Erklärung-Quelle. Eine Quelle für InfoTip-Tooltips und eine
// spätere Glossar-Seite (Teil-Projekt B). Erklärungen kurz + auf Deutsch.
const ENTRIES: Record<string, string> = {
  "Top-Down": "Analyse von oben nach unten: zuerst das große Bild (Konjunktur, Zinsen, Inflation), das den Rahmen für einzelne Anlagen setzt.",
  "Bottom-Up": "Analyse von unten nach oben: die Tiefenprüfung eines einzelnen Titels (Bewertung, Qualität, Bilanz) unabhängig vom Gesamtmarkt.",
  "Regime": "Die aktuelle Großwetterlage am Markt (z. B. Aufschwung, Abschwung, Rezession), abgeleitet aus Makro-Daten.",
  "Urteil": "Die Zusammenführung von Top-Down und Bottom-Up zu einer Gesamteinschätzung pro Anlage.",
  "Demo-Daten": "Beispielwerte, die echte Daten nachstellen, solange die echte Quelle noch nicht angebunden ist — am Etikett erkennbar.",
  "Long-Short": "AAIA beurteilt jeden Titel durch zwei gleichwertige Linsen: die Long-Sicht (lohnt sich der Kauf?) und die Short-Sicht (lohnt sich die Wette auf einen Fall?). Grundsatz: Ein Short ist nicht das Spiegelbild eines Longs — „teuer“ allein reicht nie, es braucht einen echten Grund zu fallen plus einen Katalysator.",
  "Total-Return": "Gesamtrendite einer Anlage = Kursveränderung + laufende Erträge (Dividenden, Zinsen/Kupons), im Gegensatz zum reinen Price Return (nur Kurs). Als Denkhaltung: Ertrag in beide Marktrichtungen anstreben — steigend (long) wie fallend (short).",
  "Exposure": "Wie stark dein Kapital insgesamt im Markt steckt (brutto = Summe aller Positionen, netto = long minus short).",
  // Deep-Dive-Aktienkennzahlen (Teil-Projekt B1) — etablierte Definitionen.
  "KGV": "Kurs-Gewinn-Verhältnis: Aktienkurs ÷ Gewinn je Aktie. Wie viele Jahresgewinne man zahlt; niedriger = günstiger bewertet.",
  "Forward-KGV": "KGV auf Basis des für die nächsten 12 Monate erwarteten Gewinns (statt des vergangenen).",
  "Shiller-CAPE": "Zyklisch bereinigtes KGV: Kurs ÷ durchschnittlicher, inflationsbereinigter Gewinn der letzten 10 Jahre — glättet Konjunkturzyklen.",
  "PEG": "KGV geteilt durch das erwartete Gewinnwachstum (in %). Um 1 gilt als fair, deutlich über 1 als teuer.",
  "EV/EBITDA": "Unternehmenswert (Marktkapitalisierung + Nettoschulden) ÷ operatives Ergebnis vor Abschreibungen — kapitalstrukturneutrale Bewertung.",
  "EV/Umsatz": "Unternehmenswert ÷ Jahresumsatz — nützlich, wenn der Gewinn (noch) niedrig ist.",
  "KBV": "Kurs-Buchwert-Verhältnis: Kurs ÷ bilanzieller Buchwert je Aktie.",
  "KUV": "Kurs-Umsatz-Verhältnis: Kurs ÷ Umsatz je Aktie.",
  "P/FCF": "Kurs ÷ freier Cashflow je Aktie — Bewertung am tatsächlich erwirtschafteten Geld.",
  "Dividendenrendite": "Jährliche Dividende ÷ Kurs, in %. Die laufende Ausschüttungsrendite.",
  "WACC": "Gewichtete durchschnittliche Kapitalkosten — Mindestrendite über Eigen- und Fremdkapital, die das Unternehmen verdienen muss.",
  "ROIC": "Return on Invested Capital: operativer Gewinn nach Steuern ÷ eingesetztes Kapital. Über dem WACC = wertschaffend.",
  "Bruttomarge": "Bruttogewinn (Umsatz minus Herstellkosten) ÷ Umsatz, in %.",
  "Operative Marge": "Operatives Ergebnis (EBIT) ÷ Umsatz, in % — Profitabilität des Kerngeschäfts.",
  "Umsatzwachstum": "Jährliches Umsatzwachstum, hier als 3-Jahres-Durchschnitt (CAGR), in %.",
  "Verschuldungsgrad": "Fremdkapital ÷ Eigenkapital. Höher = stärker fremdfinanziert und damit riskanter.",
  "Altman-Z": "Altman-Z-Score: aus mehreren Bilanzgrößen gebildete Kennzahl zur Insolvenzgefahr. Höher = geringeres Insolvenzrisiko (Schwellen je nach Sektor).",
  "Short-Interest": "Anteil der frei handelbaren Aktien, der leerverkauft ist, in %. Hoch = viele wetten auf fallende Kurse.",
  "Moat": "Wirtschaftlicher Burggraben (Buffett): dauerhafter Wettbewerbsvorteil, der Konkurrenz fernhält (breit / schmal / keiner).",
};

export function glossaryLookup(term: string): string | null {
  return ENTRIES[term] ?? null;
}
