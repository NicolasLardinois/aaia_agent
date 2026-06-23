from agents.anomaly.top_down_anomaly_agent import TopDownAnomalyAgent
from agents.anomaly.bottom_up_anomaly_agent import BottomUpAnomalyAgent
from core.domain.events import AnomalyChiefReady
from core.domain.models import AnomalyReport
from core.domain.taxonomy import legacy_asset_class, legacy_to_taxonomy
from core.ports.event_bus import EventBus


class AnomalyChiefAgent:
    def __init__(self, bus: EventBus):
        self.bus = bus
        self.td_anomaly_agent = TopDownAnomalyAgent()
        self.bu_anomaly_agent = BottomUpAnomalyAgent()

    def run(
        self,
        cockpit,
        bottom_up,
        ticker_history: list[dict],
        global_history: list[dict],
        market: str = "USA",
    ) -> tuple[AnomalyReport, AnomalyReport]:
        # underlying/wrapper defensiv auflösen: echte Modelle tragen die Felder direkt;
        # Test-Doubles (SimpleNamespace/MagicMock) können asset_class-String tragen → Fallback.
        if hasattr(bottom_up, "underlying") and hasattr(bottom_up, "wrapper"):
            from core.domain.taxonomy import Underlying, Wrapper as _Wrapper
            _und = bottom_up.underlying
            _wrp = bottom_up.wrapper
            # Sicherheitsprüfung: MagicMock liefert MagicMock-Objekte, keine echten Enums.
            if isinstance(_und, Underlying) and isinstance(_wrp, _Wrapper):
                asset_class = legacy_asset_class(_und, _wrp)
            else:
                asset_class = getattr(bottom_up, "asset_class", "equity")
        else:
            asset_class = getattr(bottom_up, "asset_class", "equity")
        try:
            td_anomaly = (
                self.td_anomaly_agent.run(cockpit, global_history, asset_class=asset_class, market=market)
                if cockpit is not None
                else AnomalyReport.empty()
            )
        except Exception:
            td_anomaly = AnomalyReport.empty()
        try:
            bu_anomaly = self.bu_anomaly_agent.run(bottom_up, ticker_history)
        except Exception:
            bu_anomaly = AnomalyReport.empty()

        self.bus.publish(AnomalyChiefReady(source="anomaly_chief_agent", payload={
            "td_severity": td_anomaly.severity,
            "bu_severity": bu_anomaly.severity,
        }))

        return td_anomaly, bu_anomaly
