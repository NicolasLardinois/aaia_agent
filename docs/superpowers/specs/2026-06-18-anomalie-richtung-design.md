# Block 1a: Anomalie-Richtung (`AnomalyReport.direction`) — Design

**Datum:** 2026-06-18
**Status:** Genehmigt (Design)
**Teil von:** Shorts-Programm (`docs/short.md`). **Prerequisite** für Block 1b (Short-Thesis-Engine).

## Kontext & Ziel

Heute trägt `AnomalyReport` (`core/domain/models.py`) **keine strukturierte Richtung** — nur `severity` + Texte. `compute_confidence` (`core/domain/recommendation.py`) zieht Anomalien **richtungs-blind** ab (`_SEVERITY_DEDUCTION` für `td_anomaly.severity` + `bu_anomaly.severity`): *jede* Anomalie senkt die Konfidenz, egal wohin sie zeigt. Ein Insider-**Kauf**-Cluster und ein Insider-**Verkauf**-Cluster wirken identisch.

**Ziel:** Anomalien **richtungs-bewusst** machen — von „blinder Unsicherheits-Abzug" zu „bestätigende vs. widersprechende Evidenz". Das ist die **Voraussetzung** dafür, dass Block 1b eine *bearishe* Anomalie als Short-Evidenz (Konfidenz-Boost) nutzen kann.

## Scope

**Im Block:**
- `AnomalyReport` um `direction: str` (`"bearish"` / `"bullish"` / `"neutral"`) erweitern (Default `"neutral"`).
- `BottomUpAnomalyAgent` und `TopDownAnomalyAgent` füllen `direction` aus der Tendenz der erkannten Anomalien.
- `compute_confidence` nutzt `direction` **relativ zum `alignment`**: bestätigend → kein Abzug; widersprechend/neutral → Abzug wie bisher.
- Regressionstests auf die Long-Konfidenz.

**Außerhalb (Block 1b):**
- Die Short-Engine selbst und der **Boost** der Short-Konfidenz durch bearishe Anomalien (1b konsumiert `direction`).

## Komponenten / Änderungen

### 1. `core/domain/models.py` — `AnomalyReport.direction`
- Neues Feld `direction: str = "neutral"` (Default sichert Rückwärtskompatibilität: bestehende Konstruktionen ohne `direction` bleiben `"neutral"`).
- `AnomalyReport.empty()` setzt `direction="neutral"`.

### 2. `agents/anomaly/bottom_up_anomaly_agent.py` — Richtung aus der Tendenz
Beim Erkennen der Anomalien eine **bearish/bullish-Tendenz** zählen und am Ende zu `direction` verdichten:
- **bearish:** KGV ungewöhnlich **hoch** (teuer), Short-Float ungewöhnlich **hoch**, Insider-**Verkaufs**-Cluster, Widerspruch „Mehrheit der Signale bearish".
- **bullish:** KGV ungewöhnlich **niedrig**, Insider-**Kauf**-Cluster.
- **neutral:** reine Signal-Widersprüche (Fundamentals↔Valuation etc.) ohne klare Richtung; keine Anomalien.
- Verdichtung: mehr bearish → `"bearish"`; mehr bullish → `"bullish"`; gleich/keine → `"neutral"`. (Zählung als `bearish_score`/`bullish_score` an den jeweiligen `append`-Stellen.)

### 3. `agents/anomaly/top_down_anomaly_agent.py` — Richtung aus Makro-Anomalien
Analog: risk-off / makro-bearishe Anomalien → `"bearish"`, risk-on → `"bullish"`, sonst `"neutral"`. (Implementer leitet die Tendenz aus der bestehenden Anomalie-Erkennung des Agenten ab; im Zweifel `"neutral"`.)

### 4. `core/domain/recommendation.py` — `compute_confidence` gerichtet
Die Anomalie-Behandlung (heute: immer `+= _SEVERITY_DEDUCTION[severity]`) wird **richtungs-bewusst**. Pro Anomalie (td, bu):
- **bestätigend** (Anomalie-`direction` passt zum `alignment`: `bearish` bei `aligned_bearish`, `bullish` bei `aligned_bullish`) → **kein Abzug** (die Anomalie stützt die These, ist nicht destabilisierend).
- **widersprechend** (`bearish` bei `aligned_bullish` / `bullish` bei `aligned_bearish`) **oder neutral oder alignment nicht aligned** → **Abzug wie bisher** (`_SEVERITY_DEDUCTION`).

Hilfsfunktion:
```python
def _anomaly_deduction(alignment: str, report: AnomalyReport) -> float:
    confirms = (
        (alignment == "aligned_bearish" and report.direction == "bearish") or
        (alignment == "aligned_bullish" and report.direction == "bullish")
    )
    if confirms:
        return 0.0
    return _SEVERITY_DEDUCTION.get(report.severity, 0.0)
```
In `compute_confidence` die zwei Zeilen
`score += _SEVERITY_DEDUCTION.get(td_anomaly.severity, 0.0)` / `… bu_anomaly …`
ersetzen durch `score += _anomaly_deduction(alignment, td_anomaly)` / `… bu_anomaly …`.

## Datenfluss
`AnomalyChiefAgent.run()` → (TopDown + BottomUp)-Agenten setzen jetzt **`direction`** → `compute_confidence(alignment, …, td_anomaly, bu_anomaly, …)` wertet `direction` **relativ zum alignment** aus → Long-Konfidenz. (Block 1b nutzt dieselbe `direction` für den Short-Konfidenz-Boost.)

## Fehlerbehandlung / Rückwärtskompatibilität
- `direction` hat Default `"neutral"` → bestehende `AnomalyReport`-Konstruktionen und Tests bleiben unverändert (neutral ⇒ Abzug wie bisher).
- **Einziges geändertes Verhalten:** bestätigende Anomalien (gerichtet + zur These passend) erhalten **keinen** Abzug mehr → Long-Konfidenz in genau diesen Fällen leicht höher. Alle anderen Fälle unverändert.

## Tests
- **Modell** (`tests/`): `AnomalyReport.direction` Default `"neutral"`; `empty()` → `"neutral"`.
- **BottomUpAnomalyAgent** (`tests/`): mit gemocktem `bottom_up` + History, die einen **Short-Float-Hoch** / **Insider-Verkaufs**-Cluster erzeugt → `direction == "bearish"`; Insider-**Kauf**-Cluster → `"bullish"`; keine Anomalien → `"neutral"`.
- **`compute_confidence`** (`tests/test_confidence.py` erweitern):
  - bestätigend: `alignment="aligned_bearish"` + `bu_anomaly.direction="bearish"`, `severity="high"` → **kein** Abzug (Konfidenz höher als bei neutral-direction).
  - widersprechend: `aligned_bullish` + `bearish`-Anomalie → Abzug wie bisher.
  - neutral-direction → identisch zum alten Verhalten.
- **Regression:** gesamte Suite grün; bestehende `compute_confidence`-Erwartungen (alle mit Default-`direction="neutral"`) unverändert.

## Akzeptanzkriterien
1. `AnomalyReport.direction` existiert (`bearish`/`bullish`/`neutral`), Default `"neutral"`, `empty()` → `"neutral"`.
2. Beide Anomalie-Agenten setzen `direction` aus der Tendenz der erkannten Anomalien.
3. `compute_confidence`: bestätigende Anomalie → kein Abzug; widersprechend/neutral/nicht-aligned → Abzug wie bisher.
4. Bestehende Long-Konfidenz-Tests (neutral-direction) bleiben grün; nur bestätigende Fälle ändern sich (leicht höher).
5. Gesamte Testsuite grün (0 failed).
