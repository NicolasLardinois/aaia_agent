from io import StringIO

import pandas as pd


def encode_frame(df: pd.DataFrame) -> str:
    """DataFrame → JSON-String.

    ``orient="table"`` schreibt ein JSON-Schema mit Spalten, dtypes und Index mit —
    dadurch überlebt der Round-Trip den (Datetime-)Index und die Spalten-Typen,
    anders als bei den werteorientierten Orients.
    """
    return df.to_json(orient="table")


def decode_frame(payload: str) -> pd.DataFrame:
    """Umkehrung von :func:`encode_frame`. ``StringIO``, weil ``read_json`` einen
    rohen String künftig nicht mehr direkt akzeptiert."""
    return pd.read_json(StringIO(payload), orient="table")
