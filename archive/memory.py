"""
memory.py — Erweiterung 5: Langzeitgedächtnis
==============================================
Speichert vergangene Entscheidungen in agent_memory.json und ermöglicht
das Abrufen ähnlicher Situationen für verbesserte Entscheidungsfindung.
"""

import json
import os
from datetime import datetime

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "agent_memory.json")
MAX_ENTRIES  = 200   # Maximale Anzahl gespeicherter Einträge


class AgentMemory:
    def __init__(self):
        self._data: list[dict] = self._load()

    # ------------------------------------------------------------------
    def _load(self) -> list[dict]:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def _save(self) -> None:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self._data[-MAX_ENTRIES:], f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    def record(
        self,
        state: dict,
        phase: str,
        decision: str,
        scores: dict,
        confidence: float,
        allocation: dict,
    ) -> None:
        """Speichert eine Entscheidung in den Langzeitspeicher."""
        entry = {
            "timestamp":  datetime.now().isoformat(),
            "phase":      phase,
            "state":      state,
            "decision":   decision,
            "scores":     scores,
            "confidence": confidence,
            "allocation": allocation,
        }
        self._data.append(entry)
        self._save()

    # ------------------------------------------------------------------
    def find_similar_situations(
        self, current_state: dict, top_k: int = 3
    ) -> list[dict]:
        """
        Findet die ähnlichsten vergangenen Situationen mittels euklidischer
        Distanz über gemeinsame Indikatoren.
        """
        if not self._data:
            return []

        keys = list(current_state.keys())

        def distance(entry: dict) -> float:
            past = entry.get("state", {})
            return sum(
                (current_state.get(k, 0) - past.get(k, 0)) ** 2
                for k in keys
                if k in past
            ) ** 0.5

        sorted_entries = sorted(self._data, key=distance)
        return sorted_entries[:top_k]

    # ------------------------------------------------------------------
    def get_last_decision(self) -> dict | None:
        """Gibt den letzten gespeicherten Eintrag zurück."""
        return self._data[-1] if self._data else None

    def summary(self) -> str:
        """Kurze Zusammenfassung des Gedächtnisses."""
        if not self._data:
            return "Kein Gedächtnis vorhanden."
        phases = [e["phase"] for e in self._data]
        decisions = [e["decision"] for e in self._data]
        return (
            f"{len(self._data)} Einträge gespeichert. "
            f"Häufigste Phase: {max(set(phases), key=phases.count)}. "
            f"Häufigste Entscheidung: {max(set(decisions), key=decisions.count)}."
        )
