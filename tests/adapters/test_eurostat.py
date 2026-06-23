"""TDD-Tests fuer den Eurostat-Adapter (EurostatEcbProvider) und _parse_jsonstat_latest."""
from unittest.mock import patch, MagicMock

from adapters.data.eurostat import _parse_jsonstat_latest


# ── _parse_jsonstat_latest (rein, kein Netz) ───────────────────────────────
def test_parse_nimmt_groessten_integer_key():
    # value-Keys sind Positions-Indizes; die juengste BEFUELLTE Beobachtung
    # hat den groessten Key. "5" (juengste Periode) fehlt absichtlich (unveroeffentlicht).
    data = {"value": {"0": -2.1, "1": -2.2, "4": 4.9}}
    assert _parse_jsonstat_latest(data) == 4.9


def test_parse_einzelne_beobachtung():
    assert _parse_jsonstat_latest({"value": {"0": 2.0}}) == 2.0


def test_parse_leeres_value_none():
    assert _parse_jsonstat_latest({"value": {}}) is None


def test_parse_fehlendes_value_none():
    assert _parse_jsonstat_latest({}) is None
    assert _parse_jsonstat_latest({"value": None}) is None


def test_parse_nicht_numerisch_none():
    assert _parse_jsonstat_latest({"value": {"0": "abc"}}) is None
