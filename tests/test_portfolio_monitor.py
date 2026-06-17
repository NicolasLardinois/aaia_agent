from unittest.mock import MagicMock
from agents.portfolio.portfolio_monitor_agent import PortfolioMonitorAgent, _check_cluster_risks


def _make_memory(last_recs: dict = None):
    memory = MagicMock()
    if last_recs:
        def load_history(ticker, days=90):
            if ticker in last_recs:
                return [{"recommendation": last_recs[ticker]}]
            return []
        memory.load_history.side_effect = load_history
    else:
        memory.load_history.return_value = []
    return memory


def test_empty_portfolio_skips():
    agent = PortfolioMonitorAgent(_make_memory(), MagicMock())
    result = agent._evaluate_positions([])
    assert result["overall_health"] == "green"
    assert result["total_positions"] == 0
    assert result["alerts"] == []


def test_sector_cluster_risk():
    positions = [
        {"ticker": "AAPL", "shares": 10, "buy_price": 100, "sector": "Technology",
         "asset_class": "equity", "country": "USA", "current_price": 110},
        {"ticker": "MSFT", "shares": 10, "buy_price": 100, "sector": "Technology",
         "asset_class": "equity", "country": "USA", "current_price": 110},
        {"ticker": "NVDA", "shares": 2,  "buy_price": 100, "sector": "Technology",
         "asset_class": "equity", "country": "USA", "current_price": 110},
    ]
    risks = _check_cluster_risks(positions)
    sector_risk = [r for r in risks if r["type"] == "sector"]
    assert len(sector_risk) == 1
    assert sector_risk[0]["name"] == "Technology"


def test_loss_alert():
    positions = [
        {"ticker": "AAPL", "shares": 10, "buy_price": 200, "sector": "Technology",
         "asset_class": "equity", "country": "USA", "current_price": 160},
    ]
    agent = PortfolioMonitorAgent(_make_memory(), MagicMock())
    result = agent._evaluate_positions(positions)
    loss_alerts = [a for a in result["alerts"] if "Verlust" in a]
    assert len(loss_alerts) == 1


def test_health_green_no_alerts():
    # Asset-Klassen diversifiziert: equity ~36%, bond ~57%, commodity ~7%
    # keine Klasse > 60% → kein ASSET_CLASS-Klumpenrisiko nach verschärfter Schwelle
    positions = [
        {"ticker": "AAPL", "shares": 5, "buy_price": 150, "sector": "Technology",
         "asset_class": "equity", "country": "USA", "current_price": 160},
        {"ticker": "JNJ",  "shares": 5, "buy_price": 150, "sector": "Healthcare",
         "asset_class": "bond", "country": "Canada", "current_price": 155},
        {"ticker": "GLD",  "shares": 2, "buy_price": 150, "sector": "Commodities",
         "asset_class": "commodity", "country": "USA", "current_price": 155},
        {"ticker": "BUND", "shares": 3, "buy_price": 100, "sector": "Fixed Income",
         "asset_class": "bond", "country": "Germany", "current_price": 105},
    ]
    agent = PortfolioMonitorAgent(_make_memory(), MagicMock())
    result = agent._evaluate_positions(positions)
    assert result["overall_health"] == "green"


def test_fx_conversion_applied_to_total_value():
    positions = [
        {"ticker": "NESN.SW", "shares": 10, "buy_price": 100, "sector": "Staples",
         "asset_class": "equity", "country": "CH", "currency": "CHF", "current_price": 100},
    ]
    # 1 CHF = 1.10 USD → total_value_usd = 10*100*1.10 = 1100
    agent = PortfolioMonitorAgent(
        _make_memory(), MagicMock(),
        fx_rate=lambda frm, to: 1.10 if frm == "CHF" else 1.0,
    )
    result = agent._evaluate_positions(positions)
    assert result["total_value_usd"] == 1100.0


def test_concentration_herfindahl_field_present():
    positions = [
        {"ticker": "AAPL", "shares": 10, "buy_price": 100, "sector": "Technology",
         "asset_class": "equity", "country": "USA", "current_price": 100},
        {"ticker": "MSFT", "shares": 10, "buy_price": 100, "sector": "Technology",
         "asset_class": "equity", "country": "USA", "current_price": 100},
    ]
    agent = PortfolioMonitorAgent(_make_memory(), MagicMock())
    result = agent._evaluate_positions(positions)
    assert "concentration_hhi" in result
    # zwei gleich große Positionen → HHI = 0.5
    assert abs(result["concentration_hhi"] - 0.5) < 1e-9


def test_portfolio_volatility_and_maxdd_fields():
    positions = [
        {"ticker": "AAPL", "shares": 10, "buy_price": 100, "sector": "Technology",
         "asset_class": "equity", "country": "USA", "current_price": 110},
    ]
    # returns_provider liefert tägliche Returns je Ticker
    agent = PortfolioMonitorAgent(
        _make_memory(), MagicMock(),
        returns_provider=lambda ticker: [0.01, -0.02, 0.015, -0.01, 0.005],
    )
    result = agent._evaluate_positions(positions)
    assert "portfolio_volatility" in result
    assert "portfolio_max_drawdown" in result
    assert result["portfolio_max_drawdown"] <= 0.0
