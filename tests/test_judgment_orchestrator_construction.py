"""Regressions-Test zu Bug #2 (Audit 2026-06-20, §6 Logbuch).

Der ursprüngliche Crash: `app/main.py` rief `JudgmentOrchestrator(llm, bus)` ohne
das dritte Argument `memory` → sofortiger `TypeError` im `judge`-Modus. Der Fix
übergibt `memory` als drittes Argument.

Dieser Test nagelt die 3-Argument-Signatur `(llm, bus, memory)` fest:
- Konstruktion mit den drei Pflicht-Argumenten läuft ohne `TypeError` durch und
  hält `memory` fest.
- Konstruktion **ohne** `memory` wirft `TypeError` (verhindert die Regression des
  früher fehlenden Arguments — ein blosser `(llm, bus)`-Aufruf darf nie wieder
  stillschweigend durchgehen).
"""
import pytest
from types import SimpleNamespace as NS

from orchestrators.judgment_orchestrator import JudgmentOrchestrator


def test_konstruktor_drei_pflichtargumente_kein_typeerror():
    """(llm, bus, memory) konstruiert sauber und hält memory fest."""
    llm, bus, memory = NS(), NS(), NS()
    orch = JudgmentOrchestrator(llm, bus, memory)
    # memory muss tatsächlich gespeichert werden (Bug #2 verlor es komplett).
    assert orch.memory is memory


def test_konstruktor_ohne_memory_wirft_typeerror():
    """Der ursprüngliche Bug-#2-Aufruf (llm, bus) darf nie wieder durchgehen."""
    with pytest.raises(TypeError):
        JudgmentOrchestrator(NS(), NS())
