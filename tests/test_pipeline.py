"""AS-08–12: observable restart, failure state, privacy and output reconciliation."""
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import pandas as pd
import pytest
import yaml
from goal_eval.cache import ScoreCache
from goal_eval.cli import main
from goal_eval.config import load_config
from goal_eval.data import fingerprint
import goal_eval.pipeline as pipeline
from goal_eval.rubric import load_rubric
from goal_eval.scoring import SyntheticDemo, InferenceError
from goal_eval.synthetic import generate


def read_current(path):
    cfg = load_config(path)
    out = Path(cfg["output_dir"])
    return out, json.loads((out / "manifest.json").read_text())


def test_as08_cache_identity_dimensions(tmp_path):
    base = {"rubric": "v1", "backend": "http", "model_revision": "one", "inference": {"max_length": 30}}
    cached = ScoreCache(tmp_path / "scores.sqlite", base)
    cached.put("same", {"success": 1})
    cached.commit()
    assert cached.get("same") == {"success": 1} and cached.get("new text") is None
    cached.close()
    for key, value in [("rubric", "v2"), ("backend", "direct"), ("model_revision", "two"), ("inference", {"max_length": 31})]:
        cache = ScoreCache(tmp_path / "scores.sqlite", {**base, key: value})
        assert cache.get("same") is None
        cache.close()


def test_as08_resume_duplicates_and_as10_export_reconciliation(config_factory, capsys):
    path = config_factory()
    first = pipeline.run_pipeline(path)
    second = pipeline.run_pipeline(path)
    assert first["backend_calls"] == 1 and second["backend_calls"] == 0
    first_rows = pd.read_parquet(Path(first["artifact_dir"]) / "scored.parquet")
    rows = pd.read_parquet(Path(second["artifact_dir"]) / "scored.parquet")
    csv_rows = pd.read_csv(Path(second["artifact_dir"]) / "scored.csv", dtype={"employee_id": str}, keep_default_na=False)
    assert len(rows) == len(csv_rows) == 9 and rows.record_id.nunique() == 9
    assert rows.employee_id.tolist() == csv_rows.employee_id.tolist() == ["001", "002", "003"]*3
    pd.testing.assert_frame_equal(first_rows, rows)
    annual = pd.read_csv(Path(second["artifact_dir"]) / "annual.csv")
    assert annual.query("metric == 'clarity'").n_valid_goals.tolist() == [2, 2, 2]
    coverage = pd.read_csv(Path(second["artifact_dir"]) / "coverage.csv")
    assert coverage.query("measure == 'input_goals'")["count"].sum() == 9
    assert coverage.query("measure == 'english_goals'")["count"].sum() == 6
    assert coverage.query("measure == 'english_distinct_combined_texts'")["count"].tolist() == [1, 1, 1]
    assert coverage.query("measure == 'english_repeated_rows_beyond_first'")["count"].tolist() == [1, 1, 1]
    assert rows.loc[rows.employee_id.eq("003"), "clarity"].isna().all()
    assert first["inputs"] == second["inputs"]


def test_as08_interrupted_commit_resume_and_as09_stale_report(config_factory, monkeypatch):
    path = config_factory()
    out = Path(load_config(path)["output_dir"])
    out.mkdir()
    (out / "report.html").write_text("Historical report placeholder")
    assert (out / "report.html").exists()
    original = pipeline.enrich
    calls = 0
    def interrupt(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 3:
            raise KeyboardInterrupt()
        return original(*args, **kwargs)
    monkeypatch.setattr(pipeline, "enrich", interrupt)
    with pytest.raises(KeyboardInterrupt):
        pipeline.run_pipeline(path)
    _, failed = read_current(path)
    assert failed["status"] == "failed" and failed["processed_rows"] == 2 and failed["artifact_dir"] is None
    assert not (out / "report.html").exists()
    conn = sqlite3.connect(path.parent / "cache/scores.sqlite")
    assert conn.execute("SELECT COUNT(*) FROM scores").fetchone()[0] == 1
    conn.close()
    monkeypatch.setattr(pipeline, "enrich", original)
    recovered = pipeline.run_pipeline(path)
    assert recovered["status"] == "success" and recovered["backend_calls"] == 0
    assert len(pd.read_parquet(Path(recovered["artifact_dir"]) / "scored.parquet")) == 9


def test_as09_bad_config_and_write_failure_suppress_current(config_factory, monkeypatch):
    path = config_factory()
    pipeline.run_pipeline(path)
    raw = yaml.safe_load(path.read_text())
    invalid = {**raw, "chunk_size": 0}
    path.write_text(yaml.safe_dump(invalid))
    assert main(["run", "--config", str(path)]) == 2
    output = path.parent / "outputs"
    assert json.loads((output / "manifest.json").read_text())["status"] == "failed"
    assert not (output / "report.html").exists()
    path.write_text(yaml.safe_dump(raw))
    original = pipeline.render
    monkeypatch.setattr(pipeline, "render", lambda *a, **k: (_ for _ in ()).throw(OSError("PRIVATE_SENTINEL")))
    assert main(["run", "--config", str(path)]) == 1
    assert json.loads((output / "manifest.json").read_text())["status"] == "failed"
    assert not (output / "report.html").exists()
    monkeypatch.setattr(pipeline, "render", original)
    assert main(["run", "--config", str(path)]) == 0
    path.write_text("invalid: [yaml\n")
    assert main(["run", "--config", str(path)]) == 2
    assert json.loads((output / "manifest.json").read_text())["status"] == "failed"
    assert not (output / "report.html").exists()


def test_as09_inference_failures_retry_not_cached_and_as11_logs(config_factory, monkeypatch, capsys):
    sentinel = "PRIVATE_TEXT_SENTINEL Review the monthly customer report with the team."
    path = config_factory([["PRIVATE_EMPLOYEE_SENTINEL", sentinel, ""]])
    original = SyntheticDemo.score
    def failure(self, text):
        raise RuntimeError("PRIVATE_TEXT_SENTINEL " + text)
    monkeypatch.setattr(SyntheticDemo, "score", failure)
    assert main(["run", "--config", str(path)]) == 2
    out, manifest = read_current(path)
    assert manifest["failed_rows"] == 3 and manifest["inference_failures"] > 0
    assert not (out / "report.html").exists()
    conn = sqlite3.connect(path.parent / "cache/scores.sqlite")
    assert conn.execute("SELECT COUNT(*) FROM scores").fetchone()[0] == 0
    conn.close()
    printed = capsys.readouterr()
    assert "PRIVATE_" not in printed.out + printed.err
    monkeypatch.setattr(SyntheticDemo, "score", original)
    success = pipeline.run_pipeline(path)
    assert success["backend_calls"] == 1
    html = (out / "report.html").read_text()
    assert "PRIVATE_" not in html and "goal_text" not in html


def test_as08_retry_then_success_committed(tmp_path):
    class Flaky:
        calls = 0
        def score(self, text):
            self.calls += 1
            if self.calls == 1:
                raise InferenceError("temporary")
            return {"valid": 1}
    backend = Flaky()
    cache = ScoreCache(tmp_path / "cache.sqlite", {"v": 1})
    assert pipeline.score_text("text", backend, cache, 1, 1) == {"valid": 1}
    assert backend.calls == 2 and cache.failures == 0
    assert pipeline.score_text("text", backend, cache, 1, 1) == {"valid": 1}
    assert backend.calls == 2
    cache.close()


@pytest.mark.parametrize("mode", ["unavailable", "malformed"])
def test_as09_real_adapter_failure_suppresses_previous_success(config_factory, mode):
    from test_backends import server
    path = config_factory()
    pipeline.run_pipeline(path)
    raw = yaml.safe_load(path.read_text())
    with server("malformed" if mode == "malformed" else "valid") as (url, _):
        raw["backend"] = {"kind": "http", "model": "local", "revision": "test-protocol-only", "timeout": .2, "retries": 0, "endpoint": url if mode == "malformed" else "http://127.0.0.1:1/v1/systemone"}
        path.write_text(yaml.safe_dump(raw))
        assert main(["run", "--config", str(path)]) == 2
        out, manifest = read_current(path)
        assert manifest["status"] == "failed" and manifest["failed_rows"] == 6
        assert manifest["inference_failures"] > 0 and not (out / "report.html").exists()


def test_as10_html_escaping_notices_missing_and_offline(config_factory, monkeypatch):
    path = config_factory([["001", "OKR", ""]], report_title='<script>alert("x")</script>')
    result = pipeline.run_pipeline(path)
    html = (Path(result["artifact_dir"]) / "report.html").read_text()
    assert '<script>' not in html and '&lt;script&gt;' in html
    assert html.index("SYNTHETIC DEMONSTRATION") < html.index("Annual employee means")
    assert html.index("no human validation") < html.index("Annual employee means")
    assert "Missing" in html and "n=0" in html
    assert "fixed zero to three" in html and "zero baseline" in html
    assert "<svg" in html and "<table" in html and 'src="http' not in html and 'href="http' not in html
    assert all(word in html for word in ("english_threshold", "abstention_threshold", "length_band", "title_only"))


def test_as12_generator_cli_and_manifest(config_factory, tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    generate(a, 20, 42)
    generate(b, 20, 42)
    assert [fingerprint(p) for p in sorted(a.glob("*.csv"))] == [fingerprint(p) for p in sorted(b.glob("*.csv"))]
    path = config_factory()
    assert main(["benchmark", "--config", str(path), "--limit", "4"]) == 0
    _, manifest = read_current(path)
    for key in ("inputs", "configuration", "config_sha256", "backend", "runtime", "code_revision", "seed", "rubric", "coverage", "inference_failures", "status", "peak_process_rss_mb", "records_per_second"):
        assert key in manifest
    assert manifest["benchmark"]["pilot_records"] == 4
    assert manifest["scope"] == {"kind": "input_prefix", "requested_limit": 4, "benchmark": True}
    assert "PARTIAL INPUT PREFIX / PILOT" in (Path(manifest["artifact_dir"]) / "report.html").read_text()
    assert "illustration" in manifest["benchmark"]["label"]
    assert subprocess.run([sys.executable, "-m", "goal_eval", "--help"], capture_output=True).returncode == 0


def test_as12_code_provenance_independent_of_caller_repository(tmp_path, monkeypatch):
    expected_revision, expected_source, expected_dirty = pipeline.code_version(), pipeline.source_identity(), pipeline.code_dirty()
    other = tmp_path / "unrelated-repo"
    other.mkdir()
    subprocess.run(["git", "init", str(other)], capture_output=True, check=True)
    monkeypatch.chdir(other)
    assert pipeline.code_version() == expected_revision
    assert pipeline.source_identity() == expected_source
    assert pipeline.code_dirty() == expected_dirty
