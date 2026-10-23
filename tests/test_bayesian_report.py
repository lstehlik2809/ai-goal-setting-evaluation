"""AS-B11: inferential report content, privacy, states and responsive chart geometry."""
import math
import re
from xml.etree import ElementTree

import pandas as pd
import pytest

from goal_eval.analysis import analyze
from goal_eval.report import bayesian_quality_chart, render


METRICS = ["clarity", "specificity", "assessability", "coherence", "combined_words", "combined_flesch_ease", "combined_fk_grade", "timing_present", "strategy_present"]


@pytest.fixture
def report_inputs():
    observations = pd.DataFrame([
        {"employee_id": f"PRIVATE_EMPLOYEE_{employee}", "year": year, "english_eligible": True,
         "language_reason": "eligible", "description_state": "present", **{metric: 1. + employee / 10 for metric in METRICS}}
        for year in (2023, 2024, 2025) for employee in range(3)
    ])
    tables = analyze(observations, {"language": {"threshold": .8, "sensitivity_thresholds": [.8]}})
    rows = []
    for metric in METRICS:
        for cohort in ("available", "paired", "common_three_years"):
            for before, after in ((2023, 2024), (2024, 2025)):
                rows.append({"metric": metric, "cohort": cohort, "before_year": before, "after_year": after,
                             "n_before": 6 if cohort == "available" else 4, "n_after": 8 if cohort == "available" else 4,
                             "n_overlap": 4, "n_clusters": 10 if cohort == "available" else 4,
                             "observed_change": .2, "posterior_mean": .25, "posterior_sd": .2,
                             "ci_lower": -.125, "ci_upper": .625, "credible_mass": .9, "p_increase": .8,
                             "p_decrease": .2, "p_zero": 0., "positive_draws": 80, "draws": 100,
                             "probability_mcse": .04, "mean_mcse": .02, "practical_threshold": math.nan,
                             "p_above_threshold": math.nan, "p_within_threshold": math.nan, "p_below_threshold": math.nan,
                             "status": "ok", "employee_id": "PRIVATE_ADDED_ID", "raw_text": "PRIVATE_RAW_TEXT"})
    tables["bayesian_contrasts"] = pd.DataFrame(rows)
    tables["bayesian_annual"] = pd.DataFrame([
        {"metric": metric, "year": year, "n_employees": 6, "observed_mean": 1., "posterior_mean": 1.1,
         "posterior_sd": .2, "ci_lower": .7, "ci_upper": 1.4, "credible_mass": .9, "draws": 100,
         "mean_mcse": .02, "status": "ok", "raw_text": "PRIVATE_ANNUAL_TEXT"}
        for metric in METRICS for year in (2023, 2024, 2025)
    ])
    manifest = {"synthetic": True, "backend": {"kind": "demo", "model": "fabricated", "revision": "demo-test"},
                "run_id": "test-report", "rubric": {"version": "v1"},
                "bayesian": {"enabled": True, "effective_settings": {"draws": 100, "credible_mass": .9, "seed": 2026, "draw_batch_size": 64}}}
    return tables, manifest


def test_as_b11_content_actual_level_limits_and_private_fields(report_inputs):
    tables, manifest = report_inputs
    html = render(tables, manifest)
    inference = html[html.index("Bayesian inference for annual changes"):html.index("<h2>Annual employee means")]
    assert inference.index("Read these assumptions") < inference.index("Primary comparison")
    for text in ("exchangeable", "observation and eligibility", "complete census", "fixed census means", "unvalidated Clef", "manager effects", "company-year shocks", "No counterfactual AI causal effect", "not the range of individual goals", "90% equal-tailed", "90% [-0.125, 0.625]", "0.8000", "Available annual employees", "Paired employees", "positive_draws", "probability_mcse", "mean_mcse", "Common three-year", "Historical contrasts", "Annual Bayesian", "zero-concentration", "multinomial likelihood", "not a claim that the prior was uniform", "not automatically improvements"):
        assert text in inference
    assert "95%" not in inference and "No intervals or significance tests" not in html
    assert "PRIVATE_" not in html and "employee_id" not in html and "raw_text" not in html
    assert html.index("SYNTHETIC DEMONSTRATION") < html.index("Bayesian inference")
    assert html.index("no human validation") < html.index("Bayesian inference")
    assert not re.search(r"<(?:script|link|iframe)\b|(?:src|href)=[\"']https?://", html, re.I)
    assert "No practical thresholds were configured" in html
    assert "p_above_threshold estimates" not in html


def test_as_b11_escape_custom_metric_and_real_comparative_banner(report_inputs):
    tables, manifest = report_inputs
    injected = tables["bayesian_contrasts"].iloc[[0]].copy()
    injected["metric"] = '<img src=x onerror="PRIVATE_JS()">'
    tables["bayesian_contrasts"] = pd.concat([tables["bayesian_contrasts"], injected], ignore_index=True)
    manifest["synthetic"] = False
    manifest["backend"]["kind"] = "http"
    html = render(tables, manifest, title='<script>alert("x")</script>')
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "<img" not in html and "&lt;img" in html
    assert "Exploratory comparative results" in html and "not causal effects of AI" in html
    assert "PRIVATE_RAW_TEXT" not in html and "PRIVATE_ADDED_ID" not in html


@pytest.mark.parametrize("mode", ["legacy", "disabled", "empty"])
def test_as_b11_legacy_disabled_and_empty_are_explicit(report_inputs, mode):
    tables, manifest = report_inputs
    if mode == "legacy":
        manifest.pop("bayesian")
        tables.pop("bayesian_contrasts")
        tables.pop("bayesian_annual")
    elif mode == "disabled":
        manifest["bayesian"]["enabled"] = False
    else:
        tables["bayesian_contrasts"] = pd.DataFrame()
    html = render(tables, manifest)
    assert "Bayesian inference was not computed" in html
    assert "Annual employee means" in html
    assert "posterior means and" not in html


def test_as_b11_insufficient_and_degenerate_states(report_inputs):
    tables, manifest = report_inputs
    contrasts = tables["bayesian_contrasts"]
    contrasts["status"] = "insufficient_clusters"
    contrasts[["ci_lower", "ci_upper", "posterior_mean", "p_increase", "p_decrease", "p_zero"]] = math.nan
    html = render(tables, manifest)
    inference = html[html.index("Bayesian inference for annual changes"):html.index("<h2>Annual employee means")]
    assert "Insufficient clusters" in inference and "Not computed" in inference
    charts = re.findall(r"<svg.*?</svg>", inference)
    assert all("<circle" not in chart and "<path" not in chart for chart in charts)
    contrasts["status"] = "degenerate_empirical_support"
    contrasts[["ci_lower", "ci_upper", "posterior_mean"]] = 0.
    contrasts["p_increase"] = 0.
    html = render(tables, manifest)
    assert "90% [0.000, 0.000]" in html
    assert "not certainty about unobserved trajectories" in html
    assert "not proof that alternatives are impossible" in html


@pytest.mark.parametrize("narrow", [False, True])
def test_as_b11_forest_shared_scale_geometry_and_noncolor_cues(report_inputs, narrow):
    tables, _ = report_inputs
    frame = tables["bayesian_contrasts"].query("before_year == 2024 and cohort in ['available', 'paired'] and metric in ['clarity', 'specificity', 'assessability', 'coherence']").copy()
    # Broad interval must determine the same scale for every criterion/cohort.
    frame.loc[frame.metric.eq("coherence"), ["ci_lower", "ci_upper"]] = [-2., 1.]
    svg = bayesian_quality_chart(frame, narrow=narrow)
    root = ElementTree.fromstring(svg)
    width = float(root.attrib["viewBox"].split()[2])
    assert width == (390 if narrow else 720)
    assert "stroke-dasharray" in svg and "<circle" in svg and "<path" in svg
    assert "Score point change (2025 − 2024)" in svg and "90%" in svg
    assert "-2.20" in svg and "+2.20" in svg
    for element in root.iter():
        for attribute in ("x", "x1", "x2", "cx"):
            if attribute in element.attrib:
                assert 0 <= float(element.attrib[attribute]) <= width
    circles = list(root.iter("circle"))
    assert len(circles) == 4 and len({circle.attrib["cx"] for circle in circles}) == 1


def test_as_b11_configured_native_unit_thresholds_are_explained(report_inputs):
    tables, manifest = report_inputs
    tables["bayesian_contrasts"].loc[0, ["practical_threshold", "p_above_threshold", "p_within_threshold", "p_below_threshold"]] = [.1, .6, .3, .1]
    html = render(tables, manifest)
    assert "P(change &gt; t)" in html and "P(−t ≤ change ≤ t)" in html and "P(change &lt; −t)" in html
    assert "not a validated cutoff" in html and "No practical thresholds were configured" not in html


def test_as_b11_cached_clef_provenance_is_distinct_from_synthetic_inputs(report_inputs):
    tables, manifest = report_inputs
    manifest["backend"]["kind"] = "http"
    manifest["backend"]["model"] = "Cloudflare/clef-flash"
    manifest["backend"]["revision"] = "ggml-org/Clef-Flash-GGUF@" + "8aa35d" * 10
    manifest.update({"backend_calls": 0, "cache_hits": 595})
    html = render(tables, manifest)
    assert "SYNTHETIC DEMONSTRATION" in html
    assert "Demo probabilities are also fabricated" not in html
    assert "reused validated cached probabilities" in html and "zero new model calls" in html
    assert "Bayesian summaries were computed for this run" in html
    assert "p{max-width:90ch;overflow-wrap:anywhere}" in html


def test_as_b11_optional_metric_has_human_label_and_native_units(report_inputs):
    tables, manifest = report_inputs
    tables["bayesian_contrasts"].loc[0, "metric"] = "title_mean_word_length"
    html = render(tables, manifest)
    assert "Title · Mean word length" in html and "characters per word" in html
