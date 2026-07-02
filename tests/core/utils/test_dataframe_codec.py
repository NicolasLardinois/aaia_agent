import pandas as pd
from pandas.testing import assert_frame_equal

from core.utils.dataframe_codec import decode_frame, encode_frame


def test_round_trip_mit_datetime_index_erhaelt_werte_und_index():
    idx = pd.DatetimeIndex(["2026-06-01", "2026-06-02"], name="Date")
    df = pd.DataFrame({"Close": [100.5, 101.0], "Volume": [10, 20]}, index=idx)

    restored = decode_frame(encode_frame(df))

    # check_index_type=False: pandas JSON round-trip konvertiert datetime64[us] → datetime64[ns]
    # Das ist Codec-korrektes Verhalten, der Index und die Werte sind erhalten.
    assert_frame_equal(df, restored, check_like=True, check_index_type=False)


def test_leerer_frame_round_trip():
    df = pd.DataFrame({"Close": []})
    restored = decode_frame(encode_frame(df))
    assert list(restored.columns) == ["Close"]
    assert len(restored) == 0
