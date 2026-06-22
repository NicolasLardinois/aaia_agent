"""Regime-Replay: spielt den Top-Down-Regime-Motor Point-in-Time über die Historie durch.
Führt die ECHTEN Sub-Signal-Agenten aus (Treue) und nutzt die geteilte Input-Montage."""
import asyncio

from agents.market_cockpit.macro.money_supply_agent import MoneySupplyAgent
from agents.market_cockpit.macro.credit_agent import CreditAgent
from agents.market_cockpit.macro.labor_income_agent import LaborIncomeAgent
from agents.market_cockpit.macro.buffett_indicator_agent import BuffettIndicatorAgent
from core.domain.regime import RegimeDetector
from core.domain.regime_inputs import assemble_regime_inputs


class _NullBus:
    def publish(self, event): pass


class _NullRegionProvider:
    """Leerer Regional-Provider (EU/CH ohne Daten). Hängt NUR vom Port-Verhalten ab,
    nicht von einem konkreten Adapter (AGENTS.md §1: Agenten importieren keine Adapter).
    Die konkrete Stub-/Historical-Verdrahtung liegt im Composition-Root (app/replay_regime.py).
    Liefert für die einzig genutzten Sub-Signal-Eingaben (M2/M3-Wachstum) None — wie die Stubs."""
    def get_m2_growth(self): return None
    def get_m3_growth(self): return None


# Default-Quellen-Fabrik: leeres Regional-Objekt (EU/CH leer, wie Produktion heute). Region/Quelle
# ist steckbar — ein HistoricalEcbProvider/-SnbProvider ist später ein reiner Drop-in (Spec §4.4).
def _default_region(as_of):
    return _NullRegionProvider()


async def _sub_signals(provider, bus, ecb, snb) -> dict:
    """Führt die vier echten Sub-Signal-Agenten aus (netzfrei: injizierte ECB/SNB, No-Op-WB)."""
    money = MoneySupplyAgent(provider, ecb, snb, bus)
    credit = CreditAgent(provider, bus)
    labor = LaborIncomeAgent(provider, bus)
    buffett = BuffettIndicatorAgent(provider, bus, wb_fetch=lambda: {})
    m, c, l, b = await asyncio.gather(money.run(), credit.run(), labor.run(), buffett.run())
    return {
        "money_supply": m.usa.signal,
        "credit":       c.usa.signal,
        "labor":        l.usa.signal,
        "buffett":      b.signal,
    }


def replay_step(provider, bus, ecb, snb) -> dict:
    """Ein Stichtag: Roh-Zustand + Sub-Signale (ohne Detector — Trend wird außen verwaltet)."""
    economic_state = provider.get_economic_state()
    spreads = provider.get_yield_spreads()
    sub_map = asyncio.run(_sub_signals(provider, bus, ecb, snb))
    return {
        "economic_state": economic_state,
        "usa_10y3m": spreads.get("10y3m"),
        "sub_signal_map": sub_map,
    }


def run_replay(provider_factory, stichtage: list, bus=None,
               ecb_factory=_default_region, snb_factory=_default_region) -> list:
    """Iteriert die Stichtage, pflegt die Composite-Historie, liefert Regime-Urteile.
    ecb_factory/snb_factory(as_of) sind steckbar (Default = Stubs)."""
    bus = bus or _NullBus()
    detector = RegimeDetector()
    history: list = []          # [(iso_date, composite), ...]
    urteile = []
    for as_of in stichtage:
        provider = provider_factory(as_of)
        raw = replay_step(provider, bus, ecb_factory(as_of), snb_factory(as_of))
        state, sub_signals = assemble_regime_inputs(
            raw["economic_state"], raw["usa_10y3m"], {}, {}, raw["sub_signal_map"],
        )
        regime, confidence, evidence = detector.detect(state, sub_signals, history=history)
        # Exakten Composite direkt aus evidence lesen (kein Rundungsfehler durch Rekonstruktion)
        composite = evidence["composite"]
        history = history + [(as_of.isoformat(), composite)]
        urteile.append({
            "as_of": as_of,
            "regime": regime,
            "confidence": confidence,
            "composite": round(composite, 4),
            "trend": evidence.get("trend"),
            "data_quality": getattr(provider, "quality", "unbekannt"),
        })
    return urteile
