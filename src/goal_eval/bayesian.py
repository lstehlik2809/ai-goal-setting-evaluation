"""Employee-cluster Bayesian bootstrap, conditional on fixed observed proxies.

Dirichlet(1,...,1) is the posterior on observed employee trajectories, not a
Dirichlet prior with one pseudocount per employee. See the statistical design
record for the improper zero-concentration prior and the population target.
"""
import time
import numpy as np
import pandas as pd
from .config import bayesian_settings, digest


MODEL_VERSION = "employee-cluster-bayesian-bootstrap-v1"
YEARS = (2023, 2024, 2025)
CONTRASTS = ((2024, 2025), (2023, 2024))
ANNUAL_COLUMNS = ["metric", "year", "n_employees", "observed_mean", "posterior_mean", "posterior_sd",
                  "ci_lower", "ci_upper", "credible_mass", "draws", "mean_mcse", "status"]
CONTRAST_COLUMNS = ["metric", "cohort", "before_year", "after_year", "n_before", "n_after", "n_overlap",
                    "n_clusters", "observed_change", "posterior_mean", "posterior_sd", "ci_lower", "ci_upper",
                    "p_increase", "p_decrease", "p_zero", "probability_mcse", "mean_mcse", "positive_draws",
                    "draws", "credible_mass", "practical_threshold", "p_above_threshold", "p_within_threshold",
                    "p_below_threshold", "status"]
ASSUMPTIONS = [
    "Hypothetical exchangeable joint employee trajectories on the observed empirical support; conditional on metric missingness.",
    "This is not uncertainty about the known finite observed census means.",
    "Clef scores and text features are fixed proxies; no human-rating validity, calibration or measurement-error uncertainty is modeled.",
    "Shared manager effects and year shocks are not modeled; a causal AI effect is not identified.",
    "Dirichlet(1,...,1) posterior follows an improper zero-concentration/Haldane prior and multinomial likelihood on observed employee trajectories.",
    "Probability zero or one is a Monte Carlo estimate, not proof about rare tails; no MCMC convergence diagnostics apply.",
]


def _finite(values, label):
    if not np.isfinite(values).all():
        raise ValueError(f"Nonfinite Bayesian {label}")


def _constant(values):
    return float(values[0]) if len(values) and np.all(values == values[0]) else None


def _summary(draws, settings, contrast=False, threshold=None):
    _finite(draws, "posterior draws")
    count = len(draws)
    constant = _constant(draws)
    sd = 0.0 if constant is not None else float(np.std(draws, ddof=1))
    tail = (1 - settings["credible_mass"]) / 2
    lower, upper = np.quantile(draws, [tail, 1 - tail])
    result = {"posterior_mean": constant if constant is not None else float(np.mean(draws)), "posterior_sd": sd,
              "ci_lower": float(lower), "ci_upper": float(upper), "mean_mcse": sd / np.sqrt(count)}
    if contrast:
        positive = int(np.count_nonzero(draws > 0))
        p = positive / count
        result.update({"p_increase": p, "p_decrease": int(np.count_nonzero(draws < 0)) / count,
                       "p_zero": int(np.count_nonzero(draws == 0)) / count, "positive_draws": positive,
                       "probability_mcse": float(np.sqrt(p * (1 - p) / count))})
        if threshold is not None:
            result.update({"p_above_threshold": int(np.count_nonzero(draws > threshold)) / count,
                           "p_within_threshold": int(np.count_nonzero(np.abs(draws) <= threshold)) / count,
                           "p_below_threshold": int(np.count_nonzero(draws < -threshold)) / count})
    _finite(list(result.values()), "summary")
    return result


def analyze_bayesian(employee_year, settings):
    """Return aggregate annual/contrast tables and JSON-safe inference metadata.

    Input must already contain one eligible-goal mean per employee/year. Missing
    numeric values are retained as missing; infinities and duplicate keys fail.
    Only one batch-by-employee weight array exists at a time.
    """
    start = time.perf_counter()
    settings = bayesian_settings(settings)
    metadata = {"model_version": MODEL_VERSION, "method": "employee-cluster Bayesian bootstrap",
                "enabled": settings["enabled"], "effective_settings": settings, "settings_sha256": digest(settings),
                "rng": {"bit_generator": "PCG64", "seed": settings["seed"], "draw_order": "draw-major; employee IDs sorted"},
                "cluster_unit": "employee; one shared weight across all metrics, years and cohorts",
                "assumptions": ASSUMPTIONS.copy(), "n_employee_clusters": 0,
                "max_weight_shape": [0, 0], "max_weight_bytes": 0,
                "max_weight_batch_rows": 0, "max_weight_buffer_bytes": 0, "union_employee_count": 0}
    if not settings["enabled"]:
        metadata.update({"status": "disabled", "elapsed_seconds": time.perf_counter() - start,
                         "annual_rows": 0, "contrast_rows": 0})
        return {"bayesian_annual": pd.DataFrame(columns=ANNUAL_COLUMNS),
                "bayesian_contrasts": pd.DataFrame(columns=CONTRAST_COLUMNS)}, metadata
    metrics = settings["metrics"]
    required = ["employee_id", "year"] + metrics
    if any(name not in employee_year for name in required):
        raise ValueError("Bayesian input lacks required employee/year/metric columns")
    data = employee_year[required].copy()
    if data[["employee_id", "year"]].isna().any().any() or data.duplicated(["employee_id", "year"]).any():
        raise ValueError("Bayesian input needs unique, nonmissing employee/year keys")
    if not data.year.isin(YEARS).all():
        raise ValueError("Bayesian input year must be 2023, 2024 or 2025")
    for metric in metrics:
        data[metric] = pd.to_numeric(data[metric], errors="raise")
        _finite(data[metric].dropna().to_numpy(dtype=float), "input")
    employees = sorted(data.employee_id.unique())
    n = len(employees)
    metadata["n_employee_clusters"] = n
    metadata["union_employee_count"] = n
    annual_rows, contrast_rows, estimators = [], [], []
    # Each estimator is (row, numerator-column, denominator-column, constant,
    # draw-array). Vectors contain numeric sufficient statistics, never raw text.
    vectors = []
    def estimator(row, values, mask, constant=None):
        row.update({"credible_mass": settings["credible_mass"], "draws": 0, "status": "insufficient_clusters"})
        if np.count_nonzero(mask) < 2:
            return None
        row.update({"draws": settings["draws"], "status": "degenerate_empirical_support" if constant is not None else "ok"})
        num = den = None
        if constant is None:
            num, den = len(vectors), len(vectors) + 1
            vectors.extend([np.where(mask, values, 0.0), mask.astype(float)])
        draws = np.full(settings["draws"], constant, dtype=float) if constant is not None else np.empty(settings["draws"])
        estimators.append((row, num, den, constant, draws))
        return draws

    available = []
    for metric in metrics:
        values = data.pivot(index="employee_id", columns="year", values=metric).reindex(index=employees, columns=YEARS).to_numpy(dtype=float)
        valid = ~np.isnan(values)
        annual_draws = {}
        for j, year in enumerate(YEARS):
            vals, mask = values[:, j], valid[:, j]
            observed = float(vals[mask].mean()) if mask.any() else None
            row = {"metric": metric, "year": year, "n_employees": int(mask.sum()), "observed_mean": observed}
            _finite([observed] if observed is not None else [], "observed annual mean")
            annual_draws[year] = estimator(row, vals, mask, _constant(vals[mask]))
            annual_rows.append(row)
        for cohort in ("available", "paired", "common_three_years"):
            for before, after in CONTRASTS:
                a, b = YEARS.index(before), YEARS.index(after)
                ma, mb = valid[:, a], valid[:, b]
                mask = ma & mb if cohort == "paired" else valid.all(axis=1)
                if cohort == "available":
                    na, nb = int(ma.sum()), int(mb.sum())
                    overlap, clusters = int((ma & mb).sum()), int((ma | mb).sum())
                    observed = float(values[mb, b].mean() - values[ma, a].mean()) if na and nb else None
                else:
                    na = nb = overlap = clusters = int(mask.sum())
                    observed = float(np.mean(values[mask, b] - values[mask, a])) if clusters else None
                _finite([observed] if observed is not None else [], "observed change")
                row = {"metric": metric, "cohort": cohort, "before_year": before, "after_year": after,
                       "n_before": na, "n_after": nb, "n_overlap": overlap, "n_clusters": clusters,
                       "observed_change": observed, "practical_threshold": settings["practical_thresholds"].get(metric)}
                if cohort == "available":
                    row.update({"credible_mass": settings["credible_mass"], "draws": 0, "status": "insufficient_clusters"})
                    if min(na, nb) >= 2:
                        constant = _constant(values[mb, b])
                        before_constant = _constant(values[ma, a])
                        constant = constant - before_constant if constant is not None and before_constant is not None else None
                        if np.array_equal(ma, mb):
                            constant = _constant(values[ma, b] - values[ma, a])
                        row.update({"draws": settings["draws"], "status": "degenerate_empirical_support" if constant is not None else "ok"})
                        available.append((row, annual_draws[before], annual_draws[after], constant))
                else:
                    changes = np.zeros(n)
                    changes[mask] = values[mask, b] - values[mask, a]
                    _finite(changes, "employee change")
                    estimator(row, changes, mask, _constant(changes[mask]))
                contrast_rows.append(row)

    # Draw-major PCG64 is invariant to batch size, including a short final batch.
    # Explicitly release the old batch before generating the next one.
    matrix = np.column_stack(vectors) if vectors else None
    del vectors
    rng = np.random.Generator(np.random.PCG64(settings["seed"]))
    if matrix is not None:
        _finite(matrix, "sufficient statistics")
        for offset in range(0, settings["draws"], settings["draw_batch_size"]):
            size = min(settings["draw_batch_size"], settings["draws"] - offset)
            weights = rng.exponential(size=(size, n))
            _finite(weights, "weights")
            if (weights <= 0).any():
                raise ValueError("Bayesian weights must be strictly positive")
            metadata["max_weight_shape"] = [max(metadata["max_weight_shape"][0], size), n]
            metadata["max_weight_bytes"] = max(metadata["max_weight_bytes"], weights.nbytes)
            metadata["max_weight_batch_rows"] = metadata["max_weight_shape"][0]
            metadata["max_weight_buffer_bytes"] = metadata["max_weight_bytes"]
            totals = weights @ matrix
            _finite(totals, "weighted totals")
            for _, num, den, constant, draws in estimators:
                if constant is None:
                    if (totals[:, den] <= 0).any():
                        raise ValueError("Bayesian denominator must be positive")
                    draws[offset:offset + size] = totals[:, num] / totals[:, den]
            del weights, totals
    for row, _, _, _, draws in estimators:
        row.update(_summary(draws, settings, "cohort" in row, row.get("practical_threshold")))
    for row, before_draws, after_draws, constant in available:
        draws = after_draws - before_draws if constant is None else np.full(settings["draws"], constant)
        row.update(_summary(draws, settings, True, row["practical_threshold"]))
    tables = {"bayesian_annual": pd.DataFrame(annual_rows, columns=ANNUAL_COLUMNS),
              "bayesian_contrasts": pd.DataFrame(contrast_rows, columns=CONTRAST_COLUMNS)}
    metadata.update({"status": "success", "elapsed_seconds": time.perf_counter() - start,
                     "annual_rows": len(annual_rows), "contrast_rows": len(contrast_rows),
                     "status_counts": {name: {str(k): int(v) for k, v in table.status.value_counts().items()} for name, table in tables.items()}})
    return tables, metadata
