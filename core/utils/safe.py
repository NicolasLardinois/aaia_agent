"""Geteilter Fehler-Schutz-Helfer gegen Datenquellen-/Sub-Agenten-Ausfälle.

**Wozu (AGENTS.md §2 „Defensive Aggregation"):** Nach
`asyncio.gather(..., return_exceptions=True)` ist ein Teilergebnis entweder der echte
Wert **oder** eine als Wert zurückgegebene Exception. Genau dieses Entpacken —
„Exception → neutraler Default" — ist heute in ~23 Dateien lokal in zwei Schreibweisen
kopiert:

  * Chief-Agents/Orchestratoren:  ``def _safe(r, d): return d if isinstance(r, Exception) else r``
  * Sub-Agenten:                  ``def _safe(v): return None if isinstance(v, Exception) else v``

Jede Verbesserung (z. B. Logging) müsste man sonst an ~23–40 Stellen einzeln nachziehen.
Dieser Helfer vereinheitlicht das an **einer** Stelle und legt **optionales Logging**
hinein, damit ein Ausfall nicht mehr **still** verschluckt wird (Befund 2 / Bug #46:
ein echtes neutrales Ergebnis ist sonst nicht von einem Quellen-Ausfall unterscheidbar).

**Bewusst nur `Exception`, nicht `BaseException`:** spiegelt das bestehende
`isinstance(r, Exception)` exakt — `asyncio.CancelledError` (BaseException) wird damit
NICHT zum Default maskiert, sondern durchgereicht (ein Abbruch darf nicht verschluckt werden).

Der Rollout (die ~23 lokalen `_safe` durch diese Funktion ersetzen) läuft inkrementell
pro Agenten-Paket als eigene PRs — dieses Modul ist die rein additive Grundlage.
"""
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

_T = TypeVar("_T")
_D = TypeVar("_D")

# Ein Modul-Logger als Default-Ziel; Aufrufer können einen eigenen Logger injizieren.
_LOG = logging.getLogger("aaia.safe")


def _warn(label: str | None, exc: BaseException, logger: logging.Logger | None) -> None:
    """Einheitliche Sichtbarkeit eines Ausfalls — nur wenn ein `label` gesetzt ist.
    Ohne `label` bleibt der Helfer **still** (rückwärtskompatibel zum bisherigen
    `_safe`, das nichts loggte), sodass ein Rollout das Verhalten nicht ändert,
    solange das Call-Site kein Label nachreicht."""
    if label is not None:
        (logger or _LOG).warning("%s fehlgeschlagen: %r", label, exc)


def safe_result(
    result: _T | Exception,
    *,
    default: _D,
    label: str | None = None,
    logger: logging.Logger | None = None,
) -> _T | _D:
    """Entpackt ein `gather(return_exceptions=True)`-Teilergebnis defensiv.

    Ist `result` eine `Exception` (geworfen → als Wert zurückgegeben), wird `default`
    geliefert, sonst `result` unverändert — auch falsy Werte (`0`, `""`, `None`, `[]`)
    gelten als gültiges Ergebnis und werden NICHT ersetzt.

    `label` (z. B. ``"insider-Agent für AAPL"``) + optionaler `logger` machen den
    Ausfall via `logger.warning(...)` sichtbar. Ohne `label` lautlos (s. Modul-Doku).
    """
    if isinstance(result, Exception):
        _warn(label, result, logger)
        return default
    return result


async def safe_provider_call(
    fn: Callable[..., Awaitable[_T]],
    *args,
    default: _D,
    label: str | None = None,
    logger: logging.Logger | None = None,
    **kwargs,
) -> _T | _D:
    """Ruft eine **async** Provider-Funktion defensiv auf und fängt JEDEN Fehler zu
    `default` ab — egal ob `fn` wirft oder eine Exception als Wert zurückgibt. Für
    Sub-Agenten, die eine einzelne Datenquelle abfragen (kapselt `try/except Exception`
    **und** die `isinstance`-Prüfung in einem Aufruf).

    `*args`/`**kwargs` werden an `fn` durchgereicht; `label`/`logger` steuern das Logging
    analog zu `safe_result`.
    """
    try:
        result = await fn(*args, **kwargs)
    except Exception as exc:
        _warn(label, exc, logger)
        return default
    return safe_result(result, default=default, label=label, logger=logger)
