import asyncio
from agents.market_cockpit.macro.buffett_indicator_agent import _signal, _signal_from_z, BuffettIndicatorAgent
from core.domain.models import Signal


def test_none_z_is_neutral():
    assert _signal_from_z(None) == Signal.NEUTRAL


def test_high_z_is_bearish():
    # +1.5σ über eigener Landeshistorie → historisch teuer → BEARISH
    assert _signal_from_z(1.6) == Signal.BEARISH


def test_low_z_is_bullish():
    assert _signal_from_z(-1.6) == Signal.BULLISH


def test_mid_z_is_neutral():
    assert _signal_from_z(0.5) == Signal.NEUTRAL


def test_swiss_high_ratio_with_normal_z_is_neutral():
    # CH bei 230% aber z≈0 (für CH normal) → NICHT BEARISH (kein 135%-Fix mehr)
    assert _signal_from_z(0.1) == Signal.NEUTRAL


# ── _signal-Fallback (länderspezifische Korridore statt global 75/135) ────────

def test_signal_fallback_none_ist_neutral():
    assert _signal(None, "USA") == Signal.NEUTRAL


def test_signal_fallback_usa_korridor():
    # USA-Korridor (75, 135): unter 75 günstig, über 135 teuer.
    assert _signal(70.0, "USA") == Signal.BULLISH
    assert _signal(140.0, "USA") == Signal.BEARISH
    assert _signal(100.0, "USA") == Signal.NEUTRAL


def test_signal_fallback_schweiz_korridor_statt_global():
    """Kern des Fixes: CH ist strukturell hoch (Korridor 150–260). Ein CH-Ratio von
    200 % ist NEUTRAL — unter der alten globalen 135%-Schwelle wäre es fälschlich BEARISH."""
    assert _signal(200.0, "CHE") == Signal.NEUTRAL
    assert _signal(140.0, "CHE") == Signal.BULLISH    # unter dem CH-Korridor → günstig
    assert _signal(270.0, "CHE") == Signal.BEARISH    # über dem CH-Korridor → teuer


def test_signal_fallback_unbekanntes_land_nutzt_default():
    # Unbekannter Code → Default-Korridor (75, 135).
    assert _signal(200.0, "XXX") == Signal.BEARISH
    assert _signal(50.0, "XXX") == Signal.BULLISH


class _FakeWB:
    """Fake-MarketCapToGdpProvider: liefert ein festes Länder-Dict, zählt Aufrufe."""
    def __init__(self, data):
        self._data = data
        self.calls = 0
    def get_market_cap_to_gdp(self):
        self.calls += 1
        return self._data


def test_agent_fallback_nutzt_landeskorridor_bei_kurzer_historie():
    """Agent-Pfad: CH mit zu kurzer Historie (<8 → z=None) fällt auf _signal zurück.
    Mit dem CH-Korridor bleibt 200 % NEUTRAL statt (alt) BEARISH."""
    short_series = [(2019, 195.0), (2020, 198.0), (2021, 202.0), (2022, 200.0)]  # nur 4 → z=None
    wb = _FakeWB({"CHE": (200.0, 2022, short_series, "Switzerland")})
    agent = BuffettIndicatorAgent(_FakeMacro(), _FakeBus(), world_bank=wb)
    result = asyncio.run(agent.run())
    assert result.countries["CHE"].z_score is None         # Fallback-Pfad aktiv
    assert result.countries["CHE"].signal == Signal.NEUTRAL


class _FakeBus:
    def publish(self, event): pass


class _FakeMacro:
    def get_buffett_data(self):
        # Wilshire/GDP → Ratio 150 %
        return {"market_cap_bn": 30000.0, "gdp_bn": 20000.0}
    def get_buffett_history(self, years=10):
        # genug Historie für z-Score (>= 8), Mittel ~100 → 150 ist deutlich darüber
        return [90.0, 95.0, 100.0, 105.0, 110.0, 98.0, 102.0, 99.0, 101.0]


def test_wb_provider_injizierbar_kein_netz():
    """Injizierter WB-Provider (leeres Dict) → kein Netz; USA-Signal entsteht aus FRED-Daten."""
    wb = _FakeWB({})
    agent = BuffettIndicatorAgent(_FakeMacro(), _FakeBus(), world_bank=wb)
    result = asyncio.run(agent.run())
    assert wb.calls == 1                          # der injizierte Provider wurde benutzt
    assert "USA" in result.countries             # USA aus FRED trotz leerer Weltbank
    assert result.countries["USA"].name == "United States"  # Klarname (FRED-Pfad)
    assert result.signal in (Signal.BULLISH, Signal.BEARISH, Signal.NEUTRAL)


def test_ohne_wb_provider_nur_usa_aus_fred():
    """Ohne injizierten Provider (None) macht der Agent KEIN I/O: keine Weltbank-Länder,
    nur USA aus FRED. Verhaltens-erhaltend gegenüber einem leeren Weltbank-Ergebnis."""
    agent = BuffettIndicatorAgent(_FakeMacro(), _FakeBus())
    result = asyncio.run(agent.run())
    assert set(result.countries) == {"USA"}


def test_wb_provider_exception_ist_defensiv():
    """Fällt der Provider aus, liefert der Agent trotzdem ein Ergebnis (nur USA aus FRED)."""
    class _Boom:
        def get_market_cap_to_gdp(self):
            raise RuntimeError("WB down")
    agent = BuffettIndicatorAgent(_FakeMacro(), _FakeBus(), world_bank=_Boom())
    result = asyncio.run(agent.run())
    assert "USA" in result.countries


def test_wb_country_carries_year_value_history():
    """Weltbank-Laender reichen die (Jahr, Ratio)-Serie als history durch — dieselbe
    Serie, aus der der z-Score entsteht. Fuer den Einzelland-10-J-Drilldown."""
    series = [(2015, 90.0), (2016, 95.0), (2017, 100.0), (2018, 105.0), (2019, 110.0),
              (2020, 98.0), (2021, 102.0), (2022, 120.0), (2023, 230.0)]  # >=8 -> z-Score moeglich
    # neue Form: (aktueller_ratio, jahr, [(jahr, ratio), ...] aufsteigend, klarname)
    wb = _FakeWB({"CHE": (230.0, 2023, series, "Switzerland")})
    agent = BuffettIndicatorAgent(_FakeMacro(), _FakeBus(), world_bank=wb)
    result = asyncio.run(agent.run())
    assert result.countries["CHE"].history == series
    assert result.countries["CHE"].year == 2023
    assert result.countries["CHE"].name == "Switzerland"  # Weltbank-Klarname durchgereicht
    # z-Score wird weiter aus den Werten (nicht den Tupeln) berechnet -> Zahl, kein Fehler
    assert isinstance(result.countries["CHE"].z_score, float)
