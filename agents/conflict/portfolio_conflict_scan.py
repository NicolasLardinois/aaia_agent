from collections.abc import Callable

from core.domain.conflict_inbox import record_conflict
from core.ports.conflict_store import ConflictStorePort


def scan_portfolio_conflicts(positions: list, judge_fn: Callable[[str, str], object | None],
                             store: ConflictStorePort) -> None:
    """Je gehaltener Position eine Analyse (judge_fn) laufen lassen; bei Konflikt protokollieren.

    judge_fn(ticker, direction) -> result mit .conflict/.conflict_resolution, oder None (keine Daten).
    Vollständig defensiv: ein Fehler je Position (Exception oder fehlende Daten) überspringt nur diese —
    die Inbox ist nie kritisch und darf den Scan nie abbrechen.
    """
    for p in positions:
        try:
            result = judge_fn(p.ticker, p.direction)
            if result is not None and getattr(result, "conflict", False) and result.conflict_resolution:
                record_conflict(store, p.ticker, p.direction,
                                result.conflict_resolution.verdict,
                                result.conflict_resolution.reasoning, "proactive")
        except Exception:
            continue
