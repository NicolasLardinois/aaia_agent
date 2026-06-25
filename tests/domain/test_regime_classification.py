"""§6: Kern-Regime-Klassifizierung festnageln — sie treibt jede Empfehlung an.

Bestehende Tests (`test_regime.py`) decken `detect`-Verdrahtung, Trend-Invarianz
und die Inflations-Scores ab. Diese Datei schliesst zwei Lücken:
- `_regime_from`: gewinnt an jedem Phasen-Zentrum die richtige Phase? RECOVERY nur
  mit bestätigtem Aufwärtstrend? Tipp-Verhalten bei Trend?  (Verhalten, nicht
  die Gauss-Mathematik nachgerechnet.)
- `_score_indicator`: lückenlose Bänder über mehrere Indikatoren (AGENTS.md §2),
  bisher nur für Inflation getestet.
"""
import pytest

from core.domain.models import MarketRegime
from core.domain.regime import _regime_from, _score_indicator, _TREND_NORMAL


# ── _regime_from: Phasen-Zentren (ohne Trend = reine Niveaueinschätzung) ──────

@pytest.mark.parametrize("composite,expected", [
    (-0.80, MarketRegime.DEPRESSION),
    (-0.50, MarketRegime.RECESSION),
    (-0.10, MarketRegime.SLOWDOWN),
    (0.40,  MarketRegime.EXPANSION),
    (0.75,  MarketRegime.BOOM),
])
def test_regime_from_phasen_zentren_ohne_trend(composite, expected):
    assert _regime_from(composite, trend=None) == expected


# ── RECOVERY nur mit bestätigtem Aufwärtstrend (dokumentierte Kern-Annahme) ───

def test_recovery_braucht_aufwaertstrend():
    # negativer Composite (-0.30) OHNE Trend → keine ERHOLUNG (RECOVERY = 0.0)
    assert _regime_from(-0.30, trend=None) != MarketRegime.RECOVERY


def test_recovery_feuert_bei_starkem_aufwaertstrend():
    # gleicher Composite, aber kräftiger Aufwärtstrend → ERHOLUNG
    assert _regime_from(-0.30, trend=3 * _TREND_NORMAL) == MarketRegime.RECOVERY


# ── Trend tippt einen leicht positiven Composite (Übergangsbereich) ───────────

def test_trend_kippt_leicht_positiven_composite():
    composite = 0.20  # zwischen SLOWDOWN-Zentrum (-0.10) und EXPANSION (+0.40)
    assert _regime_from(composite, trend=None) == MarketRegime.EXPANSION
    # kräftiger Abwärtstrend → kippt nach SLOWDOWN (Schwächephase verstärkt)
    assert _regime_from(composite, trend=-0.24) == MarketRegime.SLOWDOWN


# ── _score_indicator: lückenlose Bänder über mehrere Indikatoren ──────────────

@pytest.mark.parametrize("value,expected", [
    (4.0, 1.0),    # > 3 → starkes Wachstum
    (2.0, 0.5),    # (1, 3]
    (0.5, -0.5),   # (0, 1]
    (-1.0, -1.0),  # <= 0 (Schrumpfung)
    (3.0, 0.5),    # genau 3 ist NICHT > 3
])
def test_score_gdp_growth_baender(value, expected):
    assert _score_indicator("gdp_growth", value) == expected


@pytest.mark.parametrize("value,expected", [
    (3.5, 1.0),    # < 4
    (4.5, 0.5),    # [4, 5)
    (6.0, -0.5),   # [5, 7)
    (8.0, -1.0),   # >= 7
    (4.0, 0.5),    # genau 4 → nicht < 4
])
def test_score_unemployment_baender(value, expected):
    assert _score_indicator("unemployment", value) == expected


@pytest.mark.parametrize("value,expected", [
    (1.5, 1.0),    # > 1 → klar positiv (steile Kurve)
    (0.5, 0.5),    # (0, 1] → flach positiv
    (-0.3, -1.0),  # invertiert
    (1.0, 0.5),    # genau 1 → nicht > 1
    (0.0, -1.0),   # genau 0 → nicht > 0 → invertiert
])
def test_score_yield_curve_baender(value, expected):
    assert _score_indicator("yield_curve_10y3m_usa", value) == expected


def test_score_inflation_schultern_negativ():
    """Die -0.5-Schultern der Inflations-Glocke (zu niedrig / leicht zu hoch)."""
    assert _score_indicator("inflation", 1.2) == -0.5   # 1.0 <= v < 1.5
    assert _score_indicator("inflation", 3.0) == -0.5   # 2.5 < v <= 4.0
    assert _score_indicator("inflation", 2.0) == 0.5    # Zielband
    assert _score_indicator("inflation", 0.3) == -1.0   # Deflation
    assert _score_indicator("inflation", 7.0) == -1.0   # Hochinflation


def test_score_unbekannter_indikator_ist_null():
    """Ein nicht modellierter Schlüssel trägt 0.0 bei (neutral, kein Crash)."""
    assert _score_indicator("gibt_es_nicht", 42.0) == 0.0
