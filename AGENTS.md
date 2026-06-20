# AGENTS.md — Arbeitsanweisung für AAIA

> Diese Datei ist die **einzige Quelle der Wahrheit** für KI-Agenten in diesem Projekt.
> `CLAUDE.md` verweist nur hierher — alle Regeln stehen ausschließlich hier.

> AAIA (Adaptive AI Investment Agent) — vollautomatisches, KI-gestütztes Investment-Analyse-System.
> Architektur: **EDA + Hexagonal**, hierarchisches **Multi-Agenten-System** (40+ Agenten).
> Oberste Prioritäten in diesem Projekt: **(1) Code-Qualität** und **(2) finanzielle/fachliche Korrektheit**.
> Wenn diese beiden im Konflikt mit Geschwindigkeit oder Bequemlichkeit stehen, gewinnen immer Qualität und Korrektheit.

---

## 0. Sprache & Kommunikation

- Antworte und kommentiere auf **Deutsch** (Code-Kommentare sind im Projekt durchgehend deutsch).
- Erkläre **direkt das Problem + den Lösungsansatz** — frage nicht zuerst, ob du erklären sollst.
- Der Nutzer ist mit Tech-Stack-Begriffen nicht immer vertraut: **erkläre Fachbegriffe kurz**, wenn sie zum ersten Mal auftauchen.
- Nach jedem umgesetzten Plan/größeren Change: **kurze, einfach erklärte Zusammenfassung** der Änderungen.

---

## 1. Architektur — diese Regeln sind nicht verhandelbar

Das System hat drei Agenten-Schichten:

```
Orchestratoren  →  ChiefAgents  →  Sub-Agents
```

- **`orchestrators/`** — oberste Koordination (Top-Down, Bottom-Up, Judgment). Delegieren nur, rechnen nicht selbst.
- **`agents/.../*_chief_agent.py`** — Domain-Koordinatoren. Starten ihre Sub-Agents **parallel**, fangen Fehler ab, liefern **immer** ein vollständiges Ergebnis.
- **`agents/.../<sub>_agent.py`** — die eigentliche Fachlogik (ein Indikator/eine Kennzahl pro Agent).

### Hexagonal (Ports & Adapters)

- **`core/domain/`** — reine Domänen-Modelle, Events, Enums (`Signal`, `MarketRegime`, …). **Keine** I/O, keine externen Libs.
- **`core/ports/`** — abstrakte Schnittstellen (`ABC`). Agenten hängen **nur** von Ports ab, **nie** von konkreten Adaptern.
- **`adapters/`** — konkrete Implementierungen (FRED, ECB, SNB, Yahoo, Finnhub, Redis, Supabase, Claude). Nur hier passiert echtes I/O.
- **`core/utils/`** — geteilte, reine Rechen-Helfer (Bewertungsmathematik, Scoring, Statistik, Bond-Math). Keine Seiteneffekte.

**Verboten:**
- Ein Agent importiert direkt aus `adapters/` → stattdessen Port aus `core/ports/` als Konstruktor-Argument injizieren.
- I/O oder API-Calls in `core/` → gehört in `adapters/`.
- Geschäftslogik in einem Adapter → gehört in den Agenten oder `core/utils/`.

---

## 2. Verbindliche Code-Patterns (so sieht der bestehende Code aus)

Bevor du neuen Code schreibst, **lies einen vergleichbaren bestehenden Agenten** und spiegele dessen Stil. Konkret:

- **Type Hints überall**, moderne Syntax: `float | None`, `dict[str, float]`, `list[dict]`.
- **Async-Parallelität** über `asyncio.gather(..., return_exceptions=True)`; blockierendes I/O in `asyncio.to_thread(...)` wickeln.
- **Defensive Aggregation:** Ergebnisse mit einem `_safe(...)`-Helfer entpacken; bei Exception auf einen **neutralen Default** zurückfallen (`Signal.NEUTRAL`, `Agent.default()`). Eine ausgefallene Datenquelle darf **nie** die ganze Analyse abstürzen lassen.
- **Klassen-Fallbacks:** Jeder Agent, der in einem Chief aggregiert wird, stellt eine `default()`-Methode (oder ein Modul-`_DEFAULT`) bereit.
- **Reine Signal-Funktionen:** Die Schwellen-/Signal-Logik (z. B. `_signal(...)`) als pure Funktion halten — leicht testbar, keine I/O.
- **Lückenlose Schwellenbänder:** Bei numerischen Klassifizierungen (Inflation, Bewertung, Spreads) sicherstellen, dass **jeder** Wert in genau eine Klasse fällt — keine blinden Lücken zwischen `<` und `<=`.

---

## 3. Finanzielle Korrektheit — die zweite oberste Priorität

Fehler in der Finanzlogik sind **stiller als** Code-Fehler: der Test wird grün, die Schlussfolgerung ist trotzdem falsch. Deshalb:

- **Erkläre die fachliche Begründung** jeder Schwelle/Formel im Code-Kommentar **und** in deiner Antwort (z. B. „Realzins > 2 % drückt Bewertungen → BEARISH"). Magische Zahlen ohne Begründung sind nicht erlaubt.
- **Einheiten und Vorzeichen explizit** machen: Prozent vs. Dezimal (3.0 vs. 0.03), Basispunkte, nominal vs. real, YoY vs. QoQ. Bei Spreads die Richtung benennen (`10y-2y`).
- **Region/Asset-Klasse korrekt behandeln:** USA/Eurozone/CH haben unterschiedliche Schwellen (siehe `inflation_agent`). Edelmetall ≠ Aktie ≠ Bond — den richtigen Analyse-Pfad nutzen.
- **Etablierte Konzepte respektieren:** Buffett-Indikator, Moat (Buffett), Altman-Z, EV/EBITDA, DCF, Shiller-CAPE, COT, Saisonalität — wenn du eine bekannte Methode implementierst, halte dich an ihre Standard-Definition und verlinke sie im Kommentar.
- **Bei fachlicher Unsicherheit: nachfragen statt raten.** Eine plausibel klingende, aber falsche Finanzregel ist schlimmer als eine offene Frage.
- **Datenrealität bedenken:** Daten kommen oft verzögert, lückenhaft oder als `None`. Plausibilitäts-/Sanity-Checks (z. B. Caps wie der 0.70-Deckel) einbauen, statt blind zu rechnen.

---

## 4. Tests (TDD verpflichtend)

- Test-Runner: **pytest**. Tests liegen unter `tests/` und spiegeln die Paketstruktur von `agents/`.
- **TDD ist Pflicht, keine Ausnahme:** Neue Logik **immer erst als Test** (Rot), dann implementieren bis grün, dann aufräumen. Kein Implementierungs-Code ohne vorher geschriebenen, fehlschlagenden Test. Besonders für Signal-/Bewertungs-Schwellen: Grenzfälle explizit testen (genau auf der Schwelle, knapp darüber/darunter, `None`, negative Werte).
- **Fehlerpfade testen:** Datenquelle wirft Exception → Agent liefert trotzdem den Default.
- **Vor jedem „fertig"** die Tests laufen lassen und das Ergebnis nennen. Keine Erfolgsmeldung ohne grünen Lauf.

```bash
python -m pytest -q                 # alle Tests
python -m pytest tests/agents/market_cockpit/macro/ -q   # gezielt ein Paket
```

---

## 5. Arbeits- & Git-Workflow

### PR-First — gilt für JEDE Änderung (Task, Bug, neues Konzept — groß oder klein)

Jede Änderung, die zu einem Commit führt, läuft über einen **Pull Request**. **Kein direkter Merge nach `master`.**

1. **Feature-Branch** anlegen — nie direkt auf `master` arbeiten.
2. Umsetzen mit **TDD** (siehe Abschnitt 4), committen. Commit-Messages auf Deutsch im bestehenden Stil: `feat(short): …`, `fix(short): …`, `chore(short): …`.
3. **Branch pushen + PR öffnen.** Die PR-Beschreibung erklärt auf Deutsch: **was** geändert wurde, **warum** und **wie** gelöst. (Das Pushen eines Feature-Branches für einen PR ist der Standard-Flow und ausdrücklich erlaubt.)
4. **Zweiter Blick durch den User:** Der User verifiziert und überprüft den PR (so wie bei PR #4).
5. **Kommentar am PR** hält fest, ob von Anfang an alles i.O. war oder was im Review noch geändert wurde — inkl. Begründung und Lösungsweg.
6. **Erst nach ausdrücklichem OK des Users mergen.**

- **NIE direkt nach `master` pushen. NIE mergen ohne den zweiten Blick + OK des Users.**
  - **Einzige erlaubte Ausnahme — eng begrenzt:** Ein **reiner Logbuch-/PR-Protokoll-Vermerk in `docs/open_todos.md`** (die Merge-/Ablehnungs-Entscheidung gemäß PR-Protokoll: Eintrag abhaken bzw. `PR #N am YYYY-MM-DD …`) darf **direkt auf `master`** committet werden — er dokumentiert nur eine bereits vom User getroffene Entscheidung. **AUSSCHLIESSLICH dafür.** **Niemals** für Code, Tests, Refactorings, neue Features, Konfiguration oder andere Dateien/Docs — alles andere läuft weiterhin zwingend über einen PR. Im Zweifel: PR.
- Hooks/Signierung **nicht** umgehen (kein `--no-verify`).

### Logbuch — `docs/open_todos.md` ist die einzige laufende Quelle

`docs/open_todos.md` wird als **Logbuch** geführt und ist ab jetzt das **einzige** laufend gepflegte Dokument für Tasks/Bugs/Konzepte. Pro Eintrag:

- erledigten Eintrag **abhaken** + kurzen **Lösung:**-Hinweis (was, warum, wie),
- neue Folge-Aufgaben mit Lösungsansatz ergänzen.

**PR-Protokoll (Pflicht):** Sobald der User über einen PR entschieden hat, wird die Entscheidung im Logbuch protokolliert — immer mit **Datum + PR-Nummer**:

- **Akzeptiert / gemergt:** Eintrag abhaken + Vermerk `PR #N am YYYY-MM-DD gemergt`. Falls im Review noch etwas geändert wurde, kurz festhalten **was** und **warum**.
- **Abgelehnt / Nacharbeit nötig:** Eintrag bleibt **offen** + Vermerk `PR #N am YYYY-MM-DD abgelehnt — Grund: …` inkl. **nächstem Schritt**.

So bildet das Logbuch lückenlos ab: Aufgabe → Lösung → PR-Entscheidung.

**README** nur aktualisieren, wenn sich **konzeptionell oder inhaltlich** etwas ändert (z. B. ein neues/anderes Konzept, geändertes Verhalten oder geänderte Nutzung) — **nicht** bei reinen Code-/Refactoring-Änderungen ohne inhaltliche Auswirkung.

> Die `docs/code_review_*.md` / `docs/finanz_konzept_review_*.md` sind **datierte Einmal-Audits** (Gesamt-Reviews) — **kein** Logbuch. Dort nur bei einem neuen Vollaudit schreiben.

### Größere Features

- Spezifikation → `docs/superpowers/specs/`, Plan → `docs/superpowers/plans/` (Muster: `YYYY-MM-DD-thema.md`).

---

## 6. Sicherheit

- **Secrets** (`FRED_API_KEY`, `FMP_API_KEY`, …) gehören in `.env` (nicht committet). Niemals Keys in Code, Logs oder Antworten ausgeben.
- Konfiguration über `config/settings.py` lesen, nicht `os.environ` quer im Code verteilen.

---

## 7. Schneller Orientierungsindex

| Ort | Inhalt |
|---|---|
| `orchestrators/` | Top-Level-Koordination (Top-Down / Bottom-Up / Judgment) |
| `agents/market_cockpit/` | Makro, Rohstoffe, Sentiment, Zinskurve, Sektoren |
| `agents/stock_deep_dive/` | Equity, Bond, Index, Commodity, Precious Metals |
| `agents/judgment/` | Zusammenführung Top-Down + Bottom-Up zum Urteil |
| `core/domain/` | Modelle, Events, Enums (reine Domäne) |
| `core/ports/` | abstrakte Schnittstellen (Hexagonal) |
| `core/utils/` | geteilte Rechen-Helfer (pure functions) |
| `adapters/` | externe Daten/Dienste (FRED, ECB, SNB, Yahoo, Claude, Redis, Supabase) |
| `config/settings.py` | zentrale Konfiguration |
| `docs/` | Spezifikationen, Pläne, Code-Reviews, offene TODOs |
