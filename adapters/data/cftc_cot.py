"""
CFTC Commitments of Traders (COT) — Disaggregated Futures-Only, Managed Money.

Quelle: CFTC Public Reporting (Socrata), Dataset 72hh-3qpy.
Liefert pro Rohstoff die Wochenreihe der spekulativen Netto-Position
(Managed Money long − short) plus Open Interest für die konträre COT-Signallogik.

Mapping Yahoo-Futures-Ticker → exakter CFTC-Hauptkontrakt (`market_and_exchange_names`),
live verifiziert 2026-06 (jeweils der Kontrakt mit dem höchsten Open Interest, der zum
Yahoo-Instrument passt — z. B. NG=F = Henry Hub NYMEX, NICHT die größere ICE-LD1-Reihe).
"""
import logging

import requests

from core.ports.data_provider import COTProvider

_log = logging.getLogger(__name__)

_BASE = "https://publicreporting.cftc.gov/resource/72hh-3qpy.json"

_CONTRACT: dict[str, str] = {
    "GC=F":  "GOLD - COMMODITY EXCHANGE INC.",
    "SI=F":  "SILVER - COMMODITY EXCHANGE INC.",
    "PL=F":  "PLATINUM - NEW YORK MERCANTILE EXCHANGE",
    "PA=F":  "PALLADIUM - NEW YORK MERCANTILE EXCHANGE",
    "HG=F":  "COPPER- #1 - COMMODITY EXCHANGE INC.",
    "ALI=F": "ALUMINUM MWP - COMMODITY EXCHANGE INC.",
    "CL=F":  "WTI-PHYSICAL - NEW YORK MERCANTILE EXCHANGE",
    "BZ=F":  "BRENT LAST DAY - NEW YORK MERCANTILE EXCHANGE",
    "NG=F":  "NAT GAS NYME - NEW YORK MERCANTILE EXCHANGE",
    "ZW=F":  "WHEAT-SRW - CHICAGO BOARD OF TRADE",
    "ZC=F":  "CORN - CHICAGO BOARD OF TRADE",
    "ZS=F":  "SOYBEANS - CHICAGO BOARD OF TRADE",
    "KC=F":  "COFFEE C - ICE FUTURES U.S.",
    "SB=F":  "SUGAR NO. 11 - ICE FUTURES U.S.",
    "CT=F":  "COTTON NO. 2 - ICE FUTURES U.S.",
    "OJ=F":  "FRZN CONCENTRATED ORANGE JUICE - ICE FUTURES U.S.",
}


def _parse_row(row: dict) -> dict | None:
    """Rein: eine Socrata-Zeile → {date, managed_money_net, open_interest}.
    Managed-Money-Netto = long − short. None bei fehlenden/nicht-numerischen Feldern."""
    try:
        long = float(row["m_money_positions_long_all"])
        short = float(row["m_money_positions_short_all"])
        oi = float(row["open_interest_all"])
        date = row["report_date_as_yyyy_mm_dd"][:10]
    except (KeyError, TypeError, ValueError):
        return None
    if not date:
        return None
    return {"date": date, "managed_money_net": long - short, "open_interest": oi}


class CftcCotProvider(COTProvider):
    """COT-Wochenhistorie der Managed-Money-Position je Rohstoff (CFTC Disaggregated)."""

    def get_cot_history(self, commodity: str, years: int = 3) -> list[dict]:
        name = _CONTRACT.get(commodity)
        if name is None:
            return []   # Rohstoff ohne bekanntes CFTC-Mapping → UNAVAILABLE
        params = {
            "$where": f"market_and_exchange_names='{name}'",
            "$select": ("report_date_as_yyyy_mm_dd,m_money_positions_long_all,"
                        "m_money_positions_short_all,open_interest_all"),
            "$order": "report_date_as_yyyy_mm_dd DESC",
            "$limit": years * 60,   # ~52 Wochenberichte/Jahr + Puffer
        }
        try:
            resp = requests.get(_BASE, params=params, timeout=15)
            resp.raise_for_status()
            rows = resp.json()
        except Exception as exc:
            _log.warning("CFTC COT für %s nicht abrufbar (%s) — UNAVAILABLE", commodity, exc)
            return []
        parsed = [p for r in rows if (p := _parse_row(r)) is not None]
        parsed.sort(key=lambda h: h["date"])   # älteste zuerst (Port-Kontrakt)
        return parsed
