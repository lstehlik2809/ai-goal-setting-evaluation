"""AS-B01–B12: observable Bayesian-bootstrap behavior and independent oracles."""
import json
import math
import numpy as np
import pandas as pd
import pytest
import goal_eval.bayesian as bayes
from goal_eval.analysis import employee_summary
from goal_eval.config import BAYESIAN_DEFAULT_METRICS, ConfigError, bayesian_settings, load_config


def settings(**changes):
    return bayesian_settings({"metrics": ["clarity"], "draws": 257, "seed": 37, **changes})


def trajectories(values, metric="clarity"):
    return pd.DataFrame([{"employee_id": f"{i:03d}", "year": year, metric: value}
                         for i, employee in enumerate(values, 1) for year, value in zip(bayes.YEARS, employee)])


def contrast(table, cohort="paired", before=2024, metric="clarity"):
    return table.query("metric == @metric and cohort == @cohort and before_year == @before").iloc[0]


def assert_draw_summary(row, expected):
    expected = np.array(expected)
    assert row.posterior_mean == pytest.approx(expected.mean())
    assert row.posterior_sd == pytest.approx(expected.std(ddof=1))
    assert row.ci_lower == pytest.approx(np.quantile(expected, .025))
    assert row.ci_upper == pytest.approx(np.quantile(expected, .975))
    assert row.mean_mcse == pytest.approx(expected.std(ddof=1) / math.sqrt(len(expected)))


def test_as_b01_defaults_and_table_schema(config_factory):
    cfg = load_config(config_factory(seed=91))
    effective = cfg["bayesian"]
    assert effective == {"enabled": True, "draws": 4000, "credible_mass": .95, "seed": 91,
                         "draw_batch_size": 64, "metrics": BAYESIAN_DEFAULT_METRICS, "practical_thresholds": {}}
    data = trajectories([[0, 1, 2], [1, 2, 3], [3, 1, 0]])
    for metric in BAYESIAN_DEFAULT_METRICS[1:]:
        data[metric] = data.clarity
    tables, metadata = bayes.analyze_bayesian(data, {**effective, "draws": 19})
    assert len(tables["bayesian_annual"]) == 27 and len(tables["bayesian_contrasts"]) == 54
    assert tables["bayesian_annual"].columns.tolist() == bayes.ANNUAL_COLUMNS
    assert tables["bayesian_contrasts"].columns.tolist() == bayes.CONTRAST_COLUMNS
    assert metadata["enabled"] is True and metadata["rng"]["bit_generator"] == "PCG64"
    assert metadata["effective_settings"]["seed"] == 91
    assert metadata["cluster_unit"].startswith("employee")
    assert metadata["settings_sha256"] and metadata["model_version"]
    json.dumps(metadata, allow_nan=False)
    for metric in BAYESIAN_DEFAULT_METRICS[1:]:
        for table in tables.values():
            left = table.query("metric == 'clarity'").drop(columns="metric").reset_index(drop=True)
            right = table.query("metric == @metric").drop(columns="metric").reset_index(drop=True)
            pd.testing.assert_frame_equal(left, right)


@pytest.mark.parametrize("invalid", [
    None, [], {"unknown": True}, {"enabled": 1}, {"draws": True}, {"draws": 1}, {"draws": 2.0},
    {"draw_batch_size": 0}, {"draw_batch_size": False}, {"draw_batch_size": 1.5},
    {"seed": -1}, {"seed": True}, {"seed": 1.0}, {"credible_mass": 0}, {"credible_mass": 1},
    {"credible_mass": True}, {"credible_mass": float("nan")}, {"credible_mass": float("inf")},
    {"metrics": []}, {"metrics": "clarity"}, {"metrics": ["unknown"]}, {"metrics": ["clarity", "clarity"]},
    {"practical_thresholds": []}, {"practical_thresholds": {"unknown": 1}},
    {"practical_thresholds": {"clarity": 0}}, {"practical_thresholds": {"clarity": -1}},
    {"practical_thresholds": {"clarity": True}}, {"practical_thresholds": {"clarity": float("inf")}},
    {"practical_thresholds": {"clarity": float("nan")}},
])
def test_as_b02_reject_invalid_settings(invalid):
    with pytest.raises(ConfigError):
        bayesian_settings(invalid)


def test_as_b02_explicit_existing_metric_and_config_validation(config_factory):
    cfg = load_config(config_factory(bayesian={"metrics": ["description_words"], "practical_thresholds": {"description_words": 2}}))
    assert cfg["bayesian"]["metrics"] == ["description_words"]
    with pytest.raises(ConfigError):
        load_config(config_factory(bayesian={"draws": False}))
    with pytest.raises(ConfigError):
        load_config(config_factory(bayesian=None))
    with pytest.raises(ConfigError):
        load_config(config_factory(bayesian={"credible_mass": float("nan")}))


def test_as_b03_uniform_analytic_oracle_and_threshold_probabilities():
    data = trajectories([[2, 2, 0], [0, 0, 2]])
    tables, _ = bayes.analyze_bayesian(data, settings(draws=40000, practical_thresholds={"clarity": .5}))
    row = contrast(tables["bayesian_contrasts"])
    assert abs(row.posterior_mean) < .04
    assert abs(row.posterior_sd - math.sqrt(4 / 3)) < .02
    assert abs(row.ci_lower + 1.9) < .025 and abs(row.ci_upper - 1.9) < .025
    assert abs(row.p_increase - .5) < .015
    assert abs(row.p_above_threshold - .375) < .015
    assert abs(row.p_within_threshold - .25) < .015
    assert abs(row.p_below_threshold - .375) < .015
    assert row.p_zero == 0 and row.p_increase + row.p_decrease + row.p_zero == 1
    assert row.p_increase == row.positive_draws / row.draws
    assert row.probability_mcse == pytest.approx(math.sqrt(row.p_increase * (1 - row.p_increase) / 40000))
    assert row.mean_mcse == pytest.approx(row.posterior_sd / 200)


def test_as_b04_shared_weights_make_identical_years_exact_zero():
    tables, _ = bayes.analyze_bayesian(trajectories([[0, 0, 0], [3, 3, 3], [1, 1, 1]]), settings())
    rows = tables["bayesian_contrasts"]
    assert (rows.status == "degenerate_empirical_support").all()
    assert (rows[["posterior_mean", "posterior_sd", "ci_lower", "ci_upper", "p_increase", "p_decrease", "positive_draws"]] == 0).all().all()
    assert (rows.p_zero == 1).all()
    assert tables["bayesian_annual"].posterior_sd.gt(0).all()


def test_as_b05_goal_replication_and_distinct_employee_clusters():
    goals = trajectories([[0, 0, 0], [0, 0, 0], [3, 3, 3]])
    goals["english_eligible"] = True
    original = employee_summary(goals, ["clarity"])
    replicated = employee_summary(pd.concat([goals] * 7, ignore_index=True), ["clarity"])
    first, metadata = bayes.analyze_bayesian(original, settings(draws=40000))
    second, _ = bayes.analyze_bayesian(replicated, settings(draws=40000))
    for name in first:
        pd.testing.assert_frame_equal(first[name], second[name])
    annual = first["bayesian_annual"].iloc[0]
    assert annual.n_employees == metadata["union_employee_count"] == 3
    assert annual.observed_mean == 1
    assert abs(annual.posterior_mean - 1) < .02
    assert abs(annual.posterior_sd**2 - .5) < .02  # Two deduplicated support values would give .75.


def test_as_b06_controlled_weight_missingness_oracle(monkeypatch):
    class Prescribed:
        def exponential(self, size):
            assert size == (2, 4)
            return np.array([[1., 2., 3., 4.], [4., 3., 2., 1.]])
    monkeypatch.setattr(bayes.np.random, "Generator", lambda bit_generator: Prescribed())
    data = trajectories([[1, 0, 2], [np.nan, 3, 1], [np.nan, np.nan, 0], [3, 1, 2]])
    data["specificity"] = [np.nan, 1, 3, 2, np.nan, 0, 0, 3, 1, np.nan, np.nan, np.nan]
    tables, _ = bayes.analyze_bayesian(data, settings(metrics=["clarity", "specificity"], draws=2))
    annual = tables["bayesian_annual"].query("metric == 'clarity'").reset_index(drop=True)
    assert annual.observed_mean.tolist() == [2, 4 / 3, 5 / 4]
    for row, draws, count in zip(annual.itertuples(), [[13 / 5, 7 / 5], [10 / 7, 5 / 4], [6 / 5, 13 / 10]], [2, 3, 4]):
        assert_draw_summary(row, draws)
        assert row.n_employees == count
    rows = tables["bayesian_contrasts"]
    expected = {("available", 2024): [-8 / 35, 1 / 20], ("available", 2023): [-41 / 35, -3 / 20],
                ("paired", 2024): [2 / 7, 3 / 8], ("paired", 2023): [-9 / 5, -6 / 5],
                ("common_three_years", 2024): [6 / 5, 9 / 5], ("common_three_years", 2023): [-9 / 5, -6 / 5]}
    for (cohort, before), expected_draws in expected.items():
        assert_draw_summary(contrast(rows, cohort, before), expected_draws)
    assert contrast(rows, "available", 2024)[["n_before", "n_after", "n_overlap", "n_clusters"]].tolist() == [3, 4, 3, 4]
    assert contrast(rows, "available", 2023)[["n_before", "n_after", "n_overlap", "n_clusters"]].tolist() == [2, 3, 2, 3]
    for cohort, count in [("paired", 3), ("common_three_years", 2)]:
        assert contrast(rows, cohort)[["n_before", "n_after", "n_overlap", "n_clusters"]].tolist() == [count] * 4
    other = tables["bayesian_annual"].query("metric == 'specificity'").reset_index(drop=True)
    for row, draws in zip(other.itertuples(), [[4 / 5, 6 / 5], [5 / 2, 5 / 3], [1, 14 / 9]]):
        assert_draw_summary(row, draws)
    assert_draw_summary(contrast(rows, "paired", metric="specificity"), [-1, 2 / 3])
    insufficient = contrast(rows, "common_three_years", metric="specificity")
    assert insufficient.n_clusters == 1 and insufficient.draws == 0
    assert insufficient.status == "insufficient_clusters" and pd.isna(insufficient.p_increase)


def test_as_b07_row_and_batch_reproducibility_and_allocation():
    data = trajectories([[1, np.nan, 2], [3, 1, 0], [2, 3, 1], [0, 2, np.nan]])
    original, original_meta = bayes.analyze_bayesian(data, settings(draw_batch_size=64))
    for batch in (1, 13, 300):
        result, metadata = bayes.analyze_bayesian(data.sample(frac=1, random_state=2), settings(draw_batch_size=batch))
        for name in original:
            pd.testing.assert_frame_equal(original[name], result[name], rtol=0, atol=1e-12)
        assert original["bayesian_contrasts"].positive_draws.equals(result["bayesian_contrasts"].positive_draws)
        assert metadata["max_weight_batch_rows"] == min(batch, 257)
        assert metadata["max_weight_buffer_bytes"] == min(batch, 257) * 4 * 8
        assert metadata["union_employee_count"] == 4
    assert original_meta["max_weight_shape"] == [64, 4]


def test_as_b08_disabled_stable_headers_and_no_simulation(monkeypatch):
    monkeypatch.setattr(bayes.np.random, "Generator", lambda *a: pytest.fail("disabled must not simulate"))
    tables, metadata = bayes.analyze_bayesian(pd.DataFrame(), settings(enabled=False))
    assert tables["bayesian_annual"].empty and tables["bayesian_contrasts"].empty
    assert tables["bayesian_annual"].columns.tolist() == bayes.ANNUAL_COLUMNS
    assert tables["bayesian_contrasts"].columns.tolist() == bayes.CONTRAST_COLUMNS
    assert metadata["status"] == "disabled" and metadata["enabled"] is False
    assert metadata["max_weight_buffer_bytes"] == 0


@pytest.mark.parametrize("data", [pd.DataFrame(columns=["employee_id", "year", "clarity"]), trajectories([[1, 2, 3]]), trajectories([[np.nan] * 3, [np.nan] * 3])])
def test_as_b09_empty_singleton_and_all_missing_withhold_posterior(data):
    tables, _ = bayes.analyze_bayesian(data, settings())
    assert len(tables["bayesian_annual"]) == 3 and len(tables["bayesian_contrasts"]) == 6
    for table in tables.values():
        assert table.status.eq("insufficient_clusters").all() and table.draws.eq(0).all()
        assert table[["posterior_mean", "posterior_sd", "ci_lower", "ci_upper", "mean_mcse"]].isna().all().all()
    assert tables["bayesian_contrasts"].p_increase.isna().all()
    if len(data) == 3:
        assert tables["bayesian_annual"].observed_mean.tolist() == [1, 2, 3]
        assert tables["bayesian_contrasts"].observed_change.tolist() == [1] * 6


def test_as_b09_available_requires_two_clusters_each_year():
    tables, _ = bayes.analyze_bayesian(trajectories([[0, 1, 2], [3, np.nan, 0]]), settings())
    row = contrast(tables["bayesian_contrasts"], "available")
    assert row.n_clusters == 2 and row.n_before == 1 and row.n_after == 2
    assert row.draws == 0 and row.status == "insufficient_clusters" and pd.isna(row.p_increase)


def test_as_b10_constants_and_probability_boundaries():
    tables, _ = bayes.analyze_bayesian(trajectories([[.1, .2, .3]] * 2), settings(practical_thresholds={"clarity": .1}))
    for table in tables.values():
        assert table.status.eq("degenerate_empirical_support").all()
        assert table.posterior_sd.eq(0).all() and table.mean_mcse.eq(0).all()
        assert table.ci_lower.equals(table.ci_upper)
    rows = tables["bayesian_contrasts"]
    assert rows.p_increase.eq(1).all() and rows.p_decrease.eq(0).all() and rows.p_zero.eq(0).all()
    unthresholded, _ = bayes.analyze_bayesian(trajectories([[0, 1, 2], [1, 0, 3]]), settings())
    assert unthresholded["bayesian_contrasts"][["practical_threshold", "p_above_threshold", "p_within_threshold", "p_below_threshold"]].isna().all().all()


@pytest.mark.parametrize("value", [np.inf, -np.inf, "not numeric"])
def test_as_b11_nonfinite_or_nonnumeric_input_rejected(value):
    data = trajectories([[1, 2, 3], [0, 1, 2]])
    data["clarity"] = data.clarity.astype(object)
    data.loc[0, "clarity"] = value
    with pytest.raises((ValueError, TypeError)):
        bayes.analyze_bayesian(data, settings())


@pytest.mark.parametrize("bad_weights", [np.nan, np.inf, 0, -1])
def test_as_b11_invalid_generated_weights_fail(monkeypatch, bad_weights):
    class Broken:
        def exponential(self, size):
            return np.full(size, bad_weights)
    monkeypatch.setattr(bayes.np.random, "Generator", lambda bit_generator: Broken())
    with pytest.raises(ValueError):
        bayes.analyze_bayesian(trajectories([[0, 1, 2], [1, 2, 3]]), settings())


def test_as_b11_nonfinite_calculation_and_duplicate_keys_fail():
    with np.errstate(over="ignore", invalid="ignore"):
        with pytest.raises(ValueError, match="Nonfinite"):
            bayes.analyze_bayesian(trajectories([[1e308, -1e308, 1e308], [1e308, -1e308, 1e308]]), settings())
    data = trajectories([[0, 1, 2], [1, 2, 3]])
    with pytest.raises(ValueError, match="unique"):
        bayes.analyze_bayesian(pd.concat([data, data.iloc[:1]]), settings())
