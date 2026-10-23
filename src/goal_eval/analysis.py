"""Equal-employee summaries. Metric missingness determines each denominator."""
import pandas as pd
from .rubric import QUALITY, summarize, OPTIONS

LINGUISTIC = ("characters", "words", "sentences", "bullets", "mean_word_length", "mean_sentence_length", "flesch_ease", "fk_grade")
METRICS = list(QUALITY) + [f"{prefix}_{m}" for prefix in ("title", "description", "combined") for m in LINGUISTIC] + ["timing_present", "strategy_present"]


def employee_summary(df, metrics, mask=None):
    selected = df.loc[df["english_eligible"] if mask is None else mask].copy()
    keys = ["year", "employee_id"]
    if selected.empty:
        return pd.DataFrame(columns=keys + ["eligible_goals"] + metrics + [m + "__n" for m in metrics])
    grouped = selected.groupby(keys, sort=True)
    result = grouped[metrics].mean()
    counts = grouped[metrics].count().add_suffix("__n")
    return result.join(counts).join(grouped.size().rename("eligible_goals")).reset_index()


def annual_summary(employee, metrics):
    rows = []
    for year in (2023, 2024, 2025):
        group = employee.loc[employee["year"] == year]
        for metric in metrics:
            valid = group[metric].dropna()
            rows.append({"year": year, "metric": metric, "mean": valid.mean() if len(valid) else None,
                         "n_employees": len(valid), "n_valid_goals": int(group[metric + "__n"].sum()),
                         "n_eligible_goals": int(group["eligible_goals"].sum()), "eligible_employees": len(group)})
    result = pd.DataFrame(rows)
    result["mean"] = pd.to_numeric(result["mean"], errors="raise")
    return result


def comparisons(employee, metrics, observed):
    rows, trajectories = [], []
    common = set.intersection(*(set(observed.loc[observed.year == y, "employee_id"]) for y in (2023, 2024, 2025)))
    for metric in metrics:
        pivot = employee.pivot(index="employee_id", columns="year", values=metric).reindex(columns=[2023, 2024, 2025])
        for cohort in ("paired_2024_2025", "common_three_years"):
            valid = pivot[[2024, 2025]].dropna() if cohort == "paired_2024_2025" else pivot.loc[pivot.index.isin(common)].dropna()
            for employee_id, values in valid.iterrows():
                rows.append({"cohort": cohort, "metric": metric, "employee_id": employee_id,
                             "before": values[2024], "after": values[2025], "change": values[2025] - values[2024]})
            if cohort == "common_three_years":
                for year in (2023, 2024, 2025):
                    trajectories.append({"metric": metric, "year": year, "mean": valid[year].mean() if len(valid) else None, "n_employees": len(valid)})
    detail = pd.DataFrame(rows, columns=["cohort", "metric", "employee_id", "before", "after", "change"])
    summary = []
    for cohort in ("paired_2024_2025", "common_three_years"):
        for metric in metrics:
            values = detail.loc[(detail.cohort == cohort) & (detail.metric == metric), "change"]
            summary.append({"cohort": cohort, "metric": metric, "mean_change": values.mean() if len(values) else None, "n_employees": len(values)})
    return detail, pd.DataFrame(summary), pd.DataFrame(trajectories)


def analyze(df, cfg, metrics=None):
    metrics = metrics or [m for m in METRICS if m in df.columns]
    # Convert missing columns to numeric so all-missing metrics still aggregate.
    for metric in metrics:
        df[metric] = pd.to_numeric(df[metric], errors="raise")
    employee = employee_summary(df, metrics)
    annual = annual_summary(employee, metrics)
    contrasts = []
    for metric in metrics:
        values = annual.loc[annual.metric == metric].set_index("year")
        for before, after in ((2023, 2024), (2024, 2025)):
            contrasts.append({"metric": metric, "before_year": before, "after_year": after,
                              "mean_change": values.loc[after, "mean"] - values.loc[before, "mean"],
                              "n_before": values.loc[before, "n_employees"], "n_after": values.loc[after, "n_employees"]})
    paired_detail, paired, common = comparisons(employee, metrics, df[["year", "employee_id"]])
    coverage, counts, overlap = [], [], []
    for year in (2023, 2024, 2025):
        group = df.loc[df.year == year]
        eligible = group.loc[group.english_eligible]
        vals = {"input_goals": len(group), "observed_employees": group.employee_id.nunique(), "english_goals": len(eligible), "english_employees": eligible.employee_id.nunique()}
        if "text_sha256" in group:
            vals["distinct_combined_texts"] = group.text_sha256.nunique()
            vals["records_in_repeated_text_groups"] = int(group.text_sha256.duplicated(keep=False).sum())
            vals["english_distinct_combined_texts"] = eligible.text_sha256.nunique()
            vals["english_repeated_rows_beyond_first"] = len(eligible) - eligible.text_sha256.nunique()
        for reason, n in group.language_reason.value_counts().items():
            vals[f"language_{reason}"] = int(n)
        for state, n in group.description_state.value_counts().items():
            vals[f"description_{state}"] = int(n)
        if "score_status" in group:
            for state, n in group.score_status.value_counts().items():
                vals[f"scoring_{state}"] = int(n)
        for metric in metrics:
            vals[f"valid_{metric}"] = int(eligible[metric].notna().sum())
        for key in QUALITY:
            if key + "_abstained" in eligible:
                vals[f"abstained_{key}"] = int(eligible[key + "_abstained"].eq(True).sum())
        for field, value in vals.items():
            coverage.append({"year": year, "measure": field, "count": value})
        for n, count in eligible.groupby("employee_id").size().value_counts().sort_index().items():
            counts.append({"year": year, "goals_per_employee": int(n), "employees": int(count)})
    for a, b in ((2023, 2024), (2024, 2025), (2023, 2025)):
        for name, subset in (("observed", df), ("english", df.loc[df.english_eligible])):
            ids_a = set(subset.loc[subset.year == a, "employee_id"])
            ids_b = set(subset.loc[subset.year == b, "employee_id"])
            overlap.append({"population": name, "before_year": a, "after_year": b, "before_employees": len(ids_a), "after_employees": len(ids_b), "overlap_employees": len(ids_a & ids_b)})
    sensitivity = []
    if "language_confidence" in df:
        for threshold in sorted(set(cfg["language"]["sensitivity_thresholds"] + [cfg["language"]["threshold"]])):
            mask = df.language.eq("en") & df.language_evidence & df.language_confidence.ge(threshold)
            result = annual_summary(employee_summary(df, metrics, mask), metrics)
            result["sensitivity"], result["setting"] = "english_threshold", str(threshold)
            sensitivity.append(result)
    for threshold in (.25, .5, .75):
        if not all(m + "_p_0" in df for m in QUALITY):
            break
        altered = df.copy()
        for metric in QUALITY:
            mass = sum(df[f"{metric}_p_{k}"] for k in ("0", "1", "2", "3"))
            expected = sum(i * df[f"{metric}_p_{i}"] for i in range(4)) / mass
            altered[metric] = expected.where(df[f"{metric}_p_not_assessable"].lt(threshold) & mass.gt(0))
        result = annual_summary(employee_summary(altered, list(QUALITY)), list(QUALITY))
        result["sensitivity"], result["setting"] = "abstention_threshold", str(threshold)
        sensitivity.append(result)
    if "combined_words" in df:
        for low, high, label in ((0, 9, "0–9 words"), (10, 29, "10–29 words"), (30, 10**9, "30+ words")):
            mask = df.english_eligible & df.combined_words.between(low, high)
            result = annual_summary(employee_summary(df, metrics, mask), metrics)
            result["sensitivity"], result["setting"] = "length_band", label
            sensitivity.append(result)
    if all("title_" + m in df for m in QUALITY):
        altered = df.copy()
        for metric in QUALITY:
            altered[metric] = altered["title_" + metric]
        mask = altered.get("title_english_eligible", altered.english_eligible).fillna(False)
        result = annual_summary(employee_summary(altered, list(QUALITY), mask), list(QUALITY))
        result["sensitivity"], result["setting"] = "title_only", "title language eligibility"
        sensitivity.append(result)
    distributions = []
    for metric in QUALITY:
        if metric not in df:
            continue
        for year in (2023, 2024, 2025):
            vals = df.loc[df.year.eq(year) & df.english_eligible, metric].dropna()
            for low, high in ((0, .75), (.75, 1.5), (1.5, 2.25), (2.25, 3.000001)):
                distributions.append({"year": year, "metric": metric, "lower": low, "upper": min(3, high), "goals": int(((vals >= low) & (vals < high)).sum())})
    return {"employee_year": employee, "annual": annual, "contrasts": pd.DataFrame(contrasts), "paired_detail": paired_detail,
            "paired": paired, "common_three_years": common, "coverage": pd.DataFrame(coverage), "employee_overlap": pd.DataFrame(overlap),
            "goal_counts": pd.DataFrame(counts, columns=["year", "goals_per_employee", "employees"]),
            "distributions": pd.DataFrame(distributions),
            "sensitivities": pd.concat(sensitivity, ignore_index=True) if sensitivity else pd.DataFrame(columns=["sensitivity", "setting", "year", "metric", "mean", "n_employees"])}
