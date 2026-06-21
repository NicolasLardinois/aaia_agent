import json
import pytest
from adapters.persistence.json_portfolio import JsonPortfolioProvider
from core.domain.portfolio import PortfolioError


def _write(tmp_path, positions):
    p = tmp_path / "portfolio.json"
    p.write_text(json.dumps({"positions": positions}), encoding="utf-8")
    return str(p)


def test_bond_position_traegt_risk_affinity(tmp_path):
    path = _write(tmp_path, [{"ticker": "TLT", "shares": 10, "buy_price": 90,
        "direction": "long", "asset_class": "bond", "risk_affinity": "neutral"}])
    pos = JsonPortfolioProvider(path).get_positions()[0]
    assert pos.risk_affinity == "neutral"


def test_bond_ohne_risk_affinity_failt(tmp_path):
    path = _write(tmp_path, [{"ticker": "TLT", "shares": 10, "buy_price": 90,
        "direction": "long", "asset_class": "bond"}])
    with pytest.raises(PortfolioError):
        JsonPortfolioProvider(path).get_positions()


def test_equity_ohne_risk_affinity_ok(tmp_path):
    path = _write(tmp_path, [{"ticker": "AAPL", "shares": 10, "buy_price": 90,
        "direction": "long", "asset_class": "equity"}])
    assert JsonPortfolioProvider(path).get_positions()[0].risk_affinity is None
