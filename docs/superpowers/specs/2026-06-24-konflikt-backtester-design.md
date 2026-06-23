# Konflikt-Backtester — Design

- **Datum:** 2026-06-24
- **Status:** Entwurf zur Review
- **Spec-Typ:** Fokussierter Block (Spec → Plan → PR, TDD)
- **Geltungsbereich:** rückblickende Bewertung der **Konflikt-Verdikte** (`conflicts.verdict`); kleine Port-Erweiterung; reine Backtest-Mathematik

> Kontext: Die Konflikt-UX-Arbeit (PR #28, `docs/superpowers/specs/2026-06-22-konflikt-ux-design.md`)
> hat **bewusst nur die Daten** gebaut und die Auswertung als „Block #4 / Lernschleife" offen
> gelassen (dort §81/§112: „liest verdict + user_decision → lernt; diese Arbeit liefert nur die
> Daten"). Dieser Spec ist genau dieser Auswertungs-Block — die **Verdikt-Qualität gegen die
> Kursrealität**. Geschwister zum Short-Backtester (PR #39); reuse von dessen Aggregat-Mathematik.

## 0. Ein-Absatz-Zusammenfassung

Der `ConflictAgent` gibt bei einer gehaltenen Position, die der aktuellen Analyse widerspricht,
ein beratendes **Verdikt** aus — `HOLD` (drinbleiben), `EXIT` (raus), `REVERSE` (raus + Gegenposition).
Diese Verdikte werden seit PR #28 in der `conflicts`-Tabelle persistiert (mit `direction`,
`created_at`), aber **nie ausgewertet**. Dieser Block baut einen eigenen **Konflikt-Backtester**:
er benotet je Verdikt rückblickend gegen die Kursentwicklung der gehaltenen Position — war `HOLD`/`EXIT`/`REVERSE`
im Nachhinein richtig? — und weist Trefferquote, Auszahlung und Profit-Faktor **je Verdikt-Typ** aus,
inkl. der „oft recht, trotzdem negativ"-Warnung. Er **misst nur**; das Zurückspeisen in die
Konfidenz des Konflikt-Agenten ist ein separater, geprüfter Folgeschritt.

## 1. Befund (Ausgangslage)

- **Long-Seite ist bereits backgetestet** (`JudgmentBacktesterAgent`: BUY/SELL; plus TopDown/BottomUp).
  Die **Short-Seite** seit PR #39 (eigener Short-Backtester). Die **Konflikt-Verdikte** dagegen
  werden **nicht** ausgewertet — sie sind ein eigenes Prüf-Subjekt (`conflict_resolution`, nicht
  `recommendation`/`short_action`).
- **Daten sind da** (`db/schema.sql` `conflicts`): `ticker`, `direction` (`long`|`short`),
  `verdict` (`HOLD`|`EXIT`|`REVERSE`), `reason`, `status`, `source`, `user_decision`, `created_at`,
  `resolved_at`. **Kein** Preis- und **kein** `market`-Feld — beides wird zur Laufzeit beschafft
  (Preis-Provider über `created_at`; Markt-Default `USA`).
- **`ConflictStorePort`** (`core/ports/conflict_store.py`) hat heute nur Inbox-Methoden
  (`find_open`, `find_latest_resolved`, `save`, `load_open`, `resolve`) — **keine** „alle für den
  Backtest laden"-Methode. Die ergänzen wir (klein, keine DB-Migration).
- **Wiederverwendbar:** `core/utils/short_backtest.py` (`aggregate_by_reason`, `payoff_warning`),
  `core/utils/backtest.py` (`HORIZONS_DAYS`, `forward_return`, `market_adjusted_return`),
  `core/utils/performance_metrics.py` (`apply_costs`), Preis-/Benchmark-Provider aus
  `agents/backtester/bottom_up_backtester_agent.py`, `MemoryPort.save_backtester_report`.

## 2. Scope

**In Scope**
1. **Port-Erweiterung:** `ConflictStorePort.load_for_backtest(days) -> list[ConflictItem]` +
   Implementierung in `SupabaseConflictStore` (`SELECT … WHERE created_at >= cutoff`) + In-Memory-Fake (Tests).
2. **Reine Mathematik:** `core/utils/conflict_backtest.py` — `held_return(direction, adj)` +
   `grade_verdict(verdict, r, cost_per_side)`.
3. **Dünner Agent:** `agents/backtester/conflict_backtester_agent.py` — lädt Konflikte, benotet,
   aggregiert je Verdikt-Typ (reuse `aggregate_by_reason`), speichert Report. **Nur messen.**
4. **Verdrahtung** in `BacktesterChiefAgent` (analog Short-Backtester).
5. Tests (TDD).

**Out of Scope (mit Begründung)**
- **Befolgungsrate** (`verdict` vs. `user_decision`) — anderes, verhaltensbezogenes Maß; nicht Teil
  der Verdikt-Qualität. Eigene Folge-Aufgabe.
- **Kalibrierungs-Rückspeisung** in den Konflikt-Agenten — ändert lebendes Verhalten; eigener
  geprüfter Schritt (Disziplin wie Regime-Backtest ②: erst messen, dann anwenden).
- **Borrow-Kosten** auf gehaltene Shorts — das Verdikt ist im Kern eine Richtungs-/These-Frage;
  über 30–90 Tage ist die Miete klein, und die `conflicts`-Tabelle trägt kein `hard_to_borrow`-Flag.
- **Aufschlüsselung nach Richtung/Quelle** — Konflikte sind selten; mehr Dimensionen → Buckets unter
  MIN_SAMPLE. Später, wenn die Datenlage dichter ist.

## 3. Architektur & Datenfluss

Eigener Backtester, Geschwister zu Judgment-/Short-Backtester. Reine Mathematik getrennt vom I/O.
Die Aggregat-Funktionen werden **wiederverwendet** (DRY statt Duplikat) — sie gruppieren generisch
nach einem Label; hier ist das Label der **Verdikt-Typ** statt des Short-Archetyps.

```
ConflictStorePort.load_for_backtest(days)
        │  ConflictItems mit ticker + direction + verdict + created_at
        ▼
ConflictBacktesterAgent.run()
        │  je Konflikt: Horizont aus Alter(created_at); Einstieg/Forward via Preis-Provider
        ▼
core/utils/conflict_backtest.py  (rein, kein I/O)
        ├─ held_return(direction, adj)     long → adj ; short → −adj
        └─ grade_verdict(verdict, r, cost) → (correct, payoff)
        ▼
core/utils/short_backtest.aggregate_by_reason(graded)   # Label = Verdikt-Typ
        ▼
MemoryPort.save_backtester_report({backtester_type: "conflict", ...})   (je Verdikt-Bucket eine Zeile)
```

**Zwei injizierte Ports:** `ConflictStorePort` (Konflikte laden) + `MemoryPort` (Report speichern),
dazu die Preis-/Benchmark-Callables (default `_default_price_on_horizon`/`_default_benchmark_return`).
Hexagonal: nur Ports + Callables, kein `adapters/`-Import.

## 4. Benotungsregeln (Finanz-Korrektheit, AGENTS.md §3)

Einheitlich: `raw = forward_return(einstieg, forward)`, `adj = market_adjusted_return(raw, benchmark)`
(Benchmark über Markt-Default `USA`). **`r`** = markt-bereinigtes Ergebnis der **gehaltenen** Position:

- `held_return(direction, adj)`: `direction == "long"` → `adj`; `direction == "short"` → `−adj`
  (ein Short gewinnt, wenn der Kurs fällt). **Vorzeichen explizit.**

`grade_verdict(verdict, r, cost_per_side)` → `(correct, payoff)`:

| Verdikt | korrekt ⟺ | Auszahlung |
|---|---|---|
| **HOLD** (drinbleiben) | `r > 0` (These hielt) | `r` |
| **EXIT** (raus) | `r < 0` (Verlust vermieden) | `−r` |
| **REVERSE** (raus + Gegenposition) | `apply_costs(−r, cost) > 0` (Gegenposition zahlt **nach Kosten**) | `apply_costs(−r, cost)` |

- **REVERSE strenger** (entschieden): nur richtig, wenn die Umkehr sich *real* gelohnt hätte —
  nicht nur „raus wäre gut gewesen". EXIT/HOLD bleiben rein vorzeichen-basiert.
- **Kein Borrow** (v1). `r = 0` ist für HOLD und EXIT **nicht** korrekt (strikt `>`/`<`).
- Unbekanntes Verdikt (nicht in {HOLD, EXIT, REVERSE}) → übersprungen (defensiv).

## 5. Datenladen (Port-Erweiterung)

- `ConflictStorePort.load_for_backtest(days: int = 180) -> list[ConflictItem]` (neue abstrakte Methode).
- `SupabaseConflictStore`: `SELECT * FROM conflicts WHERE created_at >= %s ORDER BY created_at DESC`,
  Zeilen → `ConflictItem` (gleiches Mapping wie die bestehenden Lese-Methoden).
- Der In-Memory-/Fake-Store der Tests bekommt dieselbe Methode (gibt die gehaltenen Items zurück).
- **Horizont/Reife:** wie die anderen Backtester — `horizon = max(h ∈ HORIZONS_DAYS, h ≤ alter_tage)`;
  zu junge Konflikte (kein reifer Horizont) → übersprungen. Einstiegspreis = Provider an `created_at`
  (Horizont 0), Forward = Provider an `created_at + horizon`. Fehlender Kurs → übersprungen.
- **Markt:** `conflicts` trägt kein `market` → Default `"USA"` (wie `JudgmentBacktesterAgent`).
  Dokumentierte Vereinfachung; Region-Ableitung/-Feld ist Folge-Aufgabe.

## 6. Kennzahlen je Verdikt-Typ (reuse)

`aggregate_by_reason(graded)` aus `core/utils/short_backtest.py` **wiederverwenden** — der `graded`-Eintrag
ist `{"archetypes": [verdict], "correct": bool, "payoff": float}`; das Gruppierungs-Label (im
Funktions-Vokabular `archetypes`) trägt hier den **Verdikt-Typ**. Pro Bucket (`HOLD`/`EXIT`/`REVERSE`):
Trefferquote + Wilson-CI, mittlere Auszahlung, Profit-Faktor, Max-Drawdown, **Warn-Flag**
(`hit_rate ≥ 0.55` und `profit_factor < 1.0`), `n` — Aggregat erst ab `MIN_SAMPLE`. Buckets im Report
abgelegt (für spätere Kalibrierung), **nicht** zurückgeschrieben.

Report-Persistenz wie beim Short-Backtester (festes 11-Spalten-Schema von `save_backtester_report`):
je Bucket **eine** Zeile mit `backtester_type="conflict"`, `original_recommendation=verdict`,
`return_pct=round(mean_payoff·100, 2)`, `verdict="WARN-payoff"` bei gesetztem Flag, Kennzahlen im `notes`.

> **DRY-Entscheidung (festgelegt):** `aggregate_by_reason`/`payoff_warning` werden **unverändert
> wiederverwendet** — das bereits gemergte `short_backtest`-Modul wird **nicht** angefasst (kein
> Risiko an geliefertem Code). Der `graded`-Eintrag trägt den Verdikt-Typ unter dem generischen
> Schlüssel `archetypes`; ein erläuternder Kommentar im Konflikt-Modul macht das klar. Das Extrahieren
> in ein gemeinsames Aggregat-Modul (Schlüssel neutral benannt) ist **bewusst zurückgestellt** bis ein
> **dritter** Backtester dieselbe Aggregation braucht (Rule of Three) — dann eigener Refactor-PR.

## 7. Verdrahtung in den BacktesterChiefAgent

Wie der Short-Backtester (Review-Nachbesserung PR #39, Commit `35230f3`): den `ConflictBacktesterAgent`
im `BacktesterChiefAgent` mit denselben injizierten Providern instanziieren und im `gather`
mitstarten — sonst läuft er nur in Tests. Der `ConflictStorePort` wird (wie im
`judgment_orchestrator`/`background_runner`) per DI durchgereicht; fehlt der Store → der
Konflikt-Backtester wird übersprungen (defensiv, kein Crash).

## 8. Datenrealität (ehrliche Erwartung)

Konflikte sind **seltene** Ereignisse (nur gehaltene Positionen, die der Analyse widersprechen).
Direkt nach dem Bau ist die Ausgabe voraussichtlich „Stichprobe zu klein"; der Sofort-Wert liegt in
der **Maschinerie** — die Daten laufen seit PR #28 in die `conflicts`-Tabelle und reifen mit der Zeit.

## 9. Fehlerpfade & Tests (TDD verpflichtend, AGENTS.md §4)

- **Reihenfolge:** erst Test (Rot) → implementieren → aufräumen.
- **Reine Funktionen, Grenzfälle:** `held_return` long/short (Vorzeichen-Flip); `grade_verdict`:
  HOLD bei `r` knapp >0/<0/=0, EXIT analog, REVERSE **exakt an der Kosten-Schwelle**
  (`apply_costs(−r)=0` → nicht korrekt), unbekanntes Verdikt → übersprungen.
- **Agent (Fake-Store + injizierte Preis-Callables, kein Netz):** short-Konflikt mit fallendem Kurs
  → HOLD falsch / EXIT richtig; fehlender Forward-Preis → übersprungen, kein Crash; unreifer Konflikt
  (zu jung) → übersprungen; leere Ladung → keine Reports; `n < MIN_SAMPLE` → kein Aggregat.
- **Port-Erweiterung:** `load_for_backtest` im Fake liefert die Items; (Supabase-SELECT durch Lesen
  der Query verifiziert, kein Live-DB-Test).
- **Verdrahtung:** `BacktesterChiefAgent` startet den Konflikt-Backtester; fehlender Store → übersprungen.
- **Vor „fertig":** `python -m pytest -q` (bzw. das Backtester-Paket), Ergebnis nennen.

## 10. Logbuch / Doku

- `docs/open_todos.md` §9: den Eintrag „Konflikt-Backtester (eigener Block)" abhaken (nach Merge, PR-Protokoll);
  **Befolgungsrate** (`verdict` vs. `user_decision`) als eigene Folge-Aufgabe ergänzen.
- README: keine Änderung (interne Mess-Mechanik).
