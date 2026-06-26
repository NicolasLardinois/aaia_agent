"""Tests für den Yahoo-Live-Price-Adapter (Spotkurs + FX für den Portfolio-Monitor).

Kein echtes Netz (conftest blockt `yfinance` global): geprüft wird der defensive
Vertrag — ein blockierter/fehlgeschlagener Call liefert `None` (Kurs) bzw. `1.0`
(FX), statt die Portfolio-Analyse abstürzen zu lassen (AGENTS.md §2/§3).
"""
from adapters.data.yahoo_live_price import YahooLivePriceProvider
from core.ports.live_price import LivePriceProvider


def test_implements_port():
    assert isinstance(YahooLivePriceProvider(), LivePriceProvider)


def test_blocked_network_price_is_none():
    # yfinance ist im Test geblockt → Exception → defensiv None (kein Crash).
    assert YahooLivePriceProvider().get_current_price("AAPL") is None


def test_same_currency_fx_is_one_without_network():
    # Gleiche Währung → gar kein Call nötig → 1.0 (Kurzschluss).
    assert YahooLivePriceProvider().get_fx_rate("USD", "USD") == 1.0


def test_blocked_network_fx_defaults_to_one():
    # Fremdwährung, aber Netz geblockt → defensiv 1.0 statt stiller Fehlrechnung.
    assert YahooLivePriceProvider().get_fx_rate("CHF", "USD") == 1.0
