from abc import ABC, abstractmethod


class MarketCapToGdpProvider(ABC):
    """Port für die Rohdaten des Buffett-Indikators je Land: Börsen-
    Marktkapitalisierung in % des BIP (World-Bank-Indikator CM.MKT.LCAP.GD.ZS).

    Synchron gehalten (der Agent ruft es als blockierendes I/O via
    `asyncio.to_thread(...)`). Bei fehlenden/fehlerhaften Daten: leeres Dict.
    """

    @abstractmethod
    def get_market_cap_to_gdp(self) -> dict[str, tuple[float, int, list[tuple[int, float]], str]]:
        """{ISO-3-Code: (aktueller_ratio_pct, Jahr, [(Jahr, Ratio%), …] aufsteigend, Klarname)}.

        Die (Jahr, Ratio)-Serie ist lückenlos (nur vorhandene Werte), älteste → neueste;
        aus ihr entsteht der z-Score und der 10-J-Verlauf im Einzelland-Drilldown.
        Leeres Dict, wenn keine Daten verfügbar sind.
        """
        ...
