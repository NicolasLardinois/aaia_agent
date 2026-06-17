from agents.market_cockpit.sector_chief_agent import _top_sectors


def test_top_sectors_combines_us_and_eu():
    perf = type("P", (), {})()
    perf.usa = {"Technology": 5.0, "Energy": 4.0, "Utilities": 1.0}
    perf.eurozone = {"Financials": 6.0, "Healthcare": 2.0}
    top = _top_sectors(perf, n=3)
    # höchste relative Werte über beide Regionen
    assert "Financials" in top and "Technology" in top
