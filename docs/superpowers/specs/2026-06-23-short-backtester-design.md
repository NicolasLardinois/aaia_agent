# Short-Backtester (Shorts Block #4) — Design

- **Datum:** 2026-06-23
- **Status:** Entwurf zur Review
- **Spec-Typ:** Fokussierter Block (Spec → Plan → PR, TDD)
- **Geltungsbereich:** rückblickende Bewertung der **Short-Entscheidungen** (`short_action`); Persistenz-Erweiterung; reine Backtest-Mathematik

> Kontext: „Shorts ausbauen" §9 (`docs/open_todos.md`) + Design-Hub `docs/short.md`.
> Die **Form** von Block #4 wurde am 2026-06-18 entschieden (getrennte Short-Auswertung,
> Borrow-Kosten, Trefferquote vs. Auszahlung). Dieser Spec nagelt das **Wie** fest und
> arbeitet **einen seither neuen Befund** ein (Short-Calls werden aktuell gar nicht ausgewertet).

## 0. Ein-Absatz-Zusammenfassung

Der bestehende `JudgmentBacktesterAgent` benotet nur die **Long**-Calls (`recommendation`).
Die echten Short-Entscheidungen liegen seit PR #9 in der separaten Spalte `short_action`
(SHORT / SHORT_PLUS / COVER / HOLD / NONE) und werden **von niemandem ausgewertet** — die
SHORT-Spiegelung im Judgment-Backtester ist toter Code, weil der Long-Zweig kein `SHORT`
mehr ausgibt. Dieser Block baut einen **eigenen** Short-Backtester: er benotet die
Short-Entscheidungen **getrennt**, mit short-gerechten **Leih-Kosten**, **aufgeschlüsselt nach
Short-Grund** (Archetyp), und stellt **Trefferquote neben Auszahlung** (Profit-Faktor) inkl.
einer **Warnung**, wenn beides auseinanderläuft („oft recht, trotzdem Geld verloren").
Er **misst nur** — das Zurückspeisen in die Konfidenz ist ein separater, geprüfter Folgeschritt.

## 1. Befund (Ausgangslage)

- **Short-Calls werden nicht ausgewertet.** `JudgmentBacktesterAgent.run` filtert auf
  `recommendation ∈ {BUY, SELL, SHORT}` (`agents/backtester/judgment_backtester_agent.py:16,41`).
  Der Long-Zweig gibt seit PR #9 kein `SHORT` mehr aus → die echten Short-Calls (`short_action`)
  bleiben unbenotet. Die Return-Spiegelung (`:79`) greift für SELL, aber nicht für echte Shorts.
- **Persistenz-Lücke.** `ShortAssessment` trägt `archetypes` + `confidence`
  (`core/domain/models.py:808-812`), aber `save_analysis` persistiert nur `short_action`
  (`adapters/memory/supabase_memory.py:170,192`) — **nicht** den Short-Grund, **nicht** die
  Short-Konfidenz, **nicht** das `hard_to_borrow`-Flag. Ohne diese Felder ist weder die
  Aufschlüsselung nach Grund noch das gestaffelte Borrow-Modell möglich.
- **Wiederverwendbar vorhanden:** `core/utils/backtest.py` (`HORIZONS_DAYS`, `MIN_SAMPLE`,
  `forward_return`, `hit_rate_ci`, `market_adjusted_return`), `core/utils/performance_metrics.py`
  (`profit_factor`, `max_drawdown`, `apply_costs`), Preis-/Benchmark-Provider aus
  `agents/backtester/bottom_up_backtester_agent.py`, `MemoryPort.load_global_history`/`save_backtester_report`.

## 2. Scope

**In Scope**
1. **Persistenz-Erweiterung:** neue Spalte `short_meta jsonb` auf `analysis_memory`
   (`{archetypes, confidence, hard_to_borrow, squeeze}`); `save_analysis` befüllt sie;
   `load_global_history` liefert sie bereits (`SELECT *`). Migration: `ALTER TABLE`.
2. **Reine Backtest-Mathematik:** `core/utils/short_backtest.py` — Borrow-Modell,
   Einstieg-/Ausstieg-Benotung, Aggregation je Grund, Kennzahlen + Warn-Flag, Buckets.
3. **Dünner Agent:** `agents/backtester/short_backtester_agent.py` — lädt Historie, filtert
   Short-Entscheidungen, ruft die reinen Funktionen, speichert den Short-Report. **Nur messen.**
4. Tests (TDD).

**Out of Scope (mit Begründung)**
- **Konflikt-Backtester** (bewertet `conflict_resolution`, nicht `short_action`) — anderes
  Prüf-Subjekt, eigener Geschwister-Block.
- **Kalibrierungs-Rückspeisung** in die Short-Konfidenz (`compute_confidence`) — ändert lebendes
  Verhalten; eigener geprüfter Schritt (Disziplin wie Regime-Backtest ②: erst messen, dann anwenden).
- COVER, das aus einem geloggten Konflikt stammt, separat dem Konflikt zuzuordnen — hier zählt
  COVER nur als **Short-Motor-Entscheidung** (Spalte `short_action`).

## 3. Architektur & Datenfluss

Eigener Backtester, Geschwister zum `JudgmentBacktesterAgent` (deine „zwei verschiedene
Backtester"-Sicht). Reine Mathematik strikt getrennt vom I/O.

```
MemoryPort.load_global_history(days)
        │  rows mit short_action + short_meta + price_at_analysis + ticker + market + timestamp
        ▼
ShortBacktesterAgent.run()
        │  filtert short_action ∈ {SHORT, SHORT_PLUS, COVER}   (HOLD/NONE raus)
        │  Preis/Benchmark via injizierte Provider (wie Judgment-Backtester)
        ▼
core/utils/short_backtest.py  (reine Funktionen, kein I/O)
        ├─ borrow_cost(...)          Leih-Miete, gestaffelt
        ├─ grade_entry(...)          SHORT/SHORT_PLUS: korrekt, wenn gefallen (netto)
        ├─ grade_exit(...)           COVER: korrekt, wenn danach gestiegen (Verlust vermieden)
        ├─ aggregate_by_reason(...)  je Archetyp: Hit-Rate+CI, Auszahlung, Profit-Faktor, MaxDD
        └─ payoff_warning(...)       Hit-Rate hoch ABER Profit-Faktor < 1
        ▼
MemoryPort.save_backtester_report({backtester_type: "short", ...})   (Buckets im Report, NICHT zurückgeschrieben)
```

**Begründung eigener Agent statt Erweiterung:** anderes Prüf-Subjekt, andere „korrekt"-Regeln
(Einstieg vs. Ausstieg), andere Kosten (Borrow), getrennter Report. Ein einzweckmäßiger Agent
bleibt verständlich und testbar (AGENTS.md §1/§2).

## 4. Borrow-Modell (Leih-Miete) — entschieden A

Echte Leihgebühren sind nicht frei verfügbar → **gestaffelter Proxy** aus dem vorhandenen
`hard_to_borrow`-Flag, anteilig nach Haltedauer:

| Lage | Jahressatz (Startwert) | Begründung |
|---|---|---|
| normal leihbar (`hard_to_borrow=False`/unbekannt) | **1,0 %/Jahr** | breit verfügbare Titel („general collateral") kosten real ~0,3–1 %/Jahr |
| schwer leihbar (`hard_to_borrow=True`) | **8,0 %/Jahr** | „hard-to-borrow" real oft 5–20 %+/Jahr; 8 % als konservativer Mittelwert |
| manueller Satz vorhanden (`short_meta.borrow_rate_manual`) | **dieser Satz** | optionales Feld schlägt den Proxy (Datenrealität, AGENTS.md §3) |

- **Anteilig:** `borrow = jahressatz · (haltetage / 365)`. Haltetage = ausgewerteter Horizont.
- **Nur auf gehaltene Shorts:** Einstiege (SHORT/SHORT_PLUS) tragen Borrow über den Horizont;
  **COVER trägt keine** Borrow auf das Nach-Cover-Fenster (Position ist flach).
- Startwerte sind im Code als begründete Konstanten dokumentiert; spätere Verfeinerung
  (echte Sätze) ist das optionale manuelle Feld.

## 5. Benotungsregeln (Finanz-Korrektheit, AGENTS.md §3)

Einheitlich: erst `forward_return`, dann `market_adjusted_return`, dann `apply_costs`
(Transaktion), dann Borrow abziehen. **Vorzeichen explizit.**

**Einstieg — SHORT / SHORT_PLUS:**
- `net = market_adj_return − transaktionskosten`; **Short-Ertrag** = `−net − borrow`
  (fällt die Aktie, ist `net < 0` → `−net > 0` → Gewinn, minus Miete).
- **korrekt**, wenn `short_ertrag > 0` (Aktie netto gefallen, Miete gedeckt).
- **Auszahlung** für Profit-Faktor/Mittel = `short_ertrag` (vorzeichenbehaftet).

**Ausstieg — COVER (kontrafaktisch):**
- Bewertet das **Nach-Cover-Fenster**: `post = market_adj_return ab Cover-Datum`.
- **korrekt**, wenn `post > 0` (Aktie stieg nach dem Cover → Verlust vermieden, Ausstieg richtig).
- **Auszahlung** = `post` (vermiedener Verlust); **keine** Borrow.

**Ausschluss:** HOLD / NONE (keine Richtungsentscheidung), Einträge ohne Preis/Grund/Folgekurs
→ übersprungen (defensiv, nie Crash).

## 6. Kennzahlen, Aufschlüsselung & Warnung — entschieden A

- **Aufschlüsselung nach Short-Grund** (Archetyp aus `short_meta.archetypes`): Distress,
  Bewertungs-Extrem, Earnings-Verfall, Momentum … (ein Eintrag kann mehrere Archetypen tragen →
  zählt in jeden zugehörigen Bucket). Einstiege und Ausstiege in **getrennten** Report-Abschnitten.
- **Je Bucket:** Trefferquote + Wilson-CI (`hit_rate_ci`), mittlere Auszahlung, **Profit-Faktor**
  (`profit_factor` = Σ Gewinne / Σ Verluste), Max-Drawdown (`max_drawdown`), Stichprobengröße `n`.
- **Warn-Flag je Bucket:** `hit_rate ≥ 0.55` **und** `profit_factor < 1.0` → Flag
  „oft recht, trotzdem Geld verloren" (Squeeze-Asymmetrie). Schwellen als begründete Konstanten.
- **Aggregat** erst ab `n ≥ MIN_SAMPLE` je Bucket (analog Judgment-Backtester); darunter:
  „Stichprobe zu klein" statt Scheinzahl.
- **Buckets im Report** als JSON-serialisierbares Dict
  `{archetyp: {hit_rate, n, mean_payoff, profit_factor}}` — für die **spätere** Kalibrierung
  abgelegt, **nicht** zurückgeschrieben.

## 7. Persistenz-Erweiterung (Task 1 des Plans)

- **Migration:** `ALTER TABLE analysis_memory ADD COLUMN short_meta jsonb DEFAULT '{}'::jsonb;`
  (Muster wie `short_action`/`short_xai`). **Deploy-Schritt vor Merge** — sonst schlägt jeder
  `save_analysis`-INSERT fehl.
- **`save_analysis`** schreibt `short_meta` aus `result.short_assessment`
  (`DeepDiveResult.short_assessment` ist bereits vorhanden — keine Durchreichung nötig):
  `{archetypes, confidence, hard_to_borrow, squeeze_risk, borrow_rate_manual}`
  (defensiv: `short_assessment is None` → `{}`).
- **`load_global_history`** liefert `short_meta` bereits über `SELECT *`.
- Ein `jsonb`-Feld statt drei Einzelspalten: eine Migration, leicht erweiterbar (YAGNI-freundlich,
  konsistent zum bestehenden `indicators_snapshot jsonb`).

## 8. Datenrealität (ehrliche Erwartung)

Wie der Long-Backtester zeigt der Short-Backtester erst belastbare Zahlen, **wenn genug
Short-Calls mit den neuen Feldern aufgezeichnet sind**. Unmittelbar nach dem Bau ist die
Ausgabe voraussichtlich „Stichprobe zu klein"; der Sofort-Wert liegt in der **Maschinerie + im
Beginnen der richtigen Aufzeichnung**. Das ist erwartet, kein Mangel.

## 9. Fehlerpfade & Tests (TDD verpflichtend, AGENTS.md §4)

- **Reihenfolge:** erst Test (Rot) → implementieren → aufräumen. Kein Code ohne fehlschlagenden Test.
- **Reine Funktionen mit Grenzfällen:** Borrow exakt an der Staffel-Schwelle (HTB true/false/None),
  Haltetage 0; Profit-Faktor mit Nenner 0 (nur Gewinne / nur Verluste); Einstieg exakt break-even
  (Short-Ertrag = 0 → nicht korrekt); COVER ohne Folgekurs → übersprungen; Warn-Flag exakt bei
  `hit_rate = 0.55` und `profit_factor = 1.0` (Grenze); leere Stichprobe; `n < MIN_SAMPLE`.
- **Aufschlüsselung:** Eintrag mit mehreren Archetypen zählt in jeden Bucket; unbekannter/leerer
  Archetyp → eigener „(ohne Grund)"-Bucket, kein Crash.
- **Fehlerpfade → überspringen, nie Crash:** fehlender Preis/Grund/Folgekurs; `short_meta = {}`.
- **Persistenz:** `save_analysis` schreibt `short_meta` korrekt; fehlendes Assessment → `{}`.
- **Vor „fertig":** `python -m pytest -q` (bzw. gezielt das Backtester-Paket) laufen lassen,
  Ergebnis nennen.

## 10. Logbuch / Doku

- `docs/open_todos.md` §9: Block #4 als **Short-Backtester-Teil erledigt** vermerken; den
  **Konflikt-Backtester** und die **Kalibrierungs-Rückspeisung** als eigene Folge-Blöcke offen halten.
- `docs/short.md`: Status-Verweis bleibt im Logbuch (Design-Hub nur Design).
- README: keine Änderung (kein konzeptionelles Delta — interne Mess-Mechanik).
