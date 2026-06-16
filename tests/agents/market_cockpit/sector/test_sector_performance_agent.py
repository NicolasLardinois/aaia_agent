from agents.market_cockpit.sector.sector_performance_agent import _relative_strength, USA_SECTORS


def test_relative_strength_subtracts_benchmark():
    perf = {"Technology": 5.0, "Utilities": 1.0}
    rs = _relative_strength(perf, benchmark_return=3.0)
    assert rs["Technology"] == 2.0
    assert rs["Utilities"] == -2.0


def test_leading_is_highest_relative_not_absolute():
    # Tech +5 abs, aber Benchmark +6 → RS negativ; Utilities +1 abs, RS -5 → Tech führt relativ
    perf = {"Technology": 5.0, "Utilities": 1.0}
    rs = _relative_strength(perf, benchmark_return=6.0)
    assert max(rs, key=rs.get) == "Technology"


def test_xlc_in_universe():
    assert "CommServices" in USA_SECTORS and USA_SECTORS["CommServices"] == "XLC"
