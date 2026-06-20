import json
import pytest
from core.domain.models import PositionState
from core.domain.portfolio import PortfolioError
from adapters.persistence.json_portfolio import JsonPortfolioProvider


def _write(tmp_path, positions):
    f = tmp_path / "portfolio.json"
    f.write_text(json.dumps({"positions": positions}), encoding="utf-8")
    return str(f)


def test_valid_long_and_short(tmp_path):
    path = _write(tmp_path, [
        {"ticker": "AAPL", "shares": 10, "buy_price": 150, "direction": "long",
         "sector": "Tech", "asset_class": "equity", "country": "USA", "currency": "USD"},
        {"ticker": "NOK", "shares": 50, "buy_price": 4, "direction": "short"},
    ])
    p = JsonPortfolioProvider(path)
    pos = p.get_positions()
    assert {x.ticker for x in pos} == {"AAPL", "NOK"}
    assert p.position_state_for("AAPL") == PositionState.LONG
    assert p.position_state_for("NOK") == PositionState.SHORT
    assert p.position_state_for("MSFT") == PositionState.NONE


def test_missing_direction_raises(tmp_path):
    path = _write(tmp_path, [{"ticker": "AAPL", "shares": 10, "buy_price": 150}])
    with pytest.raises(PortfolioError):
        JsonPortfolioProvider(path).get_positions()


def test_invalid_direction_raises(tmp_path):
    path = _write(tmp_path, [{"ticker": "X", "shares": 1, "buy_price": 1, "direction": "neutral"}])
    with pytest.raises(PortfolioError):
        JsonPortfolioProvider(path).get_positions()


def test_missing_file_is_empty(tmp_path):
    p = JsonPortfolioProvider(str(tmp_path / "nope.json"))
    assert p.get_positions() == []
    assert p.position_state_for("AAPL") == PositionState.NONE


def test_missing_shares_raises(tmp_path):
    """Fehlendes Pflichtfeld 'shares' → PortfolioError (fail-loud, wie bei direction)."""
    path = _write(tmp_path, [{"ticker": "AAPL", "buy_price": 150, "direction": "long"}])
    with pytest.raises(PortfolioError):
        JsonPortfolioProvider(path).get_positions()


def test_missing_buy_price_raises(tmp_path):
    """Fehlendes Pflichtfeld 'buy_price' → PortfolioError (fail-loud, wie bei direction)."""
    path = _write(tmp_path, [{"ticker": "AAPL", "shares": 10, "direction": "long"}])
    with pytest.raises(PortfolioError):
        JsonPortfolioProvider(path).get_positions()
