# Anlageklassen-Taxonomie — Zwei-Etiketten-Modell (`underlying` × `wrapper`)

- **Datum:** 2026-06-21
- **Status:** Entwurf zur Review
- **Spec-Typ:** Design-Hub für ein größeres Feature (Folge: Plan → PRs in 3 Phasen)
- **Geltungsbereich:** Bottom-Up-Deep-Dive (Modus 2), Datenmodell, Dispatch, Urteilsbildung (Long + Short), CLI, Portfolio

## 0. Ein-Absatz-Zusammenfassung

Die heutige `asset_class` ist **ein einziges Etikett**, das zwei voneinander unabhängige (orthogonale) Fragen vermengt: *Was treibt Gewinn und Verlust?* (der **Basiswert**, engl. *underlying*) und *In welcher Hülle halte ich das, und welche Mechanik bringt diese Hülle mit?* (das **Instrument/die Hülle**, engl. *wrapper*). Dasselbe „Öl" ist über eine Öl-Aktie, einen Öl-Fonds oder einen Öl-Future erreichbar — gleicher Basiswert, völlig verschiedene richtige Analysen. Dieses Dokument schlägt vor, `asset_class` durch **zwei unabhängige Felder** zu ersetzen: `underlying` (wählt die Analyse-**Engine**) und `wrapper` (schaltet eine Risiko-/Mechanik-**Schicht** zu). „Futures" ist damit ein **Wrapper-Wert**, keine eigene oberste Anlageklasse — die Futures-Mechanik wird **einmal** gebaut und gilt für jeden Basiswert, der per Future gehalten wird. Der Umfang dieser ersten Ausbaustufe ist bewusst eng: Rohstoff- und Edelmetall-Futures plus physisch hinterlegte Metall-ETCs. Die Arbeit wird in drei TDD-Phasen geschnitten (Fundament → Futures-Mechanik → Long/Short-Feinschliff).

---

## 1. Begriffsklärung (Fachbegriffe, einmalig erklärt)

Damit die folgenden Abschnitte ohne Rückfragen lesbar sind, hier die zentralen Begriffe — jeder beim ersten Auftreten kurz erklärt:

- **Basiswert / Underlying** — der wirtschaftliche Wert, dessen Preisbewegung Gewinn oder Verlust erzeugt (z. B. das physische Öl, eine Aktie, eine Anleihe). Er bestimmt, *welche* fachliche Analyse richtig ist.
- **Hülle / Wrapper / Instrument** — die rechtlich-technische Verpackung, in der man den Basiswert hält (Einzelwert, Fonds/ETF, Future, physisch hinterlegtes ETC). Sie bestimmt *zusätzliche* Mechanik und Risiken (Hebel, Rollen, Verfall).
- **ETF** (*Exchange Traded Fund*) — börsengehandelter Fonds, der einen Korb von Werten oder einen Index abbildet. Im Modell der **Wrapper-Wert `fund`**.
- **ETC** (*Exchange Traded Commodity*) — börsengehandeltes, rohstoffbesichertes Wertpapier. **Physisch hinterlegtes ETC** (`physical_etc`) bedeutet: hinter dem Papier liegt echtes Metall im Tresor (z. B. ZKB Gold, Xetra-Gold) — kein Future, kein Hebel, reiner Kassapreis (*Spot*).
- **Future / Terminkontrakt** — Vertrag, einen Basiswert zu einem festen späteren Termin zu einem heute fixierten Preis zu kaufen/verkaufen. Bringt Hebel, Verfall und Rollzwang mit.
- **Spot / Kassapreis** — der Preis für sofortige Lieferung „jetzt".
- **Terminkurve / Term-Struktur** — die Preise derselben Ware für verschiedene Liefermonate, aufgereiht über die Zeit.
- **Contango** — Terminkurve steigt: spätere Kontrakte sind teurer als der Spot. (Normalzustand bei lagerfähigen Gütern, die Lagerkosten kosten.)
- **Backwardation** — Terminkurve fällt: spätere Kontrakte sind billiger als der Spot. (Signalisiert oft Knappheit *jetzt*.)
- **Roll / Rollen** — bevor ein Kontrakt ausläuft, schließt man ihn und eröffnet den nächsten Liefermonat, um die Position zu halten.
- **Roll-Yield / Carry** — der systematische Ertrag oder Verlust, der allein durch das Rollen entsteht (siehe §6.3).
- **Basis** — Abstand zwischen Spotpreis und Future-Preis; konvergiert bis zum Verfall gegen null.
- **Convenience-Yield** — der nicht-monetäre Nutzen, das physische Gut *jetzt* zu besitzen (z. B. Versorgungssicherheit einer Raffinerie).
- **COT** (*Commitment of Traders*) — wöchentlicher Report der US-Aufsicht CFTC über die Positionierung großer Marktteilnehmer in Futures.

---

## 2. Problemstellung — zwei Dimensionen in einem Feld

### 2.1 Der Kern: orthogonale Dimensionen werden vermischt

`asset_class` beantwortet heute *gleichzeitig* zwei Fragen, die voneinander unabhängig sind:

1. **Basiswert** — *was* treibt P&L? (Aktie? Anleihe? Rohstoff? Edelmetall? Aktienindex?)
2. **Hülle** — *wie* gehalten, mit welcher Mechanik? (Einzelwert? Fonds? Future? physisch-ETC?)

Weil beide Fragen in ein einziges String-Feld gepresst werden, kann das Modell sie nicht sauber trennen — und an genau dieser Stelle entstehen falsche Analysen.

### 2.2 Belege im aktuellen Code

| Beleg | Datei:Zeile | Befund |
|---|---|---|
| `asset_class` ist ein manuell getippter CLI-String | `app/main.py:172` | `asset_class = args[2] if len(args) >= 3 else "equity"` — keine Validierung, kein Enum. Doku-String der CLI (`app/main.py:7`) listet `equity\|bond\|commodity\|precious_metal\|etf`. |
| `etf` ist dokumentiert, hat aber **keinen** eigenen Dispatch-Zweig | `orchestrators/bottom_up_orchestrator.py:40-48` | Reihenfolge: `precious_metal` → `bond` → `index` → `commodity` → **else: equity**. `etf` fällt also stillschweigend auf den **Equity-Motor** durch (Inkonsistenz: ein ETF wird wie eine Einzelaktie analysiert). |
| Pro-Klasse-Slots, nur einer befüllt | `core/domain/models.py:705-719` | `BottomUpResult` trägt `asset_class: str` plus Equity-Slots **und** je-Klasse-Optional-Slots (`precious_metals`, `bond`, `index`, `commodity_deep`). Der String entscheidet, welcher Slot belegt ist. |
| Buffett-Indikator hängt am String | `core/domain/top_down_context.py:107` | `_BUFFETT_RELEVANT_ASSETS = {"equity", "etf", "index"}` — fachlich richtig (Marktkap./BIP) nur für **aktienartige** Werte, aber an die vermischte Klasse gekoppelt. |
| Short nur für `equity` gebaut | `core/domain/short_assessment.py:57` | `if asset_class != "equity":` → Fallback (NONE/HOLD, confidence 0.10). |
| Aggressiv/Defensiv-Mapping am String | `core/domain/recommendation.py:31-32,40-43` | `ETF_ASSET_CLASSES = {"etf","index"}`, `AGGRESSIVE_ASSET_CLASSES = {"equity","precious_metal","commodity","bond"}`, `_short_type(...)`. |
| Portfolio-Position ohne Validierung | `core/domain/portfolio.py:5-15` | `asset_class: str = "equity"` — kein Enum, keine Prüfung. `data/portfolio.json` ist leer. |

### 2.3 Die Beispiele, an denen es bricht

**Beispiel „Öl" — ein Basiswert, drei Zugänge, drei richtige Analysen:**

| Zugang | Basiswert | Hülle | Richtige Analyse |
|---|---|---|---|
| Exxon-Aktie | Aktie eines Ölkonzerns | Einzelwert | **Equity**: Fundamentaldaten, Quality, Moat, Bewertung. Öl ist nur *Rückenwind/Gegenwind*. |
| Öl-Future (WTI) | physisches Öl | Future | **Commodity + Futures-Mechanik**: Angebot/Nachfrage, Saisonalität, COT — **plus** Roll/Contango/Hebel/Verfall. |
| physisch-ETC (nur Metalle möglich) | — | — | (Bei Öl gibt es kein physisch-ETC; bei Gold schon: Spot-Engine **ohne** Roll/Hebel.) |

**Beispiel „ETF" — der Beweis, dass die Analyse am Basiswert hängen muss, nicht an der Hülle:**

| Produkt | Hülle | Hält tatsächlich | Verhält sich wie | Richtige Engine |
|---|---|---|---|---|
| **XLE** (Energy Select Sector) | ETF (`fund`) | Öl-**Aktien** (Exxon, Chevron …) | ein Aktien-Sektor-Index | `equity_index` |
| **USO** (United States Oil Fund) | ETF (`fund`) | Öl-**Futures** | rollender Future mit Contango-Drag | `commodity` + Futures-Mechanik |

Beide tragen dieselbe Hülle „ETF", haben aber **völlig verschiedene Treiber**. Würde die Analyse an der Hülle hängen, bekämen XLE und USO dieselbe (für eines von beiden grob falsche) Behandlung. **Schlussfolgerung: Die Engine-Wahl muss am Basiswert hängen, die Hülle schaltet nur eine Zusatzschicht.** (Hinweis: USO-artige synthetische Einzel-Rohstoff-ETFs sind in dieser Ausbaustufe bewusst *ausgeschlossen*, siehe §4 — das Beispiel dient nur dem Beweis der Orthogonalität.)

---

## 3. Zielbild — das Zwei-Etiketten-Modell (`underlying` × `wrapper`)

Jede Anlage bekommt **zwei unabhängige Felder**:

- **`underlying`** (Basiswert) → wählt die **Analyse-Engine**.
- **`wrapper`** (Hülle) → schaltet eine **Risiko-/Mechanik-Schicht** zu.

### 3.1 Erlaubte `underlying`-Werte (→ Engine)

| `underlying` | Bedeutung | Gewählte Engine (Bottom-Up-Chief) |
|---|---|---|
| `equity` | Einzelaktie (inkl. Rohstoff-/Minenkonzerne) | `EquityChiefAgent` |
| `equity_index` | Aktienindex / Aktien-Sektorkorb | `IndexChiefAgent` |
| `bond` | Anleihe / Zinsträger | `BondChiefAgent` |
| `commodity` | physischer Rohstoff (Öl, Gas, Agrar, Industriemetall) | `CommodityChiefAgentMikro` |
| `precious_metal` | Edelmetall (Gold, Silber, Platin, Palladium) | `PreciousMetalsChiefAgent` |

> **Hinweis Benennung:** Das alte `index` wird zu `equity_index` umbenannt, weil „Index" mehrdeutig ist (es gibt auch Rohstoffindizes). Der heutige `IndexChiefAgent` analysiert **Aktien**-Indizes (Breadth, Earnings, Sektor-Rotation) — der präzisere Name verhindert, dass jemand später einen Rohstoff-Index dort einsortiert.

> **Bewusst zurückgestellt:** `volatility` / VIX als eigener `underlying` ist **nicht** Teil dieser Arbeit (siehe §12).

### 3.2 Erlaubte `wrapper`-Werte (→ Zusatzschicht)

| `wrapper` | Bedeutung | Zusatzschicht | Hebel? | Roll/Verfall? |
|---|---|---|---|---|
| `single` | Einzelwert / direktes Wertpapier | keine | nein | nein |
| `fund` | Fonds/ETF (Korb, hält den Basiswert) | **Info-Schicht: TER (Kosten-Drag) + Tracking-Error** (s. §6.6) | nein | nein |
| `future` | Terminkontrakt | **Futures-Mechanik-Schicht** (Kurve/Roll/Carry/Basis/Hebel/Verfall) | **ja** | **ja** |
| `physical_etc` | physisch hinterlegtes Rohstoff-ETC | keine (reiner Spot) | nein | nein |

**Zentrale Aussage:** „Futures" ist ein **`wrapper`-Wert**, *keine* oberste Anlageklasse. Die Futures-Mechanik-Schicht wird **einmal** implementiert und greift für **jeden** `underlying`, der per `wrapper=future` gehalten wird.

### 3.3 Die Kombinationsmatrix (in dieser Ausbaustufe relevant)

Zeilen = `underlying`, Spalten = `wrapper`. ✅ = im Umfang, ⬜ = grundsätzlich gültig, aber nicht Teil dieser Arbeit, ❌ = fachlich ausgeschlossen.

| `underlying` \ `wrapper` | `single` | `fund` | `future` | `physical_etc` |
|---|---|---|---|---|
| `equity` | ✅ (Einzelaktie) | ⬜ (Einzelaktien-Wrapper selten) | ❌ (Einzelaktien-Future out of scope) | ❌ |
| `equity_index` | ❌ | ✅ (z. B. XLE, S&P-ETF) | ⬜ (Index-Future, später) | ❌ |
| `bond` | ✅ (Direktanleihe) | ⬜ (Bond-ETF) | ⬜ (Bund-/T-Note-Future, später) | ❌ |
| `commodity` | ❌ (physisch direkt nicht haltbar im System) | ❌ (synth. Einzel-Rohstoff-ETF *verworfen*) | ✅ (WTI, Gas, Weizen …) | ❌ (Rohstoff i. d. R. nicht physisch-hinterlegbar) |
| `precious_metal` | ❌ | ❌ | ✅ (Gold-/Silber-Future) | ✅ (ZKB Gold, Xetra-Gold) |

Die ✅-Felder definieren exakt den Lieferumfang dieser Arbeit („Futures-Grundausbau").

---

## 4. Umfang (in / out)

### 4.1 Im Umfang („Futures-Grundausbau")

- **Rohstoff-Futures** (`underlying=commodity, wrapper=future`).
- **Edelmetall-Futures** (`underlying=precious_metal, wrapper=future`).
- **Physisch hinterlegte Metall-ETCs** (`underlying=precious_metal, wrapper=physical_etc`) — z. B. ZKB Gold, Xetra-Gold. Reiner Spot, **kein** Roll/Hebel; nutzt aber dieselbe Edelmetall-Engine (Realzins-Anker, Gold/Silber-Ratio).
- Der **Wrapper `future`** als wiederverwendbare Mechanik-Schicht (Kurve/Roll/Carry/Basis/Hebel/Verfall), zunächst nur für die beiden obigen Basiswerte aktiv geschaltet.

### 4.2 Außerhalb des Umfangs (mit Begründung)

| Ausgeschlossen | Begründung |
|---|---|
| **Synthetische Einzel-Rohstoff-ETFs/-ETCs** (USO-Typ) | Fachlich = rollender Future in Fonds-Hülle; bringt Contango-Drag, ohne eigenen Mehrwert gegenüber dem direkten Future. **Verworfen**, um die Wrapper-Liste schlank zu halten. |
| **Rohstoff-Körbe / -Indizes** (DBC, BCOM) | Der Nutzer hält nur **Einzel**-Rohstoffe/-Metalle. Ein Korb bräuchte eine eigene Gewichtungs-/Index-Methodik — nicht benötigt. |
| **FX / Devisen** | Eigene Asset-Klasse mit eigener Makro-Logik (Zinsdifferenzen, Kaufkraftparität). Nicht Teil des Deep-Dive-Mandats. |
| **Krypto** | Eigene Risikoklasse, eigene Datenquellen; bewusst außen vor. |
| **Selbst gelagertes physisches Metall (Barren)** | Kein handelbares Wertpapier mit Marktpreis-Feed im System. **Physisch-ETC** (mit Börsenpreis) ist drin, der Barren nicht. |
| **VIX als eigenständige Deep-Dive-Anlage** | Gehört in die Hedge-/Regime-Schicht (Track B), nicht in den Bottom-Up. Siehe §12. |
| **Einzelaktien-Futures, Index-Futures, Bond-Futures** | Grundsätzlich vom Modell vorgesehen (Matrix §3.3), aber **nicht** in dieser Ausbaustufe aktiviert. |

---

## 5. Reklassifizierung — was zieht wohin

| Heute (`asset_class`) | Beispiel | Neu (`underlying`) | Neu (`wrapper`) | Engine danach |
|---|---|---|---|---|
| `equity` | AAPL | `equity` | `single` | Equity (unverändert) |
| `equity` | **Exxon, Barrick** (Rohstoff-/Minenaktie) | **`equity`** | `single` | Equity — bleibt Aktie; Rohstoff nur als Rücken-/Gegenwind (§12) |
| `etf` (→ fiel auf equity durch) | **XLE** (Sektor-ETF) | **`equity_index`** | **`fund`** | Index (statt fälschlich Equity) |
| `index` | S&P 500 | `equity_index` | `single` *(oder `fund`)* | Index (umbenannt) |
| `bond` | 10J-Treasury | `bond` | `single` | Bond (unverändert) |
| `commodity` | WTI-Future | `commodity` | **`future`** | Commodity **+ Futures-Schicht** |
| `precious_metal` | Gold-Future | `precious_metal` | **`future`** | PM **+ Futures-Schicht** |
| (neu) | ZKB Gold (physisch-ETC) | `precious_metal` | **`physical_etc`** | PM (Spot, ohne Futures-Schicht) |

**Wichtigste Korrekturen:** (a) `etf` verschwindet als eigener Wert — XLE wird korrekt zu `equity_index/fund`; (b) Rohstoff-/Minenaktien bleiben ausdrücklich `equity`; (c) Gold per Future vs. Gold per physisch-ETC sind jetzt **unterscheidbar** (gleiche Engine, unterschiedliche Schicht).

---

## 6. Engines — Bestand, Umzug und die neue Futures-Mechanik-Schicht

### 6.1 Bestehende Engines (bleiben, werden nur „umgehängt")

Nichts an diesen Engines wird neu geschrieben; sie werden lediglich vom String-Dispatch auf `underlying` umgeroutet.

| Engine | Datei | Sub-Agents | wird gewählt bei |
|---|---|---|---|
| Equity | `agents/stock_deep_dive/equity_chief_agent.py` | fundamentals, quality, short_interest, insider, earnings_trend, moat, valuation_range | `underlying=equity` |
| Index (Aktien) | `agents/stock_deep_dive/index_chief_agent.py` | Breadth/Earnings/Sektor | `underlying=equity_index` |
| Bond | `agents/stock_deep_dive/bond_chief_agent.py` | (Bond-Logik) | `underlying=bond` |
| **Commodity** | `agents/stock_deep_dive/commodity_chief_agent_mikro.py` (Sub-Agents in `agents/stock_deep_dive/commodity/`) | `supply_demand`, `seasonality`, `cot`, `commodity_valuation_range` | `underlying=commodity` |
| **Precious Metals** | `agents/stock_deep_dive/precious_metals_chief_agent.py` | `precious_metal_price`, `cross_metal` (Ratio), `precious_metals_valuation` (Realzins-Anker FRED `REAINTRATREARAT10Y`) | `underlying=precious_metal` |

> **Nicht verwechseln:** Es gibt zusätzlich einen **Top-Down-Makro**-Commodity-Chief (`agents/market_cockpit/commodity_chief_agent_makro.py`, Sub-Agents energy/industrial_metals/precious_metals_macro/agricultural). Der gehört in Modus 1 (Cockpit) und wird hier **nicht** angefasst.

### 6.2 Die NEUE Futures-Mechanik-Schicht — Architektur (hexagonal)

Die Schicht ist **kein** neuer Chief, sondern eine **Mechanik-Überlagerung**, die nach der Basiswert-Engine läuft, wenn `wrapper=future`. Sie braucht Termin­kurven-Daten, die heute keine Quelle liefert — also folgen wir dem Projektmuster „Port + Stub-Adapter (UNAVAILABLE), bis echte Quelle angebunden".

**Neuer Port (Vorschlag):** `core/ports/futures_curve.py` → `FuturesCurveProvider(ABC)`

```text
class FuturesCurveProvider(ABC):
    async def get_curve(symbol: str) -> FuturesCurveSnapshot | None
        # Liefert: spot, [(expiry, price)] der vorderen N Kontrakte,
        #          front/next-Preise, Tage bis Front-Verfall, Margin-Quote (falls bekannt).
```

**Neues Domänen-Modell (Vorschlag):** `FuturesCurveSnapshot` in `core/domain/models.py`
(reines Datenmodell, keine I/O), plus ein Ergebnis `FuturesMechanicsSnapshot`
(Signal je Konzept + Gesamt-Signal + Begründungstexte).

**Neuer Sub-Agent (Vorschlag):** `agents/stock_deep_dive/futures/futures_mechanics_agent.py`
— hängt nur vom **Port** ab (DI über Konstruktor), nie vom Adapter (AGENTS.md §1).
Stellt `default()` bereit (Klassen-Fallback) → bei fehlender Quelle: alle Sub-Signale
**UNAVAILABLE/NEUTRAL**, `confidence` niedrig, Begründung „Terminkurven-Quelle nicht angebunden".

**Stub-Adapter (Vorschlag):** `adapters/futures/stub_futures_curve.py`
— implementiert den Port, liefert konsequent `None` → die Schicht meldet **UNAVAILABLE**,
ohne die Gesamtanalyse zu gefährden (defensive Aggregation, AGENTS.md §2).

> So bleibt das System sofort lauffähig und testbar; der echte Adapter (z. B. Datenquelle für Termin­kurven) kann später transparent eingestöpselt werden, ohne Agent- oder Domänencode zu ändern.

### 6.3 Die Konzepte der Futures-Schicht — fachliche Erklärung + Signal-Logik

Für jedes Konzept: *was es ist*, *warum es zählt*, *Datenbedarf*, *vorgeschlagene Signal-/Schwellenlogik*. **Alle Schwellen sind Startwerte zur Review** — jede ist fachlich begründet, keine ist „magisch" (AGENTS.md §3).

#### (a) Terminkurve / Term-Struktur — Contango vs. Backwardation

- **Was:** Form der Kurve aus Spot und vorderen Kontrakten. **Contango** = Kurve steigt (spätere Kontrakte teurer); **Backwardation** = Kurve fällt (spätere billiger).
- **Warum:** Die Form bestimmt das Vorzeichen des Roll-Effekts und sagt etwas über die *physische Knappheit jetzt* aus (Backwardation ⇒ Markt zahlt Aufpreis für sofortige Lieferung ⇒ knapp).
- **Datenbedarf:** `spot`, `front`, `next` (mindestens zwei Punkte).
- **Vorzeichenkonvention (einheitlich für die ganze Schicht):** ein **positiver** Wert = **Contango** (steigende Kurve), ein **negativer** Wert = **Backwardation**.
- **Maß (Vorschlag):** annualisierte Steigung
  `slope_ann = (next/front − 1) · (365 / Δtage)`, wobei `front` = Preis des vorderen (nächst-verfallenden) Kontrakts, `next` = Preis des Folgekontrakts und `Δtage` = Kalendertage **zwischen den beiden Verfallsterminen** (nicht „bis Verfall"). In Contango gilt `next > front` ⇒ `slope_ann > 0`; in Backwardation `next < front` ⇒ `slope_ann < 0`.
- **Signal-Logik (Long-Sicht, Startwerte):**

  | Bedingung (annualisiert) | Zustand | Signal Long |
  |---|---|---|
  | `slope_ann ≤ −0.05` (≤ −5 %) | klare **Backwardation** | **BULLISH** (Knappheit + positiver Roll) |
  | `−0.05 < slope_ann < +0.05` | flach | **NEUTRAL** |
  | `slope_ann ≥ +0.05` (≥ +5 %) | klares **Contango** | **BEARISH** (Überangebot/Lagerdruck + negativer Roll) |

  > **Begründung der ±5 %-Bänder:** unterhalb ~5 % p. a. ist die Kurvenneigung im Bereich normaler Lagerkosten/Zins-Carry und damit *nicht* aussagekräftig für die Richtung; erst eine deutliche Neigung trägt Information. Lückenloses Band (`≤ / < … < / ≥`) gemäß AGENTS.md §2 — jeder Wert fällt in genau eine Klasse.

#### (b) Roll-Yield / Carry

- **Was:** der Ertrag/Verlust **allein durch das Rollen**. In Contango verkauft man billig (auslaufender Kontrakt nahe Spot) und kauft teuer (nächster Kontrakt) → **negativer** Roll-Yield für die Long-Position. In Backwardation umgekehrt → **positiver** Roll-Yield.
- **Warum:** Über die Zeit kann der Roll-Effekt den reinen Spotpreis-Effekt **dominieren** — eine Long-Position kann Geld verlieren, obwohl der Spot seitwärts läuft (klassisch USO in Contango).
- **Datenbedarf:** `front`, `next`, Δtage.
- **Maß (Vorschlag):** `roll_yield_long_ann = (front/next − 1) · (365 / Δtage)` (Vorzeichenkonvention: **positiv = Rückenwind für Long**).
- **Verhältnis zur Kurvenneigung:** Roll-Yield und Slope sind **dasselbe Phänomen mit entgegengesetztem Vorzeichen**: `roll_yield_long_ann ≈ −slope_ann`. In **Contango** (`slope_ann > 0`) ist der Roll-Yield für den Long **negativ** (Gegenwind), in **Backwardation** (`slope_ann < 0`) **positiv** (Rückenwind). Beide im Output **getrennt benannt** (Transparenz), aber im Signal **nur einmal** gezählt (§6.4).
- **Zahlenbeispiel:** `front=80`, `next=82`, `Δtage=30` ⇒ `slope_ann = (82/80 − 1)·(365/30) ≈ +0.30` (klares **Contango** ⇒ **BEARISH** für Long) und `roll_yield_long_ann = (80/82 − 1)·(365/30) ≈ −0.30` (**Gegenwind** für Long, **Rückenwind** für Short).
- **Wichtig fürs Urteil:** Roll-Yield ist genau der Hebel, der **Long und Short** unterschiedlich trifft — in Contango arbeitet der Roll *gegen* den Long und *für* den Short (§7).

#### (c) Cost-of-Carry-Modell (der theoretische Fair-Future-Preis)

- **Was:** Der faire Future-Preis ergibt sich aus Spot plus Finanzierungs-/Lagerkosten minus dem Nutzen des Sofortbesitzes:

  **`F = S · e^((r + u − y) · T)`**

  mit `S` = Spot, `r` = risikofreier Zins, `u` = Lagerkosten (storage), `y` = Convenience-Yield, `T` = Restlaufzeit in Jahren, `e` = Eulersche Zahl (stetige Verzinsung).
- **Warum:** Liefert einen **Anker**, gegen den der beobachtete Future-Preis verglichen wird. Bei Edelmetallen ist `u, y ≈ 0` ⇒ `F ≈ S·e^(r·T)` (fast reiner Zins-Carry); bei verderblichen/saisonalen Gütern sind `u, y` groß und schwanken.
- **Datenbedarf:** `S`, `r` (vorhanden via Makro-Port/FRED), `T`; `u`/`y` oft nicht direkt messbar → **implizit** aus der Kurve zurückrechnen (`y` als Residuum), statt zu raten.
- **Signal-Logik (entschieden, §13.4):** Wir **raten `u`/`y` nicht**, sondern leiten die **kombinierte implizite Convenience-Yield** aus beobachteten Preisen ab: `cy_implizit = r − ln(front/S) / T` (aus `F = S·e^((r+u−y)·T)` nach dem Netto-Carry aufgelöst). **Diese Größe ist selbst das Signal:** ein **hoher** Wert gegenüber der eigenen Historie (z. B. oberes Perzentil) ⇒ der Markt zahlt Aufpreis für sofortige Lieferung ⇒ **Knappheit ⇒ BULLISH**; ein stark **negativer** Wert ⇒ Überfluss/Lagerdruck ⇒ **BEARISH**. **Kein** „Mispricing gegen ein selbst gefittetes Modell" (das wäre zirkulär).
  > **Warum so:** Da `u`/`y` nicht direkt messbar sind, ist das Zurückrechnen aus realen Preisen die ehrliche Methode (AGENTS.md §3); bewertet wird gegen die **eigene Historie** statt gegen eine geratene Absolutschwelle.

#### (d) Basis (Spot ↔ Future)

- **Was:** `Basis = Spot − Future`. Konvergiert mit nahendem Verfall **gegen null** (Konvergenzprinzip: bei Lieferung *ist* Future = Spot).
- **Warum:** Bestätigt die Kurvenform und liefert über die **Konvergenzgeschwindigkeit** eine Plausibilitätskontrolle. **Vorzeichen-Brücke (konsistent mit (a)/(b)):** positive Basis (`Spot > Future`) ⇒ **Backwardation** ⇒ `slope_ann < 0` ⇒ `roll_yield_long_ann > 0`; negative Basis ⇒ **Contango** ⇒ `slope_ann > 0` ⇒ Roll-Yield für Long negativ.
- **Datenbedarf:** `spot`, `front`, Tage bis Verfall.
- **Signal-Logik:** primär **diagnostisch/Sanity-Check** (Vorzeichen muss zu (a) passen). Kein eigenständiges Richtungssignal, um Doppelzählung mit (a)/(b) zu vermeiden.

#### (e) Hebel / Margin

- **Was:** Ein Future bindet nur **wenige Prozent** des Kontraktwerts als Sicherheit (Margin). Damit verändert sich die **Positionsgröße und das Risiko fundamental** gegenüber dem Kassakauf.
- **Warum:** Dieselbe Marktbewegung trifft das eingesetzte Kapital **gehebelt**. Für die Empfehlung heißt das: die `suggested_size_pct` **muss** für `wrapper=future` anders (kleiner, bezogen auf Nominalexposure) gerechnet werden als für Kassa.
- **Datenbedarf:** Margin-Quote (falls vom Port geliefert), sonst konservativer Default.
- **Logik (Vorschlag):** **Risiko-Schicht, kein Richtungssignal** — sie **dämpft** die Positionsgröße: maßgeblich ist das **Nominalexposure** (Kontraktwert), nicht der Margin-Einsatz. **Default-Deckel:** Nominalexposure einer einzelnen Future-Position **≤ 10 % des Depots** — derselbe Obergrenzwert wie der bestehende `_position_size_pct`-Cap (10 %) in `core/domain/recommendation.py:54-57`, damit der Hebel die geltende Sizing-Obergrenze nicht unterläuft. Zusätzlich ein **Warnhinweis** im Output („gehebelt — Verlust kann Margin übersteigen").
  > **Begründung:** Hebel ändert nichts daran, *ob* man long/short sein will, aber sehr wohl *wie groß*. Deshalb wirkt er auf Sizing/Stops, nicht auf das Richtungssignal.

#### (f) Verfall / Roll-Termin

- **Was:** Jeder Kontrakt läuft an einem festen Termin aus und muss vorher gerollt werden.
- **Warum:** Nahe am Verfall steigen Liquiditäts-/Roll-Risiken; ein Signal „BUY" zwei Tage vor Verfall ist praktisch wertlos ohne Roll-Plan.
- **Datenbedarf:** Tage bis Front-Verfall.
- **Logik (Vorschlag):** **Kontext-/Timing-Flag**. Schwelle: **< 5 Handelstage bis Verfall** ⇒ Warnhinweis „Roll steht an — Empfehlung bezieht sich auf den Folgekontrakt".
  > **Begründung 5 Tage:** entspricht dem üblichen Roll-Fenster großer Indizes/Roll-Methoden; davor ist Liquidität typischerweise noch im Front-Kontrakt, danach wandert sie in den nächsten.

#### (g) COT (Commitment of Traders) — Wiederverwendung

- **Was/Warum:** Positionierung großer Marktteilnehmer; existiert bereits als `cot_agent` (`agents/stock_deep_dive/commodity/cot_agent.py`).
- **Logik:** **wiederverwenden**, nicht neu bauen. Der COT ist konzeptuell Teil der Futures-Welt; in der Commodity-Engine ist er bereits verdrahtet. Für `precious_metal` ist `cot_signal` heute hart `NEUTRAL` (im `PreciousMetalsResult`) — die Futures-Schicht ist der natürliche Ort, diesen später mit echten Daten zu speisen (Folge-Aufgabe, nicht Pflicht dieser Phase).

#### 6.4 Aggregation der Futures-Schicht zu einem Signal

Defensive Aggregation (AGENTS.md §2): Richtungssignale aus (a) Kurve und (b) Roll-Yield bilden den **Kern** (sie sind dasselbe Phänomen → **nicht** doppelt zählen, sondern als *ein* gewichteter Beitrag führen). (c) implizite Convenience-Yield (§6.3c, Niveau/Trend gegen die eigene Historie — **kein** Mispricing) und (g) COT sind **Verstärker/Kontext**. (d) Basis ist Sanity-Check. (e) Hebel und (f) Verfall wirken auf **Sizing/Timing**, nicht auf die Richtung. Fällt die Quelle aus → `FuturesMechanicsAgent.default()` ⇒ **UNAVAILABLE**, neutraler Beitrag, Gesamtanalyse läuft weiter.

#### 6.5 `physical_etc` — explizit ohne Futures-Schicht

`wrapper=physical_etc` schaltet **keine** Roll/Hebel-Schicht zu (reiner Spot). Es nutzt **dieselbe** Basiswert-Engine wie der entsprechende Future (z. B. Edelmetall: Realzins-Anker, Gold/Silber-Ratio), aber **ohne** Kurve/Roll/Carry/Hebel/Verfall. Damit ist „Gold per Future" vs. „Gold per physisch-ETC" sauber unterschieden: gleiche fachliche Bewertung des Basiswerts, andere Mechanik-Schicht (eine vs. keine).

### 6.6 Die `fund`-Info-Schicht (TER + Tracking-Error) — entschieden §13.2

`wrapper=fund` (ETF) schaltet eine **Info-Schicht** zu — **kein Richtungssignal**, sondern ein Kosten-/Qualitäts-Hinweis:

- **TER (Total Expense Ratio):** jährliche Kostenquote des ETF (z. B. ~0,1 %). Wirkt als kleiner **Kosten-Drag** auf die Netto-Erwartung; wird im Output ausgewiesen. **Quelle:** ETF-Stammdaten (z. B. yfinance `info`); fehlt sie → UNAVAILABLE.
- **Tracking-Error:** annualisierte Standardabweichung der **Renditedifferenz** ETF ↔ Benchmark-Index — `stdev(R_etf − R_index)`. Misst, wie treu der ETF seinen Index abbildet. **Datenbedarf:** Renditereihen von ETF **und** Benchmark — d. h. der **Benchmark des ETF muss bekannt** sein (aus der Datenquelle oder einer kleinen Zuordnung). Ist der Benchmark unbekannt → Tracking-Error UNAVAILABLE (TER bleibt).
- **Architektur (hexagonal, analog zur Futures-Schicht):** Port `FundInfoProvider` (`get_fund_info(symbol) -> FundInfoSnapshot | None`) + Stub-Adapter → UNAVAILABLE; ein `FundInfoAgent` mit `default()`. Greift **nur** bei `wrapper=fund`.
- **Wirkung aufs Urteil:** TER mindert leicht die Netto-Erwartung; ein **hoher Tracking-Error** ist ein **Qualitäts-Warnflag** (der ETF bildet schlecht ab). Beide **kippen nie die Richtung** — sie informieren und dämpfen.

---

## 7. Long + Short für die neue Kategorie

Das System bildet pro Analyse **zwei** Urteile:

- `derive_recommendation(...)` → **Long**: BUY / BUY+ / SELL / HOLD / NONE (`core/domain/recommendation.py`).
- `derive_short_assessment(...)` → **Short**: SHORT / COVER / HOLD / NONE (`core/domain/short_assessment.py`).

**Stand heute:** Der Short ist **nur für equity** gebaut — `short_assessment.py:57` `if asset_class != "equity"` fällt auf NONE/HOLD (confidence 0.10).

### 7.1 Reihenfolge: erst Long, dann Short

Die neue Kategorie bekommt **zuerst Long** (Phase 2), **später Short** (Phase 3). Das ist kollisionsfrei zur laufenden Short-Arbeit, weil der **Futures-Short heute noch gar nicht existiert** — wir bauen Neuland, nicht in bestehende equity-Short-Logik hinein.

### 7.2 Warum ein Futures-Short mechanisch anders (sauberer) ist

- **Kein Wertpapierverleih:** Eine Aktie zu shorten erfordert Leihe (Borrow) — mit Kosten, Rückrufrisiko und **Short-Squeeze**-Gefahr. Ein Future ist ein **symmetrischer** Kontrakt: Short eröffnen ist mechanisch genauso einfach wie Long. **Kein Borrow, kein Squeeze über Leihe.** (Die equity-Short-Flags rund um Days-to-Cover/Hard-to-Borrow in `core/domain/short_flags.py` sind hier **nicht** anwendbar.)
- **Roll-Yield arbeitet FÜR den Short:** In **Contango** verliert der Long beim Rollen — also **gewinnt** der Short. Die Kurve ist im Contango ein struktureller **Rückenwind für die Short-Seite** (genau die Mechanik, die USO-Longs schadet).
- **Cost-Curve-Boden als Mean-Reversion-Floor:** Rohstoffe haben tendenziell einen **Produktionskosten-Boden** (unter dem Grenzkosten-Niveau wird Förderung eingestellt ⇒ Angebot sinkt ⇒ Preis stabilisiert). Für den Short heißt das: **Vorsicht nahe dem Kostenboden** — das Short-Signal sollte gedämpft/gedeckelt werden, je näher der Preis am geschätzten Floor liegt (analog zum 0.70-Deckel-Gedanken bei equity).

### 7.3 Vorgeschlagene Short-Logik (Phase 3, Skizze)

- Eigener Zweig in `derive_short_assessment` für `wrapper=future` (statt des heutigen Pauschal-Fallbacks).
- **Kern-Treiber:** Contango-Stärke (positiver Roll-Yield für Short) + bärische Basiswert-Engine (Commodity/PM) + COT-Extrem.
- **Dämpfer/Deckel:** Nähe zum geschätzten Cost-Curve-Boden (Mean-Reversion-Risiko), Backwardation (Roll arbeitet *gegen* den Short), Verfallsnähe.
- **Short-Typ:** als **AGGRESSIV** einordnen (spekulativ, Einzel-Basiswert) — konsistent mit der bestehenden Begründung in `SHORT_WARNINGS[ShortType.AGGRESSIVE]` (`recommendation.py:23-28`), die Rohstoffe ausdrücklich nennt.
- **Sizing:** über die Hebel-Schicht (§6.3e) — Nominalexposure, nicht Kapitaleinsatz.

---

## 8. Auswirkung auf Datenmodell & Dispatch — der Blast-Radius

Konkret, Datei für Datei. „verhaltens-erhaltend" = die bestehenden 5 Engines liefern für äquivalente Eingaben **identische** Ergebnisse.

### 8.1 Modellierung: `underlying`/`wrapper` als Enums?

**Empfehlung: ja, als `str`-Enums** (`enum.StrEnum` bzw. `class X(str, Enum)`), abgelegt in `core/domain/` (reine Domäne). Begründung:

- Beseitigt die heutige Hauptschwäche (frei getippter String ohne Validierung, `app/main.py:172`, `portfolio.py:14`).
- Schließt die `etf`-Durchfall-Lücke strukturell (ein unbekannter Wert ist nicht mehr konstruierbar).
- Lückenloser Dispatch wird erzwingbar (Match über alle Enum-Mitglieder).
- `str`-Basis hält JSON-/CLI-Kompatibilität (Werte bleiben lesbare Strings in `portfolio.json`).

### 8.2 Betroffene Dateien

| Datei:Zeile | Heute | Änderung |
|---|---|---|
| `core/domain/` (neu) | — | **Neu:** `Underlying`-Enum (`equity`/`equity_index`/`bond`/`commodity`/`precious_metal`) und `Wrapper`-Enum (`single`/`fund`/`future`/`physical_etc`). |
| `core/domain/models.py:705-719` | `BottomUpResult.asset_class: str` + Slots | `asset_class: str` ersetzen durch `underlying: Underlying` + `wrapper: Wrapper`. Slots unverändert (weiterhin pro Engine ein Optional-Slot). **Neuer Slot:** `futures_mechanics: Optional[FuturesMechanicsSnapshot]` (nur bei `wrapper=future` befüllt). |
| `orchestrators/bottom_up_orchestrator.py:32-48` | `run(..., asset_class=...)`, String-`if`-Kette | Signatur auf `underlying`/`wrapper` umstellen; Dispatch über `underlying` (Match statt String-Vergleich); nach der Engine bei `wrapper=future` die **Futures-Schicht** aufrufen und das Ergebnis in `futures_mechanics` legen. `etf`-Fall entfällt (es gibt kein `etf` mehr). |
| `core/domain/recommendation.py:31-32,40-43` | `ETF_ASSET_CLASSES`, `AGGRESSIVE_ASSET_CLASSES`, `_short_type(asset_class)` | Auf das neue Schema umstellen; `_short_type` nimmt künftig (`underlying`, `wrapper`). Die **vollständige** Aggressiv/Defensiv-Zuordnung über alle (underlying × wrapper)-Kombinationen siehe **§8.4** (keine blinde Lücke). |
| `core/domain/short_assessment.py:51-60` | `if asset_class != "equity": Fallback` | Eigener Zweig für `wrapper=future` (Phase 3). Bis dahin: bestehender neutraler Fallback bleibt für alle Nicht-equity (verhaltens-erhaltend). |
| `core/domain/top_down_context.py:107` | `_BUFFETT_RELEVANT_ASSETS={"equity","etf","index"}` | Auf `underlying ∈ {equity, equity_index}` umstellen (fachlich identisch: Buffett-Indikator nur für aktienartige Werte). |
| `core/domain/portfolio.py:5-15` | `asset_class: str = "equity"` | Zwei Felder: `underlying: Underlying = Underlying.EQUITY`, `wrapper: Wrapper = Wrapper.SINGLE`. Validierung über Enum. (Depot leer ⇒ keine Datenmigration, §9.) |
| `app/main.py:7,172-177` | Positions-Arg `asset_class`, Doku-String | Zwei Args/benannte Optionen `underlying` + `wrapper`; Doku-String auf neue Werte + Default `equity/single`. |
| `tests/` (Spiegel von `agents/`) | `tests/test_short_assessment_engine.py` prüft Nicht-equity-Fallback | Anpassen auf neues Schema; neue Tests für Enum-Dispatch, Futures-Schicht, Reklassifizierung (§11). |

### 8.3 Datenfluss nach dem Umbau (Skizze)

```
CLI/Portfolio  →  (underlying, wrapper)
        │
        ▼
BottomUpOrchestrator.run(underlying, wrapper, …)
        │  match underlying →  Equity | Index | Bond | Commodity | PreciousMetals  (Engine)
        │
        ├─ if wrapper == future:  FuturesMechanicsAgent.run(symbol)  ──► futures_mechanics
        │                              (FuturesCurveProvider-Port → Stub: UNAVAILABLE)
        ▼
BottomUpResult(underlying, wrapper, <engine-slot>, futures_mechanics?)
        │
        ├─ derive_recommendation(...)     (Long)
        └─ derive_short_assessment(...)   (Short: future-Zweig ab Phase 3)
```

### 8.4 Vollständige Aggressiv/Defensiv-Matrix (für `_short_type`)

Damit beim Umbau **keine** Kombination unklassifiziert bleibt (lückenlos, AGENTS.md §2). **Regel:** *Defensiv* = marktbreite Absicherung (`underlying == equity_index` **oder** `wrapper == fund`); **alles andere** = *Aggressiv* (gezielte Einzel-Wette).

| `underlying` \ `wrapper` | `single` | `fund` | `future` | `physical_etc` |
|---|---|---|---|---|
| `equity` | Aggressiv | Defensiv | (out of scope) | — |
| `equity_index` | Defensiv | Defensiv | Defensiv | — |
| `bond` | Aggressiv (Direktanleihe) | Defensiv (Bond-ETF) | Aggressiv | — |
| `commodity` | — | — | Aggressiv | — |
| `precious_metal` | — | — | Aggressiv | Aggressiv |

> Begründung: Ein breiter Index/ETF dient typischerweise der **Absicherung** (Track B); eine Einzel-Basiswert- oder Future-Position ist eine **spekulative** Wette (Track A). `equity_index` ist immer defensiv (auch als Future), weil es den Gesamtmarkt abbildet. Diese Matrix ersetzt die heutigen Mengen `ETF_ASSET_CLASSES`/`AGGRESSIVE_ASSET_CLASSES`.

---

## 9. Migrations- & Kompatibilitätsstrategie

- **Keine Datenmigration nötig:** `data/portfolio.json` ist **leer** — es gibt keine Bestandspositionen mit altem `asset_class`. Damit entfällt das Risiko einer Bestandsdaten-Konvertierung.
- **Alte → neue Werte (für Doku/Tests/etwaige externe Eingaben):** Mapping gemäß §5 (`equity→equity/single`, `etf→equity_index/fund`, `index→equity_index/single`, `bond→bond/single`, `commodity→commodity/future`, `precious_metal→precious_metal/future|physical_etc`).
- **Verhaltens-erhaltend für die 5 Bestands-Engines:** Solange `wrapper ∈ {single, fund}`, ändert der Umbau nur den *Weg* zur Engine (Enum statt String), nicht das *Ergebnis*. Snapshot-/Regressionstests sichern das ab (§11).
- **`etf`-Inkonsistenz wird behoben, nicht nur übersetzt:** Der heutige stille Durchfall auf Equity verschwindet — `etf` existiert nicht mehr; XLE landet korrekt in der Index-Engine.
- **Übergangsfreundlichkeit (optional):** Falls externe Aufrufer noch alte Strings senden, kann ein dünner **Kompatibilitäts-Mapper** (alt-String → `(underlying, wrapper)`) an der CLI-/Eingangsgrenze sitzen — *nicht* in der Domäne. Nur, wenn benötigt; sonst weglassen (YAGNI).

---

## 10. Phasen-Schnitt (jede Phase: eigenes Spec→Plan→PR, TDD-Pflicht)

### Phase 1 — Taxonomie-Fundament (verhaltens-erhaltend)
- **Ziel:** `asset_class` durch `underlying` + `wrapper` ersetzen; Engines auf `underlying` umhängen; Dispatch/Urteil/CLI/Portfolio aufs neue Schema; `etf`-Durchfall beheben.
- **Umfang:** Enums (`Underlying`, `Wrapper`); `BottomUpResult`, Orchestrator-Dispatch, `recommendation` (`_short_type`/Mengen), `short_assessment` (Fallback auf neues Schema), `top_down_context`, `Position`, CLI; Reklassifizierung XLE/Index/Rohstoffaktien.
- **Fertig wenn:** alle Bestands-Engines liefern identische Ergebnisse (Regression grün); XLE → Index-Engine; kein `etf` mehr konstruierbar; `python -m pytest -q` grün.

### Phase 2 — Wrapper-Schichten + Daten-Ports (Long)
- **Ziel:** Die Wrapper-Schichten dazuschalten — `future` → Mechanik (Kurve/Roll/Carry/Basis/Hebel/Verfall, COT wiederverwendet); `fund` → Info-Schicht (TER + Tracking-Error). Das Long-Urteil berücksichtigt beide.
- **Umfang:** `FuturesCurveProvider`-Port, `FuturesCurveSnapshot`/`FuturesMechanicsSnapshot`-Modelle, `FuturesMechanicsAgent` (+ `default()`), **Stub-Adapter** (UNAVAILABLE), Verdrahtung im Orchestrator, `physical_etc` ohne Schicht. **Zusätzlich** (§6.6): `FundInfoProvider`-Port + `FundInfoSnapshot` + `FundInfoAgent` (TER + Tracking-Error inkl. Benchmark-Zuordnung) + Stub-Adapter.
- **Fertig wenn:** Future- und Fund-Pfad liefern mit Stub sauber UNAVAILABLE (kein Crash); reine Signal-/Kennzahl-Funktionen je Konzept getestet (Grenzfälle); Long-Empfehlung integriert beide Schichten; Tests grün.

### Phase 3 — Long/Short-Feinschliff der neuen Kategorie
- **Ziel:** Eigener Short-Zweig für `wrapper=future` (kein Borrow/Squeeze; Roll-Yield für Short; Cost-Curve-Boden als Deckel); Sizing über Hebel-Schicht.
- **Umfang:** `derive_short_assessment` future-Zweig; Short-Typ AGGRESSIV; Deckel-/Dämpfer-Logik.
- **Fertig wenn:** Short für Future bewertbar (nicht mehr Pauschal-Fallback); Grenzfälle (Contango/Backwardation/Floor-Nähe/Verfall) getestet; Tests grün.

---

## 11. Teststrategie (TDD verpflichtend, AGENTS.md §4)

- **Reihenfolge je Einheit:** erst Test (Rot) → implementieren bis Grün → aufräumen. Kein Code ohne vorher fehlschlagenden Test.
- **Schwellen-Grenzfälle** (für jede Signal-Funktion in §6.3): genau **auf** der Schwelle, knapp darüber/darunter, `None`, negative Werte. Konkret: Kurvenneigung bei exakt ±5 %, implizite Convenience-Yield exakt am Perzentil-Schwellwert (oberes/unteres Perzentil der eigenen Historie, §6.3c), Verfall bei exakt 5 Tagen, leere/einpunktige Kurve.
- **Lückenlosigkeit** (AGENTS.md §2): Property-/Tabellentest, dass **jeder** Slope-Wert in genau eine Klasse fällt (keine Lücke zwischen `<` und `<=`).
- **Fehlerpfade → neutraler Default:** `FuturesCurveProvider` wirft / liefert `None` ⇒ `FuturesMechanicsAgent.default()` ⇒ UNAVAILABLE, Gesamtanalyse läuft weiter.
- **Dispatch-Tests:** jeder `underlying` routet zur richtigen Engine; `wrapper=future` aktiviert die Schicht, `physical_etc`/`single`/`fund` **nicht**.
- **Reklassifizierung:** XLE ⇒ Index-Engine; Exxon ⇒ Equity; Gold-Future vs. Gold-physisch-ETC ⇒ gleiche PM-Engine, Schicht nur beim Future.
- **Regression (Phase 1):** Snapshot-Vergleich der 5 Bestands-Engines vor/nach dem Schema-Wechsel (verhaltens-erhaltend) — **gilt nur für `wrapper ∈ {single, fund}` auf gleichen Eingaben**. **Ausnahme `etf`:** Das ist eine **gewollte** Verhaltensänderung (XLE: Equity- → Index-Engine); der Test muss hier das **neue** Index-Ergebnis als Soll prüfen, **nicht** das alte (falsche) Equity-Ergebnis festschreiben — sonst zementiert die Regression den behobenen Durchfall-Bug.
- **Bestehender Test:** `tests/test_short_assessment_engine.py` (prüft Nicht-equity-Fallback) entsprechend anpassen.
- **Vor jedem „fertig":** `python -m pytest -q` laufen lassen, Ergebnis nennen.

---

## 12. Bewusst zurückgestellte Folge-Aufgaben (eigene Blöcke, nicht Teil dieser Arbeit)

- **VIX als Hedge-Instrument** — gehört in die **Track-B-Hedge-/Portfolio+Regime-Schicht**, *nicht* in den Deep-Dive. Dort wird die VIX-Analyse gebaut (Mean-Reversion; Contango = „wie teuer ist die Versicherung gerade"). VIX hat **nur** Hülle `future` — Spot-VIX ist nicht haltbar (nur eine berechnete Zahl). ⇒ Eigener Spec, wenn Track B drankommt.
- **Rohstoff-Sensitivität von Aktien** — Öl-/Minenaktien bleiben `equity`, **erben** aber das gerichtete Signal des relevanten Rohstoffs als **Rücken-/Gegenwind** (eine *Verknüpfung*, keine Umklassifizierung). Die neue Taxonomie **ermöglicht** das erst: das Rohstoff-Signal hat jetzt einen klaren, eindeutigen Ort (`underlying=commodity`-Engine), aus dem die Equity-Analyse es referenzieren kann. ⇒ Eigener Spec.
- **COT für Edelmetall mit echten Daten** — `PreciousMetalsResult.cot_signal` ist heute hart NEUTRAL; die Futures-Schicht ist der natürliche Ort, dies später zu speisen.
- **Natürliche-Sprache-Resolver für die Eingabe** (entschieden §13.7) — wandelt freie Eingaben wie „gold future" / „FUTURE, GOLD" in das kanonische Tripel `(underlying, wrapper, Wurzelsymbol)`. Erweiterung der bereits geplanten Ticker-Auflösung (Logbuch §9b: „apple"→AAPL) um Hüllen-/Basiswert-Erkennung, über eine **Such-/Nachschlage-Quelle** (kein LLM-Raten). Frontend-/Eingangsschicht, **nicht** Teil von Phase 1/2.

---

## 13. Getroffene Entscheidungen (Review-Session 2026-06-21)

Alle ursprünglich offenen Fragen wurden entschieden:

1. **`equity_index` `single` vs. `fund`:** ✅ **`single` = Index als Marktbarometer** (z. B. `^GSPC`), **`fund` = konkreter ETF** (SPY/XLE). Beide nutzen dieselbe Index-Engine; die Trennung zahlt sich beim späteren ETF-Look-Through aus.
2. **Schicht für `fund`:** ✅ **Jetzt einbauen, voll** — TER (Kosten-Drag) **und** Tracking-Error, beides Kosten-/Qualitäts-Hinweis (kein Richtungssignal), defensiv UNAVAILABLE. *Abhängigkeit:* Benchmark des ETF muss für den Tracking-Error bekannt sein. Details §6.6.
3. **Hebel-Default ohne Margin-Daten:** ✅ Nominalexposure einer Future-Position **≤ 10 %** des Depots (= bestehender `_position_size_pct`-Cap). Details §6.3e.
4. **Lagerkosten/Convenience-Yield:** ✅ **Nicht raten** — die **implizite Convenience-Yield** aus Spot + Future + Zins ableiten und ihr **Niveau/Trend gegen die eigene Historie** als Knappheits-Signal nutzen; zirkuläres „Mispricing" entfällt. Details §6.3c.
5. **Kompatibilitäts-Mapper (alt-String → Tupel):** ✅ **Weglassen** (Depot leer, CLI wird umgestellt, YAGNI; bei Bedarf später nachrüstbar).
6. **Benennung `equity_index`:** ✅ **Umbenennen** (`index` → `equity_index`) — eindeutig gegenüber Rohstoff-Indizes; Kosten minimal, da Phase 1 die Dateien ohnehin anfasst.
7. **Future-Symbol-Konvention:** ✅ **Intern Wurzelsymbol** (`GC`/`CL`); der `FuturesCurveProvider` liefert daraus die Kurve und wählt den vorderen Kontrakt. **Obendrauf** (Folge-Aufgabe, Frontend, §12): ein **Natürliche-Sprache-Resolver**, der „gold future" → `(precious_metal, future, GC)` auflöst (Erweiterung der Ticker-Auflösung §9b, kein LLM-Raten).
