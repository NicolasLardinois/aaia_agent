# Plan 0 — Fundament / Shared Utilities — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eine gemeinsame, getestete Utility-Schicht (robuste Statistik, relative Maße, real/nominal-Umrechnung, gewichtete Aggregation mit AVAILABLE/UNAVAILABLE-Status sowie datierte Zeitreihen-Historie) bereitstellen, auf der alle folgenden Pläne aufbauen.

**Architecture:** Reine, seiteneffektfreie Funktionen liegen in `core/utils/` (Hexagonal: Domänen-Kern ohne Infrastruktur-Abhängigkeiten). Einzige Ausnahme ist `DatedHistory` in `core/utils/timeseries_history.py`, das prozess-globalen In-Memory-State (`_RATE_HISTORY`, `regime`-History) durch eine JSON-datei-gestützte, datierte Persistenz ersetzt. Statistik-Funktionen bleiben numpy-frei und nutzen nur `math`/`statistics` aus der Standardbibliothek, konsistent zum bestehenden `core/utils/statistics.py`.

**Tech Stack:** Python, pytest, dataclasses/Enum, JSON-Persistenz

**Abhängigkeiten:** keine (dieser Plan ist die Basis aller anderen Pläne).

---

## Dateienübersicht

| Datei | Aktion | Verantwortung |
|---|---|---|
| `core/utils/statistics.py` | Modify | Bestehende `z_score`, `compute_severity`, `Z_THRESHOLD` behalten; `ROBUST_Z_THRESHOLD`, `MIN_SAMPLE_N`, `robust_z_score` (Median/MAD, Iglewicz-Hoaglin) und `bonferroni_z_threshold` ergänzen. → P4.1 |
| `core/utils/relative.py` | Create | `percentile_rank` (empirischer Rang-Perzentil, optionale Winsorisierung) und `zscore_vs_history` (Wrapper robust/klassisch). → P3.1 |
| `core/utils/real_nominal.py` | Create | `to_real` (exakte Fisher-Bereinigung) und `excess_over_nominal_gdp` (Überschuss über nominales BIP-Wachstum). → P3.2 |
| `core/domain/models.py` | Modify | `SignalStatus(str, Enum)` mit `AVAILABLE`/`UNAVAILABLE` ergänzen (Stil wie vorhandene Enums). → P1.4 |
| `core/utils/aggregation.py` | Create | `weighted_signal` — gewichtetes Voting über `(Signal, weight, SignalStatus)`-Tupel; `UNAVAILABLE` ignorieren und Restgewichte re-normalisieren. → P1.4 |
| `core/utils/timeseries_history.py` | Create | `DatedHistory` — JSON-datei-gestützte, datierte Zeitreihen-Historie mit idempotentem `append` pro `(series, observation_date)`; ersetzt prozess-globalen State. → P3.7 |
| `tests/test_robust_statistics.py` | Create | Tests für `robust_z_score` (inkl. MAD-Robustheit gegen Ausreißer) und `bonferroni_z_threshold`. |
| `tests/test_relative.py` | Create | Tests für `percentile_rank` (inkl. Winsorisierung) und `zscore_vs_history`. |
| `tests/test_real_nominal.py` | Create | Tests für `to_real` und `excess_over_nominal_gdp`. |
| `tests/test_aggregation.py` | Create | Tests für `weighted_signal` (inkl. Re-Normalisierung bei `UNAVAILABLE`). |
| `tests/test_timeseries_history.py` | Create | Tests für `DatedHistory` (inkl. idempotentes `append`, `value_on_or_before`, `latest`). |

---

## Task 1: Robuste Statistik — `robust_z_score` + `bonferroni_z_threshold`

> Review-Bezug P4.1: Der bestehende Sample-Z-Score (n−1) ist bei kurzen Jahres-Historien ausreißerempfindlich. Eine MAD-robuste Variante (Iglewicz-Hoaglin) und eine Bonferroni-Korrektur für Mehrfachtests machen die Anomalie-Erkennung robust.

**Files:**
- Modify: `core/utils/statistics.py`
- Test: `tests/test_robust_statistics.py` (Create)

- [ ] **(1) Failing Test schreiben** — `tests/test_robust_statistics.py`:

```python
import math

from core.utils.statistics import (
    ROBUST_Z_THRESHOLD,
    MIN_SAMPLE_N,
    robust_z_score,
    bonferroni_z_threshold,
)


def _history(n: int, value: float = 10.0) -> list[float]:
    # Konstante Streuung um 10.0 mit MAD > 0 (abwechselnd 9 / 11)
    return [value - 1.0 if i % 2 == 0 else value + 1.0 for i in range(n)]


def test_robust_z_konstanten():
    assert ROBUST_Z_THRESHOLD == 3.5
    assert MIN_SAMPLE_N == 20


def test_robust_z_zu_kurze_historie_ist_null():
    # len(history)=19 < MIN_SAMPLE_N=20 → 0.0
    assert robust_z_score(100.0, _history(19)) == 0.0


def test_robust_z_mad_null_ist_null():
    # Alle Werte identisch → MAD == 0 → 0.0 (kein ZeroDivision)
    assert robust_z_score(50.0, [7.0] * 25) == 0.0


def test_robust_z_normalwert_klein():
    # current == median → Zähler 0 → 0.0
    assert robust_z_score(10.0, _history(25)) == 0.0


def test_robust_z_iglewicz_hoaglin_formel():
    # history = [1..9], median=5, |x-5|=[4,3,2,1,0,1,2,3,4], MAD=median=2
    # current=11 → 0.6745*(11-5)/2 = 0.6745*3 = 2.0235
    history = [float(i) for i in range(1, 10)]
    assert abs(robust_z_score(11.0, history, min_n=9) - 2.0235) < 1e-6


def test_robust_z_mad_robust_gegen_ausreisser():
    # 24 Werte eng um 10 (abwechselnd 9 / 11) + 1 grober Ausreißer 1000.
    # Der MAD-Z des Ausreißers ist sehr groß (> ROBUST_Z_THRESHOLD),
    # während ein klassischer Sample-Z durch denselben Ausreißer in der
    # Varianz "verwässert" und kleiner ausfiele.
    base = _history(24)                      # 12x 9.0, 12x 11.0
    history = base + [1000.0]                # 25 Punkte
    z = robust_z_score(1000.0, history)
    # 25 Werte sortiert: 12x9, 12x11, 1x1000 → median = 11.0
    # |x-11| = 12x2 + 12x0 + 989 → sortiert (25 Werte) median = 2.0 → MAD = 2.0
    # 0.6745*(1000-11)/2.0 = 333.54025
    assert z > ROBUST_Z_THRESHOLD
    assert abs(z - 333.54025) < 1e-2


def test_bonferroni_keine_korrektur_bei_einem_test():
    # n_tests=1 → unveränderte Schwelle (bis auf Rundungsrauschen)
    assert abs(bonferroni_z_threshold(2.5, 1) - 2.5) < 1e-6


def test_bonferroni_strenger_bei_mehr_tests():
    # Mehr Tests → strengere (höhere) Schwelle
    base = 2.5
    assert bonferroni_z_threshold(base, 10) > base


def test_bonferroni_konkreter_wert():
    # base=1.96 → alpha = 2*(1-Phi(1.96)) ≈ 0.05; n=5 → alpha_adj=0.01
    # Phi^-1(1-0.005)=Phi^-1(0.995) ≈ 2.5758
    assert abs(bonferroni_z_threshold(1.96, 5) - 2.5758) < 1e-2
```

- [ ] **(2) Test laufen lassen → erwartet FAIL** — `python -m pytest tests/test_robust_statistics.py -q`. Erwarteter Grund: `ImportError: cannot import name 'robust_z_score' from 'core.utils.statistics'` (die Konstanten und Funktionen existieren noch nicht).

- [ ] **(3) Minimale Implementierung** — `core/utils/statistics.py` ergänzen (oben bestehender Inhalt bleibt unverändert; folgendes ans Dateiende anhängen):

```python
from statistics import median, NormalDist


ROBUST_Z_THRESHOLD = 3.5
MIN_SAMPLE_N = 20


def robust_z_score(current: float, history: list[float], min_n: int = MIN_SAMPLE_N) -> float:
    """Median/MAD-basiert (Iglewicz-Hoaglin): 0.6745*(current-median)/MAD.
    0.0 falls len(history)<min_n oder MAD==0."""
    if len(history) < min_n:
        return 0.0
    med = median(history)
    mad = median([abs(v - med) for v in history])
    if mad == 0.0:
        return 0.0
    return 0.6745 * (current - med) / mad


def bonferroni_z_threshold(base_threshold: float, n_tests: int) -> float:
    """Zweiseitige Bonferroni-Korrektur der Z-Schwelle:
    alpha = 2*(1-Phi(base)); alpha_adj = alpha/n; return Phi^-1(1-alpha_adj/2)."""
    if n_tests < 1:
        return base_threshold
    nd = NormalDist()
    alpha = 2.0 * (1.0 - nd.cdf(base_threshold))
    alpha_adj = alpha / n_tests
    return nd.inv_cdf(1.0 - alpha_adj / 2.0)
```

> Hinweis: `NormalDist` und `median` aus der Standardbibliothek `statistics`; keine externe Abhängigkeit. Der bestehende `import math` am Dateianfang bleibt erhalten.

- [ ] **(4) Test laufen → erwartet PASS** — `python -m pytest tests/test_robust_statistics.py -q`. Erwartung: 9 passed. Zusätzlich Regression sichern: `python -m pytest tests/test_statistics.py -q` (bestehende `z_score`/`compute_severity`-Tests weiterhin grün).

- [ ] **(5) Commit** — `git add core/utils/statistics.py tests/test_robust_statistics.py && git commit -m "feat(utils): robust_z_score (MAD/Iglewicz-Hoaglin) + bonferroni_z_threshold"`

---

## Task 2: Relative Maße — `percentile_rank` + `zscore_vs_history`

> Review-Bezug P3.1: Diverse Agenten (Buffett-Indikator, Gold/Silber-Ratio, Energy/Metals, P/C, VIX) klassifizieren über fixe Absolutschwellen statt über die relative Lage zur eigenen Historie. `percentile_rank` und `zscore_vs_history` liefern die gemeinsame Basis für relative Klassifikation.

**Files:**
- Create: `core/utils/relative.py`
- Test: `tests/test_relative.py` (Create)

- [ ] **(1) Failing Test schreiben** — `tests/test_relative.py`:

```python
from core.utils.relative import percentile_rank, zscore_vs_history


def test_percentile_leere_historie_ist_none():
    assert percentile_rank(5.0, []) is None


def test_percentile_median_ist_50():
    # 4 Werte < 5 von 8 → 50.0
    history = [1.0, 2.0, 3.0, 4.0, 6.0, 7.0, 8.0, 9.0]
    assert percentile_rank(5.0, history) == 50.0


def test_percentile_groesser_als_alle_ist_100():
    history = [1.0, 2.0, 3.0, 4.0]
    assert percentile_rank(99.0, history) == 100.0


def test_percentile_kleiner_als_alle_ist_0():
    history = [1.0, 2.0, 3.0, 4.0]
    assert percentile_rank(0.0, history) == 0.0


def test_percentile_winsorisierung_kappt_ausreisser():
    # 10 Werte 1..10 plus ein grober Ausreißer 1000.
    # Ohne Winsorisierung: value=11 liegt über 10 von 11 Werten → 90.909...
    # Mit winsorize=0.1: oberster Wert (1000) wird auf das 90%-Quantil
    # gekappt; value=11 liegt dann über ALLE 11 (gekappten) Werte → 100.0.
    history = [float(i) for i in range(1, 11)] + [1000.0]
    ohne = percentile_rank(11.0, history, winsorize=0.0)
    mit = percentile_rank(11.0, history, winsorize=0.1)
    assert abs(ohne - 100.0 * 10 / 11) < 1e-6
    assert mit == 100.0


def test_zscore_vs_history_robust_default():
    # robust=True (default) → identisch zu robust_z_score
    from core.utils.statistics import robust_z_score
    history = [float(i) for i in range(1, 10)]
    assert zscore_vs_history(11.0, history, min_n=9) == robust_z_score(11.0, history, min_n=9)


def test_zscore_vs_history_klassisch():
    # robust=False → identisch zu z_score
    from core.utils.statistics import z_score
    history = [1.0, 3.0, 5.0]
    assert zscore_vs_history(5.0, history, robust=False) == z_score(5.0, history)
```

- [ ] **(2) Test laufen lassen → erwartet FAIL** — `python -m pytest tests/test_relative.py -q`. Erwarteter Grund: `ModuleNotFoundError: No module named 'core.utils.relative'`.

- [ ] **(3) Minimale Implementierung** — `core/utils/relative.py` (Create):

```python
from core.utils.statistics import robust_z_score, z_score


def _winsorize(history: list[float], fraction: float) -> list[float]:
    """Kappt unterste und oberste `fraction`-Quantile auf ihre Grenzwerte."""
    if fraction <= 0.0 or len(history) < 2:
        return list(history)
    ordered = sorted(history)
    n = len(ordered)
    lo_idx = int(fraction * (n - 1))
    hi_idx = int((1.0 - fraction) * (n - 1))
    lo = ordered[lo_idx]
    hi = ordered[hi_idx]
    return [min(max(v, lo), hi) for v in history]


def percentile_rank(value: float, history: list[float], winsorize: float = 0.0) -> float | None:
    """Empirischer Rang-Perzentil 0..100 = Anteil der (ggf. winsorisierten)
    Historie < value. None falls history leer."""
    if not history:
        return None
    sample = _winsorize(history, winsorize)
    below = sum(1 for v in sample if v < value)
    return 100.0 * below / len(sample)


def zscore_vs_history(value: float, history: list[float], robust: bool = True, min_n: int = 20) -> float:
    """robust=True → robust_z_score, sonst z_score (aus statistics.py)."""
    if robust:
        return robust_z_score(value, history, min_n=min_n)
    return z_score(value, history)
```

- [ ] **(4) Test laufen → erwartet PASS** — `python -m pytest tests/test_relative.py -q`. Erwartung: 7 passed.

- [ ] **(5) Commit** — `git add core/utils/relative.py tests/test_relative.py && git commit -m "feat(utils): percentile_rank (mit Winsorisierung) + zscore_vs_history"`

---

## Task 3: Real vs. Nominal — `to_real` + `excess_over_nominal_gdp`

> Review-Bezug P3.2: Kredit-/Geldmengen-/Zins-Agenten vermischen nominale und reale Größen (z. B. 8 % Kreditwachstum bei 5 % Inflation = 3 % real; M-Wachstum vs. nominalem BIP). `to_real` (exakte Fisher-Bereinigung) und `excess_over_nominal_gdp` liefern die gemeinsame Umrechnung. Alle Eingaben sind in Prozentpunkten (8.0 = 8 %).

**Files:**
- Create: `core/utils/real_nominal.py`
- Test: `tests/test_real_nominal.py` (Create)

- [ ] **(1) Failing Test schreiben** — `tests/test_real_nominal.py`:

```python
from core.utils.real_nominal import to_real, excess_over_nominal_gdp


def test_to_real_exakte_fisher_formel():
    # ((1+0.08)/(1+0.05)-1)*100 = (1.08/1.05-1)*100 = 2.857142...
    assert abs(to_real(8.0, 5.0) - 2.857142857) < 1e-6


def test_to_real_unterscheidet_sich_von_naiver_subtraktion():
    # Naive Approximation 8-5=3.0; exakt ist ~2.857 → echte Differenz
    assert abs(to_real(8.0, 5.0) - 3.0) > 0.1


def test_to_real_null_inflation_ist_nominal():
    assert abs(to_real(4.0, 0.0) - 4.0) < 1e-9


def test_to_real_negativ_bei_inflation_ueber_nominal():
    # ((1+0.02)/(1+0.05)-1)*100 = -2.857142...
    assert to_real(2.0, 5.0) < 0.0
    assert abs(to_real(2.0, 5.0) - (-2.857142857)) < 1e-6


def test_excess_over_nominal_gdp_positiv():
    # Geldmengenwachstum 9 % über nominalem BIP-Wachstum 4 % → +5.0 pp
    assert excess_over_nominal_gdp(9.0, 4.0) == 5.0


def test_excess_over_nominal_gdp_negativ():
    assert excess_over_nominal_gdp(3.0, 4.0) == -1.0
```

- [ ] **(2) Test laufen lassen → erwartet FAIL** — `python -m pytest tests/test_real_nominal.py -q`. Erwarteter Grund: `ModuleNotFoundError: No module named 'core.utils.real_nominal'`.

- [ ] **(3) Minimale Implementierung** — `core/utils/real_nominal.py` (Create):

```python
def to_real(nominal_rate: float, inflation: float) -> float:
    """Exakte Fisher-Bereinigung: ((1+nominal_rate/100)/(1+inflation/100)-1)*100.
    Eingaben in Prozentpunkten (8.0 = 8 %)."""
    return ((1.0 + nominal_rate / 100.0) / (1.0 + inflation / 100.0) - 1.0) * 100.0


def excess_over_nominal_gdp(growth: float, nominal_gdp_growth: float) -> float:
    """growth - nominal_gdp_growth (Prozentpunkte)."""
    return growth - nominal_gdp_growth
```

- [ ] **(4) Test laufen → erwartet PASS** — `python -m pytest tests/test_real_nominal.py -q`. Erwartung: 6 passed.

- [ ] **(5) Commit** — `git add core/utils/real_nominal.py tests/test_real_nominal.py && git commit -m "feat(utils): to_real (exakte Fisher-Bereinigung) + excess_over_nominal_gdp"`

---

## Task 4: SignalStatus-Enum

> Review-Bezug P1.4 (Struktureller Hauptbefund): Stub-Signale dürfen in der Chief-Aggregation nicht als gleichberechtigtes `NEUTRAL` mitzählen. Jedes Sub-Ergebnis trägt künftig einen Status `AVAILABLE | UNAVAILABLE`. Dieser Task führt nur das Enum ein; die Aggregationslogik folgt in Task 5.

**Files:**
- Modify: `core/domain/models.py`
- Test: `tests/test_domain_extensions.py` (Modify — neue Tests anhängen)

- [ ] **(1) Failing Test schreiben** — folgende Tests ans Ende von `tests/test_domain_extensions.py` anhängen (Importpfad konsistent zu vorhandenen Domain-Tests):

```python
def test_signal_status_werte():
    from core.domain.models import SignalStatus
    assert SignalStatus.AVAILABLE.value == "available"
    assert SignalStatus.UNAVAILABLE.value == "unavailable"


def test_signal_status_ist_str_enum():
    # Stil wie vorhandene Enums (Signal, MarketRegime): str-basiert
    from core.domain.models import SignalStatus
    assert isinstance(SignalStatus.AVAILABLE, str)
    assert SignalStatus.AVAILABLE == "available"
```

- [ ] **(2) Test laufen lassen → erwartet FAIL** — `python -m pytest tests/test_domain_extensions.py -q -k signal_status`. Erwarteter Grund: `ImportError: cannot import name 'SignalStatus' from 'core.domain.models'`.

- [ ] **(3) Minimale Implementierung** — in `core/domain/models.py` direkt nach der bestehenden `Signal`-Enum (Zeilen 15–18) einfügen:

```python
class SignalStatus(str, Enum):
    AVAILABLE   = "available"
    UNAVAILABLE = "unavailable"
```

- [ ] **(4) Test laufen → erwartet PASS** — `python -m pytest tests/test_domain_extensions.py -q -k signal_status`. Erwartung: 2 passed.

- [ ] **(5) Commit** — `git add core/domain/models.py tests/test_domain_extensions.py && git commit -m "feat(utils): SignalStatus-Enum (AVAILABLE/UNAVAILABLE) fuer gewichtete Aggregation"`

---

## Task 5: Gewichtete Aggregation — `weighted_signal`

> Review-Bezug P1.4: Die Chief-Agenten verdichten Sub-Signale bisher gar nicht oder zählen UNAVAILABLE-Stubs als NEUTRAL mit (Verzerrung Richtung Mitte). `weighted_signal` nimmt UNAVAILABLE-Items aus der Gewichtung heraus und re-normalisiert die verbleibenden Gewichte.

**Files:**
- Create: `core/utils/aggregation.py`
- Test: `tests/test_aggregation.py` (Create)

- [ ] **(1) Failing Test schreiben** — `tests/test_aggregation.py`:

```python
from core.domain.models import Signal, SignalStatus
from core.utils.aggregation import weighted_signal

A = SignalStatus.AVAILABLE
U = SignalStatus.UNAVAILABLE


def test_alle_bullish_ergibt_bullish():
    sig, conf = weighted_signal([
        (Signal.BULLISH, 1.0, A),
        (Signal.BULLISH, 1.0, A),
    ])
    assert sig == Signal.BULLISH
    assert conf == 1.0


def test_gegenlaeufig_gleichgewichtet_ist_neutral():
    sig, conf = weighted_signal([
        (Signal.BULLISH, 1.0, A),
        (Signal.BEARISH, 1.0, A),
    ])
    assert sig == Signal.NEUTRAL
    assert conf == 0.0


def test_schwelle_0_15_neutral_bei_kleinem_net():
    # net = (1*1 + 9*0)/10 = 0.1 < 0.15 → NEUTRAL
    sig, conf = weighted_signal([
        (Signal.BULLISH, 1.0, A),
        (Signal.NEUTRAL, 9.0, A),
    ])
    assert sig == Signal.NEUTRAL
    assert abs(conf - 0.1) < 1e-9


def test_schwelle_0_15_bullish_knapp_darueber():
    # net = (2*1 + 8*0)/10 = 0.2 > 0.15 → BULLISH
    sig, conf = weighted_signal([
        (Signal.BULLISH, 2.0, A),
        (Signal.NEUTRAL, 8.0, A),
    ])
    assert sig == Signal.BULLISH
    assert abs(conf - 0.2) < 1e-9


def test_bearish_unterhalb_minus_0_15():
    # net = -0.2 < -0.15 → BEARISH
    sig, conf = weighted_signal([
        (Signal.BEARISH, 2.0, A),
        (Signal.NEUTRAL, 8.0, A),
    ])
    assert sig == Signal.BEARISH
    assert abs(conf - 0.2) < 1e-9


def test_unavailable_wird_ignoriert_und_renormalisiert():
    # UNAVAILABLE-Bearish (Gewicht 5) wird ENTFERNT.
    # Verbleibend: BULLISH w=1, BULLISH w=1 → net = 2/2 = +1.0 → BULLISH.
    # Würde das UNAVAILABLE-Item als NEUTRAL mitzaehlen, waere
    # net = 2/7 ≈ 0.286; zaehlte es als BEARISH mit, sogar negativ.
    sig, conf = weighted_signal([
        (Signal.BULLISH, 1.0, A),
        (Signal.BULLISH, 1.0, A),
        (Signal.BEARISH, 5.0, U),
    ])
    assert sig == Signal.BULLISH
    assert conf == 1.0


def test_alle_unavailable_ist_neutral():
    sig, conf = weighted_signal([
        (Signal.BULLISH, 1.0, U),
        (Signal.BEARISH, 2.0, U),
    ])
    assert sig == Signal.NEUTRAL
    assert conf == 0.0


def test_leere_liste_ist_neutral():
    sig, conf = weighted_signal([])
    assert sig == Signal.NEUTRAL
    assert conf == 0.0


def test_summe_der_gewichte_null_ist_neutral():
    # Alle verbleibenden Gewichte 0 → keine Division durch 0
    sig, conf = weighted_signal([
        (Signal.BULLISH, 0.0, A),
        (Signal.BEARISH, 0.0, A),
    ])
    assert sig == Signal.NEUTRAL
    assert conf == 0.0
```

- [ ] **(2) Test laufen lassen → erwartet FAIL** — `python -m pytest tests/test_aggregation.py -q`. Erwarteter Grund: `ModuleNotFoundError: No module named 'core.utils.aggregation'`.

- [ ] **(3) Minimale Implementierung** — `core/utils/aggregation.py` (Create):

```python
from core.domain.models import Signal, SignalStatus

_SCORE = {Signal.BULLISH: 1.0, Signal.BEARISH: -1.0, Signal.NEUTRAL: 0.0}
_THRESHOLD = 0.15


def weighted_signal(
    items: list[tuple[Signal, float, SignalStatus]],
) -> tuple[Signal, float]:
    """Gewichtetes Voting. UNAVAILABLE-Items ignorieren, Gewichte der
    verbleibenden re-normalisieren. Mapping BULLISH=+1, BEARISH=-1, NEUTRAL=0.
    net = Sum(w_i*s_i)/Sum(w_i) ueber AVAILABLE.
    Rueckgabe: (BULLISH wenn net>+0.15, BEARISH wenn net<-0.15, sonst NEUTRAL;
    confidence=min(1.0,abs(net)))."""
    available = [(sig, w) for sig, w, status in items if status == SignalStatus.AVAILABLE]
    weight_total = sum(w for _, w in available)
    if weight_total <= 0.0:
        return Signal.NEUTRAL, 0.0

    net = sum(_SCORE[sig] * w for sig, w in available) / weight_total
    confidence = min(1.0, abs(net))

    if net > _THRESHOLD:
        return Signal.BULLISH, confidence
    if net < -_THRESHOLD:
        return Signal.BEARISH, confidence
    return Signal.NEUTRAL, confidence
```

- [ ] **(4) Test laufen → erwartet PASS** — `python -m pytest tests/test_aggregation.py -q`. Erwartung: 9 passed.

- [ ] **(5) Commit** — `git add core/utils/aggregation.py tests/test_aggregation.py && git commit -m "feat(utils): weighted_signal mit UNAVAILABLE-Re-Normalisierung"`

---

## Task 6: Datierte Zeitreihen-Historie — `DatedHistory`

> Review-Bezug P3.7: `interest_rate_agent._RATE_HISTORY` und die `regime`-Composite-History sind prozess-globaler In-Memory-/Append-only-State; sie messen die Aufruffrequenz statt der ökonomischen Dynamik (zwei Läufe am selben Tag → „stable"). `DatedHistory` ersetzt diesen Zustand durch eine JSON-datei-gestützte, datierte Persistenz mit pro `(series, observation_date)` idempotentem `append` (gleicher Tag überschreibt). Damit lässt sich die Richtung aus „Wert heute vs. Wert vor N Monaten" mit echten Datumsstempeln ableiten.

**Files:**
- Create: `core/utils/timeseries_history.py`
- Test: `tests/test_timeseries_history.py` (Create)

- [ ] **(1) Failing Test schreiben** — `tests/test_timeseries_history.py`:

```python
from datetime import date

from core.utils.timeseries_history import DatedHistory


def test_append_und_values_chronologisch(tmp_path):
    h = DatedHistory(str(tmp_path / "hist.json"))
    # bewusst unsortierte Reihenfolge eingefuegt
    h.append("fed_rate", date(2026, 3, 1), 5.25)
    h.append("fed_rate", date(2026, 1, 1), 4.50)
    h.append("fed_rate", date(2026, 2, 1), 5.00)
    assert h.values("fed_rate") == [
        (date(2026, 1, 1), 4.50),
        (date(2026, 2, 1), 5.00),
        (date(2026, 3, 1), 5.25),
    ]


def test_append_idempotent_pro_tag(tmp_path):
    h = DatedHistory(str(tmp_path / "hist.json"))
    h.append("fed_rate", date(2026, 1, 1), 4.50)
    h.append("fed_rate", date(2026, 1, 1), 4.75)  # gleicher Tag → ueberschreibt
    vals = h.values("fed_rate")
    assert len(vals) == 1
    assert vals == [(date(2026, 1, 1), 4.75)]


def test_unbekannte_serie_ist_leer(tmp_path):
    h = DatedHistory(str(tmp_path / "hist.json"))
    assert h.values("nicht_da") == []
    assert h.latest("nicht_da") is None
    assert h.value_on_or_before("nicht_da", date(2026, 1, 1)) is None


def test_value_on_or_before(tmp_path):
    h = DatedHistory(str(tmp_path / "hist.json"))
    h.append("fed_rate", date(2026, 1, 1), 4.50)
    h.append("fed_rate", date(2026, 3, 1), 5.25)
    # exakter Treffer
    assert h.value_on_or_before("fed_rate", date(2026, 3, 1)) == 5.25
    # zwischen zwei Punkten → vorheriger gilt
    assert h.value_on_or_before("fed_rate", date(2026, 2, 15)) == 4.50
    # vor dem ersten Punkt → None
    assert h.value_on_or_before("fed_rate", date(2025, 12, 31)) is None


def test_latest(tmp_path):
    h = DatedHistory(str(tmp_path / "hist.json"))
    h.append("fed_rate", date(2026, 1, 1), 4.50)
    h.append("fed_rate", date(2026, 3, 1), 5.25)
    assert h.latest("fed_rate") == (date(2026, 3, 1), 5.25)


def test_persistenz_ueber_instanzen(tmp_path):
    path = str(tmp_path / "hist.json")
    h1 = DatedHistory(path)
    h1.append("fed_rate", date(2026, 1, 1), 4.50)
    # neue Instanz liest dieselbe Datei
    h2 = DatedHistory(path)
    assert h2.latest("fed_rate") == (date(2026, 1, 1), 4.50)


def test_mehrere_serien_getrennt(tmp_path):
    h = DatedHistory(str(tmp_path / "hist.json"))
    h.append("fed_rate", date(2026, 1, 1), 4.50)
    h.append("ecb_rate", date(2026, 1, 1), 3.00)
    assert h.latest("fed_rate") == (date(2026, 1, 1), 4.50)
    assert h.latest("ecb_rate") == (date(2026, 1, 1), 3.00)
```

- [ ] **(2) Test laufen lassen → erwartet FAIL** — `python -m pytest tests/test_timeseries_history.py -q`. Erwarteter Grund: `ModuleNotFoundError: No module named 'core.utils.timeseries_history'`.

- [ ] **(3) Minimale Implementierung** — `core/utils/timeseries_history.py` (Create):

```python
import json
import os
from datetime import date


class DatedHistory:
    """JSON-datei-gestuetzte, datierte Zeitreihen-Historie.

    Ersetzt prozess-globalen In-Memory-State (_RATE_HISTORY, regime-History).
    Persistenzformat: {series: {ISO-Datum: value}}.
    """

    def __init__(self, path: str) -> None:
        self.path = path
        self._data: dict[str, dict[str, float]] = self._load()

    def _load(self) -> dict[str, dict[str, float]]:
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception:
            return {}
        if not isinstance(raw, dict):
            return {}
        return raw

    def _save(self) -> None:
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._data, f)

    def append(self, series: str, observation_date: date, value: float) -> None:
        """Idempotent pro (series, observation_date): gleicher Tag
        ueberschreibt, haengt nicht doppelt an."""
        self._data.setdefault(series, {})[observation_date.isoformat()] = value
        self._save()

    def values(self, series: str) -> list[tuple[date, float]]:
        """Chronologisch sortiert."""
        entries = self._data.get(series, {})
        return [
            (date.fromisoformat(d), v)
            for d, v in sorted(entries.items())
        ]

    def value_on_or_before(self, series: str, target: date) -> float | None:
        result: float | None = None
        for d, v in self.values(series):
            if d <= target:
                result = v
            else:
                break
        return result

    def latest(self, series: str) -> tuple[date, float] | None:
        vals = self.values(series)
        return vals[-1] if vals else None
```

- [ ] **(4) Test laufen → erwartet PASS** — `python -m pytest tests/test_timeseries_history.py -q`. Erwartung: 7 passed.

- [ ] **(5) Commit** — `git add core/utils/timeseries_history.py tests/test_timeseries_history.py && git commit -m "feat(utils): DatedHistory (datierte, idempotente JSON-Zeitreihen-Historie)"`

---

## Task 7: Gesamt-Regression der Utility-Schicht

> Sicherstellen, dass die neue Utility-Schicht vollständig grün ist und keine bestehenden Tests bricht. Reiner Verifikations-Task, keine neue Implementierung.

**Files:**
- Test: gesamte `tests/`-Suite

- [ ] **(1) Vollständigen Utility-Testlauf ausführen** — `python -m pytest tests/test_robust_statistics.py tests/test_relative.py tests/test_real_nominal.py tests/test_aggregation.py tests/test_timeseries_history.py tests/test_domain_extensions.py tests/test_statistics.py -q`. Erwartung: alle grün.

- [ ] **(2) Gesamt-Suite laufen lassen** — `python -m pytest -q`. Erwartung: keine Regression durch die Ergänzungen (das neue `SignalStatus`-Enum und die neuen Module sind additiv).

- [ ] **(3) Bei Fehlern** superpowers:systematic-debugging anwenden, Ursache beheben, Schritte (1)/(2) wiederholen.

- [ ] **(4) Abschluss-Commit (nur falls Fixes nötig waren)** — `git add -A && git commit -m "feat(utils): Regression-Fixes nach Fundament-Utilities"`

---

## Abdeckung

| Review-Punkt | Beschreibung | Task(s) |
|---|---|---|
| P4.1 | Robuste Statistik (Median/MAD, Iglewicz-Hoaglin; Bonferroni-Korrektur) | Task 1 |
| P3.1 | Relative Maße (Z-Score / Perzentil-Rang statt Absolutschwellen) | Task 2 |
| P3.2 | Real vs. nominal (exakte Fisher-Bereinigung; Überschuss über nominales BIP) | Task 3 |
| P1.4 | AVAILABLE/UNAVAILABLE-Status + gewichtete Aggregation mit Re-Normalisierung | Task 4, Task 5 |
| P3.7 | Datierte Zeitreihen-Historie statt prozess-globalem State | Task 6 |

---

## Final definierte Signaturen (Single Source of Truth für Folgepläne)

```python
# core/utils/statistics.py  (ergänzt; z_score, compute_severity, Z_THRESHOLD bleiben)
ROBUST_Z_THRESHOLD = 3.5
MIN_SAMPLE_N = 20
def robust_z_score(current: float, history: list[float], min_n: int = MIN_SAMPLE_N) -> float
def bonferroni_z_threshold(base_threshold: float, n_tests: int) -> float

# core/utils/relative.py  (neu)
def percentile_rank(value: float, history: list[float], winsorize: float = 0.0) -> float | None
def zscore_vs_history(value: float, history: list[float], robust: bool = True, min_n: int = 20) -> float

# core/utils/real_nominal.py  (neu)
def to_real(nominal_rate: float, inflation: float) -> float
def excess_over_nominal_gdp(growth: float, nominal_gdp_growth: float) -> float

# core/domain/models.py  (ergänzt)
class SignalStatus(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"

# core/utils/aggregation.py  (neu)
def weighted_signal(items: list[tuple[Signal, float, SignalStatus]]) -> tuple[Signal, float]

# core/utils/timeseries_history.py  (neu)
class DatedHistory:
    def __init__(self, path: str) -> None
    def append(self, series: str, observation_date: date, value: float) -> None
    def values(self, series: str) -> list[tuple[date, float]]
    def value_on_or_before(self, series: str, target: date) -> float | None
    def latest(self, series: str) -> tuple[date, float] | None
```
