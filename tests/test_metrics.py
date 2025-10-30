from app.compute.metrics import basic_stats, classify_risk, compute_metrics

def test_basic_stats_mean_stdev():
    vals = [80, 82, 78, 81, 79]
    stats = basic_stats(vals)
    assert 80 <= stats.mean <= 81
    assert stats.stdev > 0

def test_classify_risk_brackets():
    assert classify_risk(mean=85, stdev=0.05) == "low"
    assert classify_risk(mean=75, stdev=0.05) == "medium"
    assert classify_risk(mean=85, stdev=0.30) == "high"
    assert classify_risk(mean=55, stdev=0.05) == "high"

def test_compute_metrics_shape():
    vals = [82.0] * 100
    out = compute_metrics(vals, window_sec=3600, source="mock")
    for key in ["coherenceMean","volatilityIndex","predictedDriftRisk","timestamp","windowSec","n","inputs","meta"]:
        assert key in out
    assert out["n"] == 100
