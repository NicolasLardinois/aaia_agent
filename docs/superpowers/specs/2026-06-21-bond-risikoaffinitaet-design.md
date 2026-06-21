# Bond-Risikoaffinität & Credit-Band-Aggregation — Design-Spec

> Stand: 2026-06-21 · Status: Entwurf zur Abnahme
> Kontext: Aus der Abarbeitung von **Bug #47** (Deep-Dive-Chiefs liefern kein/uneinheitliches Gesamtsignal).
> Das `bond_chief`-**Credit-Downgrade-Veto** ist zu starr — es macht jede Anleihe mit erhöhtem
> Ausfallrisiko automatisch BEARISH, unabhängig davon, ob die Rendite das Risiko vergütet.

---

## 1. Ziel

Das Bond-Gesamtsignal soll das **Risiko-Rendite-Abwägen** abbilden statt eines binären Vetos, und die
**Risikoaffinität des Anlegers** explizit einbeziehen:

- Das Ausfallrisiko einer Anleihe wird über ihr **S&P-Rating** in drei **Bänder** (sicher/mittel/riskant) eingeordnet.
- Die **Risikoaffinität** (konservativ/neutral/risikofreudig) bestimmt, **wie hart** das Risiko ins Gesamtsignal eingeht.
- Alle vier Bond-Sub-Signale (`metrics`, `duration`, `spread`, `credit`) werden **gleich gewichtet** aggregiert — das Credit-Veto entfällt.
- Die gewählte Risikoaffinität ist eine **Pflicht-Eingabe** pro Anleihe-Analyse, wird **pro Position** persistiert und im **Portfolio-Manager** angezeigt; sie kann **nachträglich** geändert werden (mit sofortiger Neubewertung aus gespeicherten Bausteinen).

## 2. Nicht-Ziele / Out of Scope

- **Umbenennung der `Signal`-Begriffe** (BULLISH/BEARISH/NEUTRAL). Sie bleiben eine **Bewertung**; die Handlung (BUY/HOLD/SELL/NONE) leitet weiterhin `derive_recommendation()` aus Signal + Position + Konfidenz ab. (Diskussion ergab: Umbenennung wäre ein 40-Dateien-Eingriff ohne Mehrwert, da die Handlungsebene die Bedeutung bereits auflöst.)
- **PM-Komplett-Neuanalyse** (1-Klick manuell + ~30-Tage-Hintergrundlauf für alle Portfolio-Positionen): eigenes, querschnittliches Feature (alle Anlageklassen + Scheduling) → **separater Spec**, hier nur als Folge-Aufgabe im Logbuch vermerkt. Dieser Spec legt aber das gemeinsame Fundament (gespeicherte Bausteine + persistierte Affinität).
- **Anbindung echter Bond-Rohdaten/Ratings** (`get_bond_data()` ist heute Stub, §2 Logbuch). Die Logik wird **fertig + getestet** gebaut und läuft „dormant", bis der Bond-Adapter steht.
- Andere Anlageklassen: Risikoaffinität gilt zunächst **nur für Anleihen**.

## 3. Fachliches Modell

### 3.1 S&P-Rating → Credit-Band

S&P-Langfristrating (gut → schlecht):
`AAA AA+ AA AA− A+ A A− BBB+ BBB BBB− | BB+ BB BB− B+ B B− | CCC+ CCC CCC− CC C D`

| Band | Ratings | Marktbegriff |
|---|---|---|
| `SICHER` | AAA … BBB− | Investment Grade |
| `MITTEL` | BB+ … B− | High-Yield |
| `RISKANT` | CCC+ … D | Distressed / nahe Ausfall |

Kanten an der Marktkonvention: Investment Grade endet bei **BBB−**, Distressed beginnt bei **CCC+**.
Unbekanntes/fehlendes Rating → **kein Band** (`None`) → Credit-Dimension `UNAVAILABLE` (siehe 3.4).

### 3.2 Credit-Beitrag = Band × Risikoaffinität

Eine **reine Funktion** bildet (Band, Affinität) auf einen numerischen Beitrag ab. Negativ = Risiko zieht das
Signal nach unten; selbst `risikofreudig` bewertet Ausfallrisiko **nie positiv** — die Rendite belohnt separat über `metrics`.

| Band | konservativ | neutral | risikofreudig |
|---|---|---|---|
| `SICHER` | 0,0 | 0,0 | 0,0 |
| `MITTEL` | −1,0 | −0,5 | 0,0 |
| `RISKANT` | −1,5 | −1,0 | −0,5 |

### 3.3 Aggregation (gleich gewichtet, kein Veto)

Vier Komponenten, je Gewicht 0,25:

- `metrics`, `duration`, `spread`: Signal → Score `BULLISH=+1 / NEUTRAL=0 / BEARISH=−1`.
- `credit`: der Beitrag aus 3.2 (Wertebereich bis −1,5 — **bewusst etwas weiter** als ±1, damit Ausfallrisiko spürbar zählt, **ohne** die Gewichte ungleich zu machen; das ist die einzige Stelle, an der Credit „mehr Gewicht" bekommt, und sie ist transparent dokumentiert).

`net = Σ(Gewicht·Score) / Σ(Gewicht)` über die **verfügbaren** Komponenten.
Schwelle wie `weighted_signal`: `net > +0,15 → BULLISH`, `net < −0,15 → BEARISH`, sonst `NEUTRAL`.
`confidence = min(1,0, |net|)`.

### 3.4 Fehlende Komponenten

Verfügbarkeit pro Komponente: `metrics`/`duration`/`spread` gelten als verfügbar, wenn der jeweilige Sub-Agent
echte Daten geliefert hat (Status `AVAILABLE` bzw. nicht-`None`); `credit` ist verfügbar, wenn `credit_band is not None`
(also ein Rating vorlag). Heute ist `credit` mangels Bond-Daten praktisch immer unverfügbar.

Eine unverfügbare Komponente wird aus der Summe genommen und die Gewichte der übrigen **re-normalisiert**
(analog `weighted_signal`). Sind **alle** unverfügbar → `NEUTRAL, 0.0`.

### 3.5 Durchgerechnete Beispiele (zur Validierung)

**BB-Anleihe (Mittel), Rendite attraktiv:** `metrics +1`, `duration 0`, `spread 0`.

| Affinität | credit | net = Ø | Gesamt |
|---|---|---|---|
| konservativ | −1,0 | 0,00 | NEUTRAL |
| neutral | −0,5 | 0,125 | NEUTRAL (knapp) |
| risikofreudig | 0,0 | 0,25 | **BULLISH** |

**CCC-Anleihe (Riskant), Stress sichtbar:** `metrics +1`, `duration 0`, `spread −1`.

| Affinität | credit | net = Ø | Gesamt |
|---|---|---|---|
| konservativ | −1,5 | −0,375 | **BEARISH** |
| neutral | −1,0 | −0,25 | **BEARISH** |
| risikofreudig | −0,5 | −0,125 | NEUTRAL |

→ Altes Veto hätte beide Fälle stets BEARISH gemacht. Neu skaliert die Schärfe mit Lage **und** Risikoneigung.

## 4. Komponenten & Änderungen

### 4.1 Domäne (`core/domain/models.py`)
- Neues Enum `RiskAffinity(str, Enum)`: `KONSERVATIV="konservativ"`, `NEUTRAL="neutral"`, `RISIKOFREUDIG="risikofreudig"`.
- Neues Enum `CreditBand(str, Enum)`: `SICHER="sicher"`, `MITTEL="mittel"`, `RISKANT="riskant"`.
- `BondResult` erweitern: `overall_signal: Signal`, `confidence: float`, `risk_affinity: RiskAffinity`, `credit_band: CreditBand | None` (Default-Werte rückwärtskompatibel).
- `Position` (Portfolio) erweitern: `risk_affinity: RiskAffinity | None` (für Anleihen Pflicht, sonst `None`).

### 4.2 Reine Logik (`core/utils/bond_risk.py`, neu)
- `rating_to_band(rating: str | None) -> CreditBand | None` — S&P-String → Band (case-insensitiv, normalisiert; unbekannt → `None`).
- `credit_contribution(band: CreditBand, affinity: RiskAffinity) -> float` — die Tabelle aus 3.2.
- `aggregate_bond_signal(metrics, duration, spread, credit_band, affinity, *, available) -> tuple[Signal, float]` — die Aggregation aus 3.3/3.4. Komplett seiteneffektfrei → leicht testbar.

### 4.3 `bond_credit_agent`
- Snapshot um das **S&P-Rating** (String) und das abgeleitete `credit_band` erweitern (wenn Rohdaten vorhanden; sonst `None`). Die bestehende `default_probability`-Logik bleibt; das Rating ist die **primäre** Band-Quelle (Ableitung aus `default_probability` als spätere Alternativ-Quelle möglich, hier nicht v1).

### 4.4 `bond_chief_agent`
- `_overall_signal` (Mehrheits-Voting + Veto) **ersetzen** durch `aggregate_bond_signal(...)`.
- `run(ticker, bond_type, rate_direction, risk_affinity)` — Affinität als **Pflicht-Parameter** durchreichen.
- Gesamtsignal + Confidence + `risk_affinity` + `credit_band` ins **`BondResult`** schreiben (nicht nur ins Event) → Downstream muss nicht selbst aggregieren (löst auch den `BondResult`-Teil von #47).

### 4.5 Eingabe (`app/main.py`)
- Bei Anleihe-Analysen `--risk-affinity {konservativ,neutral,risikofreudig}` **verpflichtend**. Fehlt es → klare Fehlermeldung + Abbruch (kein Default). Für Nicht-Anleihen ignoriert.
- Composition-Root reicht die Affinität an den `top_down_/judgment`-Pfad bzw. den `bond_chief` durch (hexagonal: Parameter, keine globale Variable).

### 4.6 Persistenz (`adapters/memory/supabase_memory.py`)
- `analysis_memory`: neue Spalte `risk_affinity text`; zusätzlich die **Recompute-Bausteine** (Credit-Band + die drei Sub-Signale `metrics/duration/spread`) im `indicators_snapshot`-JSON ablegen.
- **Migration (Deploy-Schritt):** `ALTER TABLE analysis_memory ADD COLUMN risk_affinity text;` (analog zur `short_action`-Migration) + `db/schema.sql` nachziehen.

### 4.7 Portfolio (`Position` / `portfolio.json` / `JsonPortfolioProvider`)
- `risk_affinity` je Position lesen/schreiben. Für Anleihe-Positionen **Pflicht** (fail-loud wie `shares`/`direction` im 3a-Ausbau); für andere Klassen optional `None`.

### 4.8 Nachträglich ändern — Recompute (Variante a)
- Reine Funktion `recompute_bond_signal(credit_band, metrics, duration, spread, new_affinity) -> (Signal, confidence)` (nutzt `aggregate_bond_signal`).
- Im PM auslösbar: Affinität einer Position ändern → Gesamtsignal **sofort** neu rechnen (aus gespeicherten Bausteinen, **ohne** neue Datenabfrage) → gespeicherte Affinität + Signal aktualisieren.

### 4.9 Monitor (`portfolio_monitor_agent`)
- Je Anleihe-Position die gewählte `risk_affinity` anzeigen (Doku: „mit welchem Risiko gekauft").

## 5. Datenfluss

```
CLI --risk-affinity ─┐
                     ▼
        bond_chief.run(..., risk_affinity)
                     │  ruft Sub-Agenten (metrics/duration/spread/credit)
                     │  credit → rating_to_band(rating)
                     ▼
        aggregate_bond_signal(metrics,duration,spread, band, affinity)
                     ▼
        BondResult{overall_signal, confidence, risk_affinity, credit_band, ...}
                     ▼
        save_analysis → analysis_memory(risk_affinity, bausteine im snapshot)
                     ▼
        Portfolio (Position.risk_affinity)  ─►  Monitor zeigt Affinität
                     ▲
        PM: Affinität ändern ─► recompute_bond_signal(bausteine, neue_affinität)
```

## 6. Teststrategie (TDD, alles vorab rot)

Reine Funktionen (`bond_risk.py`):
- `rating_to_band`: je Band Stützstellen (AAA/BBB−/BB+/B−/CCC+/D) + Grenzen (BBB− sicher, BB+ mittel) + Unbekannt/`None`.
- `credit_contribution`: alle 9 Tabellenfelder.
- `aggregate_bond_signal`: die zwei Beispiel-Szenarien (BB & CCC × 3 Affinitäten) + Schwellen-Grenzfälle (genau ±0,15) + `UNAVAILABLE`-Re-Normalisierung + alle-unavailable → NEUTRAL.

Integration:
- `bond_chief`: gleiche Sub-Signale + verschiedene Affinitäten → erwartetes `overall_signal`; `BondResult` trägt `overall_signal/confidence/risk_affinity/credit_band`.
- `app/main.py`: Anleihe-Analyse ohne `--risk-affinity` → Abbruch mit Fehlermeldung.
- Persistenz: `save_analysis` schreibt `risk_affinity` + Bausteine (mocked `_connect`, Parameter prüfen).
- Portfolio: `Position` mit/ohne `risk_affinity`; Monitor-Anzeige.
- Recompute: gespeicherte Bausteine + neue Affinität → neues Signal (deckungsgleich mit `aggregate_bond_signal`).

## 7. Offene Migrationen / Risiken

- **DB-Migration** `risk_affinity`-Spalte vor Deploy ausführen (sonst INSERT-Fehler).
- **Dormanz:** Ohne Bond-Rohdaten bleibt `credit_band=None` → Credit `UNAVAILABLE`; das Bond-Signal stützt sich dann auf `metrics/duration/spread`. Verhalten ist definiert und getestet, liefert aber erst mit echtem Bond-Adapter den vollen Mehrwert.
- **„Gleiches Gewicht" mit weiterem Credit-Bereich:** bewusst gewählt (siehe 3.3) und transparent; bei Bedarf später nachjustierbar, ohne die Struktur zu ändern.

## 8. Verwandte Folge-Aufgabe (separater Spec)

**PM: periodische + manuelle Komplett-Neuanalyse von Portfolio-Positionen** (1-Klick + ~30-Tage-Hintergrundlauf, alle Anlageklassen, Scheduling). Wird im Logbuch erfasst; baut auf den hier eingeführten gespeicherten Bausteinen + der persistierten Risikoaffinität auf.
