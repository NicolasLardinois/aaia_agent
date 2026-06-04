"""Führt genau eine Iteration des Agenten aus (ohne Endlosschleife)."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
os.chdir(os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from sensors         import EconomicSensor
from phase_detector  import PhaseDetector
from confidence      import ConfidenceCalculator
from memory          import AgentMemory
from orchestrator    import Orchestrator
from anomaly         import AnomalyDetector
from backtester      import Backtester
from explainer       import Explainer
from portfolio       import PortfolioAllocator

API_KEY = os.getenv("FRED_API_KEY", "")

print("=" * 60)
print("  AAIA — Adaptive AI Investment Agent")
print("=" * 60)

sensor       = EconomicSensor(API_KEY)
detector     = PhaseDetector()
calculator   = ConfidenceCalculator()
memory       = AgentMemory()
orchestrator = Orchestrator()
anomaly_det  = AnomalyDetector()
backtester   = Backtester()
explainer    = Explainer()
allocator    = PortfolioAllocator()

print("\n[1] Sensoren: Wirtschaftsdaten von FRED API laden...")
state, raw = sensor.get_state()
for k, v in state.items():
    print(f"    {k:<25} = {v}")

print("\n[2] Prognose: Trendextrapolation 3 Monate voraus...")
predictions = sensor.predict_state(raw, months_ahead=3)
volatility  = sensor.get_volatility(raw)
for k, pred in predictions.items():
    print(f"    {k:<25} -> {pred}  (Volatilität: {volatility.get(k)})")

print("\n[3] Phasenerkennung...")
phase, phase_conf, evidence = detector.detect(state)
print(f"    Erkannte Phase : {phase}")
print(f"    Konfidenz      : {phase_conf:.1%}")

print("\n[4] Anomalie-Erkennung...")
is_anomaly, anomalies = anomaly_det.check(state, memory._data)
if is_anomaly:
    for a in anomalies:
        print(f"    ⚠  {a['indicator']}: Z={a['z_score']} ({a['direction']})")
else:
    print(f"    Keine Anomalien (Gedächtniseinträge: {len(memory._data)})")

print("\n[5] Gedächtnis: ähnliche Situationen suchen...")
similar = memory.find_similar_situations(state)
print(f"    Ähnliche Situationen gefunden: {len(similar)}")

print("\n[6] Multi-Agenten-Abstimmung...")
final_scores, agent_votes = orchestrator.consolidate(state, phase)
for name, votes in agent_votes.items():
    best = max(votes, key=votes.get)
    print(f"    {name:<16} -> {best}")
print(f"    Konsolidierte Scores: {final_scores}")

print("\n[7] Konfidenzberechnung...")
confidence, breakdown = calculator.compute(final_scores, volatility, phase_conf)
sufficient = calculator.is_sufficient(confidence, final_scores)
status = "ausreichend" if sufficient else "zu niedrig"
print(f"    Gesamtkonfidenz: {confidence:.1%}  ({status})")
print(f"    Score-Gap: {breakdown['score_gap']:.4f}  |  Vol-Konf: {breakdown['vol_confidence']:.2f}")

print("\n[8] Softmax-Portfolioallokation...")
allocation = allocator.allocate(final_scores, confidence, sufficient)
decision   = allocator.best_portfolio(allocation)
for portfolio, pct in allocation.items():
    bar = "#" * int(pct * 20)
    print(f"    {portfolio:<10} {pct:>6.1%}  {bar}")
print(f"    >>> EMPFEHLUNG: {decision} <<<")

print("\n[9] Backtesting (Selbst-Evaluation)...")
bt = backtester.evaluate(memory._data, decision, final_scores)
print(f"    Status: {bt['status']}")
if bt.get("accuracy") is not None:
    print(f"    Genauigkeit: {bt['accuracy']:.1%}")
    print(f"    {bt['recommendation']}")

print("\n[10] Erklärbarkeit (XAI)...")
expl = explainer.explain(state, phase, decision, agent_votes)
print(f"    {expl['summary']}")
print("    Top-3 Einflussfaktoren:")
for factor, info in expl["top_factors"].items():
    print(f"      {factor:<25} Beitrag: {info['contribution']:+.4f}")

memory.record(state, phase, decision, final_scores, confidence, allocation)
print(f"\n    Gespeichert. {memory.summary()}")
print("\n" + "=" * 60)
print("  FERTIG.")
print("=" * 60)
