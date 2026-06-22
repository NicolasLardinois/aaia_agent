# ShortThesisAgent (LLM-Short-These + XAI) — Design

- **Datum:** 2026-06-22
- **Status:** Entwurf zur Review
- **Teil von:** Shorts-Programm — „Equity-Short fertig" (Baustein 3/4). Gibt der Short-Seite **lesbare Prosa** (These + XAI), symmetrisch zur Long-Seite.

## 1. Kontext & Ziel

Die bestehenden LLM-Texte (`DeepDiveResult.judgment`, `xai_explanation`) erklären die **Long-Empfehlung** — der `short_assessment` wird erst danach berechnet und fließt **nicht** in sie ein. Die Short-Seite hat heute nur **strukturierte `thesis_flags`** (z. B. „Altman-Z 0.9 (Konkurszone)"), aber **keine Fließtext-Begründung**.

**Ziel:** Ein neuer LLM-Agent, der aus dem deterministischen `ShortAssessment` zwei Texte erzeugt — **`short_thesis`** (kurz, angezeigt) und **`short_xai`** (ausführlich, gespeichert/Frontend) — exakt parallel zur Long-Seite (`judgment` + `xai_explanation`).

## 2. Entscheidungen (Brainstorm 2026-06-22)

1. **Linsen-Modell:** Beide Linsen laufen **immer** (ein Ticker → Long- **und** Short-Urteil); der Nutzer vergleicht und wählt die bessere Positionierung. **Nicht** vorab „long oder short" festlegen — *welche* Seite trägt, ist das Ergebnis der Analyse.
2. **Output-Form:** **zwei** Texte (These + XAI), wie die Long-Seite (volle Parität, Frontend-ready).
3. **Wann:** **immer** erzeugen (kein Gating) — die LLM-Kosten sind bei Einzeltitel-Analyse vernachlässigbar; auch der „kein Short-Setup"-Fall ist informativ (erklärt, *warum* kein Short). Eine künftige „Kurzfassung + aufklappen"-Anzeige ist eine reine **Frontend**-Entscheidung und kommt gratis, weil der volle Text vorliegt.
4. **Architektur:** **separater Agent** (Muster `ConflictAgent`), vom `JudgmentOrchestrator` aufgerufen — hält den schon großen `judgment_agent` schlank.

## 3. Komponenten

### 3.1 `ShortThesisAgent` (`agents/short_thesis/short_thesis_agent.py`)
```text
class ShortThesisAgent:
    def __init__(self, llm: LLMProvider, bus: EventBus)
    async def run(ticker, short_assessment, asset_class) -> tuple[str, str]   # (these, xai)
```
- **Strukturierter Block** aus dem `ShortAssessment`: `short_action`, `confidence`, `archetypes`, `thesis_flags`, `regime_effect`, `squeeze_risk`, `hard_to_borrow`, `suggested_size_pct`/`stop_pct` — als Prompt-Kontext (das LLM **erklärt** die deterministische Engine-Ausgabe, erfindet nichts dazu).
- **Call 1 — `short_thesis`** (`SHORT_SYSTEM_PROMPT`, „erfahrener Leerverkaufs-Analyst"): kurze, klare These aus den Feldern. Via `asyncio.to_thread(self.llm.complete, prompt, SHORT_SYSTEM_PROMPT)`.
- **Call 2 — `short_xai`** (`SHORT_XAI_SYSTEM_PROMPT`): bekommt zusätzlich die These + Aktion + Konfidenz → ausführliche „warum dieser Short / warum nicht". Via `asyncio.to_thread`.
- **Defensiv:** der ganze `run` ist robust — bei LLM-Fehler / leerem `short_assessment` → `("", "")` (Analyse läuft weiter). Publiziert `ShortThesisReady` (EDA-Muster).
- **Symmetrie zur Long-Seite:** Call 1 = These (analog `judgment`), Call 2 = XAI (analog `xai_explanation`); Call 2 nutzt die These als Input (wie long).

### 3.2 Event (`core/domain/events.py`)
`ShortThesisReady` analog `ConflictResolutionReady` (`source`, `payload`).

### 3.3 Modell (`core/domain/models.py`)
`DeepDiveResult` um zwei Felder erweitern (trailing, Default `""`):
```python
    short_thesis: str = ""
    short_xai: str = ""
```

### 3.4 Verdrahtung (`orchestrators/judgment_orchestrator.py`)
- `__init__`: `self.short_thesis_agent = ShortThesisAgent(llm, bus)`.
- `run()`: **nach** dem Konflikt-Block, **vor** `save_analysis`, immer (null-sicher):
```python
        if result.short_assessment is not None:
            try:
                result.short_thesis, result.short_xai = await self.short_thesis_agent.run(
                    bottom_up.ticker, result.short_assessment, result.asset_class)
            except Exception:
                result.short_thesis, result.short_xai = "", ""
```
*(Kein Thesen-Gating — `short_assessment is not None` ist nur Null-Schutz für den Default-/Fehlerpfad. Bei echter Analyse ist es immer gesetzt → Agent läuft immer.)*

### 3.5 Anzeige (`app/main.py`)
Nach „URTEIL" eine `SHORT-THESE`-Sektion drucken, wenn `result.short_thesis` nicht leer ist (analog zur `URTEIL`-Anzeige des `judgment`). `short_xai` wird **nicht** im CLI gedruckt (gespeichert/Frontend — symmetrisch zur Long-XAI).

## 4. Datenfluss

```
judgment_chief → DeepDiveResult (+ short_assessment, short_action)
      │
JudgmentOrchestrator.run:
      ├─ (bei Konflikt) ConflictAgent → conflict_resolution
      ├─ ShortThesisAgent.run(ticker, short_assessment, asset_class)
      │        ├─ Call 1 → short_thesis   (analog judgment)
      │        └─ Call 2 → short_xai      (analog xai_explanation, nutzt These)
      │     → result.short_thesis / result.short_xai
      └─ memory.save_analysis(result)
app/main.py: druckt URTEIL (Long) + SHORT-THESE (Short)
```

## 5. Fehlerbehandlung

- LLM-Fehler (Call 1 oder 2) → `("", "")`; der Orchestrator umhüllt zusätzlich mit `try/except`. Die Analyse läuft immer vollständig durch.
- `short_assessment is None` (Default-/Fehlerpfad) → Agent nicht aufgerufen, Felder bleiben `""`.
- LLM in allen Tests **gemockt** (kein echter API-Call).

## 6. Tests (TDD)

- **Agent:** baut den Prompt aus den `ShortAssessment`-Feldern (gemocktes `llm.complete` gibt z. B. `"THESE…"` / `"XAI…"`); `run` liefert das `(these, xai)`-Tupel; zwei `complete`-Aufrufe (These dann XAI, XAI-Prompt enthält die These). LLM wirft → `("", "")`. Leeres/NONE-Assessment → robust.
- **Orchestrator:** `ShortThesisAgent` wird (mit gemocktem Agenten) aufgerufen und füllt `result.short_thesis`/`short_xai`; `short_assessment is None` → nicht aufgerufen; Agent-Exception → Felder `""` (kein Crash).
- **Modell:** `DeepDiveResult` hat `short_thesis`/`short_xai` mit Default `""` (bestehende Konstruktionen brechen nicht).
- **Anzeige:** `short_thesis` wird gedruckt, wenn nicht leer (kann als Formatter-Test oder manuell geprüft werden).
- **Regression:** Gesamtsuite grün (`python -m pytest -q`).

## 7. Akzeptanzkriterien

1. `ShortThesisAgent.run(...)` liefert `(short_thesis, short_xai)` aus dem `ShortAssessment` (zwei LLM-Calls, XAI nutzt die These); defensiv `("", "")` bei Fehler.
2. `DeepDiveResult.short_thesis` + `short_xai` (Default `""`).
3. Orchestrator ruft den Agenten **immer** (null-sicher) und füllt die Felder; Fehler → `""` ohne Crash.
4. CLI zeigt `SHORT-THESE` (wenn vorhanden); `short_xai` bleibt gespeichert/ungezeigt (parallel zur Long-XAI).
5. Beide Linsen liefern weiterhin **immer** ihr Urteil (Long- + Short-Output zum Vergleich) — Linsen-Modell unverändert.
6. Gesamtsuite grün; LLM in Tests gemockt.

## 8. Bewusst draußen

- **Supabase-Persistenz** der zwei Texte (reproduzierbar aus dem strukturierten `ShortAssessment`) — Result-Feld + Anzeige genügen.
- **Long-Seite umbauen** (Gating/Zusammenlegen) — die Long-Seite bleibt wie sie ist (immer Prosa); Symmetrie ist über „beide immer voll" gegeben.
- **Frontend „Kurzfassung + aufklappen"** — reine Anzeige-Entscheidung später; der volle Text liegt dann vor.
