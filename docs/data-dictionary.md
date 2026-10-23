# Local output data dictionary

`manifest.json` at the output root governs current status and locates the successful run directory. Historical/partial directories are not current success. CSV numerical missing values are empty; Parquet uses null. Use `dtype={"employee_id": str}` and `keep_default_na=False` for scored CSV string columns.

| File / field | Meaning |
| --- | --- |
| `scored.csv`, `scored.parquet` | One row for every retained source record, including exclusions and failures. Private: contains original text and IDs. |
| `record_id` | SHA-256 of source fingerprint, configured year and one-based source record number. Duplicate source rows have distinct IDs. |
| `source_sha256`, `source_row`, `year` | Original input fingerprint, logical record number excluding header, explicit configured year. |
| `employee_id` | Original string ID; no integer conversion or automatic trimming. |
| `title`, `description`, `combined` | Original strings and consistently delimited combined text; no missing-description imputation. |
| `title_state`, `description_state` | `missing`, `blank`, `whitespace`, `present`. State columns disambiguate missing vs empty in CSV. |
| `text_sha256` | Digest of exact combined text; supports repeated-template coverage. Does not anonymize guessable text. |
| `language`, `language_confidence`, `language_evidence`, `language_reason`, `english_eligible` | Predicted code, normalized detector confidence, minimum-evidence flag, explicit exclusion reason and primary eligibility. `title_` versions describe title eligibility. |
| `{title,description,combined}_characters/words/sentences/bullets/syllables/oov_words` | Mechanical text measurements defined in methods; absent/unusable text remains missing. |
| `*_mean_word_length`, `*_mean_sentence_length` | Mean alphabetic token length in characters; words per sentence segment. |
| `*_flesch_ease`, `*_fk_grade`, `*_readability_eligible`, `*_fragment` | Formula readability and declared evidence flags; short text gets missing formulas. |
| `{clarity,specificity,assessability,coherence}_p_{0,1,2,3,not_assessable}` | Full probabilities. Demo values are fabricated. `title_` variants retain title-only distributions. |
| `clarity`, `specificity`, `assessability`, `coherence` | Conditional ordinal expectation (0–3), or missing on abstention/failure/exclusion. No total quality field. |
| `*_entropy`, `*_abstained` | Normalized assessable-option entropy and NA policy result, missing if unscored. |
| `{timing,strategy}_{present,absent,not_assessable}` | Full descriptive flag probabilities. `title_` variants have the same definitions. |
| `score_status`, `title_score_status` | `scored`, `language_excluded` or `failed`; candidate scoring can extend below primary threshold for sensitivity. |
| `any_inference_failed` | True if either combined/title inference failed after retries; makes run fail. |
| `employee_year.csv` | Per-employee/year metric means, each `metric__n` valid-goal count, and `eligible_goals`; private IDs. |
| `annual.csv` | Year/metric mean of employee means; `n_employees`, `n_valid_goals`, `n_eligible_goals`, `eligible_employees`. Each metric has its own valid denominator. |
| `contrasts.csv` | Metric, before/after year, annual `mean_change` and valid employee counts per year. |
| `paired_detail.csv` | Private employee ID, metric, cohort, before/after and change. Metric-specific paired or complete common-three-year set. |
| `paired.csv` | Cohort/metric mean employee change and actual valid employee count. |
| `common_three_years.csv` | Annual means on the same metric-complete three-year employee set; reports its denominator. |
| `coverage.csv` | Long year/measure/count table: input/eligible observations and employees, language reasons, description states, valid metrics, abstentions and scoring statuses. `distinct_combined_texts` counts all exact text groups; `records_in_repeated_text_groups` counts all rows in groups occurring twice or more (including first occurrences). `english_distinct_combined_texts` restricts unique text groups to eligible English goals; `english_repeated_rows_beyond_first` is eligible rows minus those unique groups. These count exact text, not semantic duplicates. Unobserved count categories are absent rather than fabricated rows. |
| `employee_overlap.csv` | Observed or English employee sets in each pair of years and their intersection count. |
| `goal_counts.csv` | Eligible goals per employee frequency distribution by year. |
| `distributions.csv` | Counts in fixed expectation bins [0,.75), [.75,1.5), [1.5,2.25), [2.25,3], by quality/year. |
| `sensitivities.csv` | Equal-employee annual summaries and denominators by sensitivity type/setting (English threshold, abstention cutoff, word-count band, title-only). |
| `bayesian_annual.csv` | Employee-cluster Bayesian bootstrap annual mean summaries for configured metrics; default 27 rows. Empty when disabled. No employee IDs or raw text. |
| `bayesian_contrasts.csv` | Posterior change summaries for configured metrics, two contrasts and three cohorts; default 54 rows. Empty when disabled. No employee IDs or raw text. |
| `report.html` | Self-contained escaped report; excludes employee IDs/raw text. Data tables are accessible alternatives to charts. |
| `manifest.json` | Run status, input/config/rubric/backend/runtime/code identities, seeds, coverage/failures and benchmark details. Paths/config can be sensitive. |

The SQLite cache contains validated successful probability payloads keyed by text and scoring identity. It stores no original text, but hashes are not a privacy guarantee. Cache, scored exports, employee summaries and local configs must stay private. The report's count denominators refer to records/employees for the specified metric/cohort, not a workforce headcount.

## Bayesian fields

All inference conditions on fixed proxy measurements, eligible groups and exchangeable joint employee trajectories (including observation/eligibility patterns). These are conditional generalization estimates, not uncertainty about already known census means, individual-goal prediction intervals or causal AI effects. Missing inference is never zero. Credible intervals and posterior probabilities differ from Clef's rubric-option probabilities; MCSE describes numerical draw error. See [methods and limitations](methods.md#bayesian-employee-cluster-bootstrap).

| Field | Meaning |
| --- | --- |
| `metric`, `year` | Analysis metric and annual snapshot. Defaults are four quality expectations, `combined_words`, `combined_flesch_ease`, `combined_fk_grade`, `timing_present`, `strategy_present`. |
| `cohort` | `available` annual metric-valid sets; `paired` metric-valid in both contrasted years; `common_three_years` observed and metric-valid in all three years. |
| `before_year`, `after_year` | Direction is after minus before: primary 2025−2024, historical 2024−2023. |
| `n_employees` | Annual metric-valid employee count. |
| `n_before`, `n_after` | Metric-valid counts in each year after the specified cohort restriction. |
| `n_overlap`, `n_clusters` | Intersection and union of annual sets for `available`; both equal selected cohort size for paired/common-three-year. |
| `observed_mean`, `observed_change` | Fixed equal-employee annual mean or after-minus-before change, retained even when a posterior cannot be computed. |
| `posterior_mean`, `posterior_sd` | Mean and standard deviation of independent posterior draws for the annual mean or mean change. |
| `ci_lower`, `ci_upper`, `credible_mass` | Equal-tailed posterior quantiles and configured central mass, e.g. 0.95; CrI units match the metric. |
| `draws` | Number of independent draws used for this estimate; zero for `insufficient_clusters`. |
| `p_increase`, `p_decrease`, `p_zero` | Posterior draw fractions with change >0, <0, =0. Values 0/1 from finite draws do not prove impossibility/certainty. Exact zero is not a practical-equivalence threshold. |
| `positive_draws` | Count of draws with change >0; `p_increase = positive_draws / draws` when computed. |
| `probability_mcse` | Plug-in Monte Carlo standard error for `p_increase`; zero at finite-draw 0/1 is not proof about rare tails. |
| `mean_mcse` | Monte Carlo standard error for `posterior_mean`; not posterior uncertainty or measurement-error uncertainty. |
| `practical_threshold` | Optional user-specified positive native-unit threshold; missing by default. No validated meaningful cutoff is implied. |
| `p_above_threshold`, `p_within_threshold`, `p_below_threshold` | Draw fractions with change >t, −t ≤ change ≤ t, change <−t; missing unless a threshold is configured for that metric. |
| `status` | `ok`; `insufficient_clusters` (fewer than two valid employees in a required annual set or selected cohort: no posterior interval/probability); `degenerate_empirical_support` (constant support yields point interval, without certainty about unseen trajectories). |

Quality units are score points, length is words per goal, Flesch Reading Ease uses formula points, Flesch–Kincaid uses grade units, and flags use probability points on 0–1. A 0.01 probability-point change is one percentage point. Higher values do not automatically imply improvement.

`manifest.bayesian` records `enabled`, `model_version`, `method`, `effective_settings`, `settings_sha256`, RNG/seed, `cluster_unit`, elapsed seconds, row counts/status counts, assumptions and maximum draw-weight buffer information. It documents independent Bayesian-bootstrap computation and is separate from scoring backend/cache statistics. `enabled: false` gives `status: disabled` and empty Bayesian tables; old reports without this metadata explicitly say inference was not computed.
