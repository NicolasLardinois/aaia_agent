"""EquityMomentumAgent — technisches Momentum für Einzelaktien.

Misst drei Dimensionen:
  1. Trend-Status: MA50 vs. MA200 (Golden/Death Cross)
  2. RSI-14 nach Wilder-Smoothing (Überkauf/Überverkauf)
  3. Relative Stärke: Titel-Return − Heimatmarkt-Return (Dezimal, rs < 0 = schwächer)

Der Heimatmarkt-Benchmark wird aus `country` der get_info-Antwort abgeleitet.
Bekannte Länder → landesspezifischer Index; unbekannte → ^GSPC (S&P 500) als Fallback.

Signal-Logik: siehe core.utils.momentum.momentum_signal (geteilte Pure Function).
"""
import asyncio
import math

from core.domain.events import EquityMomentumReady
from core.domain.models import MomentumSnapshot, Signal
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus
from core.utils.momentum import detect_crossover, momentum_signal
from core.utils.scoring import wilder_rsi

# ─── Benchmark-Karte: Land → Heimatmarkt-Index ────────────────────────────────
# USA → S&P 500; Schweiz → SMI; Eurozone-Länder → EURO STOXX 50.
# Alle anderen → S&P 500 als globaler Fallback.
_BENCHMARK_BY_COUNTRY: dict[str, str] = {
    # Nordamerika
    "United States": "^GSPC",
    # Schweiz (eigener nicht-EU-Markt)
    "Switzerland": "^SSMI",
    # Eurozone-Kernländer → EURO STOXX 50
    "Germany":     "^STOXX50E",
    "France":      "^STOXX50E",
    "Italy":       "^STOXX50E",
    "Spain":       "^STOXX50E",
    "Netherlands": "^STOXX50E",
    "Austria":     "^STOXX50E",
    "Belgium":     "^STOXX50E",
    "Portugal":    "^STOXX50E",
    "Finland":     "^STOXX50E",
    "Ireland":     "^STOXX50E",
    "Greece":      "^STOXX50E",
}

_DEFAULT_BENCHMARK = "^GSPC"   # S&P 500 als globaler Fallback

_HISTORY_PERIOD = "2y"         # MA200 braucht ≥ 200 Handelstage; 2y gibt Puffer


def _benchmark_for(country: str | None) -> str:
    """Gibt den passenden Benchmark-Index für ein Land zurück.

    Nicht erkannte Länder oder None → ^GSPC (S&P 500) als Fallback.
    """
    if country is None:
        return _DEFAULT_BENCHMARK
    return _BENCHMARK_BY_COUNTRY.get(country, _DEFAULT_BENCHMARK)


_DEFAULT = MomentumSnapshot(
    rsi_14=None, ma50=None, ma200=None,
    golden_cross=None, relative_strength=None,
    signal=Signal.NEUTRAL,
)


class EquityMomentumAgent:
    def __init__(self, market: MarketDataProvider, bus: EventBus):
        self.market = market
        self.bus    = bus

    async def run(self, ticker: str) -> MomentumSnapshot:
        # Defensiv: get_info-Fehler → country = None → Fallback-Benchmark.
        # get_info ist ein blockierender Netz-Call (yf.Ticker(...).info) → in
        # asyncio.to_thread auslagern, sonst blockiert er die Event-Loop und
        # serialisiert die parallel laufenden Equity-Sub-Agenten (AGENTS.md §2).
        try:
            info    = await asyncio.to_thread(self.market.get_info, ticker) or {}
            country = info.get("country")
        except Exception:
            country = None

        benchmark = _benchmark_for(country)

        try:
            hist, bench = await asyncio.gather(
                asyncio.to_thread(self.market.get_price_history, ticker, _HISTORY_PERIOD),
                asyncio.to_thread(self.market.get_price_history, benchmark, _HISTORY_PERIOD),
                return_exceptions=True,
            )

            # Titel-Daten nicht verfügbar → Default (Benchmark-Fehler ist tolerierbar)
            if isinstance(hist, Exception):
                self.bus.publish(
                    EquityMomentumReady(source="equity_momentum_agent", payload={"ticker": ticker})
                )
                return _DEFAULT

            close   = hist["Close"]
            ma50_s  = close.rolling(50).mean()
            ma200_s = close.rolling(200).mean()

            _ma50_raw  = float(ma50_s.iloc[-1])
            _ma200_raw = float(ma200_s.iloc[-1])
            # NaN (zu wenig Bars, z.B. < 200 Handelstage) → None, damit
            # momentum_signal korrekt NEUTRAL zurückgibt statt mit NaN zu rechnen.
            ma50  = None if math.isnan(_ma50_raw)  else round(_ma50_raw,  2)
            ma200 = None if math.isnan(_ma200_raw) else round(_ma200_raw, 2)

            rsi    = wilder_rsi(close)
            # golden_cross ist ein Diagnose-/Anzeigefeld (Golden/Death Cross der
            # letzten Tage). Es fliesst BEWUSST NICHT ins Signal — das nutzt den
            # Trend-STATUS (ma50 vs ma200) + RSI. Den Cross-EVENT zusaetzlich zu
            # gewichten waere eine eigene fachliche Entscheidung (eigene Spec).
            golden = detect_crossover(ma50_s, ma200_s)

            # Relative Stärke: Titel-Return − Benchmark-Return als DEZIMAL
            # (0.10 = +10 %, NICHT Prozent wie IndexMomentumSnapshot.relative_strength).
            # Positiv = Titel schlägt seinen Heimatmarkt; negativ = Underperformance.
            # Auf dem GEMEINSAMEN Datumsbereich rechnen: Titel- und Benchmark-
            # Historie haben oft versetzte Startdaten/Handelstage (anderer Börsen-
            # kalender, junges Listing) — sonst verglichen wir versetzte Fenster.
            rs = None
            if not isinstance(bench, Exception):
                bc     = bench["Close"]
                common = close.index.intersection(bc.index).sort_values()
                if len(common) >= 2:
                    tc        = close.loc[common]
                    bcc       = bc.loc[common]
                    t_ret     = (tc.iloc[-1]  - tc.iloc[0])  / tc.iloc[0]
                    b_ret     = (bcc.iloc[-1] - bcc.iloc[0]) / bcc.iloc[0]
                    rs = round(float(t_ret - b_ret), 4)

            result = MomentumSnapshot(
                rsi_14=rsi, ma50=ma50, ma200=ma200,
                golden_cross=golden, relative_strength=rs,
                signal=momentum_signal(ma50, ma200, rsi),
            )
        except Exception:
            self.bus.publish(
                EquityMomentumReady(source="equity_momentum_agent", payload={"ticker": ticker})
            )
            return _DEFAULT

        self.bus.publish(
            EquityMomentumReady(source="equity_momentum_agent", payload={"ticker": ticker})
        )
        return result

    @staticmethod
    def default() -> MomentumSnapshot:
        return _DEFAULT
