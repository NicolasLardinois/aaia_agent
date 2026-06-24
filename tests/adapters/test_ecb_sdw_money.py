"""TDD-Tests fuer ECB-SDW M2/M3 (_fetch_bsi_growth) und _parse_sdmx_last_observation."""
from unittest.mock import patch, MagicMock

from adapters.data.ecb_sdw import EcbSdwProvider, _parse_sdmx_last_observation


def _bsi_payload(value):
    """Spiegelt die ECB-SDMX-JSON-Struktur (eine Reihe, eine Beobachtung)."""
    return {"dataSets": [{"series": {"0:0:0:0:0:0:0:0:0:0": {"observations": {"0": [value]}}}}]}


def _resp(payload):
    r = MagicMock()
    r.raise_for_status.return_value = None
    r.json.return_value = payload
    return r


_GET = "adapters.data.ecb_sdw.requests.get"


# ── _parse_sdmx_last_observation (rein) ────────────────────────────────────
def test_parse_gueltige_beobachtung():
    assert _parse_sdmx_last_observation(_bsi_payload(2.74)) == 2.74


def test_parse_fehlende_struktur_none():
    assert _parse_sdmx_last_observation({}) is None
    assert _parse_sdmx_last_observation({"dataSets": [{"series": {}}]}) is None


def test_parse_nicht_numerisch_none():
    assert _parse_sdmx_last_observation(_bsi_payload("abc")) is None


# ── M3/M2 (gemocktes requests.get) ─────────────────────────────────────────
def test_get_m3_growth_liefert_wert_und_pinnt_m30():
    with patch(_GET, return_value=_resp(_bsi_payload(2.7356))) as m:
        assert EcbSdwProvider().get_m3_growth() == 2.7
    assert "M30" in m.call_args.args[0]


def test_get_m2_growth_liefert_wert_und_pinnt_m20():
    with patch(_GET, return_value=_resp(_bsi_payload(2.8671))) as m:
        assert EcbSdwProvider().get_m2_growth() == 2.9
    assert "M20" in m.call_args.args[0]


def test_get_m3_growth_implausibel_none():
    with patch(_GET, return_value=_resp(_bsi_payload(999.0))):
        assert EcbSdwProvider().get_m3_growth() is None


def test_get_m3_growth_netzfehler_none():
    with patch(_GET, side_effect=ConnectionError("boom")):
        assert EcbSdwProvider().get_m3_growth() is None


def test_get_m3_growth_cap_grenzwerte():
    # Cap ist inklusiv: 50.0 gueltig; -51.0 ausserhalb -> None
    with patch(_GET, return_value=_resp(_bsi_payload(50.0))):
        assert EcbSdwProvider().get_m3_growth() == 50.0
    with patch(_GET, return_value=_resp(_bsi_payload(-51.0))):
        assert EcbSdwProvider().get_m3_growth() is None
