"""TDD-Tests für die CH-Makro-Methoden des FredSnbProvider (Slice A).

Verifizierte Quellen:
- M2/M3-Wachstum, Bilanzwachstum, CPI  → data.snb.ch (Cubes snbmonagg, snbbipo, plkopr)
- BIP-Wachstum, 10J-Rendite            → FRED (CLVMNACSCAB1GQCH, IRLTLT01CHM156N)

Reine Parser-/Mathe-Helfer werden separat getestet; die Provider-Methoden mit
gemocktem requests.get bzw. fred.get_series (offline-sicher).
"""
from unittest.mock import MagicMock, patch

import pandas as pd

from adapters.data.fred_snb import (
    FredSnbProvider,
    _parse_snb_csv,
    _latest_match,
    _yoy_from_levels,
    _yoy_pct,
)

_GET = "adapters.data.fred_snb.requests.get"


# ── CSV-Samples (gespiegelte data.snb.ch-Struktur) ──────────────────────────
# snbmonagg: 4 Spalten (Date;D0;D1;Value); D0=VV → YoY-Wachstum, D1=GM2/GM3
_MONAGG_CSV = (
    '"CubeId";"snbmonagg"\r\n'
    '"PublishingDate";"2026-06-22 09:00"\r\n'
    "\r\n"
    '"Date";"D0";"D1";"Value"\r\n'
    '"2026-04";"VV";"GM2";"9.5"\r\n'
    '"2026-04";"VV";"GM3";"4.4"\r\n'
    '"2026-05";"B";"GM3";"253000"\r\n'
    '"2026-05";"VV";"GM2";"9.68966193"\r\n'
    '"2026-05";"VV";"GM3";"4.49074212"\r\n'
)

# plkopr: 3 Spalten (Date;D0;Value); D0=VVP → CPI YoY in %
_CPI_CSV = (
    '"CubeId";"plkopr"\r\n'
    '"PublishingDate";"2026-06-22 09:00"\r\n'
    "\r\n"
    '"Date";"D0";"Value"\r\n'
    '"2026-04";"LD2010100";"101.1045"\r\n'
    '"2026-04";"VVP";"0.60189294"\r\n'
    '"2026-05";"LD2010100";"101.2587"\r\n'
    '"2026-05";"VVP";"0.61586524"\r\n'
)

# snbbipo: 3 Spalten (Date;D0;Value); D0=T0 → Bilanzsumme (Niveau, CHF Mio.)
_BIPO_CSV = (
    '"CubeId";"snbbipo"\r\n'
    '"PublishingDate";"2026-05-29 09:00"\r\n'
    "\r\n"
    '"Date";"D0";"Value"\r\n'
    '"2025-04";"T0";"800000"\r\n'
    '"2025-04";"D";"49328.4"\r\n'
    '"2026-04";"T0";"889600"\r\n'
    '"2026-04";"D";"50000"\r\n'
)


def _provider():
    """FredSnbProvider ohne __init__ (kein echter Fred-Client nötig)."""
    return FredSnbProvider.__new__(FredSnbProvider)


def _resp(text):
    r = MagicMock()
    r.text = text
    r.raise_for_status = MagicMock()
    return r


# ── reine Helfer ────────────────────────────────────────────────────────────
def test_parse_snb_csv_findet_header_4_spalten():
    rows = _parse_snb_csv(_MONAGG_CSV)
    assert {"Date", "D0", "D1", "Value"} <= set(rows[0].keys())
    assert any(r["D1"] == "GM3" and r["D0"] == "VV" for r in rows)


def test_parse_snb_csv_findet_header_3_spalten():
    rows = _parse_snb_csv(_CPI_CSV)
    assert {"Date", "D0", "Value"} <= set(rows[0].keys())


def test_latest_match_neueste_zeile_mit_filtern():
    rows = _parse_snb_csv(_MONAGG_CSV)
    assert _latest_match(rows, {"D0": "VV", "D1": "GM3"}) == ("2026-05", 4.49074212)


def test_latest_match_keine_treffer_none():
    rows = _parse_snb_csv(_MONAGG_CSV)
    assert _latest_match(rows, {"D0": "VV", "D1": "GMX"}) is None


def test_yoy_from_levels_rechnet_jahresveraenderung():
    rows = _parse_snb_csv(_BIPO_CSV)
    # (889600 / 800000 - 1) * 100 = 11.2
    assert _yoy_from_levels(rows, {"D0": "T0"}) == 11.2


def test_yoy_from_levels_ohne_vorjahrespunkt_none():
    rows = _parse_snb_csv(_CPI_CSV)  # keine 12-Monats-Distanz für VVP
    assert _yoy_from_levels(rows, {"D0": "VVP"}) is None


def test_yoy_pct_quartalsreihe():
    # 5 Quartale: letztes vs. 4 Quartale zurück → YoY
    assert _yoy_pct([100.0, 101, 102, 103, 104.0], lag=4) == 4.0


def test_yoy_pct_zu_kurz_none():
    assert _yoy_pct([100.0, 101.0], lag=4) is None


# ── Provider-Methoden: data.snb.ch (gemocktes requests.get) ─────────────────
def test_get_m3_growth_pinnt_vv_gm3():
    with patch(_GET, return_value=_resp(_MONAGG_CSV)):
        assert _provider().get_m3_growth() == 4.5  # round(4.4907, 1)


def test_get_m2_growth_pinnt_vv_gm2():
    with patch(_GET, return_value=_resp(_MONAGG_CSV)):
        assert _provider().get_m2_growth() == 9.7  # round(9.6897, 1)


def test_get_cpi_pinnt_vvp():
    with patch(_GET, return_value=_resp(_CPI_CSV)):
        assert _provider().get_cpi() == 0.6  # round(0.6159, 1)


def test_get_balance_sheet_growth_yoy_aus_t0():
    with patch(_GET, return_value=_resp(_BIPO_CSV)):
        assert _provider().get_balance_sheet_growth() == 11.2


def test_snb_methoden_netzfehler_none():
    with patch(_GET, side_effect=ConnectionError("boom")):
        p = _provider()
        assert p.get_m3_growth() is None
        assert p.get_m2_growth() is None
        assert p.get_cpi() is None
        assert p.get_balance_sheet_growth() is None


def test_get_m3_growth_implausibel_none():
    bad = _MONAGG_CSV.replace('"4.49074212"', '"999.0"')
    with patch(_GET, return_value=_resp(bad)):
        assert _provider().get_m3_growth() is None


# ── Provider-Methoden: FRED (gemocktes fred.get_series) ─────────────────────
def test_get_gdp_growth_yoy_aus_fred_levels():
    p = _provider()
    p.fred = MagicMock()
    # reales BIP-Niveau, quartalsweise; letztes/4-zurück → YoY
    p.fred.get_series.return_value = pd.Series(
        [200000.0, 201000, 202000, 203000, 206000.0]
    )
    # (206000 / 200000 - 1) * 100 = 3.0
    assert p.get_gdp_growth() == 3.0


def test_get_sovereign_yield_10y_aus_fred():
    p = _provider()
    p.fred = MagicMock()
    p.fred.get_series.return_value = pd.Series([0.41, 0.43, 0.44])
    assert p.get_sovereign_yield_10y() == 0.44


def test_fred_methoden_fehler_none():
    p = _provider()
    p.fred = MagicMock()
    p.fred.get_series.side_effect = Exception("net")
    assert p.get_gdp_growth() is None
    assert p.get_sovereign_yield_10y() is None


# ── Slice-B-Methoden bleiben sauber None (BFS/SECO/2Y noch nicht angebunden) ─
def test_slice_b_methoden_none():
    p = _provider()
    assert p.get_core_cpi() is None
    assert p.get_unemployment() is None
    assert p.get_sovereign_yield_2y() is None
