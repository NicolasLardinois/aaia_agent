"""Anlageklassen-Taxonomie: zwei orthogonale Achsen statt eines überladenen `asset_class`.

`underlying` wählt die Analyse-Engine (WAS treibt P&L?), `wrapper` die Mechanik-Schicht
(WIE gehalten?). Siehe docs/superpowers/specs/2026-06-21-anlageklassen-taxonomie-design.md.
Reine Domäne — keine I/O.
"""
from enum import Enum


class Underlying(str, Enum):
    """Basiswert → wählt die Bottom-Up-Engine."""
    EQUITY         = "equity"          # Einzelaktie (inkl. Rohstoff-/Minenkonzerne)
    EQUITY_INDEX   = "equity_index"    # Aktienindex / Aktien-Sektorkorb (vormals "index")
    BOND           = "bond"
    COMMODITY      = "commodity"       # physischer Rohstoff (Öl, Gas, Agrar, Industriemetall)
    PRECIOUS_METAL = "precious_metal"  # Gold, Silber, Platin, Palladium


class Wrapper(str, Enum):
    """Hülle → schaltet eine Risiko-/Mechanik-Schicht zu (Phase 2)."""
    SINGLE       = "single"        # Einzelwert / direktes Wertpapier
    FUND         = "fund"          # Fonds/ETF (Korb)
    FUTURE       = "future"        # Terminkontrakt (Hebel, Roll, Verfall)
    PHYSICAL_ETC = "physical_etc"  # physisch hinterlegtes Rohstoff-ETC (reiner Spot)


# Alt-String → (underlying, wrapper). Mapping gemäß Spec §5. Behebt den `etf`-Durchfall:
# "etf" wird zu equity_index/fund (Index-Engine), nicht mehr stillschweigend Equity.
_LEGACY_MAP: dict[str, tuple[Underlying, Wrapper]] = {
    "equity":         (Underlying.EQUITY,         Wrapper.SINGLE),
    "etf":            (Underlying.EQUITY_INDEX,   Wrapper.FUND),
    "index":          (Underlying.EQUITY_INDEX,   Wrapper.SINGLE),
    "bond":           (Underlying.BOND,           Wrapper.SINGLE),
    "commodity":      (Underlying.COMMODITY,      Wrapper.FUTURE),
    "precious_metal": (Underlying.PRECIOUS_METAL, Wrapper.FUTURE),
}


def legacy_to_taxonomy(asset_class: str) -> tuple[Underlying, Wrapper]:
    """Alt-`asset_class`-String → (underlying, wrapper). Unbekannt → equity/single (defensiv)."""
    return _LEGACY_MAP.get((asset_class or "").lower(), (Underlying.EQUITY, Wrapper.SINGLE))


def legacy_asset_class(underlying: Underlying, wrapper: Wrapper) -> str:
    """Rück-Abbildung für die Übergangs-Property `BottomUpResult.asset_class`.

    Konvention (eindeutig pro Engine, deckt den Phase-1-Umfang ab):
    equity→"equity", bond→"bond", commodity→"commodity", precious_metal→"precious_metal"
    (Engine ist hüllenunabhängig dieselbe); equity_index→"etf" bei wrapper=fund, sonst "index".
    """
    if underlying == Underlying.EQUITY_INDEX:
        return "etf" if wrapper == Wrapper.FUND else "index"
    return underlying.value
