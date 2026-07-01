from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class RunContext:
    """Identität EINES Analyselaufs: ein eingefrorenes ``as_of``-Datum + ein In-Lauf-Memo.

    Garantiert, dass jede (namespace, key)-Kombination pro Lauf nur EINMAL live
    gezogen wird → Point-in-Time (alle Agenten sehen denselben Stand) + Dedup.
    Rein, keine I/O. Wird pro Lauf frisch im Composition-Root erzeugt; alle
    Caching-Decorator eines Laufs teilen sich DIESELBE Instanz.
    Backtest: ``as_of`` = historisches Datum → der Store liefert den damaligen Wert.
    """

    as_of: date
    memo: dict[tuple[str, str], Any] = field(default_factory=dict)
