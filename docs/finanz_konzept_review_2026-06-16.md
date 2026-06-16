# Fachlich-finanzieller Konzept-Review (CFA-Perspektive)

**Datum:** 2026-06-16
**Scope:** Gesamtes Repository, ausschließlich fachlich-konzeptioneller Gehalt (Finanzkennzahlen, Bewertungsmethoden, Risikomodelle, Statistik) — **nicht** Code-Qualität, Architektur oder Stil.
**Bewertungsraster:** ✅ korrekt/Standard · ⚠️ funktioniert, aber verbesserungswürdig · ❌ fachlich falsch/irreführend

---

## Inhaltsverzeichnis

- [Struktureller Hauptbefund](#struktureller-hauptbefund)
- [Teil A — Befunde nach Domäne (mit Lösungsvorschlag je Punkt)](#teil-a--befunde-nach-domäne)
  - [Domäne 1 — Makro-Cockpit](#domäne-1--makro-cockpit)
  - [Domäne 2 — Commodity-Cockpit (Makro)](#domäne-2--commodity-cockpit-makro)
  - [Domäne 3 — Sentiment / Yield Curve / Sektor](#domäne-3--sentiment--yield-curve--sektor)
  - [Domäne 4 — Equity Deep Dive](#domäne-4--equity-deep-dive)
  - [Domäne 5 — Bond Deep Dive](#domäne-5--bond-deep-dive)
  - [Domäne 6 — Index Deep Dive](#domäne-6--index-deep-dive)
  - [Domäne 7 — Commodity & Precious Metals Deep Dive](#domäne-7--commodity--precious-metals-deep-dive)
  - [Domäne 8 — Core / Statistik / Judgment / Backtester / Portfolio](#domäne-8--core--statistik--judgment--backtester--portfolio)
- [Teil B — Priorisierte Master-Liste (mit Lösungsvorschlag je Punkt)](#teil-b--priorisierte-master-liste)
- [Positiv-Befunde](#positiv-befunde)

---

## Struktureller Hauptbefund

Ein Muster zieht sich durch **alle** Domänen und ist wichtiger als jede Einzelformel: **Ein großer Teil der quantitativen Substanz ist nicht implementiert.** Zahlreiche Agenten reichen nur leere Provider-Felder durch (`None`) und liefern dadurch dauerhaft `NEUTRAL`. Das verzerrt jede nachgelagerte Aggregation systematisch Richtung „neutral" und täuscht Analysetiefe vor, die rechnerisch nicht existiert.

**Reine Stubs / leere Durchreichung:**
- Bond-Pricing komplett (`bond_metrics`, `bond_duration`, `bond_spread`)
- COT (`cot_agent`)
- Markt-Breadth (`index_breadth_agent`)
- Supply/Demand (`supply_demand_agent`)
- Edelmetall-Preis/RSI/MA/Realzins (`precious_metal_price_agent`)
- Sektor-Komposition (`sector_composition_agent`)
- Fear&Greed-Datenquelle (`fear_greed_agent`)
- Shiller CAPE (überall, wo es vorgesehen ist)

**Querschnitts-Lösung:** Stub-Signale dürfen in der Chief-Aggregation **nicht** als gleichberechtigtes `NEUTRAL` mitgezählt werden. Einheitliches Konzept einführen: jedes Sub-Ergebnis trägt einen Status `AVAILABLE | UNAVAILABLE`. `UNAVAILABLE` wird aus der Gewichtung herausgenommen (Re-Normalisierung der vorhandenen Gewichte), statt das Composite Richtung Mitte zu ziehen. Siehe Teil B, Punkt 4.

---

# Teil A — Befunde nach Domäne

---

## Domäne 1 — Makro-Cockpit

### Übersichtstabelle

| Stelle | Konzept | Bewertung |
|---|---|---|
| `buffett_indicator_agent._signal` | Marktkap/BIP mit fixer 135 %-Schwelle | ⚠️ Z-Score berechnet, aber ungenutzt; 135 % US-zentrisch |
| `buffett_indicator._z_score` | Sample-Z (n−1) | ✅ |
| `buffett_indicator` USA-Signal-Quelle | `global_median` berechnet, ungenutzt | ⚠️ |
| `credit_agent._signal` | Kreditwachstum >8 % = bullish (monoton) | ⚠️ Kreditboom = Krisensignal; nominal statt real |
| `gdp_agent` ECB-Mapping | Arbeitslosigkeit als Industrieproduktions-Proxy | ❌ invers korrelierte Größe |
| `gdp_agent._signal` | Arbeitslosenschwelle 5 %/8 % absolut | ⚠️ länderblind; Sahm-Regel besser |
| `gdp_agent` USA-Signal | fehlendes PMI, Schwelle ≥2 | ⚠️ |
| `inflation_agent._signal` | CPI-Bänder, CH 0,5–2 % | ✅/⚠️ blinder Bereich 3–4 %; `trend` ungenutzt |
| `inflation` Core-CPI-Abschwächung | transiente Inflation → NEUTRAL | ✅ |
| `inflation` `real_rate_10y` | mitgeführt, nicht im Signal | ⚠️ |
| `interest_rate` Realzins | Fisher-Approximation ex-post | ⚠️ |
| `interest_rate._signal` | Realzinsschwelle; EU/CH `real_rate=None` | ⚠️ „rising→bearish" toter Code |
| `interest_rate._RATE_HISTORY` | Richtung aus vorigem Programmlauf | ❌ misst Aufruffrequenz |
| `labor_income_agent` | Reallohnwachstum ±1 % | ✅ |
| `money_supply_agent._signal` | Glockenform 3–8 % | ⚠️ nominal; Lücke 8–10 %; `velocity` ungenutzt |
| `macro_chief_agent.run` | Aggregation | ⚠️ Sub-Signale fließen nicht ins Regime |
| `macro_chief` Yield-Mapping | `yield_curve_3m_usa` = 10y-3m | ⚠️ Benennung + Doppelzählung der US-Kurve |
| `regime._score_indicator`/Gewichte | Composite, Gewichtssumme 1,17 | ⚠️ Deflation = 0,0 |
| `regime` Fuzzy/Trend | Gauss-Zuordnung + History-Trend | ⚠️ State-Persistenz; Confidence heuristisch |

### Detailbefunde + Lösungen

#### `buffett_indicator_agent._signal` + Schwellen
- **Befund (⚠️):** Formel `market_cap / gdp * 100` korrekt. Aber die absoluten Schwellen 75 %/135 % sind US-zentriert und länderunabhängig falsch: Die Schweiz liegt strukturell bei 200–250 % (Nestlé/Roche/Novartis als globale Konzerne im SMI), Deutschland bei 50–60 %. Ein fixer 135 %-Schwellenwert klassifiziert die Schweiz dauerhaft „bearish" und Deutschland nie. Der landesbezogene **Z-Score wird sogar berechnet, im Signal aber nicht genutzt.** Zusätzlich verschiebt der säkulare Aufwärtstrend (steigende Gewinnmargen, mehr Börsengänge) den „fairen" Wert über die Zeit — ein statischer Schwellenwert ignoriert das.
- **Lösung:** Klassifizierung ausschließlich über den **Z-Score zur Landeshistorie** (Abweichung vom landeseigenen Mittel), nicht über eine globale Schwelle. Wo der Z-Score wegen kurzer Historie unsicher ist, einen entkoppelten, **länderspezifisch kalibrierten** Fallback-Korridor verwenden (z. B. CH-Median ±1σ statt 75/135). Optional zusätzlich ein detrendetes Maß (Regression gegen Zeit) zur Bereinigung des säkularen Drifts.

#### `buffett_indicator._z_score`
- **Befund (✅):** Stichprobenvarianz mit `(n−1)` (Bessel) korrekt, Division-durch-0-Schutz vorhanden, Mindest-N=8 pragmatisch.
- **Einschränkung:** Bei Jahreswerten (mrv=15) max. 15 Punkte → ausreißerempfindlich.
- **Lösung:** Als Orientierung belassen; bei Verwendung als hartes Signal mit MAD-robuster Variante (siehe Domäne 8) absichern und Mindest-N anheben, sobald genügend Datenpunkte vorliegen.

#### `buffett_indicator` USA-Signal-Quelle
- **Befund (⚠️):** Das Snapshot-Gesamtsignal ist allein das USA-Signal; der berechnete `global_median` und die anderen Länder beeinflussen das aggregierte Signal nicht. Viel Rechenaufwand ohne Wirkung.
- **Lösung:** Entweder den `global_median` als Kontext-Overlay einbeziehen (z. B. Relativierung des US-Werts gegen den globalen Median) oder die ungenutzte Berechnung entfernen, um keine Scheinpräzision zu suggerieren.

#### `credit_agent._signal`
- **Befund (⚠️):** Richtung plausibel (Kreditexpansion = Liquidität), aber zwei Fehler: (1) keine Trennung **nominal vs. real** (8 % nominal bei 5 % Inflation = 3 % real); (2) die Logik ist monoton steigend („mehr Kredit = besser") und ignoriert, dass sehr hohes Kreditwachstum (>15–20 %) ein klassisches **Krisen-Frühwarnsignal** ist (BIS Credit-to-GDP-Gap). `money_velocity` wird mitgeführt, aber nicht genutzt.
- **Lösung:** Auf den **Credit-to-GDP-Gap** (Abweichung des Kredit/BIP-Verhältnisses vom langfristigen HP-Trend, BIS-Standard) umstellen statt rohem Wachstum. Glockenförmige Bewertung: moderates Wachstum positiv, exzessives negativ. Reales Kreditwachstum (abzüglich CPI) verwenden. `money_velocity` entweder einbinden oder entfernen.

#### `gdp_agent` ECB-Datenmapping
- **Befund (❌):** `ecb.get_unemployment()` wird doppelt aufgerufen und einmal als `ecb_ind` (Industrieproduktion) belegt („using unemployment as proxy"). Arbeitslosigkeit und Industrieproduktion sind **invers** korreliert — als Proxy sachlich falsch und irreführend. (Die Variable ist aktuell toter Code, da `industrial_production=None` ins DataPoint geht.)
- **Lösung:** Zeile entfernen. Echte Industrieproduktion (Eurostat/ECB-SDW-Reihe) anbinden oder das Feld sauber als `None` belassen, ohne irreführende Proxy-Zuweisung.

#### `gdp_agent._signal`
- **Befund (⚠️):** PMI-Schwellen 48/52 sind Marktstandard (✅). BIP >2 % als „gut" ist länderblind (CH/EU-Trendwachstum eher 1–1,5 %). Schwerwiegender: Arbeitslosenschwellen 5 %/8 % sind **absolut** statt relativ zu NAIRU — CH (strukturell ~2,5 %) immer „stark", Spanien/Italien (8–12 %) fast immer „schwach".
- **Lösung:** Arbeitslosigkeit über die **Sahm-Regel** bewerten: Anstieg der 3-Monats-Durchschnitts-Arbeitslosenquote um ≥0,5 pp gegenüber dem 12-Monats-Tief signalisiert Rezession. BIP-Schwelle länderspezifisch ans jeweilige Trendwachstum koppeln (Abweichung vom Potenzialwachstum statt fixe 2 %).

#### `gdp_agent` USA-Signal ohne PMI
- **Befund (⚠️):** USA nutzt nur 2 von 3 Indikatoren (PMI=None, ISM nicht angebunden). Der für 3 Indikatoren kalibrierte Schwellenwert `≥2` wird dadurch implizit strenger (beide verbleibenden müssen positiv sein).
- **Lösung:** Score auf die Anzahl **vorhandener** Indikatoren normieren (Durchschnitts-Score statt fixer Summenschwelle). ISM-PMI für die USA anbinden.

#### `inflation_agent._signal`
- **Befund (✅/⚠️):** Zielzonen fundiert (2 % Fed/EZB; SNB-Preisstabilität 0–2 % → CH-Band 0,5–2 % korrekt enger). Aber: (1) **Blinder Bereich** — USA-CPI zwischen 3 % und 4 % fällt durch beide Zweige → Fallback NEUTRAL; eine Inflation von 3,5 % wird neutral gewertet, obwohl klar über Ziel. (2) Vorzeichen-Logik vermischt „gut für Wirtschaft" mit „gut für Aktien". (3) Der `trend`-Parameter ist reserviert, aber inaktiv — eine fallende 4 %-Inflation wird wie eine steigende behandelt.
- **Lösung:** Bänder lückenlos definieren (jeder CPI-Wert fällt in genau eine Klasse; 3–4 % = „erhöht/leicht bearish" statt NEUTRAL). Den `trend` aktivieren: Inflations-Momentum (Δ über 3–6 Monate) als Modifikator — fallende über Ziel ≠ steigende über Ziel. Signal-Semantik konsistent auf „Marktimplikation" festlegen.

#### `inflation` Core-CPI-Abschwächung
- **Befund (✅):** BEARISH→NEUTRAL bei moderater Kerninflation (transiente, energie-/nahrungsmittelgetriebene Inflation) entspricht Zentralbank-Praxis (Fokus Core PCE/CPI).
- **Lösung:** Beibehalten. Optional explizit über die Headline-Core-Differenz parametrisieren statt binärer Abschwächung.

#### `inflation` `real_rate_10y`
- **Befund (⚠️):** Feld existiert im DataPoint, fließt aber nicht in `_signal` ein — der für die Aktienbewertung zentrale Realzins bleibt ungenutzt.
- **Lösung:** Realzins als zusätzlichen Faktor in die Signallogik aufnehmen (hoher Realzins = Gegenwind für Bewertungen) oder zumindest in den nachgelagerten Equity-/Index-Bewertungspfad durchreichen.

#### `interest_rate` Realzins
- **Befund (⚠️):** `fed_rate − usa_cpi` ist die Fisher-**Approximation** und für die Praxis akzeptabel, aber (1) ex-post (realisierte Inflation) statt ex-ante (Inflationserwartung/TIPS-Breakeven); (2) exakte Fisher-Gleichung wäre `(1+i)/(1+π)−1` (bei 4–5 % nur ~0,1–0,2 pp Unterschied).
- **Lösung:** Wo verfügbar, **Breakeven-Inflation** (10J-Nominal − 10J-TIPS) statt realisierter CPI verwenden → ex-ante Realzins. Exakte Fisher-Formel bei höheren Inflationsniveaus.

#### `interest_rate._signal`
- **Befund (⚠️):** Ökonomische Richtung korrekt (expansiv/restriktiv). Schwelle „Realzins >2 % = restriktiv" ist gegenüber r* (~0,5–1,5 % real) eher konservativ-hoch, aber vertretbar. **Problem:** EU/CH bekommen `real_rate=None` → der „rising→bearish"-Zweig kann nie auslösen (toter Code), asymmetrische Regionenbewertung.
- **Lösung:** Realzins für EU/CH berechnen (EZB/SNB-Leitzins − HVPI/CH-CPI bzw. Breakeven). Restriktiv-Schwelle an die jeweilige r*-Schätzung der Region koppeln.

#### `interest_rate._RATE_HISTORY`
- **Befund (❌):** `_RATE_HISTORY` ist ein prozess-lebenslanges In-Memory-Array; die „Richtung" vergleicht den aktuellen Zins mit dem des **vorherigen Programmlaufs** (`history[-2]`), nicht mit der Vorperiode. Zwei Läufe am selben Tag → „stable", obwohl sich der Leitzins seit Wochen bewegt. **Die Richtungserkennung misst die Frequenz der Programmausführung, nicht die geldpolitische Dynamik.**
- **Lösung:** Historische, **datierte** Zinszeitreihe direkt vom Provider beziehen (z. B. FRED `FEDFUNDS`/`DFEDTARU`) und die Richtung aus dem Vergleich aktueller Wert vs. Wert vor N Monaten/Quartalen mit echten Datumsstempeln ableiten. Keine prozess-globale Zustandsliste.

#### `labor_income_agent`
- **Befund (✅):** Reallohnwachstum (nominal − Inflation) als Signalbasis ist methodisch richtig; ±1 %-Bänder plausibel (US-Reallohnwachstum historisch ~0,5–1,5 %).
- **Lösung:** Beibehalten. Optional Lohnstückkosten/Produktivität als Ergänzung, aber für ein Signal nicht zwingend.

#### `money_supply_agent._signal`
- **Befund (⚠️):** Glockenform konzeptionell gut (moderates Wachstum gesund, >10 % Inflations-/Blasenrisiko, <0 % Kontraktion). Schwächen: (1) Schwellen **nominal** statt zum nominalen BIP normiert; (2) **Lücke 8–10 %** → 9 % fällt durch alle Zweige → NEUTRAL; (3) `velocity_m2` ungenutzt, obwohl für die Inflationswirkung entscheidend (MV=PQ).
- **Lösung:** Geldmengenwachstum relativ zum **nominalen BIP-Trend** bewerten (Überschuss-Liquidität = M-Wachstum − nominales BIP-Wachstum). Bänder lückenlos. Umlaufgeschwindigkeit einbeziehen (sinkende Velocity dämpft die Inflationswirkung hohen M-Wachstums).

#### `macro_chief_agent.run`
- **Befund (⚠️):** Robuste Ausfallbehandlung. **Konzeptionelles Problem:** Die sieben Sub-Signale (BULLISH/BEARISH) fließen **nicht** in die Regime-Erkennung ein — der RegimeDetector nutzt nur rohe State-Werte. Geldmenge, Kredit, Reallöhne und Buffett-Indikator haben damit **null Einfluss auf das Regime.**
- **Lösung:** Entweder die Sub-Signale als zusätzliche, gewichtete Indikatoren in den Regime-Composite aufnehmen, oder die Regime-Logik explizit als „nur Kern-Makro" dokumentieren und die übrigen Signale in einem separaten, sichtbaren Aggregat verdichten (damit sie nicht wirkungslos bleiben).

#### `macro_chief` Yield-Curve-Mapping
- **Befund (⚠️):** Schlüssel `yield_curve_3m_usa` enthält den 10y-3m-Spread — irreführend benannt, aber inhaltlich der vom NY-Fed bevorzugte Rezessionsprädiktor (Estrella/Mishkin). Allerdings erhält der separate `yield_curve` (10y-2y) mit 0,12 das höchste Gewicht → beide US-Kurven zusammen dominieren (**Doppelzählung der US-Zinskurve**).
- **Lösung:** Umbenennen (`yield_curve_10y3m_usa`). Im Regime-Gewicht entweder 10y-3m als primären Rezessionsprädiktor führen und 10y-2y entfernen/abwerten, oder beide bewusst zu einem kombinierten Kurven-Score zusammenfassen, der insgesamt ein angemessenes (nicht doppeltes) Gewicht trägt.

#### `regime._score_indicator` + Gewichte
- **Befund (⚠️):** Einzel-Scorings plausibel. Aber: (1) Gewichte summieren auf **1,17–1,27** (nicht 1,0) und werden dynamisch durch `weight_total` normiert → effektive Gewichte hängen davon ab, **welche** Indikatoren vorhanden sind (fehlt z. B. `gdp_growth`, steigt das Gewicht der übrigen). (2) Die Inflations-Scoring-Regel bewertet **Deflation (<1 %) mit 0,0** statt negativ, obwohl Deflation ein klares Warnsignal ist.
- **Lösung:** Gewichte auf Summe 1,0 normieren und dokumentieren; bei fehlenden Indikatoren die Re-Normalisierung explizit machen und protokollieren. Deflations-Score negativ setzen (Schuldendeflation, Nachfrageaufschub) — z. B. Glockenkurve um das 2 %-Ziel mit negativen Flanken nach beiden Seiten.

#### `regime` Fuzzy-Regime + Trend
- **Befund (⚠️):** Fuzzy-Glockenkurven elegant. Probleme: (1) **State-Persistenz** — `detect()` speichert bei jedem Aufruf den aktuellen Composite; läuft der Detektor mehrmals täglich, besteht die „Historie" aus Intraday-Wiederholungen → der Trend (`current − mean(history)`) misst Rauschen/Aufruffrequenz statt ökonomischer Veränderung (gleiche Schwäche wie `_RATE_HISTORY`). (2) Glockenzentren und RECOVERY-Spezialfall nicht empirisch kalibriert. (3) Confidence `abs(composite)*1.5+0.3` misst die Stärke des Composite, nicht die statistische Trennschärfe zwischen Regimen; `_MAX_HISTORY=8` Punkte sind für einen Trend sehr grob.
- **Lösung:** Composite-Historie an **datierte** Zeitpunkte koppeln (max. ein Eintrag pro Periode, z. B. Monatsende) statt pro Aufruf. Trend über eine Regression der letzten N datierten Punkte (Steigung + Signifikanz) statt `current − mean`. Confidence aus der relativen Zugehörigkeit zu konkurrierenden Regimen ableiten (z. B. Abstand der zwei höchsten Fuzzy-Memberships). Gauss-Parameter mit historischen Regime-Daten kalibrieren/validieren.

### Domänen-Fazit 1 (Top-3)
1. Zeitreihen-Historie als prozess-globaler Zustand (`_RATE_HISTORY`, `regime._save_history`) misst Aufruffrequenz statt ökonomischer Dynamik.
2. Absolute, US-zentrische Schwellen ohne Länder-/Strukturnormierung → systematische Fehlklassifikation CH/EU.
3. Entkopplung von Sub-Agenten-Signalen und Regime + ungenutzte Schlüsselgrößen (`real_rate_10y`, `money_velocity`, Buffett-Z-Score) + blinde Schwellen-Lücken.

---

## Domäne 2 — Commodity-Cockpit (Makro)

### Übersichtstabelle

| Stelle | Konzept | Bewertung |
|---|---|---|
| `agricultural_agent._yoy_change` | Start/End-Punkt-Vergleich | ⚠️ endpunktsensitiv; Roll-Yield ignoriert |
| `agricultural._signal` | Median, ±20 % fix | ⚠️ nicht vol-adjustiert; implizite Gleichgewichtung |
| `agricultural` Annualisierung | exakt 1y | ✅ |
| `energy_agent._signal` | Öl-Niveau >100/<40 = bearish | ❌ Niveau statt Momentum; nominal; Gas ignoriert |
| `industrial_metals._signal` | Kupfer-Niveau >4,5/<3,0 | ❌ Niveau statt Richtung |
| `industrial_metals` Aggregation | nur Kupfer | ⚠️ Al/Zn/Ni verworfen |
| `industrial_metals._fmp_price` | Zink/Nickel USD/Tonne | ⚠️ Einheiten-Falle bei Aggregation |
| `precious_metals_macro` Ratios | Gold/Silber, Gold/Platin | ✅ |
| `precious_metals_macro._signal` | GS >80/<50; Gold/Platin „1:1" | ⚠️ veraltet; `gold`-Momentum ungenutzt |
| `commodity_chief_agent_makro.run` | Aggregation | ⚠️ keine Gewichtung |

### Detailbefunde + Lösungen

#### `agricultural_agent._yoy_change`
- **Befund (⚠️):** Math. korrekt als Total-Return, aber (1) endpunktsensitiv (nur `iloc[0]` vs. `iloc[-1]` — ein Ausreißer-Schlusskurs verzerrt die Jahresveränderung); (2) **Roll-Yield ignoriert** — `ZW=F`, `KC=F`, `SB=F` sind Front-Month-Futures-Ketten mit ausgeprägter Saisonalität/Contango; die Futures-Veränderung ≠ Spot-Inflation.
- **Lösung:** Start-/Endwerte glätten (5- oder 20-Tage-Mittel) statt Einzelschlusskurse. Für die Inflations-Aussage einen Spot-/Cash-Preisindex oder Total-Return-Index (mit expliziter Roll-Komponente) verwenden statt der nackten Front-Month-Kette.

#### `agricultural._signal`
- **Befund (⚠️):** Median statt Mittelwert ist robust (✅ Teil). Aber: (1) **implizite Gleichgewichtung** — Weizen/Mais/Soja (hohes CPI-Gewicht) zählen wie Orangensaft; (2) **±20 % nicht volatilitätsadjustiert** — Agrar hat 25–40 % annualisierte Vola, ±20 % ist oft Rauschen; (3) Signal-Semantik (hohe Agrarpreise → BEARISH) inkonsistent zum Energy-Agent.
- **Lösung:** Gewichtung nach Konsum-/Index-Anteil (CPI-Food-Gewichte oder GSCI/BCOM-Agrar-Gewichte). Schwellen auf **Z-Score** der Jahresveränderungen umstellen statt fixer ±20 %. Signal-Konvention domänenweit vereinheitlichen.

#### `agricultural` Annualisierung
- **Befund (✅):** Da `get_price_history(..., "1y")` ~1 Jahr liefert, ist die absolute Veränderung näherungsweise annualisiert.
- **Lösung:** Beibehalten; sicherstellen, dass der Provider wirklich exakt ~1 Jahr liefert.

#### `energy_agent._signal`
- **Befund (❌):** Mehrere gravierende Fehler: (1) **absolutes Preisniveau statt Veränderung** — 100 USD ist keine ökonomische Konstante (real heute << als vor 15 Jahren); (2) `wti or brent`-Fallback ignoriert den WTI-Brent-Spread (3–6 USD); (3) **Natural Gas wird ignoriert** (`gas` erhoben, aber nicht im Signal); (4) Roll-Yield/Contango bei `CL=F`/`NG=F` ignoriert (NG extrem contango-/saisonalitätsgetrieben).
- **Lösung:** Signal auf **Momentum/Veränderungsrate** umstellen (3M/6M/12M-Return, Z-Score-normalisiert), idealerweise real. WTI und Brent getrennt behandeln. Gas als eigenständigen, hochvolatilen Faktor einbeziehen (v. a. für EU-Energiekosten). Für Niveau-Aussagen reale (inflationsbereinigte) Preise.

#### `industrial_metals._signal`
- **Befund (❌):** Gleiches Grundproblem wie Energy — **absolutes Niveau statt Momentum.** „Dr. Copper" als Frühindikator wirkt über die **Richtung/Dynamik**, nicht über ein statisches Niveau; 4,0 USD/lb kann je nach Trend bullish oder bearish sein. Schwellen 4,5/3,0 sind nicht inflations-/zeitadjustiert.
- **Lösung:** YoY-/Multi-Monats-Momentum von Kupfer, idealerweise als **Copper/Gold-Ratio** (etablierter Makro-/Zins-Frühindikator). Optional Z-Score gegen die historische Verteilung.

#### `industrial_metals` Aggregation
- **Befund (⚠️):** Signal beruht nur auf Kupfer; Aluminium/Zink/Nickel werden erhoben und verworfen.
- **Lösung:** Gewichteten Industriemetall-Index (LMEX-ähnlich) oder eine Breadth-Bestätigung (wie viele Metalle steigen?) einführen, um die Robustheit zu erhöhen.

#### `industrial_metals._fmp_price` (Einheiten)
- **Befund (⚠️):** LME-Zink/Nickel notieren in **USD/Tonne**, Kupfer/Aluminium hier in USD/lb. Aktuell kein Schaden (Signal nur Kupfer), aber **latente Falle**: bei Aggregation in einen gemeinsamen Index entstünde ein massiver Einheitenfehler.
- **Lösung:** Vor jeder Aggregation Einheiten normalisieren (alles auf USD/lb oder USD/Tonne). Einheit pro Preis explizit mitführen.

#### `precious_metals_macro` Ratios
- **Befund (✅):** Gold/Silber- und Gold/Platin-Ratio math. korrekt, Division-durch-0 abgesichert. Dimensionslos → zeit-/inflationsrobust (sauberster Ansatz der Gruppe).
- **Lösung:** Beibehalten.

#### `precious_metals_macro._signal`
- **Befund (⚠️):** GS-Ratio als Risikoindikator anerkannt, aber: (1) Schwellen 50/80 veraltet (seit ~2018 dauerhaft >70–80, Spitze >120 in Q1 2020) → fixe >80=BEARISH heute zu niedrig; (2) `GOLD_PLATINUM_AVG = 1.0` faktisch falsch (Platin seit ~2015 deutlich unter Gold, Ratio 1,5–2,5); (3) `gold`-Parameter wird geprüft, aber das Gold-Momentum nicht implementiert (Kommentar „Safe Haven" ohne Umsetzung).
- **Lösung:** Schwellen durch rollierenden **Z-Score/Perzentil-Rang** ersetzen statt fixer Absolutwerte. Gold/Platin-Anker auf aktuelles strukturelles Niveau (~1,8–2,5) bzw. ebenfalls Perzentil. Gold-Momentum-Komponente tatsächlich implementieren (stark steigend = Safe-Haven-Nachfrage).

#### `commodity_chief_agent_makro.run`
- **Befund (⚠️):** Keine fachliche Aggregation — die vier Snapshots werden nur eingesammelt; **kein Gesamt-Commodity-Signal**, **keine Sektorgewichtung** (Energie dominiert reale Indizes: GSCI ~50–60 %, BCOM ~30 %).
- **Lösung:** Gewichtetes Gesamtsignal mit ökonomisch begründeten Sektorgewichten (GSCI-/BCOM-nah oder makro-relevanzbasiert).

### Domänen-Fazit 2 (Top-3)
1. Niveau- statt Momentum-Signale (Energy, Industrial Metals) — gravierendster Fehler.
2. Roll-Yield/Contango/Saisonalität bei Futures durchgängig ignoriert.
3. Fixe, veraltete, nicht vol-adjustierte Schwellen + fehlende Index-Gewichtung im Chief.

---

## Domäne 3 — Sentiment / Yield Curve / Sektor

### Übersichtstabelle

| Stelle | Konzept | Bewertung |
|---|---|---|
| `fear_greed_agent._label` | 5-Stufen-Klassifikation | ✅ |
| `fear_greed._signal` | Contrarian-Mapping | ⚠️ löst zu früh (≤45); Datenquelle Stub |
| `put_call_agent._signal` | P/C >1,2/<0,7 | ⚠️ nicht auf definierte CBOE-Serie kalibriert |
| `vix_agent._signal` | VIX >30 bearish | ⚠️ Momentum vs. Contrarian-Inkonsistenz |
| `sentiment_chief_agent.run` | Aggregation | ❌ keine Verdichtung |
| `yield_spread_agent._point` | 10Y-2Y primär | ⚠️ 10Y-3M besser; kein Lag |
| `yield_spread.run` CH | nur 10Y-3M (SARON) | ⚠️ Geldmarkt-/Bond-Mischung |
| `sovereign_spread_agent._signal` | >300bp / 3×>200bp | ✅ (Kernländer in Zähl-Logik unsauber) |
| `yield_curve_chief_agent.run` | Aggregation | ⚠️ kein konsolidiertes Signal |
| `sector_performance._pct_return` | 1M absolute Performance | ⚠️ kein Benchmark → Beta-Artefakt |
| `sector_rotation` ROTATION_MAP | Zyklus-Playbook | ✅ („Gold" toter Match) |
| `sector_chief_agent.run` | nur `leading_usa` | ⚠️ EU ignoriert |

### Detailbefunde + Lösungen

#### `fear_greed_agent._label`
- **Befund (✅):** Schwellen (≤25 / ≤45 / ≤55 / ≤75 / >75) entsprechen weitgehend der CNN-Konvention. Neutrale Zone leicht asymmetrisch, im Rahmen.
- **Lösung:** Beibehalten.

#### `fear_greed._signal`
- **Befund (⚠️):** Contrarian-Richtung korrekt, aber BULLISH bereits bei `value ≤45` (normales „Fear") — die Contrarian-Prämie ist empirisch nur in den **Extremen** robust. Asymmetrie: Greed löst erst ab 75 aus, Fear schon ab 45. Zudem: Datenquelle ist **Stub** (`_fetch_fear_greed` liefert immer `None`).
- **Lösung:** BULLISH nur bei ≤20–25, BEARISH nur bei ≥75–80, dazwischen neutral (symmetrische Extremzonen). Echte Datenquelle anbinden (z. B. CNN Fear&Greed bzw. eigene Konstruktion aus den 7 Subindikatoren).

#### `put_call_agent._signal`
- **Befund (⚠️):** Contrarian-Richtung korrekt (hohes P/C = Pessimismus = BULLISH). Aber die Schwellen 1,2/0,7 hängen davon ab, **welche** CBOE-Serie gezogen wird: Total P/C (~0,9–1,0 Mittel) vs. Equity-only (~0,6–0,7 Mittel). Der Fetcher nimmt je nach CSV-Header mal Total, mal die erste P/C-Spalte → Schwellen nicht konsistent kalibriert.
- **Lösung:** Eine feste Serie definieren (Total CBOE P/C). Schwellen relativ via rollierendem Mittel ± Z-Score statt fixer Absolutwerte, da das mittlere P/C-Niveau säkular driftet.

#### `vix_agent._signal`
- **Befund (⚠️):** Richtung „VIX hoch = Stress = BEARISH" behandelt VIX als **Momentum/Regime**-Indikator. Aber Fear&Greed und Put/Call sind **contrarian** — derselbe Panik-Zustand erzeugt im VIX-Agent BEARISH, in den anderen BULLISH (konzeptioneller Widerspruch). `ref = vix or vstoxx`: VIX=0,0 würde fälschlich auf VSTOXX ausweichen. Fixe 30/15-Schwelle ignoriert das VIX-Regime.
- **Lösung:** Konvention vereinheitlichen — VIX-Spikes (>30/40) klassisch als **contrarian-Kaufsignal** behandeln, konsistent mit dem übrigen Sentiment-Block. VIX relativ zum gleitenden Mittel/Perzentil bewerten oder die VIX-Terminstruktur (Contango/Backwardation) nutzen statt absolutem Level. `is None`-Check statt Falsiness.

#### `sentiment_chief_agent.run`
- **Befund (❌):** Es findet **keine Aggregation** statt — VIX/FearGreed/PutCall werden nur eingesammelt; **kein zusammengeführtes Sentiment-Gesamtsignal** (kein Voting, keine Gewichtung, keine Konfliktauflösung). Der VIX-vs-Contrarian-Widerspruch bleibt unaufgelöst.
- **Lösung:** Gewichtetes Composite — alle drei auf eine **einheitliche Contrarian-Konvention** normieren (z. B. Z-Scores), Mittelwert bilden, definierte Tie-Break-Regel. So wird die fachlich wichtigste Chief-Aufgabe (Verdichtung) erfüllt.

#### `yield_spread_agent._point`
- **Befund (⚠️):** `inverted` korrekt (10Y-2Y<0 ODER 10Y-3M<0). Aber: (1) Signal nutzt nur 10Y-2Y als `ref`, obwohl **10Y-3M der überlegene Rezessionsprädiktor** ist (NY Fed/Estrella); (2) **kein Inversions-Lag** — bei `ref < 0` sofort BEARISH, obwohl Aktien nach Inversion historisch oft weiterlaufen und der Abschwung erst mit der Wieder-Versteilerung (Bull-Steepening) kommt; (3) `ref > 1.0` → BULLISH mit arbiträrer 1,0-Schwelle.
- **Lösung:** 10Y-3M als primären `ref` oder beide kombiniert. Inversion nicht sofort als BEARISH werten, sondern mit Lag/Steepening-Kontext (Inversion = Warnung, Bull-Steepening nach Inversion = eigentliches Timing-Signal). Schwellen aus historischer Verteilung statt fixem 1,0.

#### `yield_spread.run` (CH)
- **Befund (⚠️):** CH nutzt nur 10Y-3M (SARON), kein 2J. SARON ist ein Overnight-Referenzzins, kein 3M-Bond-Yield → Mischung von Geldmarkt-Referenz und Anleihe-Yield im Spread ist nur als Näherung sauber.
- **Lösung:** Wo verfügbar, einen echten CH-3M- bzw. 2J-Bond-Yield verwenden. Andernfalls die Näherung klar dokumentieren und nicht 1:1 mit den US-Schwellen gleichsetzen.

#### `sovereign_spread_agent._signal`
- **Befund (✅):** Logik sinnvoll (max-Spread >300bp = akuter Stress ODER ≥3 Länder >200bp = systemisch). Schwellen für Peripherie realistisch. Spread-Berechnung `(v − de)*100` in bp korrekt. **Einschränkung:** Die Stress-Länderliste wirft Kernländer (NL/FI/AT/LU, <50bp) mit Peripherie zusammen für die „3 Länder >200bp"-Regel.
- **Lösung:** Für die systemische Zählung nur die Peripherie (IT/ES/PT/GR + ggf. weitere) heranziehen. Funktional unkritisch, aber konzeptionell sauberer.

#### `yield_curve_chief_agent.run`
- **Befund (⚠️):** Reines Einsammeln, **kein konsolidiertes Zinskurven-Gesamtsignal** (Inversion USA + Eurozonen-Sovereign-Stress nicht verdichtet).
- **Lösung:** Gewichtetes Gesamtsignal aus US-Kurven-Status und EU-Stress-Status bilden.

#### `sector_performance._pct_return`
- **Befund (⚠️):** (1) Total-Return-Näherung über 1M rechnerisch korrekt, aber „leading"/"lagging" = nur bestes/schlechtestes **absolutes** Return ohne **Benchmark** → echte relative Stärke = Sektor-Return **minus** Markt-Return; sonst misst man nur Markt-Beta (in Rallyes führt immer High-Beta XLK/XLY, in Korrekturen XLP/XLU → tautologisch). (2) 1 Monat ist rauschanfällig. (3) GICS-Abdeckung unvollständig (XLC fehlt; EU ohne RealEstate).
- **Lösung:** Relative Stärke als Sektor-Return − Benchmark-Return (SPX/STOXX600) berechnen. Mehrere Zeitfenster kombinieren (1M/3M/6M-Momentum). GICS-Abdeckung vervollständigen (11 Sektoren inkl. Communication Services).

#### `sector_rotation` ROTATION_MAP
- **Befund (✅):** Mapping folgt korrekt dem klassischen Zyklus-Playbook (Recovery/Expansion → zyklisch; Slowdown/Recession → defensiv; Boom → Energy/Materials). **Einschränkungen:** (1) DEPRESSION empfiehlt „Gold" — kein Sektor in der Performance-Map → toter Match; (2) Alignment nur gegen den **einen** Top-Sektor.
- **Lösung:** „Gold" aus der Sektor-Map entfernen oder als separate Asset-Klasse führen. Alignment über den Anteil der empfohlenen Sektoren in den **Top-N** (z. B. Top-3) statt nur des einen Spitzensektors.

#### `sector_chief_agent.run`
- **Befund (⚠️):** Rotation wird nur mit `performance.leading_usa` gespeist — **EU-Sektoren (`leading_eu`) fließen nicht ein**, obwohl berechnet. Für ein EU/CH-orientiertes System eine echte Lücke: das Rotationssignal ist faktisch rein US-getrieben.
- **Lösung:** EU-Sektoren analog einbinden (eigene Rotation je Region) oder regionsgewichtetes Gesamt-Rotationssignal.

### Domänen-Fazit 3 (Top-3)
1. Sentiment-Inkonsistenz VIX (Momentum) vs. Fear&Greed/Put-Call (Contrarian), vom Chief nicht aufgelöst.
2. Inversions-Logik suboptimal: 10Y-2Y statt 10Y-3M, kein 6–18M-Lag/Bull-Steepening.
3. Sektor-„leading/lagging" ohne Benchmark-Normierung (Beta-Artefakt); EU-Sektoren ignoriert; P/C nicht auf feste Serie kalibriert.

---

## Domäne 4 — Equity Deep Dive

### Übersichtstabelle

| Stelle | Konzept | Bewertung |
|---|---|---|
| `fundamentals._score` P/E | <20/>40 absolut | ⚠️ sektor-blind; negatives EPS als „billig" |
| `fundamentals._score` Forward vs. Trailing | +1 wenn fwd<trailing | ✅ |
| `fundamentals._score` CAPE | CAPE auf Einzelaktie | ❌ |
| `fundamentals._score` PEG | <1,5 günstig | ⚠️ Standard 1,0; Growth-Basis ungeprüft |
| `fundamentals._score` EV/EBITDA | <12/>25 | ⚠️ sektor-blind (Banken) |
| `fundamentals._score` CAGR/Margin/D&E | Schwellen | ⚠️ Einheiten-Risiko; branchenblind |
| `fundamentals._score` Aggregation | ≥3/≤−2 | ⚠️ Asymmetrie; Doppelzählung; ungenutzte Felder |
| `quality._signal` ROE/ROIC | >15 %/>12 % | ⚠️ ROIC gegen WACC; ROE leverage-verzerrt |
| `quality._signal` NetDebt/EBITDA | <2/>4 | ✅ |
| `quality._signal` Altman Z | 2,99/1,81 | ✅ (nur Manufacturing) |
| `quality` Aggregation | 4 Faktoren | ⚠️ kein Piotroski; viele Felder ungenutzt |
| `earnings_trend.run` Beat-Rate | Anteil Beats | ⚠️ Magnitude/Sandbagging ignoriert; n=2 Revisionen |
| `earnings_trend._signal` | UND/ODER-Logik | ⚠️ asymmetrisch sensibel |
| `insider_agent.run` | Anzahl Buy vs. Sell | ❌ Wert/Volumen entscheidend |
| `short_interest.run` | hoch=bearish | ⚠️ Squeeze ignoriert; days_to_cover ungenutzt |
| `moat_agent._overall` | 5 Morningstar-Quellen | ✅ Rahmen / ⚠️ additiv statt max |
| `valuation_range` KGV-Multiple | EPS×Sektor-PE | ✅ (trailing; negatives EPS) |
| `valuation_range` EV/EBITDA | EV→Equity-Bridge | ✅ |
| `valuation_range` „DCF" | Gordon-Growth | ❌ |
| `valuation_range._combine_methods` | Median low/high | ⚠️ fragil bei n=2–3 |
| `valuation_range._position`/Terminal-Growth | ±5 %; 2,5–3,0 % | ✅ |
| `equity_chief_agent.run` | Orchestrierung | ⚠️ keine Gewichtung; sector nicht weitergegeben |

### Detailbefunde + Lösungen

#### `fundamentals._score` P/E
- **Befund (⚠️):** Absolute, sektorunabhängige Schwellen (<20/>40) sind grob. P/E 18 ist bei einem Versorger teuer, bei SaaS günstig. **Kein Handling für negatives EPS** — ein negatives KGV (Verlust) wird wie ein extrem niedriges KGV behandelt → fälschlich +1 (bullish).
- **Lösung:** Negatives/n/a-P/E neutralisieren bzw. auf Forward-P/E ausweichen. Schwellen relativ zum Sektor-Median oder zum historischen Eigen-P/E des Titels.

#### `fundamentals._score` Forward vs. Trailing P/E
- **Befund (✅):** `forward_pe < pe` impliziert erwartetes EPS-Wachstum — sinnvolle, sauber abgesicherte Logik.
- **Lösung:** Beibehalten.

#### `fundamentals._score` CAPE
- **Befund (❌):** Das **Shiller-CAPE ist ein Index-/Marktmaß** (inflationsbereinigter 10J-Durchschnitts-EPS), entworfen für breite Indizes. Auf eine **Einzelaktie** angewandt verzerren strukturelle Gewinnsprünge (M&A, Geschäftsmodellwandel) den 10J-Schnitt; zudem Doppelzählung mit P/E.
- **Lösung:** CAPE im Single-Stock-Score **entfernen** und auf Markt-/Sektor-Ebene reservieren (siehe Index-Domäne, wo es fehlt).

#### `fundamentals._score` PEG
- **Befund (⚠️):** Marktstandard ist **PEG = 1,0** (Peter Lynch); <1,5 ist großzügig. PEG ist nur bei positivem, nicht-trivialem Wachstum sinnvoll — bei sehr niedrigem g explodiert er künstlich, bei negativem g wird er sinnlos.
- **Lösung:** Schwelle näher an 1,0; Growth-Basis prüfen (PEG nur bei g in einem sinnvollen positiven Bereich anwenden). PEGY (inkl. Dividendenrendite) als robustere Variante erwägen.

#### `fundamentals._score` EV/EBITDA
- **Befund (⚠️):** Schwellen (<12/>25) plausibel, aber sektorunabhängig. Für Banken/Financials hat EBITDA praktisch keine Aussagekraft; EBITDA ignoriert Capex-Intensität (kapitalintensive Sektoren überzeichnet).
- **Lösung:** Sektor-relative Multiples (die Sektor-Tabelle aus `valuation_range_agent` wiederverwenden). Für Financials EV/EBITDA durch geeignetere Maße (P/B, P/TBV) ersetzen.

#### `fundamentals._score` Revenue-CAGR / Op-Margin / Debt-Equity
- **Befund (⚠️):** Einzeln plausibel, aber: **Einheiten-Risiko** — hier als Prozentzahl interpretiert (>10, >15), während `valuation_range` `revenue_cagr_3y` durch 100 teilt (Annahme Prozentzahl). Konsistent, aber fragil/unkommentiert. D/E-Schwelle branchenblind (Financials/Utilities strukturell hoch).
- **Lösung:** Einheiten-Konvention systemweit explizit dokumentieren und normieren. D/E und Margen sektor-relativ bewerten.

#### `fundamentals._score` Aggregation
- **Befund (⚠️):** (1) **Asymmetrie** unbegründet (bullish ≥+3, bearish ≤−2); (2) ungewichtete Addition heterogener Faktoren mit **Doppelzählung** korrelierter Bewertungsdimensionen (CAPE/P/E); (3) `price_book`, `price_sales`, `price_fcf`, `ev_revenue`, `dividend_yield` erfasst, aber **nicht im Score** (insb. P/FCF, P/B für Financials).
- **Lösung:** Symmetrische, begründete Schwellen. Korrelierte Faktoren zu einer Bewertungsdimension bündeln (Composite-Z statt naiver Addition). Relevante ungenutzte Multiples (P/FCF, P/B) einbeziehen, sektor-abhängig gewichtet.

#### `quality._signal` ROE/ROIC
- **Befund (⚠️):** Schwellen (>15 %/>12 %) marktüblich. Aber **ROIC sollte gegen WACC** verglichen werden (Wertschöpfung nur bei ROIC > WACC); der WACC ist im System vorhanden (DCF), wird hier aber nicht genutzt. Hohes ROE kann durch Leverage erkauft sein (DuPont).
- **Lösung:** ROIC−WACC-Spread als zentralen Qualitätsindikator. ROE mit Leverage-Adjustierung interpretieren oder ROIC dominieren lassen.

#### `quality._signal` Net Debt/EBITDA
- **Befund (✅):** Standard-Schwellen (<2 gut, >4 schlecht; IG typ. <3x).
- **Lösung:** Beibehalten; optional branchenabhängige Toleranz (Telco/Utilities höher).

#### `quality._signal` Altman Z
- **Befund (✅):** Schwellen 2,99/1,81 = Original Altman Z (Manufacturing, 1968). Interpretation standardkonform. **Vorbehalt:** gilt nur für produzierende Nicht-Finanzunternehmen.
- **Lösung:** Modellvariante nach Unternehmenstyp wählen: Z'' (2,6/1,1) für Dienstleister/Nicht-Manufacturing; für Financials gar nicht anwenden.

#### `quality` Aggregation
- **Befund (⚠️):** `net_margin`, `fcf_margin`, `roa`, `interest_coverage`, `current_ratio`, `gross_margin` werden erfasst, aber **nicht im Signal** verwendet. Kein echter **Piotroski F-Score** trotz vorhandener Rohdaten.
- **Lösung:** Piotroski F-Score (9 Kriterien: Profitabilität, Leverage/Liquidität, operative Effizienz) implementieren — alle nötigen Inputs liegen vor. Mindestens `interest_coverage` und `fcf_margin` in den Score aufnehmen.

#### `earnings_trend.run` Beat-Rate & Revisionen
- **Befund (⚠️):** Beat binär gezählt — **Magnitude (Surprise %) ignoriert**; Sandbagging-Effekt (Unternehmen schlagen routinemäßig „gemanagte" Schätzungen → 75 % Beat ist fast Normalfall, nicht bullish). Revisionen aus nur 2 Datenpunkten (`history[-2:]`) statistisch dünn; `q.get("revision", 0)` ohne klare Definition.
- **Lösung:** **SUE-Score** (Standardized Unexpected Earnings) statt binärer Beat-Rate, plus 3-Monats-Estimate-Revisions-Trend (PEAD-Literatur — Revisionen sind der stärkere Performance-Prädiktor). Beat-Rate gegen die branchenübliche Baseline (~70–75 %) relativieren.

#### `earnings_trend._signal`
- **Befund (⚠️):** Asymmetrische UND/ODER-Logik macht das Bearish-Signal überempfindlich (jede „down"-Revision triggert bärisch, auch bei hoher Beat-Rate).
- **Lösung:** Gewichtetes Scoring statt strikter ODER-Veto-Logik; Revisions-Momentum höher gewichten als die rohe Beat-Rate.

#### `insider_agent.run`
- **Befund (❌):** Es wird die **Anzahl** der Transaktionen gezählt, nicht **Volumen/Wert**. 10 kleine automatische 10b5-1-Verkäufe vs. 1 großer Conviction-Kauf werden als „net_sell" gewertet, obwohl der ökonomische Gehalt umgekehrt ist. Käufe (signalstark) und Verkäufe (oft nicht-informativ) werden symmetrisch behandelt.
- **Lösung:** **Wertgewichtete** Netto-Insider-Aktivität (Dollar-Betrag/Aktienzahl). Geplante 10b5-1-Programme und Optionsausübungen herausrechnen. Fokus auf Open-Market-Käufe von Top-Insidern (CEO/CFO); Käufe stärker gewichten als Verkäufe.

#### `short_interest.run`
- **Befund (⚠️):** „Hoher Short-Interest = bearish" ist eindimensional und teils gegenläufig — hoher Short-Float ist auch **Short-Squeeze-Brennstoff** (bullish, contrarian). `days_to_cover` (Short-Interest-Ratio) wird erfasst, aber **nicht genutzt**, obwohl es genau die Squeeze-Anfälligkeit misst. Niedriger Short-Float <5 % als „bullish" ist schwach begründet.
- **Lösung:** Kombination Short-%-Float + Days-to-Cover + Trend (steigend/fallend). Hohe Werte als Risiko-/Squeeze-Flag (kontextabhängig), nicht als simples Bearish; niedrigen Short-Float neutral statt bullish.

#### `moat_agent._overall`/`_signal`
- **Befund (✅ Rahmen / ⚠️ Mapping):** Die fünf Quellen entsprechen exakt dem **Morningstar-Economic-Moat-Framework** (✅). Aber: (1) **ungewichtete Summe** — ein einzelner sehr starker Netzwerkeffekt (Visa, Google) begründet real einen Wide Moat allein, erreicht hier mit max. 2 Punkten nur „narrow"; (2) Score ≥7 für „wide" verlangt 3–4 gleichzeitig starke Kategorien — zu streng; (3) `none → BEARISH` fragwürdig (fehlender Moat ist Bewertungssache, nicht per se bärisch); (4) reines LLM-Scoring **ohne quantitativen Anker**.
- **Lösung:** Maximum- bzw. Schwellen-pro-Kategorie-Logik statt linearer Summe (eine dominante Quelle kann „wide" begründen). Moat-Signal von der Aktien-Empfehlung entkoppeln (Moat ist Qualitätsmerkmal, nicht Timing). Quantitative Anker ergänzen: ROIC-WACC-Persistenz über 10+ Jahre, Bruttomargen-Stabilität, Marktanteils-Trend.

#### `valuation_range` KGV-Multiple
- **Befund (✅):** Fair Value = EPS × Sektor-P/E-Band — Standard-Multiple-Bewertung, korrekt. **Vorbehalt:** nutzt Trailing-EPS; kein Handling für negatives EPS (negativer Fair Value).
- **Lösung:** Forward-EPS bevorzugen. Negatives EPS abfangen (Methode überspringen oder auf Umsatz-/Buchwert-Multiple ausweichen).

#### `valuation_range` EV/EBITDA-Multiple
- **Befund (✅):** Equity-Fair-Value = EBITDA/Aktie × EV-Multiple − NetDebt/Aktie — saubere EV→Equity-Bridge.
- **Lösung:** Beibehalten; optional Minderheitenanteile/Preferreds in die Bridge aufnehmen (meist vernachlässigbar).

#### `valuation_range` „DCF"
- **Befund (❌):** Dies ist **kein DCF, sondern ein einstufiges Gordon-Growth-Modell**. Fehler: (1) **Inkonsistenz** — Zähler nutzt kurzfristiges `growth`, Nenner `terminal_growth` (bei Gordon muss dieselbe perpetuierliche Rate stehen); (2) **keine explizite Prognosephase** → systematische **Unterschätzung von Wachstumswerten**; (3) **WACC=0,09 hart kodiert** ohne Beta/Kapitalstruktur/risikofreien Zins; (4) **Revenue-CAGR als FCF-Proxy** (Umsatz ≠ FCF); (5) bei WACC ≈ g extrem instabil (der 0,001-Guard verhindert nur Division durch ~0, nicht die ökonomische Instabilität).
- **Lösung:** Echtes **2-Stufen-DCF**: explizite n-Jahres-FCF-Prognose (5–10 J) mit Hochwachstum, danach barwertiger Terminal Value via Gordon mit **konsistenter** g_terminal. WACC **bottom-up** aus CAPM (risikofreier Zins + β·ERP) und Kapitalstruktur. FCF statt Umsatz-CAGR projizieren. Sensitivitätsanalyse über WACC/g.

#### `valuation_range._combine_methods`
- **Befund (⚠️):** Median über typischerweise nur 2–3 Methoden ist fragil und kann inkonsistente Bänder erzeugen (Median-Low aus einer, Median-High aus anderer Methode → nicht methoden-kohärent). Bei 3 Methoden = mittlerer Wert, ignoriert die anderen beiden.
- **Lösung:** Gewichteter Durchschnitt nach Methoden-Zuverlässigkeit (DCF höher bei stabilen Cashflows, Multiples bei Zyklikern). Bänder methoden-kohärent bilden (pro Methode low/high, dann gewichten).

#### `valuation_range._position` + Terminal-Growth
- **Befund (✅):** Terminal-Growth 2,5–3,0 % (nahe nominalem BIP/Inflation) **fachlich vorbildlich** und gut kommentiert. ±5 %-Puffer für „fair" pragmatisch.
- **Lösung:** Beibehalten.

#### `equity_chief_agent.run`
- **Befund (⚠️):** Reiner Orchestrator — **keine Aggregation der 7 Einzelsignale** zu einem Gesamturteil (kein gewichteter Composite, kein Mapping Bewertung×Qualität×Moat → Kauf/Halten/Verkauf). `sector` wird nur an `valuation_range` weitergereicht, **nicht** an `fundamentals`/`quality`, wo es für sektor-relative Schwellen gebraucht wird.
- **Lösung:** Gewichtetes Gesamturteil bilden, das Bewertung (Langfrist-Anker), Qualität/Moat (Prämien-Rechtfertigung) und Momentum/Earnings (Timing) gegeneinander abwägt — ein Wide-Moat-Unternehmen darf höher bewertet sein. `sector` an alle sektor-sensitiven Sub-Agenten durchreichen.

### Domänen-Fazit 4 (Top-3)
1. „DCF" ist ein fehlkonstruiertes Gordon-Growth-Modell (inkonsistente g, keine Prognosephase, harter WACC, Umsatz als FCF-Proxy).
2. Insider zählt Anzahl statt Volumen und behandelt Käufe/Verkäufe symmetrisch.
3. Durchgängig sektor-/WACC-blinde Schwellen + ungenutzte Kennzahlen + fehlende Gesamtbeurteilung im Chief.

---

## Domäne 5 — Bond Deep Dive

### Übersichtstabelle

| Stelle | Konzept | Bewertung |
|---|---|---|
| Gesamtes Modul | YTM/Duration/Convexity/OAS/Z-Spread | ❌ keine Pricing-Engine; leerer Provider |
| `bond_metrics` current_yield | `coupon/price×100` | ⚠️ Clean/Dirty + Einheiten undefiniert |
| `bond_metrics` real_yield | `ytm − inflation` | ⚠️ ex-post; `breakeven_inflation` ungenutzt |
| `bond_metrics._signal` | Realzins-Schwellen | ⚠️ Heuristik, nicht durationsbereinigt |
| `bond_metrics` YTC | nur durchgereicht | ⚠️ kein Yield-to-Worst |
| `bond_duration` DV01 | `ModDur×Preis×0,0001` | ⚠️ Clean/Dirty + Einheiten |
| `bond_duration` Convexity | eingelesen, nie verwendet | ❌ |
| `bond_duration` Macaulay/Modified | nur durchgereicht | ⚠️ keine Effective Duration für Optionalität |
| `bond_duration._signal` | Duration × Zinsrichtung | ✅ Richtung / ⚠️ Schwelle |
| `bond_credit` DEFAULT_RATES | 1J-PD je Rating | ⚠️ %/Dezimal uneinheitlich |
| `bond_credit` `_default_prob(moodys)` | PD nur aus Moody's | ⚠️ Inkonsistenz mit `_category` |
| `bond_credit._default_prob` startswith | Prefix-Matching | ❌ S&P „CCC" → Moody's `C`=50 % |
| `bond_credit._category` | IG/HY/Junk | ⚠️ „C" doppelt; „junk" nicht marktüblich |
| `bond_credit._signal` | Rating-Trend | ✅ |
| `bond_spread` run | OAS/Z/G-Spread | ❌ keine Berechnung; Spread-Duration fehlt |
| `bond_spread._signal` | Spread-Trend | ✅ |
| `bond_chief_agent.run` | Aggregation | ✅ neutral / ⚠️ keine Gesamtsicht |

### Detailbefunde + Lösungen

#### Gesamtes Modul — fehlende Pricing-Engine
- **Befund (❌):** YTM, YTC, Macaulay/Modified/Effective Duration, Convexity, OAS, Z-Spread, G-Spread werden **nicht berechnet**, sondern aus `provider.get_bond_data()` durchgereicht; der einzige Provider (`finnhub.py`) gibt `{}` zurück → im Live-Betrieb sind praktisch alle Felder `None`. Preis-Yield-Gleichung, Cashflow-Diskontierung, Compounding-Frequenz, Day-Count und Accrued Interest existieren nirgends.
- **Lösung:** Eine echte Bond-Pricing-Engine implementieren: Cashflow-Generierung aus Kupon/Frequenz/Fälligkeit, YTM via numerischer Nullstellensuche der Preis-Yield-Gleichung, Macaulay/Modified Duration analytisch, Convexity, Effective Duration via OAS-Shift für optionsbehaftete Bonds. Day-Count-Konvention (ACT/ACT, 30/360) und Clean/Dirty-Preis explizit. Alternativ eine etablierte Bibliothek (z. B. QuantLib) anbinden.

#### `bond_metrics` current_yield
- **Befund (⚠️):** `coupon/price*100` grundsätzlich korrekt, aber **Einheiten-/Konventionsfehler wahrscheinlich**: Kurse werden marktüblich als % vom Nennwert quotiert (98,5); wird `coupon` als absoluter Geldbetrag und `price` als Prozentkurs gemischt, ist das Ergebnis falsch. Clean vs. Dirty undefiniert.
- **Lösung:** Konvention festlegen und normalisieren: Current Yield = (Couponrate × Nennwert) / Clean Price mit konsistenten Einheiten. Einheiten dokumentieren.

#### `bond_metrics` real_yield
- **Befund (⚠️):** `ytm − inflation` ist die Fisher-Approximation (akzeptabel), aber (1) exakt wäre `(1+ytm)/(1+inf)−1`; (2) hier wird **realisierte** Inflation (`state.inflation`) statt **erwarteter** (Breakeven) abgezogen → ex-post statt ex-ante. Das Feld `breakeven_inflation` existiert, wird aber nicht genutzt.
- **Lösung:** `breakeven_inflation` verwenden für die ex-ante Realrendite; exakte Fisher-Formel bei höheren Inflationsniveaus.

#### `bond_metrics._signal`
- **Befund (⚠️):** Reine Heuristik (Realrendite >2 % bullish, <0 bearish) ohne Fixed-Income-Fundierung; eine hohe Realrendite kann auch gestiegene Realzinsen = Kursverlust für Bestandshalter bedeuten. Schwellen nicht durations-/laufzeitbereinigt.
- **Lösung:** Signal um Duration/Carry/Roll-Down erweitern (Total-Return-Perspektive: Carry + Roll-Down − Duration·erwartete Yield-Änderung) statt reiner Realrendite-Schwelle.

#### `bond_metrics` YTC / Yield-to-Worst
- **Befund (⚠️):** YTC wird nur durchgereicht; es fehlt die **Yield-to-Worst**-Logik (min(YTM, YTC) für callable Bonds), Marktstandard für die maßgebliche Rendite. Callability bleibt in der Bewertung unberücksichtigt.
- **Lösung:** Yield-to-Worst = min über alle Call-/Put-Szenarien berechnen und als maßgebliche Rendite verwenden.

#### `bond_duration` DV01
- **Befund (⚠️):** `DV01 = ModDur × Preis × 0,0001` ist die lineare Näherung, für 1bp akzeptabel (Convexity bei 1bp vernachlässigbar). Aber: (1) **Dirty Price** nötig, nicht Clean; (2) bei Prozentkurs (98,5) statt Geldbetrag ist die Bezugsgröße (per 100 Nominal vs. per Bond) undefiniert.
- **Lösung:** `DV01 = ModDur × DirtyPrice × 0,0001`; Bezugsgröße (per 100 Nominal) festlegen und dokumentieren.

#### `bond_duration` Convexity
- **Befund (❌):** `convexity` wird eingelesen, aber **nirgends verwendet** — keine Preisänderungsschätzung `ΔP/P ≈ −ModDur·Δy + ½·Convexity·Δy²`. Bei großen Yield-Changes (Signal bei ModDur>10) ist die rein lineare Approximation deutlich fehlerbehaftet.
- **Lösung:** Zweite-Ordnungs-Term mit Convexity in jede Preisänderungsschätzung aufnehmen.

#### `bond_duration` Macaulay vs. Modified / Effective
- **Befund (⚠️):** Beide nur durchgereicht; keine Konsistenzableitung `ModDur = MacDur / (1 + y/k)`. Keine **Effective Duration** für Optionalität (Callable/Putable/MBS), wo Modified Duration konzeptionell unzulässig ist.
- **Lösung:** Konsistenzbeziehung prüfen/ableiten. Für optionsbehaftete Bonds Effective Duration (numerisch via paralleler Kurvenverschiebung mit OAS) verwenden.

#### `bond_duration._signal`
- **Befund (✅ Richtung / ⚠️ Schwelle):** Richtungslogik korrekt (hohe Duration + steigende Zinsen = Kursverlust). Schwäche: starre Schwelle `>10`; bei `stable` oder Duration ≤10 immer NEUTRAL, obwohl eine 9er-Duration durchaus zinssensitiv ist.
- **Lösung:** Kontinuierliche Risikobewertung über die erwartete Kursänderung (Duration × erwartete Yield-Änderung + Convexity-Korrektur) statt binärer Schwelle.

#### `bond_credit` DEFAULT_RATES
- **Befund (⚠️):** Werte als **Prozent** hinterlegt (z. B. „B": 4.3), aber das Feld heißt `default_probability` und wird ohne `/100` weitergegeben → Verwechslungsgefahr Prozent vs. Dezimalbruch. Größenordnungen entsprechen grob Moody's-1J-Raten (plausibel). Es fehlen **Recovery Rate/LGD** und die Verknüpfung zum Spread (Credit Triangle `Spread ≈ PD × LGD`).
- **Lösung:** Einheit vereinheitlichen (Dezimalbruch) und dokumentieren. Recovery-Rate-Annahmen ergänzen; PD, LGD und Spread konsistent über das Credit Triangle verknüpfen.

#### `bond_credit` `_default_prob(moodys)`
- **Befund (⚠️):** PD nur aus `moodys`, während `_category` aus `primary = sp or moodys or fitch` kommt → Inkonsistenz: liegt nur S&P vor, ist `category` gesetzt, `default_probability` aber `None`.
- **Lösung:** PD aus demselben primären Rating ableiten wie die Kategorie; einheitliche Rating-Quelle/Priorisierung.

#### `bond_credit._default_prob` startswith
- **Befund (❌):** `startswith`-Matching auf einer **Moody's-only-Tabelle** ist gefährlich: Ein **S&P „CCC"** trifft über `startswith("C")` fälschlich die Moody's-`C`-Rate (50 %), obwohl CCC real bei einigen Prozent liegt — massive Fehleinschätzung. Vermischung der Rating-Skalen.
- **Lösung:** Rating zuerst auf eine **einheitliche Skala normalisieren** (S&P↔Moody's-Mapping-Tabelle), dann exakter Lookup statt Prefix-Matching. Getrennte PD-Tabellen je Skala oder ein gemeinsames normalisiertes Rating.

#### `bond_credit._category`
- **Befund (⚠️):** „C" ist **doppelt** in `JUNK_RATINGS` (Vermischung S&P/Moody's). Die Trennung „high_yield" vs. „junk" ist **nicht marktüblich** — Standard ist binär IG (≥BBB-/Baa3) vs. HY/Non-IG.
- **Lösung:** Binäre IG/Non-IG-Grenze als Hauptklassifizierung; optional feinere Sub-Stufen, aber konsistent auf normalisierter Skala. Duplikate entfernen.

#### `bond_credit._signal`
- **Befund (✅):** Upgrade → bullish, Downgrade → bearish (Ratingverbesserung = Spread-Einengung = Kursgewinn). Korrekt.
- **Lösung:** Beibehalten.

#### `bond_spread` run
- **Befund (❌):** **Keinerlei Spread-Berechnung** — alle Werte aus leerem Provider. Es fehlen: G-Spread (vs. interpolierte Govvy-Kurve), Z-Spread (konstanter Aufschlag auf die Spot-Kurve), OAS (Z-Spread bereinigt um Optionswert, erfordert Zinsmodell/Lattice), Plausibilitätsbeziehung OAS ≤ Z-Spread und **Spread-Duration** (zentrales Credit-Risikomaß).
- **Lösung:** Spreads berechnen: G-Spread aus interpolierter Staatskurve, Z-Spread via Solver gegen die Spot-Kurve, OAS über ein einfaches Zinsmodell für callable Bonds. Spread-Duration ergänzen. Konsistenzprüfung OAS ≤ Z-Spread.

#### `bond_spread._signal`
- **Befund (✅):** Tightening → bullish, Widening → bearish — korrekt. Schwäche: absolutes Spread-Niveau nur als vorhanden/None geprüft, nie zur Bewertung (Carry, vs. historischem Mittel) genutzt.
- **Lösung:** Spread-Niveau gegen historisches Mittel/Perzentil bewerten (Carry-/Value-Komponente).

#### `bond_chief_agent.run`
- **Befund (✅ neutral / ⚠️):** Reine Orchestrierung, keine Finanzmathematik. Es fehlt eine **Gesamtsicht** (konsolidiertes Signal, Duration×Spread-Duration zum Gesamtrisiko, Total-Return-/Carry-Roll-Down).
- **Lösung:** Gesamt-Bond-Urteil aus Duration-Risiko, Credit-Risiko (Spread-Duration × Spread-Trend) und Carry/Roll-Down bilden.

### Domänen-Fazit 5 (Top-3)
1. Keine Bond-Pricing-Engine — alle Kernkennzahlen sind Durchreiche-Felder eines leeren Providers.
2. Convexity und Spread-Duration vollständig ignoriert; keine Effective Duration für Optionalität; kein Yield-to-Worst.
3. Credit-Logik vermischt Moody's/S&P-Skalen fehlerhaft (startswith → CCC=50 %), entkoppelt PD von Spread, „junk"-Klasse nicht marktüblich.

---

## Domäne 6 — Index Deep Dive

### Übersichtstabelle

| Stelle | Konzept | Bewertung |
|---|---|---|
| `index_breadth_agent` | Breadth | ⚠️ Stub; Schwelle ok |
| `index_earnings` estimate_revision-Proxy | Fwd-PE < Trailing-PE = „up" | ❌ |
| `index_earnings` earningsGrowth | Single-Stock-Feld auf Index | ❌ |
| `index_earnings._signal` | ±10 % | ✅ |
| `index_momentum._compute_rsi` | SMA statt Wilder | ⚠️ |
| `index_momentum` MA200 (1y) | fragil | ❌ |
| `index_momentum._signal` | `not golden_cross and rsi>70` | ❌ BEARISH ~nie |
| `index_momentum` Relative Strength | vs. URTH | ⚠️ Währung/Überlappung |
| `index_price._pct` | kumulativ | ⚠️ TR vs. PR |
| `index_price` YTD | searchsorted | ✅ |
| `index_price` 52W High/Low | aus `info` | ⚠️ Inkonsistenz; ungenutzt |
| `index_valuation._signal` | −15 %/+20 % | ⚠️ Bullish-Bias |
| `index_valuation` shiller_cape | None | ❌ |
| `index_valuation` trailingPE Index | aus `get_info` | ⚠️ unzuverlässig |
| `index_valuation` falsy-check | `if pe` | ⚠️ Grenzfall; Zinsumfeld fehlt |
| `index_valuation` Earnings Yield/ERP | fehlt | ❌ |
| `index_valuation_range._method1` | Range-Position | ✅ |
| `index_valuation_range._method2` | PE vs. Mid | ⚠️ redundant zu M1 |
| `index_valuation_range._combine` | `_FUZZY_THRESHOLD 0,70` | ⚠️ zu streng |
| `index_valuation_range` EPS-Basis | trailingEps or forwardEps | ⚠️ Forward×Trailing-Mix |
| `sector_composition_agent` | hardcoded | ⚠️ Stub; NEUTRAL |
| `index_chief_agent.run` | Aggregation | ⚠️ keine Synthese |

### Detailbefunde + Lösungen

#### `index_breadth_agent`
- **Befund (⚠️):** Berechnet faktisch nichts (`run()` liefert immer `_DEFAULT`/NEUTRAL); als TODO dokumentiert. Breadth ist eine der aussagekräftigsten Index-Kennzahlen (Divergenz Index-Hoch vs. fallende Breadth = klassisches Top-Warnsignal). Hardcodierte Schwelle (>70 % bullish, <30 % bearish) ist als Konvention vertretbar.
- **Lösung:** % über MA200 aus den Komponenten-Preisen berechnen; kumulative Advance/Decline-Line; New-High/New-Low-Index. Solange Stub: nicht als „neutrale Information" in die Aggregation einrechnen (siehe Querschnitts-Lösung).

#### `index_earnings` estimate_revision-Proxy
- **Befund (❌):** Forward-PE < Trailing-PE bedeutet **erwartetes Gewinnwachstum**, nicht „Analysten haben hochrevidiert" — die Konzepte sind orthogonal (eine Aktie kann seit Monaten nach unten revidiert werden und trotzdem Fwd-PE<Trailing-PE haben). Der Fehler entscheidet den Trigger (`eps_growth>10 and revision=="up"`) mit.
- **Lösung:** Echte Estimate-Revisions über die zeitliche Veränderung der Konsensschätzung (z. B. FMP `analyst-estimates`, Anzahl Up-/Down-Revisionen 30/90 Tage).

#### `index_earnings` earningsGrowth (Single-Stock auf Index)
- **Befund (❌):** `earningsGrowth`/`revenueGrowth`/`operatingMargins` aus `get_info` sind **Einzelaktien-Felder**; bei Index-Tickern (`^GSPC`) liefert Yahoo sie meist nicht/als Müll → fast immer `None` → Default NEUTRAL.
- **Lösung:** Aggregierte (bottom-up) Index-EPS aus den Konstituenten oder offizielle S&P/STOXX-Aggregate verwenden.

#### `index_earnings._signal`
- **Befund (✅):** ±10 % YoY-EPS als Bull/Bear-Grenze plausibel und marktnah.
- **Lösung:** Beibehalten (Periodendefinition dokumentieren).

#### `index_momentum._compute_rsi`
- **Befund (⚠️):** Standard-RSI nach **Wilder** nutzt Wilder's Smoothing (modifizierte EMA), nicht `rolling(14).mean()` (= „Cutler's RSI"). Abweichung v. a. nach starken Einzelbewegungen → Inkonsistenz mit den marktüblichen 70/30-Schwellen.
- **Lösung:** `gain.ewm(alpha=1/period, adjust=False).mean()` analog Loss (Wilder-Smoothing).

#### `index_momentum` MA200 aus 1y
- **Befund (❌):** `get_price_history("1y")` ≈ 252 Tage; `rolling(200).mean()` ist nur am Ende knapp definiert. Der Cross-Detektor schaut auf die letzten 6 MA200-Punkte; bei kleinen Datenlücken kippt MA200 auf `NaN` und golden_cross auf `None` — sehr fragil.
- **Lösung:** Mindestens „2y" laden, damit MA200 über das gesamte Cross-Fenster stabil definiert ist.

#### `index_momentum._signal`
- **Befund (❌):** BEARISH nur bei `not golden_cross and (rsi is None or rsi>70)`. `golden_cross==False` = Death Cross (bärisch), kombiniert mit `rsi>70` (überkauft) — beides ~nie gleichzeitig → BEARISH praktisch unerreichbar. Bei `golden_cross is None` (kein frisches Cross — der häufigste Fall) immer NEUTRAL → der Agent ignoriert die bereits berechnete Trendlage (MA50/MA200-Status).
- **Lösung:** Trendrichtung über den **Status** `ma50 vs ma200` (nicht nur das Crossing-Event) plus RSI-Extreme bewerten: über MA200 + RSI nicht überkauft = bullish; unter MA200 / Death Cross = bearish.

#### `index_momentum` Relative Strength
- **Befund (⚠️):** Differenz der 1J-Total-Returns vs. MSCI World (URTH) ok als simple RS-Kennzahl. Aber: (a) URTH ist USD-ETF — ein EU/CH-Index in Lokalwährung verglichen → **Währungseffekt** verfälscht; (b) US-Indizes sind ~70 % von URTH → Benchmark fast deckungsgleich, RS wenig informativ.
- **Lösung:** Währungskonsistente Vergleichsbasis (gleiche Währung) und regionsspezifischen Benchmark (z. B. STOXX600 für EU) verwenden.

#### `index_price._pct`
- **Befund (⚠️):** `_ago(days)` mit Kalendertagen + searchsorted ist als Näherung ok. Renditen sind **kumulativ, nicht annualisiert** (unkritisch, da nur perf_1y/perf_3m genutzt). **Total Return vs. Price Return:** Index-Kurse (`^GSPC`) sind Price-Return → Dividenden fehlen, perf_5y wird ~1,5–2 %/J unterzeichnet.
- **Lösung:** TR vs. PR kennzeichnen; wo möglich Total-Return-Indizes nutzen. Bei Vergleich verschiedener Horizonte konsistent annualisieren.

#### `index_price` YTD
- **Befund (✅):** `searchsorted("YYYY-01-01")` nimmt den ersten Handelstag ≥ 1. Januar — korrekt.
- **Lösung:** Beibehalten.

#### `index_price` 52W High/Low
- **Befund (⚠️):** Aus `info` geholt, während alles andere aus der Historie kommt → Inkonsistenzrisiko (anderer Datenstand). Werden zudem nirgends im Signal genutzt (Distanz zum 52W-Hoch wäre ein klassischer Momentum-Input).
- **Lösung:** 52W-High/Low aus derselben Historie berechnen. Distanz zum 52W-Hoch als Momentum-Faktor einbeziehen.

#### `index_valuation._signal`
- **Befund (⚠️):** Nach Bug #41 simple Schwellen, aber **Asymmetrie bleibt** — BULLISH bei `pe < lo*0.85` (−15 %), BEARISH erst bei `pe > hi*1.20` (+20 %). Unbegründeter **Bullish-Bias** (man wird leichter „günstig" als „teuer").
- **Lösung:** Symmetrische Puffer (oder gar keine — die Range ist bereits die Toleranz). Auf der teuren Seite eher strenger als großzügiger (konservativer Standard).

#### `index_valuation` shiller_cape = None
- **Befund (❌):** CAPE nicht implementiert (TODO) → die einzige inflationsbereinigte, mean-reversion-fähige Kennzahl fehlt. Trailing-PE allein ist prozyklisch (am Gewinnhoch niedrig, am Gewinntief hoch → Value Trap).
- **Lösung:** CAPE = Preis / (10J-Durchschnitt der inflationsbereinigten EPS) implementieren. US: Shiller-Daten (multpl.com); EU/CH: laut Projekt-Memory bereits FMP für 10J-EPS vorgesehen (FMP_API_KEY).

#### `index_valuation` trailingPE für Index
- **Befund (⚠️):** `trailingPE` aus `get_info` ist für Index-Ticker bei Yahoo unzuverlässig/oft leer → bei `None` ist das gesamte Bewertungssignal NEUTRAL.
- **Lösung:** Index-PE aus aggregierten Konstituenten-Gewinnen oder offiziellen Quellen.

#### `index_valuation` falsy-check + Zinsumfeld
- **Befund (⚠️):** `round(pe, 2) if pe else None` — ein gültiger Wert `0.0` würde zu `None` (bei PE praktisch irrelevant, methodisch unsauber). **Wichtiger:** keine **Zinsumfeld-Berücksichtigung** — PE 22 ist bei 1,5 % Anleiherendite günstig, bei 5 % teuer; statische `_PE_RANGES` ignorieren das Zinsniveau.
- **Lösung:** `is not None` statt Falsiness. Bewertung zinsabhängig machen (Fed-Modell / Equity Risk Premium, s. u.).

#### `index_valuation` Earnings Yield / ERP
- **Befund (❌):** Earnings Yield (=1/PE) und **ERP = Earnings Yield − risikofreier Zins** werden nirgends berechnet, obwohl zentral. Das ist die Brücke zwischen Bewertung und Zinsumfeld.
- **Lösung:** `earnings_yield = 1/pe_trailing`; `erp = earnings_yield − treasury_10y` (lokaler Staatsanleihen-Yield je Region). ERP als Kern-Bewertungssignal.

#### `index_valuation_range._method1`
- **Befund (✅):** Lineare Interpolation zwischen low/mid/high, geclippt, Score [−1,+1]; `price = EPS × KGV-Band` ist die klassische Justified-PE-Range. Korrekt.
- **Lösung:** Beibehalten.

#### `index_valuation_range._method2`
- **Befund (⚠️):** Redundant zu Method 1 — beide basieren auf `pe_mid` und letztlich `eps × pe`. Wenn `current = pe_trailing × eps`, sind beide dieselbe Information, nur unterschiedlich skaliert → Mittelung korrelierter Schätzer = Scheindiversifikation. Können bei abweichendem EPS-Stand sogar widersprüchlich werden.
- **Lösung:** Eine konsistente PE-basierte Range verwenden oder eine **echt unabhängige** zweite Methode ergänzen (z. B. Dividend-Discount oder ERP-basiert) statt einer Reskalierung derselben Größe.

#### `index_valuation_range._combine` / `_FUZZY_THRESHOLD`
- **Befund (⚠️):** Schwelle 0,70 ist **sehr hoch** — bei Method 2 ≈ 0 muss der Preis fast am unteren Range-Rand liegen, um „undervalued" auszulösen → Signal fast immer „fair"/NEUTRAL. (Trotz Namens keine echte Fuzzy-Logik mehr, konsistent mit Bug-#41-Linie.)
- **Lösung:** Schwelle empirisch kalibrieren (deutlich niedriger), sodass der Agent realistische Voten abgibt; oder graduelles Signal (Score) statt harter Schwelle.

#### `index_valuation_range` EPS-Basis
- **Befund (⚠️):** `trailingEps or forwardEps` — fällt auf Forward-EPS zurück, multipliziert dann mit **Trailing-KGV-Bändern** → Forward-EPS (i. d. R. höher) × Trailing-PE = Fair-Value-Range zu hoch → Preis erscheint „günstiger".
- **Lösung:** Konsistenz: Forward-EPS nur mit Forward-PE-Bändern, Trailing-EPS mit Trailing-Bändern.

#### `sector_composition_agent`
- **Befund (⚠️):** Komplett hardcodierte Werte (Stand „approx. 2025"), `top_10_concentration=None`, Signal immer NEUTRAL. Teils fragwürdig (`^DJI` „Technology 22 %" beim preisgewichteten Dow diskutabel). Konzentration ist eine relevante Risikokennzahl („Magnificent 7"), wird aber nicht berechnet.
- **Lösung:** Sektor-/Top-10-Konzentration dynamisch aus aktuellen Indexgewichten berechnen (HHI als Konzentrationsmaß). Statische Platzhalter ersetzen.

#### `index_chief_agent.run`
- **Befund (⚠️):** Reiner Aggregator, keine **Gesamt-Signal-Synthese** über die 7 Sub-Signale (kein gewichtetes Voting, kein Konfliktauflöser zwischen BULLISH-Valuation und BEARISH-Momentum). Da viele Sub-Agenten faktisch immer NEUTRAL liefern (Breadth-Stub, Earnings/Valuation mangels Index-Daten), ist das Bild strukturell zu NEUTRAL verzerrt.
- **Lösung:** Top-down-gewichtete Synthese: Bewertung (Langfrist-Anker) + Momentum/Breadth (Timing) mit definierten Gewichten; Stub-/unavailable-Signale aus der Gewichtung herausnehmen.

### Domänen-Fazit 6 (Top-3)
1. Falsche Datenquelle für Index-Fundamentaldaten (Einzelaktien-Felder auf Index-Ticker → meist NEUTRAL).
2. Bewertung ignoriert Zinsumfeld/Inflation/CAPE komplett; zusätzlich Bullish-Bias durch asymmetrische Puffer.
3. Momentum-Signallogik fehlerhaft (BEARISH ~nie), RSI nicht Wilder, MA200 fragil; Breadth ein Stub.

---

## Domäne 7 — Commodity & Precious Metals Deep Dive

### Übersichtstabelle

| Stelle | Konzept | Bewertung |
|---|---|---|
| `commodity_valuation_range._percentile` | `(cur−min)/(max−min)` | ❌ kein echtes Perzentil |
| `commodity_valuation_range._position` | <20 cheap/>80 expensive | ⚠️ mean-reverting ohne Trend; cost-curve None |
| `commodity_valuation_range.run` | nominale Historie | ⚠️ nominal; Roll-Yield |
| `cot_agent.run` | CFTC COT | ❌ Stub |
| `cot_agent._signal` | Konträr | ⚠️ absolute Schwellen; COT-Index besser |
| `seasonality.run` | Monatsrenditen 10J | ⚠️ n≥3; arithm. Mittel; nominal |
| `seasonality._signal` | avg>2 % & pos>60 % | ⚠️ als eigenständiges Signal überrepräsentiert |
| `supply_demand` S2F-Dict | Bestand/Produktion | ❌ inkonsistente Definition |
| `supply_demand` Schwellen/run | Knappheit | ❌ Mehrwert-Teil Stub |
| `cross_metal` Konstanten | GS=68; Gold/Platin=1,0 | ⚠️/❌ veraltet/falsch |
| `cross_metal._ratio_signal` | ±15 % vom Schnitt | ⚠️ Richtung unklar; Fallback maskiert |
| `precious_metal_price.run` | Preis/RSI/MA/Realzins | ❌ weitgehend Stub |
| `precious_metal_price` STOCK_TO_FLOW | Gold 62/Silber 22 | ⚠️ Definition unklar; inkonsistent |
| `precious_metals_valuation` Methode 1 | Realzins, Anker=Preis | ❌ zirkulär |
| `precious_metals_valuation` Methode 2 | 0,85–1,40×1200$ | ❌ Anker falsch |
| `precious_metals_valuation` Methode 3/Kombi | AISC; min/max-Union | ⚠️/❌ |
| `precious_metals_valuation` fehlende Faktoren | USD/Zentralbank/ETF | ⚠️ |
| Chiefs (commodity/precious) | Aggregation | ⚠️ keine Gewichtung; COT hart NEUTRAL |

### Detailbefunde + Lösungen

#### `commodity_valuation_range._percentile`
- **Befund (❌):** Kein Perzentil, sondern **Min-Max-Spanne** `(current − min)/(max − min)`. Ein einzelner Ausreißer-Spike verzerrt die ganze Skala → der aktuelle Preis erscheint fälschlich „billig".
- **Lösung:** Echtes empirisches Rang-Perzentil: `percentile = (hist < current).mean() * 100`. Mindestens Winsorisierung oder Quantil-Grenzen (5./95. Perzentil) statt roher Min/Max.

#### `commodity_valuation_range._position`
- **Befund (⚠️):** Schwellen (<20 cheap, >80 expensive) plausibel, aber rein **mean-reverting ohne Trend-Filter** — „expensive bei 80. Perzentil" zu shorten ist in einem Superzyklus (Energie 2021–22) gefährlich. `production_cost_low/high` sind hartcodiert `None` — gerade bei Rohstoffen ist die Cost-Curve der eigentliche Bewertungsanker.
- **Lösung:** Range-Signal mit Momentum-/Trend-Regime kombinieren. Produktionskosten-Kurve (Cost-Curve-Perzentile) als fundamentalen Anker anbinden.

#### `commodity_valuation_range.run`
- **Befund (⚠️):** Nominale Preishistorie — über 10 Jahre verzerrt Inflation die Range erheblich (~25–30 % USD-Kaufkraftverlust); ein nominaler 10J-Höchststand kann real ein Mittelwert sein. Roll-Yield bei `=F`-Tickern ebenfalls ignoriert.
- **Lösung:** Reale (inflationsbereinigte) Preise für lange Ranges. Roll-Yield/Investierbarkeit über Total-Return-Indizes berücksichtigen.

#### `cot_agent.run`
- **Befund (❌):** Reiner **Stub** — `run()` gibt immer `_DEFAULT` (alle `None`). Keine CFTC-Daten; das COT-Signal fließt nie ein (auch der PM-Chief setzt `cot_signal=NEUTRAL` hart).
- **Lösung:** CFTC-Disaggregated-COT (Managed Money) anbinden und echte Positionierung berechnen.

#### `cot_agent._signal`
- **Befund (⚠️):** Konträre Grundidee korrekt, aber **absolute, asymmetrische Schwellen** (`<−20` bullish, `>50` bearish) gelten für jeden Rohstoff gleich, obwohl die typische Positionierungsspanne stark variiert. Net-Long ist strukturell positiv → `>50 % OI` wird bei vielen Kontrakten nie erreicht → bearish löst praktisch nie aus.
- **Lösung:** **COT-Index** (Net-Position normalisiert auf das eigene 1–3-Jahres-Min/Max, Skala 0–100) statt starrer %-OI-Schwellen. „Managed Money"-Kategorie statt Legacy „non-commercial".

#### `seasonality.run`
- **Befund (⚠️):** (1) 10J → max. ~10 Beobachtungen/Monat, Mindestfilter `<3` viel zu lax → statistisch nicht belastbar (kein Signifikanztest, keine Konfidenzintervalle); (2) `pct_change().dropna()` reduziert die kleine Stichprobe weiter; (3) **arithmetisches Mittel** überschätzt bei volatilen Rohstoffen die zentrale Tendenz; (4) nominal → Inflationstrend gibt jedem Monat einen leichten positiven Bias.
- **Lösung:** Deutlich längere Historie (15–30+ Jahre). Signifikanztest (t-Test gegen 0) und Konfidenzintervalle. Median oder geometrisches Mittel statt arithmetischem. Reale Preise oder Detrending.

#### `seasonality._signal`
- **Befund (⚠️):** Logik defensiv ok, aber Saisonalität sollte **nie ein eigenständiges Handelssignal** sein, sondern nur ein Tilt-Faktor — als gleichgewichtetes Signal neben Bewertung/Positionierung überrepräsentiert.
- **Lösung:** Saisonalität nur als kleingewichteten Tilt in die Aggregation, nicht als vollwertiges Einzelsignal.

#### `supply_demand` S2F-Dict
- **Befund (❌):** Werte konzeptionell falsch/inkonsistent — Öl 0,1/Kupfer 0,5 meinen offensichtlich nicht „Gesamtbestand/Jahresproduktion"; selbst als kommerzielle Lager stimmt Kupfer (0,5 vs. real ~0,02–0,05) nicht. Gleichzeitig nutzt der Edelmetall-S2F (Gold 62/Silber 22) die oberirdischen Bestände/Produktion → **zwei verschiedene S2F-Definitionen** in der Codebasis, nicht vergleichbar.
- **Lösung:** Eine einheitliche, dokumentierte S2F-Definition für alle Rohstoffe. Für Industrierohstoffe sind Lagerreichweiten (Tage) das relevantere Maß; für Edelmetalle oberirdische Bestände/Produktion. Klar trennen und benennen.

#### `supply_demand` Schwellen/run
- **Befund (❌):** Der Mehrwert-Teil ist **Stub** — `inventory_current/avg_5y/pct_vs_avg`, `production_change_yoy` alle `None`, `_signal` wird nie mit echten Daten gefüttert → Signal immer NEUTRAL. Nur das statische S2F-Label kommt durch (eine strukturelle Konstante, kein zyklisches Signal).
- **Lösung:** Echte Lagerbalancen (EIA/USDA/LME) anbinden; das preisrelevante Signal aus Lagerveränderung vs. 5J-Schnitt berechnen. S2F nur als Knappheits-Kontext, nicht als Timing-Signal.

#### `cross_metal` Konstanten
- **Befund (⚠️/❌):** `GOLD_SILVER_AVG = 68` zu niedrig für lange Historie und ignoriert, dass die Ratio **trendet** (kein stabiler Mean-Revert-Anker). `GOLD_PLATINUM_AVG = 1.0` veraltet/falsch — Gold/Platin liegt seit Jahren bei ~1,8–2,5; ein Anker von 1,0 labelt Platin permanent als „extrem teuer". `gold_platinum_ratio` wird berechnet, aber **nie zu einem Signal** verarbeitet.
- **Lösung:** Rollierende Perzentile/Z-Scores statt fixer Mean-Revert-Anker. Gold/Platin-Anker auf aktuelles Niveau (~2) bzw. Perzentil. Gold/Platin-Ratio tatsächlich in ein Signal überführen.

#### `cross_metal._ratio_signal`
- **Befund (⚠️):** (1) Fallback `gs_ratio or GOLD_SILVER_AVG` prüft bei None den AVG gegen sich selbst → deviation 0 → NEUTRAL, **maskiert fehlende Daten** als valides Signal; (2) **Richtung unklar** — hoher GS-Ratio → `BEARISH`, aber wofür? Der Agent analysiert ein bestimmtes Metall, das Signal ist aber metall-unabhängig auf Gold/Silber bezogen; ein hoher GS-Ratio ist eigentlich **bullish für Silber** (Mean-Reversion), nicht generisch bearish; (3) ±15 % ist für eine trendende Ratio eng → häufige Fehlsignale.
- **Lösung:** Fehlende Daten als `UNAVAILABLE` behandeln, nicht als NEUTRAL. Signal metallspezifisch zuordnen (hoher GS-Ratio → bullish Silber / bearish Gold relativ). Schwelle über Perzentil statt fixer ±15 %.

#### `precious_metal_price.run`
- **Befund (❌):** `performance={}`, `rsi=None`, `ma50/ma200=None`, `real_yield_correlation=None`, `signal=NEUTRAL` — alle quantitativen Felder TODO. Eine 5J-Historie wird geladen, aber **nicht verwendet**. Der wichtigste Gold-Treiber (**Realzins-Sensitivität**) ist nicht berechnet.
- **Lösung:** Performance/RSI/MA aus der geladenen Historie tatsächlich berechnen. Realzins-Korrelation/-Sensitivität (Regression Goldpreis vs. 10J-TIPS-Realzins) implementieren — der zentrale fundamentale Faktor.

#### `precious_metal_price` STOCK_TO_FLOW
- **Befund (⚠️):** Gold-S2F ~62 plausibel; Silber 22 diskutabel (viel Silber wird industriell verbraucht). **Wichtig:** Diese Definition (oberirdische Bestände) ist **unvereinbar** mit der S2F-Definition im `supply_demand_agent` (Lager/Verbrauch).
- **Lösung:** Einheitliche S2F-Definition systemweit (siehe `supply_demand` S2F oben). Definition explizit dokumentieren.

#### `precious_metals_valuation` Methode 1 (Realzins)
- **Befund (❌):** (1) Anker ist der **aktuelle Preis selbst** (`base = current_price`) → das Modell ist **zirkulär** und kann den aktuellen Preis nie als über-/unterbewertet ausweisen; (2) `(0 − real_rate) × 150` ist eine willkürliche Daumenregel ohne empirische Basis; (3) **Skalenfehler bei Silber** — dieselbe +150-USD-Regel auf einen ~28-USD-Silberpreis ist absurd; (4) asymmetrische Faktoren 0,7/1,3 ad hoc.
- **Lösung:** Preis-**unabhängiger** Anker aus einer empirischen Gold-Realzins-**Regression** (mit Konstante). Sensitivität **metallspezifisch und prozentual** statt fixer USD-Beträge. Asymmetrie nur mit Begründung.

#### `precious_metals_valuation` Methode 2 (Inflationsbereinigt)
- **Befund (❌):** `GOLD_INFLATION_ADJ_AVG = 1200` (2024 USD) → Fair-Range ~1020–1680 USD; bei Goldpreis ~2300–3000 USD wird Gold **permanent als massiv überbewertet** ausgewiesen. „Mean Reversion zum realen Langzeitschnitt" ist für Gold empirisch nicht belegt (der reale Preis ist seit 2005 strukturell gestiegen).
- **Lösung:** Diese Methode entfernen oder durch ein Modell ersetzen, das den strukturellen Aufwärtstrend (Zentralbanknachfrage, Geldmengenwachstum) berücksichtigt — kein statischer realer Mittelwert.

#### `precious_metals_valuation` Methode 3 (AISC) + Kombination
- **Befund (⚠️/❌):** AISC als unterer Boden konzeptionell richtig (Grenzkosten stützen den Preis), aber: (a) Werte (1050–1800) veraltet (Gold-AISC-Median 2024/25 ~1250–1450); (b) **Kombinationslogik fehlerhaft** — `combined_low = min(alle lows)`, `combined_high = max(alle highs)` erzeugt eine **maximal breite Union** statt eines konvergierenden Fair-Value → `_position` (±5 % Puffer) liefert fast immer „fair"/NEUTRAL.
- **Lösung:** AISC mit aktuellen Daten. Kombination als **gewichteter Mittelwert/Median** der Methoden-Ranges (oder Schnittmenge), nicht als Union der Extreme.

#### `precious_metals_valuation` fehlende Faktoren
- **Befund (⚠️):** Es fehlen die zentralen Gold-Treiber: **USD-Index** (invers zum DXY), **Zentralbank-Nachfrage** (seit 2022 dominant), **ETF-Flows** und die explizite **Realzins-Korrelation**.
- **Lösung:** USD-Effekt, Zentralbank-Käufe und ETF-Flows als Faktoren ergänzen; Realzins-Korrelation aus dem Price-Agent einbinden.

#### Chiefs (commodity/precious metals)
- **Befund (⚠️):** (1) Nur strukturelle Aggregation (parallel `gather`), **keine gewichtete Signal-Synthese** — unzuverlässige Signale (Saisonalität mit n<10) werden nicht heruntergewichtet; (2) im PM-Chief `cot_signal=NEUTRAL` **hart verdrahtet**, obwohl ein COT-Agent existiert; (3) `currency_impact={}` leer — der USD-Effekt fehlt.
- **Lösung:** Gewichtete Synthese mit Zuverlässigkeits-Gewichten je Signal. COT-Agent verdrahten statt hart NEUTRAL. USD-Effekt erfassen und einbeziehen.

### Domänen-Fazit 7 (Top-3)
1. Edelmetall-Bewertung methodisch unbrauchbar (zirkulär + falsche Anker 1200$/1.0 + Range-Union → immer „fair"; Silber-Skalenfehler).
2. Zentrale fundamentale Treiber sind Stubs (COT, Supply/Demand, Realzins, USD).
3. Fragwürdige Kennzahlen bei den implementierten Teilen (Min-Max statt Perzentil, dünne Saisonalität, falsche Cross-Metal-Anker/Richtung, zwei S2F-Definitionen).

---

## Domäne 8 — Core / Statistik / Judgment / Backtester / Portfolio

### Übersichtstabelle

| Stelle | Konzept | Bewertung |
|---|---|---|
| `statistics.z_score` | Sample-Z, n≥3 | ⚠️ Mindest-N zu klein; Normalannahme |
| `statistics.compute_severity` | Zählung | ⚠️ keine Effektstärke; kein Multiple-Testing |
| `recommendation.compute_confidence` | additiv ab 0,70 | ❌ nicht kalibriert |
| `recommendation.derive_recommendation` | Schwellen 0,35/0,50 | ⚠️ keine Positionsgröße/Risiko |
| `judgment._derive_alignment` | „≥3 bullish" | ⚠️ absolute Schwelle; gleichgewichtet |
| `judgment._backtester_summary` | „accuracy_30d" | ⚠️ irreführend beschriftet |
| `backtester` judgment/bottom_up | Hit-Rate vs. Spot | ❌ Survivorship/Horizont/Benchmark |
| `top_down_backtester._accuracy` | Regime-Adjazenz | ❌ Zirkularität |
| `regime.detect` | Composite+Fuzzy+Trend | ⚠️ Gewichte/Sprünge/Confidence/History |
| `regime` inflation-Regel | Deflation = 0,0 | ⚠️ |
| `anomaly` bottom_up/top_down `_check` | Z-Score-Ausreißer | ⚠️ Mindest-N/MAD/Multiple-Testing |
| `anomaly` insider-Check | >10 Transaktionen | ⚠️ absolut; Richtung ignoriert |
| `portfolio_monitor` | Klumpenrisiko/Health | ⚠️ keine Korrelation/VaR; FX |
| `top_down_context` | Buffett/Spread-Notes | ✅ (Buffett nicht länderspezifisch) |

### Detailbefunde + Lösungen

#### `statistics.z_score`
- **Befund (⚠️):** Berechnung korrekt (Bessel n−1). Aber: (a) **Mindeststichprobe 3 viel zu klein** — bei n=3–5 dominiert der Std-Schätzfehler; Standard sind 20–30+; (b) **keine Normalitäts-/Stationaritätsprüfung** — Finanzkennzahlen (KGV, VIX, Spreads) sind rechtsschief und fat-tailed; Schwelle Z=2,5 unterstellt Normalität; (c) der aktuelle Wert ist oft selbst in der History → Bias.
- **Lösung:** Mindest-N deutlich anheben (≥20–30). **Modifizierter Z-Score auf Median/MAD-Basis** (Iglewicz-Hoaglin, Schwelle 3,5) für robuste, fat-tail-feste Ausreißererkennung. Aktuellen Wert aus der Referenz-History ausschließen.

#### `statistics.compute_severity`
- **Befund (⚠️):** Reine Abzählung ohne Gewichtung der Effektstärke (Z=2,6 zählt wie Z=8). **Kein Multiple-Testing-Korrektiv** — bei ~4–6 parallelen Z-Checks steigt die False-Positive-Wahrscheinlichkeit (Family-Wise Error).
- **Lösung:** Effektstärken aggregieren statt zählen. Bonferroni/Holm-Korrektur der Schwelle oder FDR-Kontrolle bei multiplen Tests.

#### `recommendation.compute_confidence`
- **Befund (❌):** Die „Konfidenz" ist ein **arbiträr kalibrierter Score, keine Wahrscheinlichkeit**: (a) Basis 0,70 ohne Grundlage; (b) **additive statt multiplikativer** Verknüpfung unabhängiger Evidenzen (bei Wahrscheinlichkeiten wäre Bayes/Log-Odds korrekt); (c) **nicht gegen die Backtest-Trefferquote kalibriert** — 80 % Konfidenz sollte ~80 % Trefferrate bedeuten; der `_backtester_summary` fließt nur als LLM-Text ein, nicht quantitativ.
- **Lösung:** Konfidenz aus der **historischen bedingten Trefferrate** je `(alignment, severity)`-Bucket schätzen (Reliability-/Calibration-Plot). Evidenzen über Log-Odds/Bayes verknüpfen. Backtest-Ergebnisse quantitativ einbinden.

#### `recommendation.derive_recommendation`
- **Befund (⚠️):** Schwellen 0,35/0,50 willkürlich. Schwerwiegender: **keine Positionsgrößen-/Risikodimensionierung** (kein Kelly, kein Vol-Targeting, keine ATR-/Stop-Logik). BUY/SELL/SHORT binär ohne Bezug zu Konfidenz oder Asset-Volatilität. Short ohne Borrow-Kosten/Squeeze-Risiko (obwohl `short_float_pct`/`days_to_cover` vorhanden).
- **Lösung:** Positionsgröße aus Konfidenz und Volatilität (fractional Kelly oder Vol-Targeting). Short-Empfehlungen um Borrow-Kosten/Squeeze-Flag (days_to_cover) anreichern. Schwellen empirisch kalibrieren.

#### `judgment._derive_alignment`
- **Befund (⚠️):** Harte Schwelle „≥3" problematisch, weil die Anzahl gültiger Signale stark variiert (None-Werte gefiltert) — bei 3 verfügbaren Signalen trivial „aligned", bei 6 streng. Alle Signale **gleichgewichtet** (Valuation aus mehreren Methoden zählt wie ein einzelnes Insider-Signal).
- **Lösung:** **Relative** Schwelle (Anteil >60 % der nicht-neutralen Signale). Signale nach prädiktiver Kraft gewichten.

#### `judgment._backtester_summary`
- **Befund (⚠️):** Die als „System-Treffsicherheit" gezeigte `accuracy_30d` stammt für Judgment aus einer Stichprobe **ohne fixes Haltefenster** → die „30 Tage"-Beschriftung ist irreführend.
- **Lösung:** Beschriftung an das tatsächliche Messfenster anpassen oder ein fixes Forward-Window einführen (siehe Backtester unten).

#### `backtester` (judgment/bottom_up)
- **Befund (❌):** Mehrere schwere Fehler:
  1. **Variabler Horizont:** `return_pct = (price_now − price_then)/price_then` misst von Analyse bis heute — eine 3-Tage- und eine 89-Tage-Empfehlung werden in dieselbe Trefferquote gemischt.
  2. **Spot-Repricing:** stets der heutige `last_price` → das Urteil über dieselbe Empfehlung ändert sich bei jedem Lauf; kein eingefrorener Forward-Return.
  3. **Keine Benchmark-/Risikoadjustierung:** BUY „correct" bei +3 % absolut, auch wenn der Markt +10 % machte (Underperformance); keine Vola-Adjustierung.
  4. **Willkürliche, asymmetrische Schwellen** (BUY +3 %, SELL −3 %, HOLD ±5 %); die „neutral"-Klasse (|ret|≤1,5 %) **definiert Fehler weg** → überschätzt die Trefferquote.
  5. **Keine Transaktionskosten, Slippage, Gebühren, Steuern, Dividenden;** bei SHORT keine Borrow-Kosten.
  6. **Survivorship Bias:** delistete/insolvente Ticker → `None` → `continue` übersprungen → genau die Totalverluste fallen aus der Statistik.
  7. **Kleine Stichprobe / keine Signifikanz** (keine Konfidenzintervalle, keine Mindest-N).
  8. **Keine klassischen Performance-Metriken** (Sharpe/Sortino/MaxDD/annualisierte Rendite/Information Ratio/Profit Factor) — eine reine Hit-Rate ohne Payoff-Ratio ist irreführend.
- **Lösung:** **Fixes Forward-Window** je Eintrag (z. B. exakt 30/60/90 Tage, event-time aligned) mit eingefrorenem Forward-Return-Snapshot. **Marktbereinigter Return** (Alpha vs. Benchmark) und Vola-Adjustierung. „Neutral"-Klasse entfernen. Transaktionskosten/Slippage/Borrow-Kosten/Dividenden einrechnen. Delistete Titel als Totalverlust einbeziehen (Survivorship beheben). Konfidenzintervalle + Mindest-N. Sharpe/Sortino/MaxDD/Profit Factor ergänzen.

#### `top_down_backtester._accuracy`
- **Befund (❌):** **Look-ahead/Zirkularität** — die „Treffsicherheit" misst, ob historische Regime-Einträge adjazent zum **heutigen** Regime (`ref_regime = latest`) sind. Das ist kein Prognose-Backtest, sondern ein Maß für die Autokorrelation/Glätte der Regime-Zeitreihe (konstruktionsbedingt hoch). Zudem: RECOVERY/DEPRESSION nicht im `REGIME_CYCLE` → potenzieller KeyError-Fallback → systematisch „incorrect".
- **Lösung:** Echten Prognose-Backtest: Regime-Prognose zum Zeitpunkt t vs. **realisiertes** Regime/Marktergebnis zu t+h. RECOVERY/DEPRESSION in die Zyklus-/Adjazenzlogik aufnehmen.

#### `regime.detect`
- **Befund (⚠️):** (a) **Gewichtssumme ~1,17** (nicht 1,0), Normierung durch `weight_total` der vorhandenen Keys → Composite hängt davon ab, welche Indikatoren vorliegen; (b) **diskrete Scoring-Funktionen** erzeugen Sprungstellen an Schwellen; (c) **Confidence** `abs(composite)*1.5+0.3` ohne statistische Bedeutung; (d) `_MAX_HISTORY=8` Punkte für den Trend (`current − mean`) sehr grob; (e) Gauss-Zentren/Breiten nicht empirisch kalibriert.
- **Lösung:** Gewichte auf 1,0 normieren und Re-Normalisierung bei fehlenden Indikatoren explizit machen. Sanfte (kontinuierliche) Scoring-Funktionen statt harter Schwellen. Confidence aus Fuzzy-Membership-Abständen. Trend über Regression statt `current − mean`. Gauss-Parameter empirisch kalibrieren.

#### `regime` inflation-Regel
- **Befund (⚠️):** **Deflation (<1 %) wird mit 0,0 bewertet** (alle Zweige falsch → 0,0), obwohl Deflation makroökonomisch klar negativ ist (Schuldendeflation, Nachfrageaufschub).
- **Lösung:** Deflation negativ scoren — Glockenkurve um das 2 %-Ziel mit negativen Flanken nach beiden Seiten.

#### `anomaly` bottom_up/top_down `_check`
- **Befund (⚠️):** (a) **Mindesthistorie 5** statistisch unzureichend für Z=2,5; (b) **keine MAD-Robustifizierung** für fat-tailed Größen (VIX/Spreads/KGV) — Mittelwert+Std werden durch den Ausreißer selbst kontaminiert (maskierter Ausreißer); (c) **Multiple Testing** über mehrere Kennzahlen ohne Korrektur. Positiv: Buffett-Z gegen 10J-History methodisch sinnvoller.
- **Lösung:** Mindest-N anheben, MAD-basierter robuster Z-Score, Multiple-Testing-Korrektur (analog `statistics`).

#### `anomaly` insider-Check
- **Befund (⚠️):** „>10 Transaktionen = Anomalie" — absoluter Schwellenwert ohne Normierung an Unternehmensgröße/typische Frequenz; ignoriert die **Richtung** (Käufe vs. Verkäufe).
- **Lösung:** An die typische Insider-Frequenz/Unternehmensgröße normieren; Netto-Richtung (wertgewichtet) einbeziehen (konsistent mit `insider_agent`-Fix).

#### `portfolio_monitor`
- **Befund (⚠️):** (a) Konzentration nur über **Wertanteile**, keine **Korrelationen** — echtes Klumpenrisiko ist ein Kovarianz-/Marginal-Risk-Contribution-Problem; (b) `ASSET_CLASS_THRESHOLD 0,80` sehr lax (80 % in einer Klasse als Grenze); (c) Verlustschwelle −15 % ohne Vola-Normierung; (d) **Health-Ampel** zählt nur Alert-Anzahl ohne Gewichtung; (e) `total_value` mischt Währungen ohne FX-Umrechnung (Feld `total_value_usd`, aber `current_price` kommt unkonvertiert aus yfinance); (f) keine **Drawdown-/VaR-/Volatilitätskennzahlen** auf Portfolioebene.
- **Lösung:** Klumpenrisiko über Marginal Risk Contribution (Kovarianzmatrix der Positionen). Schwellen verschärfen/risikoadjustieren. Verlust-Trigger vol-normiert (z. B. in σ statt fixer −15 %). Health-Ampel nach Schweregrad gewichten. **FX-Umrechnung** aller Positionen in die Basiswährung. Portfolio-VaR/Volatilität/Max-Drawdown ergänzen.

#### `top_down_context`
- **Befund (✅):** Z-Score gegen eigene 10J-History mit Fallback auf absolute Schwellen (75 %/135 % Buffett, 150/300bp Spread) ist marktüblich. **Einschränkung:** absolute Buffett-Schwellen nicht länderspezifisch (US-typische 75/135 % passen nicht für CH/EU); der Z-Score-Pfad mildert das, der Fallback nicht.
- **Lösung:** Fallback-Schwellen länderspezifisch kalibrieren (konsistent mit dem Buffett-Indicator-Fix in Domäne 1).

### Domänen-Fazit 8 (Top-3)
1. Backtest-Validität fundamental gebrochen (variabler Horizont, Spot-Repricing, Survivorship Bias, keine Benchmark-Bereinigung, „neutral" definiert Fehler weg; Top-Down zirkulär) → Trefferquoten systematisch nach oben verzerrt.
2. Keine Risikoadjustierung auf allen Ebenen (kein Sharpe/Sortino/MaxDD/Information Ratio, keine Positionsgröße, keine Kosten) — Hit-Rate ohne Payoff-Ratio ist wertlos.
3. Konfidenz nicht kalibriert und statistisch unsauber aggregiert (additiv ab 0,70, nicht gegen reale Trefferrate); Z-Scores auf zu kleinen Stichproben mit Normalannahme für fat-tailed Größen.

---

# Teil B — Priorisierte Master-Liste

Sortiert nach Auswirkung auf die **Ergebnisqualität** der Endempfehlung. Jeder Punkt mit konkretem Lösungsvorschlag.

## Priorität 1 — Kritisch (verfälschen Endurteil/Vertrauen direkt)

### 1.1 Backtest-Validität grundlegend reparieren
- **Problem:** Variabler Forward-Horizont, Spot-Repricing, Survivorship Bias, keine Benchmark-Bereinigung, „neutral"-Klasse definiert Fehler weg; Top-Down-Backtest misst Regime-Autokorrelation statt Prognosegüte.
- **Lösung:** Fixes Forward-Window je Eintrag (30/60/90 Tage, event-time aligned, eingefrorener Snapshot); marktbereinigter (Alpha) + vol-adjustierter Return; „neutral"-Klasse entfernen; delistete Totalverluste einbeziehen; Top-Down neu als echte Prognose t → realisiertes Ergebnis t+h. *Betrifft: alle drei `backtester`-Agenten.*

### 1.2 Risikoadjustierung einführen — überall
- **Problem:** Eine nackte Hit-Rate ohne Payoff-Ratio ist für Anlageentscheidungen wertlos (70 % Treffer mit seltenen Großverlusten = negativer Erwartungswert).
- **Lösung:** Sharpe/Sortino, Max Drawdown, annualisierte Rendite, Profit Factor, Information Ratio ergänzen; Transaktionskosten/Slippage/Borrow-Kosten einrechnen. *Betrifft: Backtester, `recommendation`, `portfolio_monitor`.*

### 1.3 Konfidenz gegen realisierte Trefferrate kalibrieren
- **Problem:** `compute_confidence` ist eine willkürliche additive Heuristik ab 0,70, ohne Bezug zur tatsächlichen Genauigkeit.
- **Lösung:** Konfidenz aus historischer bedingter Trefferrate je `(alignment, severity)`-Bucket schätzen; Backtest-Ergebnisse quantitativ einbinden (statt nur als LLM-Text); Evidenzen über Log-Odds verknüpfen.

### 1.4 Stubs sind keine Neutralität
- **Problem:** Breadth, COT, Supply/Demand, Bond-Pricing, Edelmetall-Preis liefern `NEUTRAL`, weil sie nichts berechnen → jede Chief-Aggregation wird strukturell Richtung neutral gezogen.
- **Lösung:** Status `AVAILABLE | UNAVAILABLE` je Sub-Ergebnis; `UNAVAILABLE` aus der Gewichtung herausnehmen (Re-Normalisierung) statt als gleichberechtigtes NEUTRAL mitzuzählen. Parallel die Stubs schrittweise implementieren.

## Priorität 2 — Schwere Einzelmodell-Fehler

### 2.1 „DCF" reparieren (`equity/valuation_range`)
- **Problem:** Mislabeled Gordon-Growth; inkonsistente g (Zähler/Nenner), keine Prognosephase, harter WACC 0,09, Umsatz-CAGR als FCF-Proxy, instabil bei WACC≈g.
- **Lösung:** 2-Stufen-DCF (explizite n-Jahres-FCF-Prognose + barwertiger Terminal Value mit konsistenter g_terminal), WACC bottom-up aus CAPM + Kapitalstruktur, FCF statt Umsatz-CAGR.

### 2.2 Edelmetall-Bewertung entzirkularisieren (`precious_metals_valuation`)
- **Problem:** Realzins-Modell um den aktuellen Preis zentriert (zirkulär); Inflations-Anker 1200$ → Gold dauerhaft „überbewertet"; `min/max`-Union → immer „fair"; Silber-Skalenfehler.
- **Lösung:** Preis-unabhängiger Anker (empirische Realzins-Regression, metallspezifische % -Beta); aktuelle AISC; gewichteter Median der Methoden statt Union; 1200$-Methode entfernen/ersetzen.

### 2.3 Credit-Rating-Bug (`bond_credit._default_prob`)
- **Problem:** `startswith` mappt S&P-„CCC" auf Moody's-`C`=50 %; Skalen vermischt; %/Dezimal uneinheitlich; PD von Spread entkoppelt.
- **Lösung:** Rating auf einheitliche Skala normalisieren, exakter Lookup; Recovery/LGD ergänzen; PD-LGD-Spread über das Credit Triangle verknüpfen; Yield-to-Worst für callable Bonds.

### 2.4 Niveau → Momentum bei Rohstoffen (`energy`, `industrial_metals`)
- **Problem:** Makro-Signal aus nominalem Preisniveau (Öl>100, Kupfer>4,5) statt Dynamik.
- **Lösung:** Signal aus Veränderungsrate/Z-Score (3M/6M/12M), idealerweise real; bei Kupfer Copper/Gold-Ratio; WTI/Brent getrennt; Gas einbeziehen.

### 2.5 CAPE richtig einsetzen
- **Problem:** CAPE fehlt im Index-Bewerter (gehört dorthin) und ist im Einzelaktien-`fundamentals` falsch angewandt.
- **Lösung:** CAPE im Index-Agenten implementieren (US: Shiller-Daten; EU/CH: FMP 10J-EPS) und aus `fundamentals` entfernen. Zusätzlich Earnings Yield + ERP (E/P − lokaler Staatsanleihen-Yield) als Zins-Brücke.

## Priorität 3 — Systematische Verzerrungen (Methodik/Schwellen)

### 3.1 Absolute US-Schwellen → relative Maße (Z-Score/Perzentil zur Landeshistorie)
- **Problem:** Buffett 135 %, BIP 2 %, Arbeitslosigkeit 5 %/8 %, GS-Ratio 50/80 — länderblind, für EU/CH-Fokus systematisch falsch; Buffett-Z-Score wird sogar berechnet, aber verworfen.
- **Lösung:** Durchgängig Z-Score/Perzentil zur Landeshistorie; bei Arbeitslosigkeit Sahm-Regel; bei Ratios rollierende Perzentile.

### 3.2 Real statt nominal
- **Problem:** Kreditwachstum, Geldmenge, lange Rohstoff-Ranges und Saisonalität sind nominal.
- **Lösung:** Reale Größen; Geldmenge/Kredit zum nominalen BIP normieren (Credit-to-GDP-Gap, Überschuss-Liquidität).

### 3.3 Sub-Agenten-Signale mit Regime/Chief verbinden
- **Problem:** Die 7 Makro-Signale beeinflussen das Regime nicht; Chiefs reichen nur durch (kein Composite/Konfliktauflösung).
- **Lösung:** Sub-Signale gewichtet in Regime/Chief-Composite aufnehmen; je Chief ein konsolidiertes Gesamtsignal mit Tie-Break.

### 3.4 VIX-Inkonsistenz auflösen
- **Problem:** VIX als Momentum (hoch=bearish) widerspricht Fear&Greed/Put-Call (contrarian).
- **Lösung:** Einheitliche Contrarian-Konvention (VIX-Spike = Kaufsignal) + gewichtetes Sentiment-Composite.

### 3.5 Yield-Curve verbessern
- **Problem:** 10Y-2Y statt 10Y-3M; sofortiges BEARISH ohne Lag.
- **Lösung:** 10Y-3M als Primärspread; Inversions-Lag (6–18M) bzw. Bull-Steepening als eigentliches Timing-Signal.

### 3.6 Insider wertgewichtet + Sektor benchmark-relativ
- **Problem:** Insider zählt Anzahl statt Wert, behandelt Käufe/Verkäufe symmetrisch; Sektor-„leading/lagging" ist Beta-Artefakt.
- **Lösung:** Wertgewichtete Open-Market-Käufe (10b5-1 bereinigt, Käufe > Verkäufe gewichtet); Sektor-RS = Sektor-Return − Benchmark-Return.

### 3.7 Prozess-globale History ersetzen
- **Problem:** `_RATE_HISTORY` und Regime-Trend vergleichen mit dem letzten Programmlauf → messen Aufruffrequenz.
- **Lösung:** Datierte Zeitreihen vom Provider mit echtem Vorperioden-Vergleich; max. ein History-Eintrag pro Periode.

## Priorität 4 — Robustheit/Detail

### 4.1 Statistik härten
- **Problem:** Z-Scores auf n≥3/5; Normalannahme für fat-tailed Größen; kein Multiple-Testing-Korrektiv.
- **Lösung:** Mindest-N ≥20–30; MAD-basierter robuster Z-Score (Schwelle 3,5); Bonferroni/Holm bzw. FDR.

### 4.2 Wilder-RSI + stabilerer MA200
- **Problem:** RSI nutzt SMA (Cutler) statt Wilder-Smoothing; MA200 aus nur 1y-Historie fragil.
- **Lösung:** `ewm(alpha=1/period)` (Wilder); ≥2y Historie für MA200.

### 4.3 Echtes Perzentil im Commodity-Range
- **Problem:** Min-Max-Spanne statt Rang-Perzentil, ausreißeranfällig, nominal.
- **Lösung:** `(hist < current).mean()`, winsorisiert, real.

### 4.4 Blinde Schwellen-Lücken schließen
- **Problem:** Inflation 3–4 % und Geldmenge 8–10 % fallen durch alle Zweige → fälschlich NEUTRAL.
- **Lösung:** Bänder lückenlos definieren (jeder Wert → genau eine Klasse).

### 4.5 Ungenutzte Kennzahlen aktivieren
- **Problem:** `real_rate_10y`, `money_velocity`, `days_to_cover`, `convexity`, `interest_coverage`, `fcf_margin`, Gold/Platin-Ratio, 52W-High-Distanz, `breakeven_inflation` erfasst, aber nicht genutzt.
- **Lösung:** In die jeweilige Signallogik einbinden oder bewusst entfernen (keine Scheinpräzision).

### 4.6 Total Return vs. Price Return + Roll-Yield
- **Problem:** Index-Performance (Price-Return) unterzeichnet langfristig ~1,5–2 %/J; Futures-Veränderung ≠ Spot.
- **Lösung:** TR vs. PR kennzeichnen, wo möglich TR-Indizes; Roll-Yield bei Futures explizit berücksichtigen.

---

## Positiv-Befunde

Fachlich sauber umgesetzt (zur Erhaltung):
- `labor_income_agent` — Reallohnwachstum als Signalbasis.
- `precious_metals_macro_agent` — dimensionslose Metall-Ratios.
- `valuation_range_agent` (Equity) — EV→Equity-Bridge und Terminal-Growth-Annahmen (2,5–3,0 %).
- `sovereign_spread_agent` — Stress-Logik (300/200bp).
- `sector_rotation` ROTATION_MAP — klassisches Zyklus-Playbook.
- `quality_agent` — Altman-Z-Schwellen (2,99/1,81), Net-Debt/EBITDA-Schwellen.
- `index_valuation_range._method1` — Justified-PE-Range-Interpolation.
- `buffett_indicator._z_score` — korrekte Sample-Statistik.
- `top_down_context` — Z-Score-Pfad mit Spread-Schwellen.
- `index_price` YTD-Bestimmung via `searchsorted`.

---

*Erstellt im Rahmen eines fachlich-konzeptionellen Reviews (CFA-Perspektive). Bezieht sich auf den Repository-Stand vom 2026-06-16. Keine Code-Änderungen vorgenommen; dieses Dokument dient als Grundlage für die priorisierte Umsetzung.*
