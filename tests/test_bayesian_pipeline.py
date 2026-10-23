"""AS-B01/B08/B11: pipeline exports, disable behavior and stale-report recovery."""
import json
from pathlib import Path
import pandas as pd
import pytest
import goal_eval.pipeline as pipeline


def test_bayesian_exports_config_and_scoring_cache_identity(config_factory):
    path = config_factory(bayesian={"draws": 31})
    first = pipeline.run_pipeline(path)
    second = pipeline.run_pipeline(path)
    assert first["bayesian"]["enabled"] is True and first["bayesian"]["effective_settings"]["draws"] == 31
    assert first["cache_identity"] == second["cache_identity"]
    assert first["backend_calls"] == 1 and second["backend_calls"] == 0
    root = Path(second["artifact_dir"])
    assert len(pd.read_csv(root / "bayesian_annual.csv")) == 27
    assert len(pd.read_csv(root / "bayesian_contrasts.csv")) == 54
    json.dumps(second, allow_nan=False)
    old_root = Path(first["artifact_dir"])
    for name in ("scored.csv", "annual.csv", "contrasts.csv", "paired.csv", "common_three_years.csv"):
        assert (root / name).read_bytes() == (old_root / name).read_bytes()


def test_bayesian_failure_suppresses_current_success_and_cache_recovers(config_factory, monkeypatch):
    path = config_factory(bayesian={"draws": 13})
    first = pipeline.run_pipeline(path)
    out = Path(first["artifact_dir"]).parent.parent
    assert (out / "report.html").exists()
    original = pipeline.analyze_bayesian
    def fail(*args, **kwargs):
        raise ValueError("Nonfinite Bayesian injected draw")
    monkeypatch.setattr(pipeline, "analyze_bayesian", fail)
    with pytest.raises(ValueError):
        pipeline.run_pipeline(path)
    failed = json.loads((out / "manifest.json").read_text())
    assert failed["status"] == "failed" and failed["failure_type"] == "ValueError" and failed["artifact_dir"] is None
    assert not (out / "report.html").exists()
    assert failed["backend_calls"] == 0 and failed["cache_hits"] > 0
    monkeypatch.setattr(pipeline, "analyze_bayesian", original)
    recovered = pipeline.run_pipeline(path)
    assert recovered["status"] == "success" and recovered["backend_calls"] == 0
    assert recovered["bayesian"]["status"] == "success" and (out / "report.html").exists()


def test_bayesian_disabled_pipeline_exports_empty_headers(config_factory):
    result = pipeline.run_pipeline(config_factory(bayesian={"enabled": False}))
    assert result["bayesian"]["status"] == "disabled" and result["bayesian"]["enabled"] is False
    root = Path(result["artifact_dir"])
    assert pd.read_csv(root / "bayesian_annual.csv").empty
    assert pd.read_csv(root / "bayesian_contrasts.csv").empty
