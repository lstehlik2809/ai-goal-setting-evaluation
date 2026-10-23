# Build brief: AI availability and employee goal setting

Version: v1 | Date: 2026-10-23 | Status: accepted for initial implementation; synthetic workflow implemented and under release review. Actual Clef execution and intended-machine feasibility remain unverified.

## Purpose and agreed scope

Build a reproducible Python pipeline to examine how recorded goals changed after AI became available and identify priorities for redesigning the company's goal-setting agent. Analyze 2023 and 2024 as pre-rollout years and 2025 as the first year with AI available globally. Goals are a mixture of performance, development, and OKR-style goals, jointly negotiated by employees and managers.

Use English-language goals in the initial analysis. Inputs are separate CSV files for 2023, 2024, and 2025, preserving original goal-setting snapshots. Each contains employee ID, goal name, and an optional goal description, with one row per goal. Derive year from an explicit configured file-to-year mapping. Design for approximately 400,000 goals per year if the reported 80,000 employees and five goals apply annually; this scale is provisional. Employee attributes are available but excluded from v1. Human rating and validation are outside this initial phase.

Publish code and synthetic examples in a new public GitHub repository, provisionally named `ai-goal-setting-evaluation`. Real inputs, outputs, caches, model weights, and credentials stay outside the repository. All processing and model inference run locally after dependencies and weights have been acquired.

## Evaluation design

The primary comparison is 2025 versus 2024. Use the 2024 versus 2023 change as historical context. Report changes in recorded language and model-assessed textual qualities, rather than attributing them to AI or to employees alone. Availability does not establish actual AI use.

The causal problem is that calendar year determines AI availability while also allowing business conditions, goal-setting processes, workforce composition, and export practices to change. These other paths can change recorded goals. Restricting to repeat employees addresses only part of this structure; restricting to English goals adds selection that may itself vary after rollout.

Retain all eligible records. Within each year, average each metric across an employee's eligible goals and then across employees, so employees with more goals do not dominate. Also show goal-level distributions, goal counts per employee, and denominator/coverage tables. Missing scores remain missing and are never converted to zero.

Provide a paired 2024-2025 comparison for employees with eligible English goals in both years, plus a sensitivity analysis restricted to employees observed in all three years. These address different populations; neither removes common year-specific shocks. Absence from a goals export is not evidence that an employee left the company. Do not attempt to pair individual goals across years without a reliable goal identifier.

Identification strategy: no defensible causal strategy is established with the available design; use descriptive annual and within-employee contrasts.

Required assumptions for causal attribution: a credible untreated counterfactual, comparable goal snapshots, and a defensible account of concurrent changes and observation/selection. These are not established.

Empirically assessable implications: inspect 2023-2024 changes, employee overlap, language eligibility, missingness, repeated templates, and available export provenance. These checks cannot establish the missing counterfactual.

Identification status: **not identified** for the causal effect of AI. One globally treated company and three annual observations do not support an identified difference-in-differences or interrupted-time-series estimate. A projected 2025 value based on two pre-rollout years must not be presented as an estimated causal effect. [World Bank evaluation guide](https://thedocs.worldbank.org/en/doc/300711529868962964-0160022017/original/2pmMarch8ImpactEvaluationinPractice.pdf).

## Measurements

Keep goal name and description separate, and also construct a consistently delimited combined text. Report description availability and title-only results separately. Do not impute missing descriptions. Preserve original inputs and distinguish missing, blank, and unusable text.

Linguistic measures: character and word counts; sentence/bullet counts; average word and sentence length; Flesch Reading Ease and Flesch-Kincaid Grade Level. Treat readability as a formula-based description, not a direct comprehension test or a quality score. Flag fragments and short texts; define eligibility rules before comparing years. Omit SMOG from default per-goal reporting because its usual text-length requirements are poorly suited to short goals. [NCI readability guidance](https://ebccp.cancercontrol.cancer.gov/readabilityMeasures.do).

Use a local language detector with fixed configuration. Retain uncertain and mixed-language classifications in the coverage report and compare reasonable English-inclusion thresholds. Changes in English eligibility can change the analyzed population. No translation in v1.

The proposed quality rubric evaluates evidence in the available text, using separately anchored 0-3 scales:

| Dimension | What the rating asks |
| --- | --- |
| Clarity | Is the intended meaning understandable and unambiguous? |
| Specificity | Is the intended outcome, deliverable, or learning target sufficiently defined? |
| Assessability | Is there observable evidence by which progress or success could be assessed, including qualitative evidence? |
| Coherence | Do the stated aims and success criteria fit together without material contradictions? |

Record explicit time references and learning/action strategies as separate descriptive features. Their absence from an export need not mean they were absent from the goal-setting process. Describe goal-type mixtures rather than assuming every goal should use the same outcome target. Specific learning goals can be appropriate when acquiring knowledge or strategies is central. [Locke and Latham](https://med.stanford.edu/content/dam/sm/s-spire/documents/PD.locke-and-latham-retrospective_Paper.pdf); [Seijts and Latham](https://journals.aom.org/doi/10.5465/ame.2005.15841964).

Do not score actual feasibility, appropriate challenge, employee commitment, strategic alignment, or actual performance without supporting context. Keep dimensions separate; no overall quality index in v1. This is a proposed research-informed rubric, not an established validated scale.

## Local decision-model scoring

Use Cloudflare Clef, initially evaluating the smaller Clef-Flash candidate. Clef-Flash has a 9B backbone, a schema-scoring head, and returns probabilities over specified options. Its model card provides a custom Python loading route and a local SystemOne serving interface. The released artifacts use Apache-2.0. [Official Clef-Flash model card](https://huggingface.co/Cloudflare/clef-flash). Runtime, quantization, and hardware suitability remain pending a benchmark on the intended computer.

Use one fixed, versioned rubric and model configuration for all years. Supply goal text and a common neutral description of the annual goal-setting context; exclude employee ID, year labels, and rollout information from model inputs. Treat text as evidence rather than instructions. Retain legitimate dates in goal text and document that blinding is incomplete.

Store each criterion's full probability distribution, expected ordinal score, and uncertainty summary. Keep an explicit not-assessable status separate from the ordinal scale. Model uncertainty is not a middle-quality rating; model probabilities are not probabilities of goal attainment. Report scoring coverage and abstention by year, including sensitivity to any abstention threshold.

Without human labels, domain accuracy, probability calibration, and measurement equivalence across years remain unverified. Synthetic contrast cases, option-order checks, formatting changes, and meaning-preserving variants can expose technical brittleness; they cannot validate ratings on company goals. Flag relationships between score and text length and compare results within length bands as descriptive checks.

## Pipeline and outputs

Stages: validate and inventory inputs; detect language; compute linguistic measures; benchmark local inference; score a reproducible pilot; optionally score all eligible goals; aggregate annual and paired results; render a self-contained HTML report.

Support batched processing, progress reporting, restartable checkpoints, and caching keyed by text, model revision, rubric, and inference configuration. Reuse identical-text scores while retaining every source record and its analysis weight. Failed inference must remain visible and retryable; never silently substitute another model or a zero score.

Deliver a Python package/CLI, configuration, synthetic three-year example data, setup and offline-operation instructions, automated technical checks, scored CSV/Parquet exports, employee-year summaries, and an HTML report with annual distributions, contrasts, paired changes, and coverage charts. The report should identify recurring textual weaknesses and link them to proposed agent prompts or interaction changes; recommendations remain hypotheses to test.

Show magnitudes and distributions before statistical significance. If intervals are provided, preserve employee dependence and pairing and label them as conditional employee/sampling variability. They do not quantify causal-counterfactual uncertainty, company-wide shocks, or model validity; population summaries need not have sampling intervals.

Keep operational logs free of goal text and employee IDs. Produce a local run manifest containing input fingerprints, model/runtime revisions, rubric and configuration versions, code version, seeds, counts, failures, and completion status. The public repository contains only synthetic reports and synthetic-data checks.

## Build acceptance and remaining questions

Acceptance: the documented synthetic workflow runs end to end; setup and runtime failures are actionable; real-data paths are configurable outside the checkout; scoring resumes without duplicate rows; probability outputs are valid; failures and missingness retain correct denominators; summaries use the specified employee weights; and report claims match the descriptive design and unvalidated measurement status. Verify actual local decision-model loading and probability extraction before claiming local inference is supported. A mock backend only verifies orchestration.

Python package installation is permitted. The operating system name, RAM capacity, GPU/VRAM availability, and WSL/Docker permissions are still unspecified. Select the deployment route after establishing the relevant hardware and runtime details. Do not depend on WSL/Docker without confirming availability. Include a CPU-oriented feasibility check rather than assuming a GPU is present. Benchmark throughput and peak memory before projecting full-run duration; published hosted latency is not a local runtime estimate.

Confirmed input contract: one original-snapshot CSV per year, with configurable mappings for employee ID, goal name, and goal description. Use the configured year for each file rather than guessing from goal text. Preserve employee IDs as strings, including leading zeros, and inspect CSV encoding, delimiter, and missing-value conventions during validation. These inputs measure recorded goals at the goal-setting stage, rather than later progress edits.

Concurrent organizational/process changes and availability of company guidance remain unknown. Document them as unresolved limitations rather than supplying assumed answers. The synthetic implementation follows this brief; local model adapters and intended-machine feasibility have distinct verification status. No model weights were downloaded and no company data were analyzed. See implementation-plan-v1.md and acceptance-v1.md for the implementation contract and verification boundaries.
