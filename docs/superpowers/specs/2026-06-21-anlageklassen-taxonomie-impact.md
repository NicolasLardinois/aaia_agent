# Impact-Analyse: Anlageklassen-Taxonomie (underlying + wrapper) auf die offene Roadmap

**Datum:** 2026-06-21 · **Typ:** Impact-/Vorab-Analyse (kein Code, keine Tests) · **Scope dieser Datei:** ausschließlich Analyse.

> Diese Datei beantwortet **eine** Frage: Wenn wir die geplante Taxonomie-Umstellung umsetzen, **wie wirkt sie auf jede bereits geplante, noch offene Aufgabe** aus `docs/open_todos.md` und `docs/short.md`? Für jede betroffene Aufgabe: (a) Auswirkung (keine/gering/mittel/hoch), (b) **warum**, (c) **wie** anpassen. Positive Effekte (Vereinfachung, behobene Bugs) sind ausdrücklich mitgenommen.

---

## 1. Zusammenfassung + Methodik

### 1.1 Was die geplante Änderung tut (Kurzfassung, eingeordnet)

Heute trägt jede Anlage **ein** Feld `asset_class: str` (`"equity" | "bond" | "commodity" | "precious_metal" | "index"`, im CLI zusätzlich `"etf"`). Dieses eine Feld erfüllt **zwei** Aufgaben gleichzeitig: es bestimmt die **Analyse-Engine** (Dispatch im `BottomUpOrchestrator`) **und** dient als Proxy für die **Mechanik/Hülle** (z. B. `_short_type` leitet aus `etf`/`index` „defensiv" ab, `ETF_ASSET_CLASSES` mischt Instrument-Typ und Engine).

Die Umstellung **zerlegt** dieses überladene Feld in zwei orthogonale Achsen:

- **`underlying`** (Basiswert) — bestimmt die **Analyse-Engine**: `equity · equity_index · bond · commodity · precious_metal`.
- **`wrapper`** (Hülle) — schaltet eine **Mechanik-Schicht** zu: `single · fund · future · physical_etc`.

Kernaussagen, die für die Folgenabschätzung entscheidend sind:

1. **„Futures" ist KEINE Anlageklasse**, sondern ein `wrapper`-Wert. Das löst die im Logbuch (`short.md` §10, `open_todos.md` §9) noch offene, ungelöste Frage „Futures als neue Anlageklasse?" **strukturell auf** — sie wird vom Tisch genommen und durch eine saubere Mechanik-Schicht ersetzt.
2. **Umfang dieser Arbeit:** Rohstoff-/Edelmetall-**Futures** (wrapper=future) + **physische Metall-ETCs** (wrapper=physical_etc). Rohstoff-/Minenaktien → `underlying=equity`; Sektor-ETFs → `underlying=equity_index`.
3. **Bestehende Engines werden wiederverwendet** (`CommodityChiefAgentMikro`, `PreciousMetalsChiefAgent`). **NEU** ist nur die **Futures-Mechanik-Schicht** bei `wrapper=future`: Terminkurve (Contango/Backwardation), Roll-Yield/Carry, Hebel/Margin, Verfall, Basis, Cost-of-Carry.
4. **Long zuerst, Short später.** **VIX** wird hier **nicht** gebaut (Track B / später). Aktien-Rohstoff-Sensitivität ist eine spätere Verknüpfung.

### 1.2 Verifizierter Blast-Radius (im Code geprüft)

| Datei | Heutiger Zustand (verifiziert) | Berührung |
|---|---|---|
| `core/domain/models.py` | `BottomUpResult.asset_class: str` + pro-Klasse-Slots (`bond`, `index`, `commodity_deep`, `precious_metals`); `ShortAssessment.asset_class`, `DeepDiveResult.asset_class` | Modell-Erweiterung (zwei Felder statt einem) |
| `orchestrators/bottom_up_orchestrator.py` | `run()` Z. 40-48: `if asset_class == "precious_metal"/"bond"/"index"/"commodity" → …`, sonst equity | **Dispatch-Kern** — wird auf `underlying` umgestellt |
| `core/domain/recommendation.py` | `ETF_ASSET_CLASSES={"etf","index"}`, `AGGRESSIVE_ASSET_CLASSES={"equity","precious_metal","commodity","bond"}`, `_short_type()` Z. 40-43 | `_short_type` ist heute eine **wrapper-Frage**, im Code aber an `asset_class` aufgehängt |
| `core/domain/short_assessment.py` | Z. 57 `if asset_class != "equity": …` → Fallback „klassenspezifische Short-Logik folgt" | Dispatch-Punkt für künftige Klassen-Shorts |
| `core/domain/portfolio.py` | `Position` (frozen dataclass): `asset_class: str = "equity"`, **kein Enum**, kein wrapper | Position-Modell erweitern |
| `core/domain/top_down_context.py` | `_BUFFETT_RELEVANT_ASSETS={"equity","etf","index"}` | Buffett-Relevanz ist eine **underlying**-Frage |
| `app/main.py` | CLI: `bottomup TICKER [asset_class] [sector]`; akzeptiert `equity|bond|commodity|precious_metal|etf` | CLI-Argument-Schema |
| `agents/judgment/judgment_agent.py` | reicht `bottom_up.asset_class` an `derive_recommendation`, `derive_short_assessment`, `DeepDiveResult` durch (Z. 167-214) | Durchreich-Stellen |
| `tests/` | spiegeln die Paketstruktur; Tests mit `asset_class=`-Literalen | Test-Anpassung |

**Wichtige Beobachtung (motiviert die ganze Umstellung):** Es existieren **zwei inkonsistente Mengen** für „ist das ein Korb/ETF?":
- `recommendation.ETF_ASSET_CLASSES = {"etf", "index"}`
- `top_down_context._BUFFETT_RELEVANT_ASSETS = {"equity", "etf", "index"}`

und der **Orchestrator kennt `"etf"` gar nicht** (es fällt in den equity-Default), während CLI/`_short_type`/Buffett `"etf"` sehr wohl kennen. Das ist genau die Art „ein Feld, zwei Bedeutungen"-Drift, die die Trennung beseitigt — siehe §4.

### 1.3 Methodik

Jede offene Aufgabe aus `open_todos.md` (§1-§10) und `short.md` wurde gegen die zwei neuen Achsen geprüft:
- **Berührt die Aufgabe Dispatch nach `asset_class`?** → mind. mechanische Berührung.
- **Braucht die Aufgabe Futures-Kurven-/Roll-/Hebel-Daten?** → **starke Synergie oder Vorbedingung** (die hier gebaute Schicht liefert genau das).
- **Behandelt die Aufgabe ETF/Fonds/physisch als Sonderfall?** → der `wrapper` ersetzt heutige String-Heuristiken (Vereinfachung).
- **Rechnet die Aufgabe mit Exposure/Beta/Sizing?** → **Hebel** (Future) und **physische** Hülle ändern die Nominal-/Exposure-Rechnung (Risiko, muss bewusst behandelt werden).

Auswirkungs-Skala: **keine** (läuft unverändert) · **gering** (mechanische Signatur-/String-Anpassung) · **mittel** (Logik muss eine neue Achse berücksichtigen) · **hoch** (Aufgaben-Design ändert sich, oder die Reihenfolge ggü. dieser Arbeit muss neu entschieden werden).

---

## 2. Auswirkungs-Matrix

| # | Aufgabe (Roadmap) | Auswirkung | +/− | Kurzbegründung |
|---|---|---|---|---|
| A | **Rohstoff-Short** (Roll-Yield/Carry, Contango/Backwardation, Cost-Curve-Boden, Angebotsschock-Squeeze) — `short.md` §10 / `open_todos.md` §9 | **hoch** | **+ positiv** | Braucht GENAU die Futures-Kurve/Roll-Daten, die diese Arbeit als Schicht einführt → Schicht ist die Vorbedingung; Short-Block erbt sie statt sie selbst zu bauen |
| B | **Edelmetall-Short** | mittel | + positiv | Profitiert von derselben Schicht (GC/SI-Futures); Reihenfolge-Synergie |
| C | **Anleihe-Short** (Carry/Duration/Credit-Asymmetrie) | gering | neutral | Eigene Mechanik (DV01), nutzt die Futures-Schicht (noch) nicht; profitiert nur vom sauberen `underlying`-Dispatch |
| D | **Asset-Klassen-Short-Dispatch** in `derive_short_assessment` (Z. 57 `!= "equity"`) | mittel | + positiv | Muss von `asset_class` auf `underlying`+`wrapper` umgestellt werden; danach sauberer Dispatch-Punkt für A/B/C |
| E | **F4c — Nicht-Aktien-Hedges** (Bonds DV01, Rohstoffe je Underlying, Edelmetalle) — Track B | mittel | + positiv | „je Underlying" ist exakt die neue Achse; Hedge-Instrument-Registry kann `underlying`+`wrapper` als Schlüssel nutzen; Future ist das natürliche Hedge-Instrument |
| F | **Risk-Kennzahlen: net_exposure / net_beta** (PR #11) — Hebel & physische ETCs | **hoch** | − Risiko | Future trägt Nominal ≫ Margin; physisches ETC ≈ 1:1 → naives `Σ signed_value` und `net_beta` werden ohne Hebel-/Notional-Behandlung falsch |
| G | **F4b — ETF-Look-Through** (`get_index_holdings`) | gering | + positiv | `wrapper=fund` macht „ist das ein Korb?" explizit statt String-Rateraten (`etf`/`index`); Look-Through-Trigger wird sauberer |
| H | **Block #4 — Short-Backtest** (gespiegelte Returns, Borrow-Kosten, getrennte Auswertung) | mittel | neutral | Future-Returns = Spot + Roll (Carry); physisch hat keine Borrow-Kosten, aber Lager-/TER-Carry → Backtest braucht wrapper-bewusste Carry-Behandlung |
| I | **ShortThesisAgent (LLM, Track B)** | gering | neutral | Prompt/These muss `underlying`+`wrapper` kennen (Future-These ≠ Spot-These), sonst unverändert |
| J | **Equity-Momentum-Agent (long+short)** | keine | neutral | Reines Equity-`underlying`, kein wrapper-Bezug |
| K | **Konfidenz-Kalibrierung** (`recommendation.py:67-79`, Buckets je (alignment, severity)) | mittel | − Risiko | Neue `underlying×wrapper`-Kombis haben andere Trefferquoten (Future-Carry, Roll); Bucket-Schlüssel sollte um `underlying`/`wrapper` erweitert werden, sonst vermischt der Backtest heterogene Trades |
| L | **Daten-Go-Live Plan E** — COT, Supply/Demand, Fear&Greed, Bond-Rohdaten, Index-Holdings | mittel | + positiv | **NEUER `FuturesCurveProvider`-Port** kommt hinzu (passt ins Plan-E-Muster); COT/Supply-Demand-Adapter speisen sowohl Long- als auch Rohstoff-Short → Doppelnutzen |
| M | **`cot_signal` hart NEUTRAL** in commodity/precious_metals_chief | gering | + positiv | Wird durch die Datenanbindung (L) ohnehin gelöst; die Schicht macht COT zudem für die Roll-/Positionierungs-Analyse nutzbar |
| N | **VIX/Sentiment, fear_greed_agent Stub** | keine | neutral | Ausdrücklich NICHT Teil dieser Arbeit (VIX-Hedge = Track B, Folge-Aufgabe) |
| O | **§9b Ticker-Auflösung** (`SymbolSearchProvider`) | gering | neutral | Muss künftig zusätzlich `underlying`+`wrapper` klassifizieren (z. B. „GLD" → precious_metal/physical_etc), nicht nur das Symbol |
| P | **Portfolio: Position-Modell** (`portfolio.py`) | **hoch** | + positiv | `Position` muss um `wrapper` (und am besten `underlying`) erweitert werden; betrifft P&L, Klumpen-Buckets, Exposure — überschneidet sich direkt mit F |
| Q | **Offene Bugs #30, #42, #46, #47** | keine | neutral | Kein Bezug zur Taxonomie (Regime-Default, YTD-Index, except-Schluck, Chief-Aggregat) |
| R | **Test-Lücken** (RegimeDetector, Moat, ValuationRange, Fundamentals, Chief-Aggregation, Round-Trip) | keine–gering | neutral | Inhaltlich unberührt; nur Round-Trip-/Cache-Tests müssen die zwei neuen Felder mit-serialisieren |
| S | **ResultCache Bottom-Up Round-Trip** (Folge Bug #1) | gering | − Achtung | `save_bottom_up`/`load_bottom_up` müssen die neuen Felder symmetrisch lesen/schreiben (sonst neuer „Bug #1"-Typ) |
| T | **Foundation-/`_short_type`-Logik** (`recommendation.py`) | mittel | + positiv | „defensiv vs. aggressiv" ist eine reine **wrapper/underlying**-Frage, heute fälschlich an `asset_class` gehängt → wird korrekt |

---

## 3. Detailanalyse je betroffener Aufgabe

### A — Rohstoff-Short (Auswirkung: HOCH, positiv) — die zentrale Synergie

**Was ändert sich:** Der Rohstoff-Short (`short.md` §10, `open_todos.md` §9 „Asset-Klassen-Shorts") nennt als Spezifika explizit **Roll-Yield/Carry, Contango/Backwardation, Cost-Curve-Boden, Angebotsschock-Squeeze** und als Datenbedarf „**Futures-Kurve, Produktionskosten**". Das ist deckungsgleich mit der **Futures-Mechanik-Schicht** (Terminkurve, Roll-Yield/Carry, Basis, Cost-of-Carry), die diese Arbeit für `wrapper=future` einführt.

**Warum:** Ohne diese Schicht müsste der Rohstoff-Short die Terminkurven-/Roll-Logik **selbst** bauen — die teuerste Komponente des Blocks. Mit der Schicht reduziert sich der Rohstoff-Short auf eine **short-spezifische Interpretation** bereits beschaffter Fakten (Grundsatz aus `short.md` §4: „geteilte Fakten + Short-Schicht"): Contango wirkt für den Shortenden als **Carry-Rückenwind** (negativer Roll-Yield kostet den Long, hilft also dem Short), Backwardation als Gegenwind; der Cost-Curve-Boden ist ein **Mean-Reversion-Risiko nach oben** (Squeeze).

**Wie anpassen:**
- **Reihenfolge fixieren:** Die Futures-Schicht (diese Arbeit, **Long**) **vor** dem Rohstoff-Short bauen. Im Logbuch ist „Asset-Klassen-Shorts" heute ein offener Block ohne Vorbedingung — diese Vorbedingung jetzt **explizit eintragen** (Rohstoff-Short hängt an der Futures-Schicht).
- **Schicht so kapseln, dass die Short-Seite sie konsumiert:** Roll-Yield/Carry/Contango als **strukturierte Felder** auf dem Commodity-Future-Snapshot ausgeben (nicht nur im Long-Signal verbacken), damit `derive_short_assessment` sie als Flags lesen kann (analog zur Flag-Registry `core/domain/short_flags.py`).
- Beim Bau der Schicht die **Vorzeichen-Konvention** dokumentieren (Carry aus Sicht des Long; der Short dreht das Vorzeichen) — fachliche Korrektheit (AGENTS.md §3).

### B — Edelmetall-Short (mittel, positiv)

**Was ändert sich:** Edelmetall-Short (GC/SI als Future) erbt dieselbe Futures-Schicht; bei `wrapper=physical_etc` (z. B. physisches Gold-ETC) gibt es **keinen Roll**, dafür **Lager-/Verwaltungs-Carry (TER)**.

**Warum:** Die Schicht deckt beide Hüllen des Edelmetall-Universums ab, die in dieser Arbeit ohnehin gebaut werden (Future + physical_etc). Der Edelmetall-Short ist danach analog zum Rohstoff-Short eine reine Interpretationsschicht über `PreciousMetalsResult` + Future-/ETC-Mechanik.

**Wie anpassen:** Edelmetall-Short **nach** dieser Arbeit terminieren; die Realzins-/Zyklus-Logik (bereits in `precious_metals`-Engine) mit dem Carry der jeweiligen Hülle kombinieren.

### C — Anleihe-Short (gering, neutral)

**Was ändert sich:** Wenig direkt. Der Anleihe-Short nutzt **DV01/Duration/Credit-Asymmetrie/Carry (Kupon)** — eine **andere** Mechanik als Terminkurven-Roll. Ein Bond-**Future** wäre erst eine spätere Erweiterung (außerhalb des Scopes dieser Arbeit, der Rohstoff/Edelmetall ist).

**Warum:** Die Futures-Schicht ist hier (noch) nicht der Engpass; der Bond-Short braucht zuerst echte Bond-Rohdaten (`get_bond_data` = `{}`, Plan C/§2). Profitiert nur indirekt: der saubere `underlying=bond`-Dispatch ersetzt das heutige `!= "equity"`-Fallback.

**Wie anpassen:** Anleihe-Short unabhängig von dieser Arbeit planen; **wenn** später ein Bond-Future-Hedge kommt (siehe F4c/E), die hier gebaute Future-Mechanik wiederverwenden statt neu zu bauen.

### D — Short-Dispatch in `derive_short_assessment` (mittel, positiv)

**Was ändert sich:** Heute (`short_assessment.py:53,57`):
```python
asset_class = getattr(bottom_up, "asset_class", "equity")
...
if asset_class != "equity":
    # Fallback: klassenspezifische Short-Logik folgt
```
Nach der Umstellung ist die Verzweigung nach `underlying` (welche Engine/These) und `wrapper` (welche Mechanik) zu treffen.

**Warum:** Mit zwei Achsen wird der Equity-Zweig sauber von Commodity/Precious-Metal getrennt, und der Future-Mechanik-Aufschlag (Carry/Squeeze als Modifikator) hängt an `wrapper`, nicht an der Klasse.

**Wie anpassen:**
- `derive_short_assessment` so umstellen, dass es `bottom_up.underlying` für die Thesen-Engine und `bottom_up.wrapper` für den Mechanik-Aufschlag liest.
- Den heutigen einzeiligen Fallback (`!= "equity"`) durch echte Zweige je `underlying` ersetzen — **schrittweise**: Equity bleibt voll, commodity/precious_metal bekommen ihren Zweig erst mit Block A/B, bis dahin weiterhin Fallback (Verhalten unverändert, kein Regressionsrisiko).
- **Achtung Reihenfolge:** Diese Umstellung **berührt die Long-Seite nicht** (`derive_recommendation`), aber `short_assessment.py` und Tests — wegen Regressionsrisiko (AGENTS.md §4) Grenzfälle explizit testen.

### E — F4c: Nicht-Aktien-Hedges, instrumentengenau (mittel, positiv)

**Was ändert sich:** F4c will Bonds via **DV01** → Staatsanleihe-Future, Rohstoffe **je Underlying** → eigener Future/ETF, Edelmetalle einzeln (GC/SI). Die Formulierung „je Underlying" und „eigener Future" ist **wörtlich** die neue `underlying`+`wrapper`-Achse.

**Warum:** Die in F4c skizzierte „Hedge-Instrument-Registry + Exposure-Rechner je Anlageklasse" wird mit zwei Achsen natürlich modellierbar: Schlüssel = `underlying`, Hedge-Instrument = passende `wrapper=future`-Position. Das hier gebaute Future-Notional/Hebel-Wissen (siehe F) ist genau die Größe, die der Hedge-Rechner braucht.

**Wie anpassen:** F4c **nach** dieser Arbeit; die Future-Schicht als Lieferant für „1 Future = wie viel Nominal-Exposure" nutzen, statt es im Hedge-Rechner zu duplizieren. Hinweis im Logbuch: F4c-Vorbedingung „Future-Notional aus der Mechanik-Schicht" ergänzen.

### F — Risk-Kennzahlen: Hebel & physische ETCs im net_exposure/net_beta (HOCH, Risiko)

**Was ändert sich:** Das ist der **gefährlichste** Berührungspunkt. Heute (PR #11, `open_todos.md` §9):
- `net_exposure = Σ long − Σ short` (naiv, je Position `signed_value`),
- `net_beta = Σ(signed_value · β)` nur für equity/index.

Ein **Future** trägt ein **Nominal-Exposure ≫ eingesetztem Kapital (Margin)**. Wenn `signed_value` aus „Stückzahl × Preis" oder gar aus dem Margin-Einsatz gebildet wird, **unterschätzt** das Exposure-/Beta-Maß das echte Marktrisiko dramatisch. Ein **physisches ETC** dagegen ist ≈ 1:1 zum Spot (kein Hebel) — verhält sich also exposure-seitig wie eine normale Position.

**Warum:** Eine Netto-Skalarzahl, die Hebel ignoriert, ist die finanziell **stillste** Fehlerquelle (AGENTS.md §3: „der Test wird grün, die Schlussfolgerung ist falsch"). Ein gehebelter Future von 100 k Nominal bei 10 k Margin würde als 10 k ins Netto eingehen → das Buch sähe 10× weniger exponiert aus, als es ist.

**Wie anpassen:**
- Exposure muss auf **Notional-Basis** rechnen: `notional = kontrakte × kontraktgröße × preis` (Future), `wert = stück × preis` (physisch/single/fund). Der `wrapper` entscheidet die Formel.
- `signed_value` in `_evaluate_positions`/Snapshot so definieren, dass es **Notional** ist, nicht Margin. Margin separat ausweisen (Kapitalbindung ≠ Exposure).
- `net_beta` für `underlying ∈ {equity, equity_index}` weiterführen; für `wrapper=future` auf Rohstoff/Edelmetall **kein Aktienmarkt-Beta** ansetzen (konsistent mit der PR-#11-Entscheidung „Bonds/Rohstoffe/Edelmetalle raus aus net_beta") — deren Risiko fängt die Vola.
- **TDD:** Grenzfälle — gehebelter Future, physisches ETC (1:1), und die Mischung — explizit testen, dass Notional korrekt skaliert.

### G — F4b: ETF-Look-Through (gering, positiv)

**Was ändert sich:** F4b braucht `get_index_holdings` und entscheidet „ist das ein Korb, der durchschaut werden muss?". Heute wird „Korb" über Strings (`etf`/`index`) erraten.

**Warum:** `wrapper=fund` macht die Korb-Eigenschaft **explizit und orthogonal** zum `underlying`. Ein Sektor-ETF ist dann `underlying=equity_index, wrapper=fund` — der Look-Through-Trigger ist „wrapper == fund" statt einer der zwei heute divergierenden String-Mengen.

**Wie anpassen:** Beim Bau von F4b den Look-Through an `wrapper=fund` knüpfen. Geringer Aufwand, aber Reihenfolge: die Taxonomie sollte **vor oder gemeinsam mit** F4b stehen, damit F4b nicht erneut String-Heuristiken einbaut, die später zurückgebaut werden müssen.

### H — Block #4: Short-Backtest (mittel, neutral)

**Was ändert sich:** Future-Returns ≠ Spot-Returns: der **Roll/Carry** ist Teil der realisierten Rendite. Physische ETCs haben **keine** Borrow-Kosten (man besitzt das Metall), aber **Lager-/TER-Carry**.

**Warum:** Der Block-#4-Plan nennt „Borrow-Kosten im Backtest". Für Futures ist die ökonomisch korrekte Carry-Größe der **Roll-Yield**, nicht die Aktien-Leihgebühr; für physische ETCs die **TER**. Ein einheitliches „Borrow-Kosten"-Modell wäre fachlich falsch.

**Wie anpassen:** Backtest-Carry **wrapper-bewusst** modellieren: `future → Roll/Carry`, `single (Aktie) → Borrow-Rate`, `physical_etc → TER/Lager`, `fund → TER`. Im Block-#4-Logbucheintrag diesen Carry-Split als Anforderung ergänzen.

### I — ShortThesisAgent (LLM, Track B) (gering, neutral)

**Was ändert sich:** Der LLM-Prompt muss `underlying`+`wrapper` kennen (heute reicht `judgment_agent.py:127` nur `bottom_up.asset_class` in den Prompt). Eine Future-These (Contango/Roll/Verfall) liest sich anders als eine Spot-These.

**Wie anpassen:** Beide Felder in den Prompt aufnehmen; ansonsten keine strukturelle Änderung (B sitzt auf A).

### J — Equity-Momentum-Agent (keine)

Reines `underlying=equity`, kein Wrapper-Bezug. Läuft unverändert; speist Long + die dormanten Short-Momentum-Flags.

### K — Konfidenz-Kalibrierung (mittel, Risiko)

**Was ändert sich:** `compute_confidence` (`recommendation.py:72-108`) bucketet historische Trefferraten als String-Key `"{alignment}:{severity}"`. Neue `underlying×wrapper`-Kombinationen (z. B. Rohstoff-Future-Short) haben **andere** Erfolgswahrscheinlichkeiten als Equity (Carry/Roll/Squeeze-Dynamik), und der **harte 0.70-Deckel** der Short-Engine (`short_assessment.py:101`) ist heute equity-kalibriert.

**Warum:** Wenn Future-Short-Trades und Equity-Long-Trades in **denselben** Bucket fallen, mischt der Backtest heterogene Verteilungen → die kalibrierte Konfidenz wird für beide unscharf.

**Wie anpassen:**
- Bucket-Schlüssel um **`underlying`** (mindestens) erweitern, sobald Nicht-Equity-Trades in nennenswerter Zahl entstehen: `"{underlying}:{alignment}:{severity}"`. **Achtung Stichprobengröße:** mehr Dimensionen → kleinere Buckets → `_CALIB_MIN_N` (=10) wird seltener erreicht → häufiger Fallback 0.70. Daher erst splitten, wenn genügend Daten je Underlying da sind; vorher bewusst zusammenfassen.
- Diese Erweiterung ist **kein** Vorbedingungs-Blocker dieser Arbeit (Long-Future zuerst, Kalibrierung folgt mit Block #4). Im Logbuch als Folge-Frage notieren.

### L — Daten-Go-Live Plan E + neuer FuturesCurveProvider-Port (mittel, positiv)

**Was ändert sich:** Die Futures-Schicht braucht **Terminkurven-Daten** (mehrere Kontraktmonate, Settlement, Open Interest) → ein **neuer Port** `FuturesCurveProvider` (Hexagonal, analog `COTProvider`/`CommoditySupplyProvider` aus Plan E). Cost-Curve-Boden braucht zudem **Produktionskosten** — überschneidet sich mit `CommoditySupplyProvider` (EIA/USDA/LME).

**Warum:** Plan E hat das Muster „Port + Agenten-Logik gebaut, echte Quelle folgt" bereits etabliert. Der neue Port fügt sich nahtlos ein. **Doppelnutzen:** COT (CFTC) und Supply/Demand speisen sowohl den Long-Rohstoff-Pfad als auch später den Rohstoff-Short → eine Datenanbindung, zwei Konsumenten.

**Wie anpassen:**
- `FuturesCurveProvider`-Port in `core/ports/data_provider.py` definieren; Stub-Adapter, der `UNAVAILABLE`-äquivalent liefert (nicht-brechend), bis eine echte Quelle (z. B. Yahoo-Futures-Chains, CME) angebunden ist.
- Cost-Curve-Boden an `CommoditySupplyProvider` (Produktionskosten-Kurve, Plan E) hängen — keine zweite Kostenquelle.
- Im Plan-E-Logbucheintrag den neuen Port **explizit** ergänzen.

### M — `cot_signal` hart NEUTRAL (gering, positiv)

**Was ändert sich:** `precious_metals_chief_agent.py:45,56` und der Commodity-Pfad setzen `cot_signal`/COT real, sobald COT-Daten (L) angebunden sind. Die Futures-Schicht macht die COT-Positionierung zusätzlich für **Roll-/Squeeze-Analyse** nutzbar (Spekulanten-Extreme an der Kurve).

**Wie anpassen:** Wird durch die COT-Anbindung (L) ohnehin gelöst; hier nur Mitnahmeeffekt — beim Anbinden gleich an die Future-Mechanik koppeln.

### N — VIX/Sentiment (keine)

Ausdrücklich **nicht** Teil dieser Arbeit. VIX bleibt Indikator; der VIX-**Hedge** ist eine Folge-Aufgabe (Track B). `fear_greed_agent`-Stub unberührt. Hier nur festhalten, damit niemand VIX in diese Arbeit hineinzieht.

### O — §9b Ticker-Auflösung (gering, neutral)

**Was ändert sich:** Der `SymbolSearchProvider` muss künftig nicht nur das **kanonische Symbol** liefern, sondern das Ergebnis auch der Taxonomie zuordnen (z. B. „GLD" → `underlying=precious_metal, wrapper=physical_etc`; „CL=F" → `commodity/future`; „XLE" → `equity_index/fund`).

**Wie anpassen:** Bei der Umsetzung von §9b ein **Klassifikations-Mapping** (Symbol/Instrument-Typ → underlying+wrapper) vorsehen. Geringe Berührung, aber jetzt mitdenken, damit das Auflösungs-Ergebnis direkt in die zwei neuen Felder fließt.

### P — Portfolio: Position-Modell (HOCH, positiv) — überschneidet F

**Was ändert sich:** `core/domain/portfolio.py` `Position` ist eine frozen dataclass mit `asset_class: str = "equity"` (kein Enum), **ohne** wrapper. Das Logbuch fordert ohnehin, das Position-Modell um `wrapper` zu erweitern (P&L, Klumpen-Buckets, Exposure).

**Warum:** Eine Future-Position braucht `wrapper=future` für die **korrekte Notional-/Hebel-P&L** (F). Eine ETF-Position braucht `wrapper=fund` für **Look-Through** (G) und korrektes Bucketing (das heutige Ein-Feld-`asset_class`/`sector`/`country` kann einen Korb nicht abbilden — bekannter Befund in `open_todos.md` §9).

**Wie anpassen:**
- `Position` um `underlying` und `wrapper` erweitern (Default-Werte für Abwärtskompatibilität der bestehenden `portfolio.json`, z. B. `wrapper="single"`, `underlying` aus `asset_class` ableiten).
- **Migration der `portfolio.json`-Lesung** (`JsonPortfolioProvider`) — wie schon bei `direction` ein **fail-loud** für unbekannte Werte erwägen (konsistent mit PR #7 F3), aber für Bestandsdaten einen klaren Default.
- P&L wrapper-bewusst (Future: Notional/Hebel; physisch: 1:1) — **gemeinsam mit F** umsetzen, da identische Notional-Logik.

### Q — Offene Bugs #30, #42, #46, #47 (keine)

Kein Taxonomie-Bezug: #30 (Regime-Default EXPANSION→NEUTRAL), #42 (Index-YTD/tz-aware), #46 (breites `except` schluckt Fehler), #47 (Chief-Aggregat-Signal). Unabhängig abarbeitbar; **kein** Reihenfolge-Konflikt mit dieser Arbeit.

### R — Test-Lücken (keine–gering)

RegimeDetector, Moat, ValuationRange, Fundamentals, Chief-Aggregation: inhaltlich unberührt. Einzige Berührung: Tests, die `BottomUpResult`/`Position` konstruieren, müssen die zwei neuen Felder setzen (mechanisch).

### S — ResultCache Bottom-Up Round-Trip (gering, Achtung)

**Was ändert sich:** Genau hier entstand **Bug #1** (asymmetrisches save/load von `BottomUpResult`-Feldern → `TypeError`). Zwei **neue** Felder (`underlying`, `wrapper`) erhöhen exakt dieses Risiko.

**Wie anpassen:** `save_bottom_up`/`load_bottom_up` in `adapters/cache/result_cache.py` **symmetrisch** um beide Felder erweitern; den (ohnehin offenen) Round-Trip-Regressionstest **vor** dem Merge dieser Arbeit nachziehen — diese Umstellung ist der ideale Anlass, die Test-Lücke aus §6 zu schließen.

### T — `_short_type`/Foundation-Logik (mittel, positiv)

**Was ändert sich:** `_short_type` (`recommendation.py:40-43`) leitet „DEFENSIV vs. AGGRESSIV" aus `asset_class ∈ {etf,index}` ab. Das ist eigentlich eine **wrapper/underlying**-Frage: ein breiter Index-Fonds → defensiver Hedge; ein Einzeltitel-Future/Aktie → aggressiv.

**Warum:** Mit der Trennung wird die Heuristik korrekt: defensiv ↔ `underlying=equity_index` (Korb), aggressiv ↔ Einzelwert — unabhängig davon, dass „etf"/„index" heute zwei Bedeutungen tragen.

**Wie anpassen:** `_short_type` auf `underlying`/`wrapper` umstellen und `ETF_ASSET_CLASSES`/`AGGRESSIVE_ASSET_CLASSES` durch die Achsen ersetzen. **Gleichzeitig** die in §1.2 dokumentierte **etf-Inkonsistenz** beheben (siehe §4).

---

## 4. Besondere Synergien (der Umbau hilft / behebt Bestehendes)

1. **Rohstoff-Short erbt die Futures-Schicht (größte Synergie).** Die teuerste Komponente des Rohstoff-Shorts (Terminkurve/Roll) wird hier für Long gebaut und steht dem Short danach fertig zur Verfügung — „geteilte Fakten + Short-Schicht" (`short.md` §4) greift exakt. → Aufgaben A, B, H.

2. **„Futures als neue Anlageklasse?" wird strukturell aufgelöst.** Die seit `short.md` §10 / `open_todos.md` §9 **offene, unentschiedene** Frage entfällt: Futures sind eine **Hülle**, kein Asset. Das verhindert eine sonst drohende Verdopplung der Deep-Dive-Struktur (eigener „Futures"-Dispatch-Zweig). Positiver Netto-Effekt auf die gesamte Roadmap-Komplexität.

3. **Die etf-Inkonsistenz wird beseitigt (latenter Bug).** Heute kennt der `BottomUpOrchestrator` `"etf"` **nicht** (fällt in equity-Default), während `_short_type`, `ETF_ASSET_CLASSES` und `_BUFFETT_RELEVANT_ASSETS` `"etf"` kennen — und letztere zwei sind sogar **unterschiedlich** definiert (`{etf,index}` vs. `{equity,etf,index}`). Ein Sektor-ETF läuft so heute durch die **Aktien**-Engine, wird aber bei Short/Buffett wie ein Korb behandelt → inkonsistentes Verhalten. Mit `underlying=equity_index, wrapper=fund` verschwindet die Drift: **eine** Achse für die Engine, **eine** für die Mechanik. (Empfehlung: diese Bereinigung als Teil von T ausdrücklich mitnehmen.)

4. **Position-`wrapper` macht ETF-Look-Through und korrektes Bucketing erst sauber möglich.** `wrapper=fund` ist der explizite Trigger für F4b (Look-Through) und löst das in `open_todos.md` §9 beschriebene „ein ETF passt in keinen einzelnen Sektor/Land-Bucket"-Problem an der Wurzel (statt per String-Schwelle). → Aufgaben G, P.

5. **Ein Daten-Adapter, zwei Konsumenten.** COT (CFTC) und Supply/Demand (EIA/USDA/LME) aus Plan E speisen Long-Rohstoff **und** Rohstoff-Short; der neue `FuturesCurveProvider` ebenso. Die Datenarbeit zahlt doppelt ein. → Aufgaben L, M.

6. **`_short_type` wird fachlich korrekt.** Defensiv/aggressiv ist endlich an die richtige Achse gekoppelt. → Aufgabe T.

---

## 5. Besondere Risiken / Konflikte

1. **Reihenfolge ggü. der laufenden Short-Arbeit (mittel).** `short.md`/`open_todos.md` legen die Short-Reihenfolge fest: F4a ✅ → F4b → SHORT+ → 3b Track-B-Hedge → Block #4. Diese Futures-Schicht ist **Long-only** und steht logisch **vor** dem Rohstoff-Short, **kollidiert aber nicht** mit dem laufenden Equity-Short-Programm (anderes `underlying`). **Konkrete Empfehlung:** die Futures-Schicht als **eigenen Track** parallel zum Equity-Short führen; den Rohstoff-Short im Logbuch **explizit hinter** diese Schicht hängen (heute steht er ohne Vorbedingung im Backlog).

2. **Hebel im Exposure (hoch — Finanz-Korrektheit).** Siehe F/P. Das ist das **gefährlichste** Detail: ein naives Notional/Margin-Missverständnis macht das ganze Buch scheinbar sicherer, als es ist. Die Notional-Logik **muss** zusammen mit der Future-Mechanik gebaut und mit Grenzfall-Tests (gehebelt vs. physisch 1:1) abgesichert werden — **bevor** F4c/Track-B-Hedge auf `net_beta`/`net_exposure` aufsetzt. Andernfalls dimensioniert der Hedge falsch.

3. **Kalibrierungs-Buckets vermischen heterogene Trades (mittel).** Siehe K. Solange Future-Short/Long und Equity in **einen** Bucket fallen, ist die kalibrierte Konfidenz unscharf. Konflikt mit der Stichprobengröße: mehr Achsen → kleinere Buckets → öfter Fallback 0.70. **Empfehlung:** Bucket-Split erst mit Block #4 und nur, wenn `n` je Underlying reicht.

4. **Round-Trip-/Persistenz-Regression (gering, aber konkret).** Zwei neue Felder auf `BottomUpResult`, `Position`, `DeepDiveResult`, `ShortAssessment` müssen **überall symmetrisch** serialisiert werden (Cache, Supabase-Memory `analysis_memory`/`portfolio_snapshots`, JSON-Depot). Bug #1 ist die Blaupause, was passiert, wenn nicht. **Empfehlung:** Round-Trip-Test (offene Test-Lücke) im selben PR schließen; Supabase-Spalten (analog `short_action`/`metrics` aus PR #9/#11) **vor** Deploy per `ALTER TABLE` ergänzen, falls Felder persistiert werden.

5. **CLI-/API-Bruch (gering).** Das CLI-Argument `asset_class` (`app/main.py`) und die Doku müssen auf zwei Argumente (oder ein kombiniertes Schema) umgestellt werden. Abwärtskompatibilität: alte Aufrufe `bottomup AAPL equity` sollten weiter funktionieren (Default `wrapper=single`, `underlying` aus dem Alt-Wert ableiten).

---

## 6. Empfohlene Reihenfolge der betroffenen Aufgaben nach diesem Umbau

> Leitlinie: **Modell-/Dispatch-Grundlage zuerst (nicht-brechend), dann Mechanik, dann die Konsumenten.** Jede Stufe per TDD, je eigener PR (AGENTS.md §4/§5).

1. **Taxonomie-Grundlage (diese Arbeit, Teil 1 — nicht-brechend):**
   `underlying`+`wrapper` in die Modelle (`BottomUpResult`, `Position`, `DeepDiveResult`, `ShortAssessment`) mit abwärtskompatiblen Defaults; Dispatch im `BottomUpOrchestrator` auf `underlying`; `_short_type`/Buffett/`ETF_ASSET_CLASSES` auf die Achsen umstellen **und dabei die etf-Inkonsistenz beheben** (§4.3/T). Cache-/Memory-Serialisierung symmetrisch + **Round-Trip-Test** (schließt Test-Lücke S/§6). → deckt D (Vorbereitung), G (Trigger), P, S, T.

2. **Futures-Mechanik-Schicht (diese Arbeit, Teil 2 — Long):**
   `FuturesCurveProvider`-Port + Stub; Schicht bei `wrapper=future` (Contango/Backwardation, Roll-Yield/Carry, Basis, Cost-of-Carry, Verfall, Hebel/Margin); **Notional-Exposure** sauber definieren. Edelmetall + Rohstoff-Future + physisches ETC. → deckt L (Port), F (Notional-Grundlage).

3. **Exposure-/Risk-Korrektur (F):**
   `net_exposure`/`net_beta`/Vola wrapper-bewusst (Notional statt Margin; physisch 1:1) — **bevor** ein Hedge darauf dimensioniert wird.

4. **Daten-Go-Live für die Schicht (L, M):**
   echte Terminkurven-Quelle anbinden; COT + Supply/Demand (Plan E) anschließen; `cot_signal` real verdrahten.

5. **F4b — ETF-Look-Through (G):** an `wrapper=fund` knüpfen (Holdings-Quelle `get_index_holdings`).

6. **Rohstoff-Short (A) + Edelmetall-Short (B):** als Short-Schicht **auf** der Futures-Mechanik; Dispatch-Zweige in `derive_short_assessment` (D).

7. **F4c — Nicht-Aktien-Hedges (E)** + **Track-B-Hedge (3b)**: nutzen Notional/Underlying-Achse.

8. **Block #4 — Short-Backtest (H)** + **Kalibrierungs-Bucket-Erweiterung (K)**: wrapper-bewusste Carry-Modellierung; Bucket-Split je `underlying`, sobald `n` reicht.

9. **Unabhängig / parallel (kein Reihenfolge-Bezug):** §9b Ticker-Auflösung (O, Klassifikations-Mapping mitdenken), ShortThesisAgent (I), Equity-Momentum (J), Bugs #30/#42/#46/#47 (Q), restliche Test-Lücken (R).

**Nicht in diesem Programm:** VIX-Hedge / fear_greed (N — Track B), Anleihe-Short als Future (C — eigene DV01-Mechanik, erst mit Bond-Rohdaten/Plan C).
