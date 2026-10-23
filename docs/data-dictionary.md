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
| `report.html` | Self-contained escaped report; excludes employee IDs/raw text. Data tables are accessible alternatives to charts. |
| `manifest.json` | Run status, input/config/rubric/backend/runtime/code identities, seeds, coverage/failures and benchmark details. Paths/config can be sensitive. |

The SQLite cache contains validated successful probability payloads keyed by text and scoring identity. It stores no original text, but hashes are not a privacy guarantee. Cache, scored exports, employee summaries and local configs must stay private. The report's count denominators refer to records/employees for the specified metric/cohort, not a workforce headcount.
