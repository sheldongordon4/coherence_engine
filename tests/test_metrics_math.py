from app.compute.metrics import basic_stats, classify_risk, compute_metrics


def test_basic_stats_mean_stdev_nonempty():
    vals = [80, 82, 78, 81, 79]
    stats = basic_stats(vals)
    assert 79.0 <= stats.mean <= 82.0
    assert stats.stdev > 0
    assert stats.n == len(vals)


def test_basic_stats_empty_list():
    stats = basic_stats([])
    assert stats.mean == 0.0
    assert stats.stdev == 0.0
    assert stats.n == 0


def test_classify_risk_buckets():
    assert classify_risk(mean=85, stdev=0.05) == "low"
    assert classify_risk(mean=75, stdev=0.05) == "medium"
    assert classify_risk(mean=85, stdev=0.30) == "high"
    assert classify_risk(mean=55, stdev=0.05) == "high"


def test_compute_metrics_shape_and_ranges():
    vals = [82.0] * 100
    out = compute_metrics(vals, window_sec=3600, source="mock")
    for k in ["coherenceMean", "volatilityIndex", "predictedDriftRisk", "timestamp", "windowSec", "n", "inputs", "meta"]:
        assert k in out
    assert out["n"] == 100
    assert 0.0 <= out["coherenceMean"] <= 100.0
    assert out["predictedDriftRisk"] in {"low", "medium", "high"}

