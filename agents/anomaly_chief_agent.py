from agents.anomaly.top_down_anomaly_agent import TopDownAnomalyAgent
from agents.anomaly.bottom_up_anomaly_agent import BottomUpAnomalyAgent
from core.domain.events import AnomalyChiefReady
from core.domain.models import AnomalyReport
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
    ) -> tuple[AnomalyReport, AnomalyReport]:
        asset_class = getattr(bottom_up, "asset_class", "equity")
        td_anomaly = (
            self.td_anomaly_agent.run(cockpit, global_history, asset_class=asset_class)
            if cockpit is not None
            else AnomalyReport.empty()
        )
        try:
            bu_anomaly = self.bu_anomaly_agent.run(bottom_up, ticker_history)
        except Exception:
            bu_anomaly = AnomalyReport.empty()

        self.bus.publish(AnomalyChiefReady(source="anomaly_chief_agent", payload={
            "td_severity": td_anomaly.severity,
            "bu_severity": bu_anomaly.severity,
        }))

        return td_anomaly, bu_anomaly
