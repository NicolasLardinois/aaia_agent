"""TDD-Tests fuer CnnFearGreedProvider und die reine _parse-Funktion."""
import logging
from unittest.mock import patch, MagicMock

from adapters.data.cnn_fear_greed import CnnFearGreedProvider, _parse


def _payload(score):
    """Spiegelt die verschachtelte CNN-Struktur: data['fear_and_greed']['score']."""
    return {"fear_and_greed": {"score": score, "rating": "neutral"}}


# ── _parse (rein, kein Netz) ───────────────────────────────────────────────
def test_parse_gueltiger_score():
    assert _parse(_payload(42.7)) == 42.7


def test_parse_rundet_auf_eine_stelle():
    assert _parse(_payload(42.66)) == 42.7


def test_parse_grenzen_0_und_100_gueltig():
    assert _parse(_payload(0)) == 0.0
    assert _parse(_payload(100)) == 100.0


def test_parse_ausserhalb_bereich_none():
    assert _parse(_payload(150)) is None
    assert _parse(_payload(-5)) is None


def test_parse_fehlender_key_none():
    assert _parse({}) is None
    assert _parse({"fear_and_greed": {}}) is None


def test_parse_nicht_numerisch_none():
    assert _parse(_payload("abc")) is None
    assert _parse(_payload(None)) is None


# ── Adapter (gemocktes requests.get) ───────────────────────────────────────
def _make_response(payload):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = payload
    return resp


def test_get_fear_greed_liefert_score():
    with patch("adapters.data.cnn_fear_greed.requests.get",
               return_value=_make_response(_payload(63.2))):
        assert CnnFearGreedProvider().get_fear_greed() == 63.2


def test_get_fear_greed_bei_netzfehler_none():
    with patch("adapters.data.cnn_fear_greed.requests.get",
               side_effect=ConnectionError("boom")):
        assert CnnFearGreedProvider().get_fear_greed() is None


def test_get_fear_greed_bei_http_error_none():
    resp = MagicMock()
    resp.raise_for_status.side_effect = Exception("418 Teapot")
    with patch("adapters.data.cnn_fear_greed.requests.get", return_value=resp):
        assert CnnFearGreedProvider().get_fear_greed() is None


# ── Logging: inoffiziellen Endpoint bei Ausfall beobachtbar machen ──────────
_LOGGER = "adapters.data.cnn_fear_greed"


def test_get_fear_greed_loggt_warnung_bei_netzfehler(caplog):
    """Netz-/HTTP-Fehler → WARNING, damit ein dauerhafter Bruch nicht still bleibt."""
    with patch("adapters.data.cnn_fear_greed.requests.get",
               side_effect=ConnectionError("boom")):
        with caplog.at_level(logging.WARNING, logger=_LOGGER):
            assert CnnFearGreedProvider().get_fear_greed() is None
    assert any(r.levelno == logging.WARNING and r.name == _LOGGER for r in caplog.records)


def test_get_fear_greed_loggt_warnung_bei_unplausibler_antwort(caplog):
    """Erfolgreicher Fetch, aber Struktur passt nicht → _parse=None → WARNING (Strukturbruch)."""
    with patch("adapters.data.cnn_fear_greed.requests.get",
               return_value=_make_response({"unerwartet": True})):
        with caplog.at_level(logging.WARNING, logger=_LOGGER):
            assert CnnFearGreedProvider().get_fear_greed() is None
    assert any(r.levelno == logging.WARNING and r.name == _LOGGER for r in caplog.records)

