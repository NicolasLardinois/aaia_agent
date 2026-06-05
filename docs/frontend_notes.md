# Frontend Notes — AAIA Dashboard

Notizen aus der Entwicklungsphase, die beim Aufbau der Benutzeroberfläche berücksichtigt werden müssen.

---

## Buffett-Indikator Widget

### Daten, die das Backend liefert
- `BuffettIndicatorSnapshot.countries` — ca. 150 Länder (ISO-3-Kürzel → `BuffettCountryPoint`)
  - `ratio_pct`: aktueller Wert in % (Marktkapitalisierung / BIP × 100)
  - `signal`: BULLISH / NEUTRAL / BEARISH (basierend auf Schwellenwerten: <75 % = bullish, >135 % = bearish)
  - `year`: `None` = Echtzeit-FRED-Wert (USA); `int` = letztes verfügbares Weltbank-Jahr
  - `z_score`: aktueller Wert vs. eigene 10-Jahres-Geschichte (nur wenn ≥ 8 Datenpunkte vorhanden)
- `BuffettIndicatorSnapshot.global_median` — globaler Median über alle Länder
- USA-Daten kommen von FRED (Echtzeit, monatlich aktualisiert); alle anderen Länder von der Weltbank API (Jahreswerte, i.d.R. 1–2 Jahre Verzögerung)

### Anzeige im Dashboard
- Weltkarte oder sortierbare Tabelle mit allen ~150 Ländern
- Hervorhebung des analysierten Landes (wird aus dem `market`-Parameter der aktuellen Analyse übernommen)
- Globalen Median als Referenzlinie anzeigen
- Z-Score-Spalte: zeigt an, wie stark ein Land von seiner eigenen Geschichte abweicht (|Z| ≥ 1.5 = auffällig)
- Zeitstempel / Jahreszahl der Daten je Land anzeigen (wichtig wegen Weltbank-Verzögerung)
- Filter: nur Länder anzeigen mit Z-Score-Ausreisser, oder nur Länder mit BEARISH-Signal

### Erläuterung der Berechnung (Pflicht im Dashboard)
> **Buffett-Indikator = Gesamtmarktkapitalisierung aller börsennotierten Unternehmen ÷ Bruttoinlandsprodukt × 100**
>
> USA: Wilshire 5000 Total Market Index (FRED: `WILL5000INDFC`) ÷ BIP (FRED: `GDP`) × 100 — monatlich aktualisiert
>
> Alle anderen Länder: Weltbank-Datenserie `CM.MKT.LCAP.GD.ZS` (Market Capitalization of listed domestic companies, % of GDP) — Jahreswerte

### Einschränkungen — müssen sichtbar im Dashboard sein
1. **Globalisierung** — S&P 500-Unternehmen erwirtschaften einen Grossteil ihrer Gewinne ausserhalb der USA; das BIP misst aber nur die US-Wirtschaft → strukturell verzerrter Vergleich (Indikator tendiert zur Überbewertungsanzeige)
2. **Zinsniveau wird ignoriert** — bei 0 % Zinsen sind höhere Bewertungen rational; der Indikator kennt keinen Zinskontext
3. **Kein Timing-Tool** — kann jahrelang „überteuert" anzeigen, ohne dass der Markt fällt (z. B. USA 2016–2021)
4. **Aktienrückkäufe** — erhöhen die Marktkapitalisierung ohne realwirtschaftlichen Gegenwert und verzerren den Quotienten strukturell nach oben

### Asset-Klassen-Filter
- Nur relevant für: **Aktien, ETFs, Indizes**
- Nicht anzeigen / nicht hervorheben bei: Anleihen, Rohstoffe, Edelmetalle

---

## Big Mac Index Widget

### Konzept
- Adjustierter Big Mac Index: Vergleicht reale Kaufkraftparität zwischen Ländern, adjustiert für Einkommensniveaus
- Zeigt Währungsüber- oder -unterbewertung relativ zur Kaufkraftparität
- Datenquelle: The Economist (öffentlich verfügbar, halbjährlich aktualisiert)

### Anzeige
- Tabelle oder Balkendiagramm mit Ländern und % Über-/Unterbewertung vs. USD
- Für analysiertes Land hervorheben (Verbindung zur `market`-Auswahl)
- Datum der letzten Datenpublikation anzeigen (halbjährlich: Juli / Januar)

### Einschränkungen (optional im Dashboard)
- Nicht-handelsfähige Güter und Dienstleistungen stark gewichtet → nicht 1:1 auf Wechselkurse übertragbar
- Lokale Steuern, Subventionen und Franchise-Strukturen verzerren den Preis
- Nur für Länder verfügbar, in denen McDonald's präsent ist

---

## Allgemeine UI-Prinzipien (aus Architekturentscheidungen)

### Märkte / Länder
- **Keine "EU"-Aggregierung** — immer das spezifische Land angeben (DE, FR, IT, ES, ...)
- Eurozone-Länder werden einzeln ausgewiesen: DE, FR, IT, ES, NL, AT, BE, PT, FI, IE, GR, SK, SI, EE, LV, LT, LU, MT, CY
- Markt-Eingabe: `USA` / `CH` / ISO-2-Länderkürzel

### Konfidenz und Empfehlungen
- Konfidenz < 0.50 → automatisch HOLD (zu wenig Sicherheit)
- Konfidenz < 0.35 → zusätzlich Cash-Bias signalisieren
- Jede Empfehlung enthält eine XAI-Erklärung (welche Signale entscheidend waren, wo Widersprüche lagen)

### Anomalie-Anzeige
- Z-Score-basiert (|Z| > 2.0 = Anomalie)
- Getrennt: statistische Ausreisser vs. Signalwidersprüche (Top-Down und Bottom-Up separat)
- Schwere: none / low / medium / high

---

## Offene Entscheidungen (zu klären beim Frontend-Sprint)

- [ ] Weltkarte vs. Tabelle für Buffett-Indikator
- [ ] Drill-down: Einzelland-Zeitreihe (10 Jahre) im Buffett-Widget
- [ ] Big Mac Index: Halbjährliche Daten-Refresh-Strategie (manuelle Pflege vs. API)
- [ ] Mobile-first oder Desktop-first
- [ ] Framework-Wahl: React / Vue / Svelte (noch nicht entschieden)
- [ ] Echtzeit-Refresh: WebSocket oder Polling für Dashboard-Updates
