"""World-Bank-Adapter: Börsen-Marktkapitalisierung in % des BIP je Land.

Liefert die Rohdaten für den Buffett-Indikator (Indikator CM.MKT.LCAP.GD.ZS).
Einziges Stück echtes I/O — die Z-Score-/Korridor-/Signal-Logik bleibt im
Agenten (Hexagonal §1).
"""
import requests

from core.ports.world_bank import MarketCapToGdpProvider

# mrv=15 → letzte 15 Jahreswerte pro Land (reicht für Z-Score-Berechnung)
# per_page=5000 verhindert Paginierung bei ~150 Ländern × 15 Jahre = ~2250 Einträgen
_WB_URL = (
    "https://api.worldbank.org/v2/country/all/indicator/"
    "CM.MKT.LCAP.GD.ZS?format=json&mrv=15&per_page=5000"
)


class WorldBankMarketCapProvider(MarketCapToGdpProvider):
    def get_market_cap_to_gdp(self) -> dict[str, tuple[float, int, list[tuple[int, float]], str]]:
        try:
            resp = requests.get(_WB_URL, timeout=20)
            payload = resp.json()
            if not isinstance(payload, list) or len(payload) < 2:
                return {}
            entries = payload[1] or []

            by_country: dict[str, list[tuple[int, float]]] = {}
            names: dict[str, str] = {}   # ISO-3 → Klarname (aus der Weltbank-Antwort)
            for entry in entries:
                if entry.get("value") is None:
                    continue
                code = entry.get("countryiso3code", "")
                if not code or len(code) != 3:
                    continue
                try:
                    year  = int(entry["date"])
                    value = round(float(entry["value"]), 1)
                    by_country.setdefault(code, []).append((year, value))
                    names.setdefault(code, entry.get("country", {}).get("value", ""))
                except (TypeError, ValueError):
                    continue

            result = {}
            for code, points in by_country.items():
                points.sort(key=lambda x: x[0])        # älteste → neueste
                current_year, current_val = points[-1]
                # (aktueller Ratio, Jahr, (Jahr, Ratio)-Paare, Klarname)
                result[code] = (current_val, current_year, points, names.get(code, ""))

            return result
        except Exception:
            return {}
