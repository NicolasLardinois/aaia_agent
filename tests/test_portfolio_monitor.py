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
    positions = [
        {"ticker": "AAPL", "shares": 5, "buy_price": 150, "sector": "Technology",
         "asset_class": "equity", "country": "USA", "current_price": 160},
        {"ticker": "JNJ",  "shares": 5, "buy_price": 150, "sector": "Healthcare",
         "asset_class": "equity", "country": "Canada", "current_price": 155},
        {"ticker": "GLD",  "shares": 2, "buy_price": 150, "sector": "Commodities",
         "asset_class": "commodity", "country": "USA", "current_price": 155},
        {"ticker": "BOND", "shares": 3, "buy_price": 100, "sector": "Fixed Income",
         "asset_class": "bond", "country": "Germany", "current_price": 105},
    ]
    agent = PortfolioMonitorAgent(_make_memory(), MagicMock())
    result = agent._evaluate_positions(positions)
    assert result["overall_health"] == "green"
