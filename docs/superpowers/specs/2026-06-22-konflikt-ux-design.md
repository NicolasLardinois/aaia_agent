# Konflikt-UX (Inbox + Entscheidungs-Protokoll) — Design

- **Datum:** 2026-06-22
- **Status:** Entwurf zur Review
- **Teil von:** Shorts-Programm — „Equity-Short fertig" (Baustein 4/4). Bringt den bereits gebauten **Konflikt-Agenten** (§18) zum Nutzer: eine persistente **Konflikt-Inbox**. Brainstorm-Kontext: `docs/short.md §19`.

## 1. Kontext & Ziel

Der Konflikt-Agent (§18) liefert bei einer gehaltenen Position, die der aktuellen Analyse widerspricht, ein beratendes **Verdikt** (HOLD/EXIT/REVERSE) — heute nur flüchtig im `judge`-Output. **Ziel:** Konflikte als **persistente, entscheidbare Posten** führen (offen → erledigt), aus **zwei Quellen** gespeist (on-demand + proaktiv), mit **CLI** zum Listen/Entscheiden. Das Tool **handelt nie selbst** — es zeigt, fragt, **protokolliert nur** (harte Leitplanke, §19.1).

**Zwei Daten getrennt erfassen** (für die Block-#4-Lernschleife): **System-Rat** (`verdict`) und **tatsächliche Nutzer-Entscheidung** (`user_decision`).

## 2. Entscheidungen (§19 + Brainstorm 2026-06-22)

1. **Umfang:** voller Block — on-demand **und** proaktiv.
2. **Storage:** **Supabase-Tabelle `conflicts`** über einen `ConflictStorePort` (hexagonal, konsistent mit `analysis_memory`; abfragbar für Block #4). *(JSON wäre die simplere Alternative — verworfen wegen Lernschleife/Abfragbarkeit.)*
3. **Reopen-Regel:** ein erledigter Konflikt (Ticker+Richtung) öffnet bei Wiederauftreten **nur** wieder, wenn das Verdikt **schärfer** ist (`HOLD < EXIT < REVERSE`). Gleich/milder → bleibt erledigt.
4. **Proaktiv-Kosten:** billige **deterministische** Erkennung; der **LLM**-ConflictAgent läuft **nur bei echtem Konflikt** (nicht pro Position).

## 3. Komponenten

### 3.1 `ConflictItem` (`core/domain/models.py`)
```python
@dataclass
class ConflictItem:
    ticker: str
    direction: str               # gehaltene Position: "long" | "short"
    verdict: str                 # "HOLD" | "EXIT" | "REVERSE"
    reason: str
    status: str = "open"         # "open" | "resolved"
    source: str = "on_demand"    # "on_demand" | "proactive"
    user_decision: Optional[str] = None   # "held" | "closed" | None
    id: Optional[int] = None
    created_at: Optional[str] = None
    resolved_at: Optional[str] = None
```
Verdikt-Severity-Helfer (pure, Modul): `_VERDICT_SEVERITY = {"HOLD": 0, "EXIT": 1, "REVERSE": 2}`.

### 3.2 `ConflictStorePort` (`core/ports/conflict_store.py`, ABC) + `SupabaseConflictStore` (`adapters/...`)
```text
class ConflictStorePort(ABC):
    def find_open(ticker, direction) -> ConflictItem | None
    def find_latest_resolved(ticker, direction) -> ConflictItem | None
    def save(item: ConflictItem) -> None
    def load_open() -> list[ConflictItem]
    def resolve(conflict_id, user_decision) -> None     # status=resolved, user_decision, resolved_at=now
```
- `SupabaseConflictStore`: Tabelle `conflicts` (Spalten = Felder), Muster wie `SupabaseMemory` (psycopg). `db/schema.sql` + **Migration** ergänzen.
- **Defensiv:** DB-Fehler in `save`/`load`/`resolve` werden vom Aufrufer (Orchestrator/Runner/CLI) mit `try/except` umhüllt; die Inbox ist Beiwerk, kein Blocker.

### 3.3 `record_conflict(store, ticker, direction, verdict, reason, source)` (`core/domain/conflict_inbox.py`, pure Logik)
Lebenszyklus/Dedupe/Reopen — **reine Funktion gegen den Port** (leicht testbar):
```text
offener (ticker,direction) existiert        → return (skip; Dedupe)
sonst letzter erledigter (ticker,direction):
    neues Verdikt schärfer als dessen Verdikt → store.save(neuer offener)   # reopen
    sonst                                     → return (skip)
kein erledigter                              → store.save(neuer offener)
```

### 3.4 On-demand (`orchestrators/judgment_orchestrator.py`)
Nach dem Konflikt-Block (es gibt `result.conflict` + `result.conflict_resolution`): wenn `result.conflict` und der Store vorhanden:
`record_conflict(store, ticker, current_position.value, result.conflict_resolution.verdict, result.conflict_resolution.reasoning, source="on_demand")` — in `try/except` (defensiv). Store wird per DI in den Orchestrator gegeben (`conflict_store=None`).

### 3.5 Proaktiv (`background_runner.py` + Probe)
- **`probe_conflict(...)`** — eine **deterministische** Konflikt-Erkennung **ohne** Prosa-LLM: nutzt die vorhandenen reinen Funktionen (`_bottom_up_signals`/`_derive_alignment`, `derive_short_assessment`, `compute_confidence`, `detect_conflict`) auf **gecachten** `bottom_up` + `cockpit` + (deterministischen) Anomalien je gehaltener Depot-Position. Liefert `(conflict: bool, reason, dominant_signal, …)`.
- **`background_runner`:** je gehaltener Position aus dem Depot (`PortfolioPort`) → `probe_conflict`. **Nur bei `conflict`** den vorhandenen **`ConflictAgent`** (LLM) fürs Verdikt aufrufen, dann `record_conflict(..., source="proactive")` (Dedupe/Reopen greift). Positionen ohne gecachte Analyse → übersprungen (geloggt).
- (Der exakte Reuse der deterministischen Schritte — eigene Probe-Funktion vs. dünner Helfer im Orchestrator — wird im Plan gepinnt; **kein** Prosa-LLM in der Probe.)

### 3.6 CLI (`app/main.py`)
- **`conflicts`** — offene Konflikte listen: `store.load_open()` → je Zeile `#id  TICKER (richtung)  VERDIKT — reason`.
- **`resolve <id> <held|closed>`** — `store.resolve(id, decision)`; bestätigt „protokolliert (kein Trade ausgeführt)". Validierung: `held|closed`, sonst Hinweis.
- Doku-String (Modi) + Dispatch (`elif args[0] == "conflicts"/"resolve"`) ergänzen.

## 4. Datenfluss

```
on-demand:  judge → JudgmentOrchestrator (result.conflict + verdict) → record_conflict(source=on_demand) → conflicts-Tabelle
proaktiv:   background_runner → je Depot-Position: probe_conflict (deterministisch) → bei Konflikt: ConflictAgent (Verdikt) → record_conflict(source=proactive)
CLI:        conflicts (load_open) · resolve <id> <held|closed> (status=resolved + user_decision)
Block #4 (später): liest verdict + user_decision → lernt (war der Rat gut? folgte der Nutzer?)
```

## 5. Fehlerbehandlung
- Store-/DB-Fehler an **jeder** Schreib-/Lesestelle → `try/except`, Analyse/Runner/CLI laufen weiter (Inbox ist nicht kritisch).
- `probe_conflict` ohne gecachte Daten → übersprungen (kein Crash).
- Ungültige `resolve`-Eingabe → Nutzerhinweis, kein Schreibvorgang.

## 6. Phasen (TDD, je eigener Abschnitt)
- **P1 — Datenschicht:** `ConflictItem`, `ConflictStorePort`, `SupabaseConflictStore` (+ `schema.sql`/Migration), `record_conflict` (Dedupe/Reopen). Voll testbar gegen einen Fake-Store.
- **P2 — On-demand + CLI:** Orchestrator-Aufnahme + `conflicts`/`resolve`. Sofort nutzbar.
- **P3 — Proaktiv:** `probe_conflict` (deterministisch) + `background_runner`-Scan (LLM-Verdikt nur bei Konflikt).

## 7. Tests (TDD)
- **`record_conflict`** gegen Fake-Store: offener existiert → skip; kein vorheriger → save; erledigter + schärferes Verdikt → reopen (save); erledigter + gleich/milder → skip. Severity-Ordnung (HOLD<EXIT<REVERSE), Grenzfälle.
- **`SupabaseConflictStore`**: gemockter Cursor — `save`/`load_open`/`resolve`/`find_*` setzen die richtigen SQL-Parameter (analog `test_supabase_memory`).
- **On-demand:** Orchestrator ruft `record_conflict` bei `result.conflict` (gemockter Store), nicht ohne Konflikt; Store-Exception → kein Crash.
- **Proaktiv:** `probe_conflict` erkennt Konflikt deterministisch (kein LLM-Call); `background_runner` ruft ConflictAgent nur bei Konflikt (gemockt).
- **CLI:** `conflicts` listet; `resolve` schreibt `user_decision`/Status; ungültige Eingabe → Hinweis. LLM/DB in Tests gemockt.
- **Regression:** Gesamtsuite grün.

## 8. Akzeptanzkriterien
1. `ConflictItem` + `ConflictStorePort` + `SupabaseConflictStore` (Tabelle `conflicts`, `schema.sql`, Migration).
2. `record_conflict` mit Dedupe (offen → skip) + Reopen **nur bei schärferem Verdikt**.
3. On-demand: `judge` einer gehaltenen Position mit Konflikt legt einen offenen Posten an (defensiv).
4. Proaktiv: `background_runner` scannt das Depot, **deterministische** Erkennung, **LLM nur bei echtem Konflikt**, legt Posten an (Dedupe).
5. CLI: `conflicts` listet offene; `resolve <id> <held|closed>` protokolliert die Nutzer-Entscheidung; **kein Trade** wird ausgeführt.
6. `verdict` (System) + `user_decision` (Nutzer) getrennt persistiert (für Block #4).
7. Alle Fehlerpfade defensiv (Inbox nie kritisch); Gesamtsuite grün; LLM/DB in Tests gemockt.

## 9. Bewusst draußen
- **Block-#4-Lernschleife** (Auswertung verdict vs. user_decision) — eigener Block; diese Arbeit liefert nur die **Daten**.
- **Frontend-Widget** — `short.md §19.5` (XAI + Schweregrad); reine Anzeige später, kein Backend-Aufwand offen.
- **Automatische Positionsänderung** — **niemals** (harte Leitplanke).
