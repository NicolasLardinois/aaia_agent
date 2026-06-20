import asyncio
from unittest.mock import MagicMock
from core.domain.portfolio import Position
from agents.portfolio.portfolio_monitor_agent import PortfolioMonitorAgent, _check_cluster_risks


def _make_memory(last_recs: dict = None):
    memory = MagicMock()
    if last_recs:
        def load_history(ticker, days=90):
            if ticker in last_recs:
                v = last_recs[ticker]
                # str → Long-Aktion (Spalte "recommendation"); dict → ganze History-Zeile
                # (z. B. {"short_action": "COVER"}), wie sie supabase_memory.load_history liefert.
                return [v if isinstance(v, dict) else {"recommendation": v}]
            return []
        memory.load_history.side_effect = load_history
    else:
        memory.load_history.return_value = []
    return memory


def _make_port(positions: list) -> MagicMock:
    port = MagicMock()
    port.get_positions.return_value = positions
    return port


def _pos(ticker, shares, entry_price, current_price, direction="long",
          sector="Technology", asset_class="equity", country="USA", currency="USD"):
    return Position(
        ticker=ticker, shares=shares, entry_price=entry_price,
        direction=direction, currency=currency, current_price=current_price,
        sector=sector, asset_class=asset_class, country=country,
    )


# ---------------------------------------------------------------------------
# Existing tests — adapted for Position objects + injected portfolio_port
# ---------------------------------------------------------------------------

def test_empty_portfolio_skips():
    agent = PortfolioMonitorAgent(_make_memory(), portfolio_port=_make_port([]), fx_rate=lambda a, b: 1.0)
    result = agent._evaluate_positions([])
    assert result["overall_health"] == "green"
    assert result["total_positions"] == 0
    assert result["alerts"] == []


def test_sector_cluster_risk():
    positions = [
        _pos("AAPL", 10, 100, 110, sector="Technology"),
        _pos("MSFT", 10, 100, 110, sector="Technology"),
        _pos("NVDA",  2, 100, 110, sector="Technology"),
    ]
    gross = sum(p.shares * p.current_price for p in positions)
    values = [p.shares * p.current_price for p in positions]
    risks = _check_cluster_risks(positions, values, gross)
    sector_risk = [r for r in risks if r["type"] == "sector"]
    assert len(sector_risk) == 1
    assert sector_risk[0]["name"] == "Technology"


def test_loss_alert():
    positions = [
        _pos("AAPL", 10, 200, 160, direction="long"),
    ]
    agent = PortfolioMonitorAgent(
        _make_memory(), portfolio_port=_make_port(positions), fx_rate=lambda a, b: 1.0
    )
    result = agent._evaluate_positions(positions)
    loss_alerts = [a for a in result["alerts"] if "Verlust" in a]
    assert len(loss_alerts) == 1


def test_health_green_no_alerts():
    # Asset-Klassen diversifiziert: equity ~36%, bond ~57%, commodity ~7%
    # keine Klasse > 60% → kein ASSET_CLASS-Klumpenrisiko nach verschärfter Schwelle
    positions = [
        _pos("AAPL", 5, 150, 160, sector="Technology",    asset_class="equity",    country="USA"),
        _pos("JNJ",  5, 150, 155, sector="Healthcare",    asset_class="bond",      country="Canada"),
        _pos("GLD",  2, 150, 155, sector="Commodities",   asset_class="commodity", country="USA"),
        _pos("BUND", 3, 100, 105, sector="Fixed Income",  asset_class="bond",      country="Germany"),
    ]
    agent = PortfolioMonitorAgent(
        _make_memory(), portfolio_port=_make_port(positions), fx_rate=lambda a, b: 1.0
    )
    result = agent._evaluate_positions(positions)
    assert result["overall_health"] == "green"


def test_fx_conversion_applied_to_total_value():
    positions = [
        _pos("NESN.SW", 10, 100, 100, sector="Staples", asset_class="equity", country="CH", currency="CHF"),
    ]
    # 1 CHF = 1.10 USD → total_value_usd = 10*100*1.10 = 1100
    agent = PortfolioMonitorAgent(
        _make_memory(),
        portfolio_port=_make_port(positions),
        fx_rate=lambda frm, to: 1.10 if frm == "CHF" else 1.0,
    )
    result = agent._evaluate_positions(positions)
    assert result["total_value_usd"] == 1100.0


def test_concentration_herfindahl_field_present():
    positions = [
        _pos("AAPL", 10, 100, 100, sector="Technology"),
        _pos("MSFT", 10, 100, 100, sector="Technology"),
    ]
    agent = PortfolioMonitorAgent(
        _make_memory(), portfolio_port=_make_port(positions), fx_rate=lambda a, b: 1.0
    )
    result = agent._evaluate_positions(positions)
    assert "concentration_hhi" in result
    # zwei gleich große Positionen → HHI = 0.5
    assert abs(result["concentration_hhi"] - 0.5) < 1e-9


def test_portfolio_volatility_and_maxdd_fields():
    positions = [
        _pos("AAPL", 10, 100, 110),
    ]
    agent = PortfolioMonitorAgent(
        _make_memory(),
        portfolio_port=_make_port(positions),
        fx_rate=lambda a, b: 1.0,
        returns_provider=lambda ticker: [0.01, -0.02, 0.015, -0.01, 0.005],
    )
    result = agent._evaluate_positions(positions)
    assert "portfolio_volatility" in result
    assert "portfolio_max_drawdown" in result
    assert result["portfolio_max_drawdown"] <= 0.0


# ---------------------------------------------------------------------------
# NEW tests — Short-P&L, Pairtrade, Exposure-Felder
# ---------------------------------------------------------------------------

def test_short_pnl_loss_alert():
    """Short bei Einstand 100, current 130 → Verlust ~-30% → Verlust-Alert."""
    positions = [
        _pos("XYZ", 10, 100, 130, direction="short"),
    ]
    agent = PortfolioMonitorAgent(
        _make_memory(), portfolio_port=_make_port(positions), fx_rate=lambda a, b: 1.0
    )
    result = agent._evaluate_positions(positions)
    loss_alerts = [a for a in result["alerts"] if "Verlust" in a and "XYZ" in a]
    assert len(loss_alerts) == 1, f"Erwartet 1 Verlust-Alert für Short, got: {result['alerts']}"


def test_pairtrade_no_cluster_alarm():
    """Long A (Tech, Wert 100) + Short B (Tech, Wert 100) → net_exposure ≈ 0, KEIN Klumpen-Alarm."""
    positions = [
        _pos("LONG_A",  1, 100, 100, direction="long",  sector="Technology"),
        _pos("SHORT_B", 1, 100, 100, direction="short", sector="Technology"),
    ]
    agent = PortfolioMonitorAgent(
        _make_memory(), portfolio_port=_make_port(positions), fx_rate=lambda a, b: 1.0
    )
    result = agent._evaluate_positions(positions)
    # Netto-Exposure ≈ 0
    assert result["net_exposure"] == 0.0, f"net_exposure sollte 0 sein, ist {result['net_exposure']}"
    # Brutto-Exposure > 0
    assert result["gross_exposure"] > 0, "gross_exposure sollte > 0 sein"
    # Kein Klumpen-Alarm für Sektor (netto nettet sich aus)
    cluster_alerts = [a for a in result["alerts"] if "Klumpenrisiko" in a and "Sector" in a]
    assert len(cluster_alerts) == 0, f"Kein Sektor-Klumpen-Alarm erwartet, got: {result['alerts']}"


def test_exposure_fields_present():
    """Snapshot enthält long_value, short_value, net_exposure, gross_exposure."""
    positions = [
        _pos("AAPL", 5, 100, 100, direction="long"),
        _pos("SPY",  2, 100, 100, direction="short"),
    ]
    agent = PortfolioMonitorAgent(
        _make_memory(), portfolio_port=_make_port(positions), fx_rate=lambda a, b: 1.0
    )
    result = agent._evaluate_positions(positions)
    for field in ("long_value", "short_value", "net_exposure", "gross_exposure"):
        assert field in result, f"Feld '{field}' fehlt im Snapshot"
    assert result["long_value"] == 500.0
    assert result["short_value"] == 200.0
    assert result["net_exposure"] == 300.0
    assert result["gross_exposure"] == 700.0


# ---------------------------------------------------------------------------
# Alignment-Warnung richtungs-bewusst UND an echte Persistenz gekoppelt:
#   long  liest die Long-Aktion (Spalte "recommendation") → Fehlausrichtung = SELL
#   short liest die Short-Aktion (Spalte "short_action")   → Fehlausrichtung = COVER
# (Die Long-Linse deferiert bei Short auf NONE, daher MUSS die Short-Warnung am
#  separat persistierten short_action hängen, nicht am recommendation-Feld.)
# ---------------------------------------------------------------------------

def test_long_with_sell_rec_triggers_alignment_warning():
    """Long + letzte Long-Aktion SELL → Fehlausrichtung → Alignment-Warnung (Regression)."""
    positions = [_pos("AAPL", 10, 100, 100, direction="long")]
    agent = PortfolioMonitorAgent(
        _make_memory({"AAPL": "SELL"}), portfolio_port=_make_port(positions),
        fx_rate=lambda a, b: 1.0,
    )
    result = agent._evaluate_positions(positions)
    align = [a for a in result["alerts"] if "Alignment" in a]
    assert len(align) == 1, f"Erwartet 1 Alignment-Warnung, got: {result['alerts']}"


def test_long_with_short_rec_no_alignment_warning():
    """Long + 'recommendation'=SHORT → vestigial (wird nie ausgegeben) → KEINE Warnung."""
    positions = [_pos("AAPL", 10, 100, 100, direction="long")]
    agent = PortfolioMonitorAgent(
        _make_memory({"AAPL": "SHORT"}), portfolio_port=_make_port(positions),
        fx_rate=lambda a, b: 1.0,
    )
    result = agent._evaluate_positions(positions)
    align = [a for a in result["alerts"] if "Alignment" in a]
    assert align == [], f"SHORT ist vestigial — keine Warnung erwartet, got: {result['alerts']}"


def test_short_with_cover_action_triggers_alignment_warning():
    """Short + persistierte short_action=COVER → Fehlausrichtung (Engine will eindecken) → Warnung."""
    positions = [_pos("XYZ", 10, 100, 100, direction="short")]
    agent = PortfolioMonitorAgent(
        _make_memory({"XYZ": {"short_action": "COVER"}}), portfolio_port=_make_port(positions),
        fx_rate=lambda a, b: 1.0,
    )
    result = agent._evaluate_positions(positions)
    align = [a for a in result["alerts"] if "Alignment" in a]
    assert len(align) == 1, f"Erwartet 1 Alignment-Warnung (Short+COVER), got: {result['alerts']}"


def test_short_with_hold_action_no_alignment_warning():
    """Short + persistierte short_action=HOLD → ausgerichtet → KEINE Warnung."""
    positions = [_pos("XYZ", 10, 100, 100, direction="short")]
    agent = PortfolioMonitorAgent(
        _make_memory({"XYZ": {"short_action": "HOLD"}}), portfolio_port=_make_port(positions),
        fx_rate=lambda a, b: 1.0,
    )
    result = agent._evaluate_positions(positions)
    align = [a for a in result["alerts"] if "Alignment" in a]
    assert align == [], f"Short+HOLD ist ausgerichtet — keine Warnung erwartet, got: {result['alerts']}"


# ---------------------------------------------------------------------------
# F4 — run() weist Netto- UND Brutto-Exposure getrennt aus (statt mehrdeutiger 'Wert'-Zeile)
# ---------------------------------------------------------------------------

def test_run_prints_net_and_gross_exposure(capsys):
    positions = [
        _pos("AAPL", 5, 100, 100, direction="long"),   # long  500
        _pos("SPY",  2, 100, 100, direction="short"),  # short 200
    ]
    agent = PortfolioMonitorAgent(
        _make_memory(), portfolio_port=_make_port(positions), fx_rate=lambda a, b: 1.0,
    )
    asyncio.run(agent.run())
    out = capsys.readouterr().out
    assert "Netto" in out, f"Netto-Exposure fehlt in Ausgabe: {out!r}"
    assert "Brutto" in out, f"Brutto-Exposure fehlt in Ausgabe: {out!r}"
    assert "300" in out, f"Netto-Wert 300 fehlt in Ausgabe: {out!r}"   # net  = 500 - 200
    assert "700" in out, f"Brutto-Wert 700 fehlt in Ausgabe: {out!r}"  # gross = 500 + 200


# ---------------------------------------------------------------------------
# net_beta pro Region
# ---------------------------------------------------------------------------

def _market(betas):
    m = MagicMock()
    m.get_info.side_effect = lambda t: {"beta": betas.get(t)}
    return m


def _agent_mp(positions, betas):
    port = MagicMock()
    port.get_positions.return_value = positions
    return PortfolioMonitorAgent(
        MagicMock(), portfolio_port=port,
        market_provider=_market(betas), fx_rate=lambda a, b: 1.0)


def test_net_beta_signed_and_beta_weighted():
    # SPY long  100 shares * $100 = $10 000, beta=1.0  → +10 000
    # TSLA short 100 shares * $100 = $10 000, beta=1.8  → -18 000
    # net_beta USA = 10 000 - 18 000 = -8 000 → round(..., 0) = -8000
    positions = [_pos("SPY",  100, 100, 100, direction="long",  sector="Index"),
                 _pos("TSLA", 100, 100, 100, direction="short", sector="Auto")]
    snap = _agent_mp(positions, {"SPY": 1.0, "TSLA": 1.8})._evaluate_positions(positions)
    assert round(snap["net_beta"]["USA"], 0) == -8000


def test_net_beta_missing_beta_defaults_one():
    # beta=None → defaults to 1.0; 100 shares * $100 * 1.0 = 10 000
    positions = [_pos("X", 100, 100, 100, direction="long")]
    snap = _agent_mp(positions, {"X": None})._evaluate_positions(positions)
    assert snap["net_beta"]["USA"] == 10000.0


def test_net_beta_per_region_split():
    from core.domain.portfolio import Position
    positions = [
        _pos("US1", 10, 10, 10, direction="long", country="USA"),
        Position(ticker="CH1", shares=10, entry_price=10, direction="long",
                 current_price=10, sector="Pharma", asset_class="equity", country="CH"),
    ]
    snap = _agent_mp(positions, {"US1": 1.0, "CH1": 1.0})._evaluate_positions(positions)
    assert set(snap["net_beta"].keys()) == {"USA", "CH"}
