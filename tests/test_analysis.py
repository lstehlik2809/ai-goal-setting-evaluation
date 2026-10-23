"""AS-06/07: literal independent fixture, not an implementation-derived oracle."""
import pandas as pd
import pytest
from goal_eval.analysis import analyze


def oracle_fixture():
    rows = []
    def add(employee, year, clarity, second):
        rows.append({"employee_id": employee, "year": year, "clarity": clarity, "specificity": second,
                     "english_eligible": True, "language_reason": "eligible", "description_state": "missing"})
    add("001", 2023, 1, 1)
    for _ in range(3):
        add("001", 2024, 0, 1)
    add("001", 2025, 2, 1)
    add("002", 2024, 3, None)
    add("002", 2025, 1, 3)
    add("002", 2025, 1, 3)
    add("003", 2024, None, 2)
    add("003", 2025, 0, 0)
    add("004", 2023, 3, 3)
    return pd.DataFrame(rows)


def test_as06_employee_weighting_counts_contrasts_export(tmp_path):
    tables = analyze(oracle_fixture(), {}, ["clarity", "specificity"])
    annual = tables["annual"].query("metric == 'clarity'").set_index("year")
    assert annual["mean"].to_dict() == {2023: 2, 2024: 1.5, 2025: 1}
    assert annual.loc[2024, ["n_eligible_goals", "n_valid_goals", "eligible_employees", "n_employees"]].tolist() == [5, 4, 3, 2]
    contrasts = tables["contrasts"].query("metric == 'clarity'")
    assert contrasts.mean_change.tolist() == [-.5, -.5]
    tables["annual"].to_csv(tmp_path / "annual.csv", index=False)
    exported = pd.read_csv(tmp_path / "annual.csv")
    assert exported.query("metric == 'clarity'")["mean"].tolist() == [2, 1.5, 1]


def test_as07_metric_specific_pairs_and_three_year_completeness():
    tables = analyze(oracle_fixture(), {}, ["clarity", "specificity"])
    detail = tables["paired_detail"]
    clarity = detail.query("cohort == 'paired_2024_2025' and metric == 'clarity'")
    assert clarity.employee_id.tolist() == ["001", "002"]
    assert clarity.change.tolist() == [2, -2]
    second = detail.query("cohort == 'paired_2024_2025' and metric == 'specificity'")
    assert second.employee_id.tolist() == ["001", "003"] and second.change.tolist() == [0, -2]
    summary = tables["paired"].query("cohort == 'paired_2024_2025'").set_index("metric")
    assert summary.loc["clarity", "mean_change"] == 0
    assert summary.loc["specificity", "mean_change"] == -1
    common = detail.query("cohort == 'common_three_years' and metric == 'clarity'")
    assert common.employee_id.tolist() == ["001"] and common.change.tolist() == [2]
    frame = oracle_fixture()
    frame.loc[(frame.employee_id == "001") & (frame.year == 2023), "clarity"] = None
    tables = analyze(frame, {}, ["clarity", "specificity"])
    common = tables["common_three_years"].query("metric == 'clarity'")
    assert common.n_employees.tolist() == [0, 0, 0]
    assert common["mean"].isna().all()
    assert tables["paired"].query("cohort == 'paired_2024_2025' and metric == 'clarity'").n_employees.iloc[0] == 2
