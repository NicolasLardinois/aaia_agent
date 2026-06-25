// Eine Quelle für die Bereichs-Beschreibungen der Willkommen-Seite (Reihenfolge wie die Sidebar).
export interface AreaInfo {
  to: string;
  icon: string;
  name: string;
  question: string; // "Welche Frage beantwortet dieser Bereich?"
  howto: string;    // 1 Satz Bedienung
}

export const AREAS: AreaInfo[] = [
  { to: "/cockpit", icon: "▣", name: "Cockpit",
    question: "Wie ist die Großwetterlage am Markt?",
    howto: "Regime-Ampel + Domänen-Kacheln; ein Klick öffnet die jeweilige Detailseite." },
  { to: "/deep-dive", icon: "◆", name: "Deep-Dive",
    question: "Lohnt sich dieser eine Titel?",
    howto: "Oben einen Ticker suchen (z. B. AAPL) — Bewertung, Qualität und Urteil im Detail." },
  { to: "/portfolio", icon: "⬚", name: "Portfolio",
    question: "Wie steht mein Gesamtbestand da?",
    howto: "Exposure, Klumpenrisiken und Konflikte deiner Positionen auf einen Blick." },
  { to: "/inbox", icon: "✉", name: "Inbox",
    question: "Wo widerspricht ein neues Urteil meiner Position?",
    howto: "Konflikte mit beratendem Vorschlag — rein zur Notiz, ohne automatische Ausführung." },
  { to: "/backtester", icon: "↺", name: "Backtester",
    question: "Hätten die früheren Einschätzungen Geld gebracht?",
    howto: "Trefferquoten je Analyse-Bereich, rückblickend ausgewertet." },
];
