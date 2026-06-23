import json
import pytest
from core.domain.models import PositionState
from core.domain.portfolio import PortfolioError
from core.domain.taxonomy import Underlying, Wrapper
from adapters.persistence.json_portfolio import JsonPortfolioProvider


def _write(tmp_path, positions):
    f = tmp_path / "portfolio.json"
    f.write_text(json.dumps({"positions": positions}), encoding="utf-8")
    return str(f)


def test_contract_multiplier_defaults_to_one(tmp_path):
    """Ohne JSON-Key bleibt der Multiplikator 1.0 (rückwärtskompatibel)."""
    path = _write(tmp_path, [{"ticker": "AAPL", "shares": 10, "buy_price": 100, "direction": "long"}])
    pos = JsonPortfolioProvider(path).get_positions()
    assert pos[0].contract_multiplier == 1.0


def test_contract_multiplier_read_from_json(tmp_path):
    """Future-Position liefert die Kontraktgröße fürs Notional."""
    path = _write(tmp_path, [{
        "ticker": "CL", "shares": 2, "buy_price": 80, "direction": "long",
        "underlying": "commodity", "wrapper": "future", "contract_multiplier": 1000,
    }])
    pos = JsonPortfolioProvider(path).get_positions()
    assert pos[0].contract_multiplier == 1000.0


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


def test_position_state_case_insensitive(tmp_path):
    """Ticker-Abgleich ist case-insensitiv: CLI-Eingabe 'aapl' findet Depot-'AAPL'
    und 'NOK' findet Depot-'nok' (kanonische Ticker-Schreibweise im System ist Großschrift)."""
    path = _write(tmp_path, [
        {"ticker": "AAPL", "shares": 10, "buy_price": 150, "direction": "long"},
        {"ticker": "nok", "shares": 50, "buy_price": 4, "direction": "short"},
    ])
    p = JsonPortfolioProvider(path)
    assert p.position_state_for("aapl") == PositionState.LONG   # Eingabe klein, Depot groß
    assert p.position_state_for("NOK") == PositionState.SHORT   # Eingabe groß, Depot klein


def test_position_default_und_legacy_asset_class(tmp_path):
    """(a) Neues Schema: underlying/wrapper direkt aus JSON laden.
    (b) Alt-Schlüssel asset_class wird via legacy_to_taxonomy korrekt abgebildet."""
    p = tmp_path / "portfolio.json"
    p.write_text(json.dumps({"positions": [
        {"ticker": "GC", "shares": 1, "buy_price": 1800, "direction": "long",
         "underlying": "precious_metal", "wrapper": "future"},
        {"ticker": "XLE", "shares": 1, "buy_price": 80, "direction": "long",
         "asset_class": "etf"},   # Legacy-Schlüssel → equity_index/fund
    ]}), encoding="utf-8")
    positions = JsonPortfolioProvider(str(p)).get_positions()
    assert positions[0].underlying == Underlying.PRECIOUS_METAL
    assert positions[0].wrapper == Wrapper.FUTURE
    assert positions[1].underlying == Underlying.EQUITY_INDEX
    assert positions[1].wrapper == Wrapper.FUND


def test_unbekannter_underlying_failt(tmp_path):
    """Unbekannter underlying-Wert → fail-loud (PortfolioError), wie bei direction."""
    path = _write(tmp_path, [{"ticker": "X", "shares": 1, "buy_price": 1,
                               "direction": "long", "underlying": "krypto"}])
    with pytest.raises(PortfolioError):
        JsonPortfolioProvider(path).get_positions()


def test_unbekannter_wrapper_failt(tmp_path):
    """Unbekannter wrapper-Wert → fail-loud (PortfolioError), wie bei direction."""
    path = _write(tmp_path, [{"ticker": "X", "shares": 1, "buy_price": 1,
                               "direction": "long", "underlying": "equity",
                               "wrapper": "hebel"}])
    with pytest.raises(PortfolioError):
        JsonPortfolioProvider(path).get_positions()


def test_tier3_default_no_keys(tmp_path):
    """Tier-3-Default: keine underlying/wrapper/asset_class Schlüssel vorhanden
    → Position nutzt Domain-Defaults: Underlying.EQUITY, Wrapper.SINGLE."""
    path = _write(tmp_path, [{"ticker": "HOLD", "shares": 100, "buy_price": 50, "direction": "long"}])
    positions = JsonPortfolioProvider(path).get_positions()
    assert len(positions) == 1
    assert positions[0].underlying == Underlying.EQUITY
    assert positions[0].wrapper == Wrapper.SINGLE


def test_partial_schema_only_underlying_raises(tmp_path):
    """Tier-1 partiell: nur underlying vorhanden, wrapper fehlend
    → fail-loud mit PortfolioError (beide Achsen müssen gültig sein, wenn eine present ist)."""
    path = _write(tmp_path, [{"ticker": "PART", "shares": 10, "buy_price": 100,
                               "direction": "long", "underlying": "bond"}])
    with pytest.raises(PortfolioError):
        JsonPortfolioProvider(path).get_positions()
