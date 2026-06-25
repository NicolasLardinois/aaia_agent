import asyncio
from unittest.mock import MagicMock

from agents.stock_deep_dive.index.sector_composition_agent import (
    SectorCompositionAgent, _hhi, _concentration_signal,
)
from core.domain.models import Signal, SignalStatus


def test_hhi_equal_weights():
    # 10 gleich gewichtete Titel à 10 % → HHI = 10 * 10^2 = 1000
    holdings = [{"name": f"T{i}", "weight_pct": 10.0, "sector": "X"} for i in range(10)]
    assert _hhi(holdings) == 1000.0


def test_hhi_concentrated_is_higher():
    holdings = [{"name": "Big", "weight_pct": 50.0, "sector": "X"}] + \
               [{"name": f"T{i}", "weight_pct": 5.0, "sector": "Y"} for i in range(10)]
    assert _hhi(holdings) > 2000.0


def test_concentration_signal_high_is_bearish():
    assert _concentration_signal(hhi=2500.0) == Signal.BEARISH


def test_concentration_signal_low_is_neutral():
    assert _concentration_signal(hhi=800.0) == Signal.NEUTRAL


def test_unbekannte_sektoren_kein_top_sector_aber_konzentration():
    """Quelle ohne Sektor-Info (z. B. slickcharts): kein irreführender 'Unknown'-Top-Sektor,
    aber Top-Holding/Konzentration/Signal bleiben gültig."""
    market = MagicMock()
    market.get_index_holdings.return_value = [
        {"name": "NVDA", "weight_pct": 7.0, "sector": None},
        {"name": "AAPL", "weight_pct": 6.0, "sector": None},
    ] + [{"name": f"T{i}", "weight_pct": 1.0, "sector": None} for i in range(20)]
    agent = SectorCompositionAgent(market, MagicMock())
    res = asyncio.run(agent.run("^GSPC"))
    assert res.status == SignalStatus.AVAILABLE
    assert res.top_sector is None and res.top_sector_weight is None
    assert res.top_holding == "NVDA" and res.top_holding_weight == 7.0
    assert res.top_10_concentration is not None


def test_run_unavailable_without_holdings():
    provider = MagicMock()
    provider.get_index_holdings.return_value = []
    agent = SectorCompositionAgent(provider, MagicMock())
    result = asyncio.run(agent.run("^GSPC"))
    assert result.status == SignalStatus.UNAVAILABLE


def test_run_available_computes_top10_and_top_sector():
    provider = MagicMock()
    provider.get_index_holdings.return_value = [
        {"name": "Apple", "weight_pct": 7.0, "sector": "Technology"},
        {"name": "Microsoft", "weight_pct": 6.0, "sector": "Technology"},
        {"name": "Nvidia", "weight_pct": 5.0, "sector": "Technology"},
    ] + [{"name": f"T{i}", "weight_pct": 1.0, "sector": "Financials"} for i in range(10)]
    agent = SectorCompositionAgent(provider, MagicMock())
    result = asyncio.run(agent.run("^GSPC"))
    assert result.status == SignalStatus.AVAILABLE
    assert result.top_sector == "Technology"
    assert result.top_holding == "Apple"
    assert result.top_10_concentration is not None


def test_top10_concentration_correct_when_unsorted_input():
    """Unsortierte Eingabe: top_10_concentration muss Summe der 10 grössten Gewichte sein."""
    # Erstelle 15 Holdings in zufälliger Reihenfolge (nicht nach Gewicht sortiert)
    # Die 10 größten haben Gewicht 10..19 (Summe = 145), die 5 kleinsten 1..5 (Summe = 15)
    holdings_unsorted = [
        {"name": "Small3", "weight_pct": 3.0, "sector": "X"},
        {"name": "Big10", "weight_pct": 10.0, "sector": "A"},
        {"name": "Small1", "weight_pct": 1.0, "sector": "X"},
        {"name": "Big19", "weight_pct": 19.0, "sector": "A"},
        {"name": "Big11", "weight_pct": 11.0, "sector": "A"},
        {"name": "Small5", "weight_pct": 5.0, "sector": "X"},
        {"name": "Big18", "weight_pct": 18.0, "sector": "A"},
        {"name": "Big12", "weight_pct": 12.0, "sector": "A"},
        {"name": "Small2", "weight_pct": 2.0, "sector": "X"},
        {"name": "Big17", "weight_pct": 17.0, "sector": "A"},
        {"name": "Big13", "weight_pct": 13.0, "sector": "A"},
        {"name": "Small4", "weight_pct": 4.0, "sector": "X"},
        {"name": "Big16", "weight_pct": 16.0, "sector": "A"},
        {"name": "Big14", "weight_pct": 14.0, "sector": "A"},
        {"name": "Big15", "weight_pct": 15.0, "sector": "A"},
    ]
    expected_top10 = round(10 + 11 + 12 + 13 + 14 + 15 + 16 + 17 + 18 + 19, 1)  # 145.0
    provider = MagicMock()
    provider.get_index_holdings.return_value = holdings_unsorted
    agent = SectorCompositionAgent(provider, MagicMock())
    result = asyncio.run(agent.run("^GSPC"))
    assert result.top_10_concentration == expected_top10
