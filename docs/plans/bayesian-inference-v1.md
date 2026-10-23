# Bayesian inference design, v1

Implementation contract: parent-approved `SP-BAYES-v1-P1` and `AS-BAYES-v1`,
STANDARD mode, with plan-review PASS before implementation. This record is
written before the estimator. Core scope is configuration, NumPy inference,
pipeline integration, examples and targeted tests. Reporting has a separate owner.

## Statistical target and model

The input is the existing eligible-goal employee/year table: each employee's
valid goal scores are averaged before inference, retaining metric-specific
missingness. Employees, including distinct IDs with identical text, remain
distinct clusters. A single random weight per employee and draw is shared across
all years, metrics and cohorts. No goal, year or metric is independently resampled.

Following [Rubin (1981), The Bayesian Bootstrap](https://people.eecs.berkeley.edu/~jordan/sail/readings/rubin.pdf),
the distribution on the observed employee trajectories has a
Dirichlet(1,...,1) **posterior**, obtained from a zero-concentration/improper
Haldane prior and the multinomial likelihood. Normalized iid Exp(1) draws supply
these weights. Normalization cancels in each ratio, so unnormalized positive
weights can be used directly.

Annual means use sum(weight * observed employee mean) / sum(weight) over the
metric-valid employees in that year. Contrasts are 2025 minus 2024 (primary) and
2024 minus 2023 (historical), each for the available annual populations, metric-valid
paired employees, and metric-valid employees in all three years. Paired and
three-year contrasts average employee changes. Missing values never become zero.

The target is a hypothetical exchangeable population of joint employee
trajectories on the observed support, conditional on missingness and fixed Clef
and text-feature proxies. This is not uncertainty about a known finite census
mean. The model does not address human-rating validity, calibration, shared
manager/year shocks, or Clef measurement error, and identifies no causal AI effect.

## Summaries, edge cases and reproducibility

Return posterior mean, sample SD (ddof=1), equal-tailed credible bounds,
mean MCSE = SD/sqrt(draws), strict increase/decrease and exact zero draw fractions,
and binomial MCSE for the increase fraction. Optional positive native-unit
thresholds supply strict above, inclusive within, and strict below probabilities.
Probabilities zero and one are Monte Carlo estimates, not rare-tail proof.

Each annual or paired/common estimate needs at least two contributing clusters;
available contrasts need at least two in each year. With fewer, retain a point
estimate if defined, withhold posterior summaries and use zero draws. A constant
functional with enough clusters has a point interval and
`degenerate_empirical_support` status. Identical varied annual trajectories have
exactly zero contrasts and probability one of zero.

Use NumPy PCG64 and a nonnegative integer seed. Sort employee IDs and generate
Exp(1) weights in draw-major batches so row order and batch size do not change
draws. Allocate at most min(batch size, draws) * union employees float64 weights,
never draws * employees. Retaining draws * summary count is acceptable. Validate
all nonmissing inputs and numerical results as finite; numerical failures abort
the pipeline without publishing a stale report.

## Independent verification oracles (AS-B01–B14)

* Nine default metrics yield 27 annual rows and 54 contrast rows with stable headers.
* Two paired changes [-2,+2] give Uniform[-2,2]: mean 0, SD sqrt(4/3), 95% bounds
  [-1.9,1.9], P(increase)=.5; threshold .5 gives .375/.25/.375.
* Identical varied values in each year give exactly zero change; identical metrics
  share posterior results. Replicating all goals within an employee changes neither
  employee estimates nor posterior. Three IDs with values [0,0,3] have posterior
  variance .5; deduplicating to two support values incorrectly gives .75.
* Prescribed weights [1,2,3,4] and [4,3,2,1] on employees 001=[1,0,2],
  002=[missing,3,1], 003=[missing,missing,0], 004=[3,1,2] (2023/24/25) give
  annual draws [13/5,10/7,6/5] and [7/5,5/4,13/10]. Available changes are
  [-8/35,1/20] and [-41/35,-3/20]; paired changes [2/7,3/8] and [-9/5,-6/5];
  common-three-year changes [6/5,9/5] and [-9/5,-6/5]. Unweighted annual means
  are 2,4/3,5/4. A second metric has a different missingness mask.
* Check exact event counts, reproducible nondivisor final batches, invalid config,
  disabled mode, empty/singleton/constant cases, nonfinite rejection, and strict JSON.
* Inject a Bayesian error after a successful pipeline run: root report disappears,
  manifest records failure, and recovery reuses cached scores.

The parent owns full regression/build, actual cached Clef replay, large-resource
profiling, independent solution review and any publication. Core checks do not
establish those completion gates.
