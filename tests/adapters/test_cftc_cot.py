"""TDD: CFTC-COT-Adapter (CftcCotProvider) — Disaggregated Managed Money via Socrata."""
from unittest.mock import MagicMock, patch

from adapters.data.cftc_cot import CftcCotProvider, _parse_row, _CONTRACT

_GET = "adapters.data.cftc_cot.requests.get"


def _row(date, long, short, oi):
    return {
        "report_date_as_yyyy_mm_dd": f"{date}T00:00:00.000",
        "m_money_positions_long_all": str(long),
        "m_money_positions_short_all": str(short),
        "open_interest_all": str(oi),
    }


def _resp(rows):
    r = MagicMock()
    r.raise_for_status.return_value = None
    r.json.return_value = rows
    return r


# ── _parse_row (rein) ───────────────────────────────────────────────────────
def test_parse_row_net_long_minus_short():
    p = _parse_row(_row("2026-06-16", 128043, 14322, 339330))
    assert p == {"date": "2026-06-16", "managed_money_net": 113721.0, "open_interest": 339330.0}


def test_parse_row_unvollstaendig_none():
    assert _parse_row({"report_date_as_yyyy_mm_dd": "2026-06-16T00:00:00.000"}) is None
    assert _parse_row({}) is None


def test_parse_row_nicht_numerisch_none():
    assert _parse_row(_row("2026-06-16", "x", 1, 2)) is None


# ── Mapping (verifizierte Hauptkontrakte) ───────────────────────────────────
def test_mapping_enthaelt_kernkontrakte():
    assert _CONTRACT["GC=F"] == "GOLD - COMMODITY EXCHANGE INC."
    assert _CONTRACT["NG=F"] == "NAT GAS NYME - NEW YORK MERCANTILE EXCHANGE"  # Henry Hub NYMEX, nicht ICE
    assert _CONTRACT["CL=F"] == "WTI-PHYSICAL - NEW YORK MERCANTILE EXCHANGE"


# ── get_cot_history ─────────────────────────────────────────────────────────
def test_get_cot_history_sortiert_aelteste_zuerst_und_nutzt_kontraktnamen():
    rows = [_row("2026-06-16", 130, 10, 1000), _row("2026-06-09", 120, 20, 900)]
    with patch(_GET, return_value=_resp(rows)) as m:
        out = CftcCotProvider().get_cot_history("GC=F", 3)
    assert [h["date"] for h in out] == ["2026-06-09", "2026-06-16"]   # aufsteigend
    assert out[-1]["managed_money_net"] == 120.0
    # Hauptkontrakt landet im $where-Filter
    assert "GOLD - COMMODITY EXCHANGE INC." in str(m.call_args.kwargs["params"]["$where"])


def test_get_cot_history_unbekannter_ticker_leer():
    with patch(_GET) as m:
        assert CftcCotProvider().get_cot_history("UNKNOWN", 3) == []
    m.assert_not_called()   # kein Netzaufruf für unbekannten Ticker


def test_get_cot_history_netzfehler_leer():
    with patch(_GET, side_effect=ConnectionError("boom")):
        assert CftcCotProvider().get_cot_history("GC=F", 3) == []
