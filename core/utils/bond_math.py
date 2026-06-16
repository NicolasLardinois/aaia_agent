"""Bond-Pricing-Engine (framework-frei, deterministisch).

Einheiten-Konvention:
- Preise: % vom Nennwert (face=100). clean=quotiert, dirty=clean+accrued.
- Renditen/YTM/Yields: Dezimal (0.05 == 5 %).
- periods: Restlaufzeit in Jahren; Kuponperioden = round(periods*freq).
- Kupon je Periode = coupon_rate/freq * face.
- DV01: Geldwertänderung per 1 bp, per 100 Nominal, auf Dirty Price.
"""
from __future__ import annotations


def _cashflows(face: float, coupon_rate: float, periods: float, freq: int) -> list[float]:
    if freq <= 0:
        raise ValueError(f"freq must be positive, got {freq}")
    n = max(1, round(periods * freq))
    cpn = coupon_rate / freq * face
    cf = [cpn] * n
    cf[-1] += face  # Rückzahlung des Nennwerts in der letzten Periode
    return cf


def bond_price(y: float, face: float, coupon_rate: float, periods: float, freq: int = 2) -> float:
    """Barwert (dirty) der Cashflows bei periodischem Yield y (p.a., Dezimal)."""
    cf = _cashflows(face, coupon_rate, periods, freq)
    per = y / freq
    return sum(c / (1.0 + per) ** (i + 1) for i, c in enumerate(cf))


def ytm(price: float, face: float, coupon_rate: float, periods: float, freq: int = 2) -> float:
    """Yield-to-Maturity via Bisektion über bond_price(y) == price.

    price ist der bewertungsrelevante (dirty) Preis. Robuste Nullstellensuche
    ohne Ableitung: Suchintervall [-0.99, 1.0] (−99 %..+100 % p.a.).
    """
    if price <= 0:
        raise ValueError("price must be positive")
    lo, hi = -0.99, 1.0
    f = lambda y: bond_price(y, face, coupon_rate, periods, freq) - price
    flo, fhi = f(lo), f(hi)
    if flo * fhi > 0:
        # Preis außerhalb des Klammerbereichs → Intervall aufweiten
        hi = 5.0
        fhi = f(hi)
        if flo * fhi > 0:
            raise ValueError("YTM not bracketed in search interval")
    for _ in range(200):
        mid = (lo + hi) / 2.0
        fm = f(mid)
        if abs(fm) < 1e-10:
            return mid
        if flo * fm < 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
    return (lo + hi) / 2.0


def macaulay_duration(price: float, face: float, coupon_rate: float, periods: float, freq: int = 2) -> float:
    """Barwert-gewichtete mittlere Restlaufzeit in Jahren.

    Diskontiert mit der bondeigenen YTM (aus dem dirty price); Gewichte sind
    die Barwerte der Cashflows, Zeiten in Jahren (Periode/freq).
    """
    y = ytm(price, face, coupon_rate, periods, freq)
    per = y / freq
    cf = _cashflows(face, coupon_rate, periods, freq)
    pv_total = 0.0
    weighted = 0.0
    for i, c in enumerate(cf):
        t_years = (i + 1) / freq
        pv = c / (1.0 + per) ** (i + 1)
        pv_total += pv
        weighted += t_years * pv
    return weighted / pv_total if pv_total else 0.0


def modified_duration(mac_dur: float, y: float, freq: int) -> float:
    """ModDur = MacDur / (1 + y/freq) — Konsistenzbeziehung."""
    return mac_dur / (1.0 + y / freq)


def convexity(price: float, face: float, coupon_rate: float, periods: float, freq: int = 2) -> float:
    """Konvexität in Jahren^2 (annualisiert).

    C = (1/P) * Σ [ CF_t * t(t+1) / (1+per)^(t+2) ] / freq^2
    """
    y = ytm(price, face, coupon_rate, periods, freq)
    per = y / freq
    cf = _cashflows(face, coupon_rate, periods, freq)
    p = bond_price(y, face, coupon_rate, periods, freq)
    acc = 0.0
    for i, c in enumerate(cf):
        t = i + 1
        acc += c * t * (t + 1) / (1.0 + per) ** (t + 2)
    return acc / (p * freq ** 2) if p else 0.0


def effective_duration(price_up: float, price_down: float, price0: float, dy: float) -> float:
    """Numerische Duration für optionsbehaftete Bonds.

    EffDur = (P_- − P_+) / (2 * P0 * Δy). price_up/price_down sind die Preise
    nach paralleler Aufwärts-/Abwärtsverschiebung der Kurve um Δy.
    """
    if price0 == 0 or dy == 0:
        return 0.0
    return (price_down - price_up) / (2.0 * price0 * dy)


def dv01(mod_dur: float, dirty_price: float) -> float:
    """Dollar Value of 1 bp, per 100 Nominal, auf DIRTY price.

    DV01 = ModDur * DirtyPrice * 0.0001. Convexity bei 1 bp vernachlässigbar.
    """
    return mod_dur * dirty_price * 0.0001


def price_change_estimate(mod_dur: float, conv: float, dy: float) -> float:
    """Relative Preisänderung ΔP/P inkl. Convexity 2. Ordnung.

    ΔP/P ≈ −ModDur*Δy + ½*Convexity*Δy².
    """
    return -mod_dur * dy + 0.5 * conv * dy ** 2


def yield_to_worst(ytm_value: float | None, ytc_value: float | None = None) -> float | None:
    """Maßgebliche Rendite für callable Bonds: min über YTM und Call-Yields.

    None-Werte werden ignoriert; sind beide None, ist das Ergebnis None.
    Weitere Call-/Put-Szenarien können als zusätzliche Argumente vorab zu
    ytc_value reduziert werden (min) und hier eingespeist werden.
    """
    candidates = [v for v in (ytm_value, ytc_value) if v is not None]
    return min(candidates) if candidates else None
