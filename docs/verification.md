# Verification of the initial synthetic release

Date: 2026-10-23. Source package SHA-256: `87972892fe4d4d4c53b77f8f05ac47d1a7adc53a33616479ad0877439dfdc773` (digest over packaged Python/JSON resources). Public-repository verification is recorded separately after publication.

The independent AS-v1 specification is in [acceptance-v1.md](plans/acceptance-v1.md). The coordinating agent ran verification separately from implementation. An independent read-only release review is required before publication.

## Executed checks

- Final parent run: `.venv/Scripts/python.exe -m pytest -q` with a separate pytest cache: **44 passed in 42.84 seconds** on Python 3.10.7 / Windows. Tests include literal independently specified arithmetic for unequal goal counts, metric-specific denominators and paired cohorts; schema/language/readability/rubric checks; offline adapter protocols; cache interruption/recovery; malformed responses; proxy bypass and redirect rejection; privacy sentinels; failed/malformed-config stale-report suppression; pilot labels; and provenance.
- Implementer also executed compileall, dependency checks and an isolated wheel build successfully. The built wheel's 15 package files were compared byte for byte with source: no differences.
- A new environment outside the checkout installed the wheel and its dependencies. From that unrelated working directory, the installed `goal-eval` command processed all **823 fabricated goals** successfully. Packaged rubric loading worked; provenance correctly reported `installed-package` rather than another directory's Git revision. Its package-source digest matched the source above.
- Export readback: **823 unique record IDs**, matching CSV/Parquet row IDs, preserved string employee IDs/leading zeros, **279 employee-year rows**, and no failed records. Repeated source text remains separate observations. Repeating the full workflow reused the score cache: zero backend calls and 595 cache hits across combined/title variants.
- Independently recalculated 21 year/metric means from Parquet (four quality criteria, combined word count, Flesch Reading Ease and Flesch-Kincaid Grade). They matched annual CSV exports. Categorical probability sums also passed inspection.
- Benchmark mode executed a 100-record prefix and marked the run/report as a partial, non-representative pilot. The final full synthetic workflow was rerun afterwards. Demo timings are not Clef throughput measurements.
- The actual HTML was rendered and visually inspected at desktop width and 390-pixel mobile width. All 0-3 score ticks, separate language/readability units, synthetic notices, denominator tables and expandable details were visible. The page stayed within the narrow viewport; detailed tables scroll. Desktop viewport was restored after testing. Chart values were checked against derived exports.

The public example contains the report, scored CSV and compact summaries from synthetic run `20261023T151324Z-70ab039a`; its manifest omits absolute execution paths. Real data and private outputs were not available or used.

## Corrections during verification

An initial test used a source hash that ignored Windows newline conversion; the test now hashes actual file bytes. Pandas dtype warnings were corrected at source. Narrow charts initially clipped their right edge and long detail tables interrupted the reading path; mobile chart layouts and expandable tables corrected those issues. Provenance is anchored to package source, and partial-run notices distinguish pilots from full inputs.

## Explicitly unverified

The HTTP fixture server and a tiny fake local release exercise adapters and probability extraction contracts. **No actual Clef weights were loaded.** AS-14, intended-computer compatibility, RAM/VRAM fit and real-model throughput remain deferred. No human rating, domain accuracy, probability calibration, option-order/format robustness or cross-year measurement equivalence has been established. Million-row performance is untested; aggregation currently holds projected numeric fields in memory.

There is no untreated comparison group. All reported year contrasts are descriptive, and a causal AI effect is not identified. Passing software tests does not establish causal identification or validate the rating construct.
