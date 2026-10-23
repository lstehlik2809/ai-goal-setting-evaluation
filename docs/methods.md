# Measurement, descriptive comparisons and Bayesian inference

This pipeline examines recorded text, not the full employee–manager negotiation. It preserves original annual snapshots and excludes employee attributes. It does not match individual goals between years or infer employment status from export absence. The 2025–2024 contrast is primary; 2024–2023 supplies historical context. Neither is a causal estimate. Descriptive comparisons retain their observed values. A separately labeled Bayesian analysis adds conditional credible intervals and posterior directional probabilities; no frequentist significance test is performed.

## Eligibility and text

The default `langid` detector runs its bundled model over all 97 supported languages (`LanguageIdentifier.from_modelstring(model, norm_probs=True)`). A record is English eligible if the predicted language is `en`, the detector confidence is at least 0.8, and the text contains at least four letter-based words and 20 alphabetic characters. Values exactly at a boundary qualify. No language restriction is imposed before classification. Empty/unusable text, insufficient evidence, non-English predictions and uncertain English predictions have separate reasons. Mixed language can still receive a confident single-language label; the detector cannot certify English purity or domain-valid confidence.

Language sensitivity repeats annual aggregation at 0.5, 0.8 and 0.95 by default. Scoring covers English candidates meeting the lowest requested threshold, so the sensitivity can include those additional records. Records below every threshold remain accounted for in coverage. Title-only scoring independently applies the same language evidence rules to the title; it may have low coverage. Non-English text is neither translated nor imputed.

Title, description and combined text have parallel measurements. Combined text joins nonblank available title/description with two newline characters; these separators count toward character length. The model receives that text and neutral rubric context. Employee ID, snapshot year and AI-rollout metadata are absent from requests. Legitimate dates inside text remain; blinding is incomplete. Input text is explicitly evidence, not instructions to the scorer.

## Formula readability

Words are Unicode alphabetic sequences, retaining internal apostrophes or hyphens; digit-only numbers are not words. Sentence segments end at `.`, `!` or `?` followed by whitespace/end, or at newlines; segments with no words are discarded. Bullet counts recognize line-start `-`, `*`, `•`, or numbered `1.`/`1)` markers. These mechanical rules handle list fragments consistently but are not linguistic parsing.

Syllables use the first pronunciation from the offline CMU dictionary distributed inside `cmudict==1.1.3`. A digit-bearing phoneme is one syllable. Out-of-vocabulary words use Latin vowel groups (`aeiouy`), minus terminal silent `e` unless ending `le`, minimum one. Non-Latin OOV words also receive the minimum fallback; OOV counts are exported. No NLTK or network resource download is used. OOV estimates, acronyms, bullets and domain terms can distort readability.

With W words, S sentence segments and Y syllables:

* Flesch Reading Ease = 206.835 − 1.015(W/S) − 84.6(Y/W).
* Flesch–Kincaid Grade = 0.39(W/S) + 11.8(Y/W) − 15.59.

Readability is reported only for at least 20 words, two sentence segments and a punctuation sentence boundary. This exploratory minimum is a fixed analysis convention, not a validated threshold for employee goals. Short/fragment flags and per-metric coverage remain visible; short text is not assigned zero readability. The formulas are not a comprehension test or quality score and can produce values outside customary ranges. SMOG is omitted because short goals poorly meet its text-length requirements. See [NCI readability guidance](https://ebccp.cancercontrol.cancer.gov/readabilityMeasures.do).

## Rubric and uncertainty

The packaged `goal-text-rubric-v1` separately anchors clarity, specificity, assessability and coherence at 0/1/2/3. Every criterion also includes `not_assessable`. Timing and strategy are separate categorical descriptive flags. Observable evidence can be qualitative; learning targets need not look like output quotas. The scorer does not infer feasibility, difficulty, commitment, actual performance or strategic alignment. There is no total score. Research on goal specificity and learning strategies motivates these questions but does not validate this rubric: [Locke and Latham](https://med.stanford.edu/content/dam/sm/s-spire/documents/PD.locke-and-latham-retrospective_Paper.pdf), [Seijts and Latham](https://journals.aom.org/doi/10.5465/ame.2005.15841964).

For each criterion retain all five probabilities. Require exact option keys, finite values in [0,1] and sum within 0.001 of one (the released SystemOne implementation rounds options to four decimals). If p(not_assessable) ≥ 0.5, the default numerical score and entropy are missing. Otherwise let q(k)=p(k)/sum[p(0),…,p(3)]. Expected ordinal score is sum[k q(k)] and normalized entropy is −sum[q(k) ln q(k)]/ln(4), defining 0 ln 0 as zero. The remaining numerical mass is normalized to handle rounding and to condition on assessability. Entropy ranges from zero to one and is distinct from quality; high entropy is not an exclusion rule or evidence of medium quality. Scores are exploratory ordinal expectations, not interval-validated measurements.

Abstention sensitivity recomputes scores at p(not_assessable) cutoffs 0.25/0.5/0.75. These cutoffs are analysis conventions. Probabilities are not calibrated attainment probabilities. Human validation, calibration, option-order robustness and measurement equivalence across years remain unverified. Technical protocol and synthetic tests do not establish those properties.

## Aggregation and sensitivity

For every metric, first average its valid values across eligible goals within employee/year. Then average those employee means, giving each employee with a valid value equal weight. Report both valid goal and valid employee denominators. Employees with many recorded goals therefore do not dominate the annual estimate. Missingness remains metric-specific; NA never becomes zero. Flags are means of predicted `present` probabilities, not proportions of verified human labels.

Paired 2024–2025 contrasts include employees with a valid employee mean for that metric in both years. A different metric can have a different paired set. Common-three-year trajectories require employees observed in all three snapshots and a valid metric in all three years. Their 2025–2024 contrasts describe that narrower cohort. No individual goal pairing is attempted. Common trajectories display each year's mean using the same complete cohort.

Other descriptive checks include language, description/readability/scoring coverage; observed/English employee overlap; repeated-text counts; eligible goals per employee; goal-level score distributions; length-band (0–9, 10–29, 30+ words) comparisons; and title-only results. Length sensitivities describe score–length associations and selection; they do not remove measurement bias. Separate title/description/combined annual metrics expose changing export completeness. Repeated text retains every original row and its employee weight while sharing inference cache entries.

Recommendations connect an observed score range to candidate prompt/interaction changes. They are hypotheses for a subsequent evaluation, including separate human/domain validation. They cannot establish that the proposed change improves goal setting or that AI caused any observed year difference. Concurrent organizational changes and company guidance remain unknown limitations.

## Bayesian employee-cluster bootstrap

### Target and assumptions

The inferential target is the mean recorded proxy and its annual change in a hypothetical population of **exchangeable joint employee trajectories**, including their observation, eligibility and metric-missingness patterns. This is a conditional generalization target. If the exports contain the complete population of interest, the finite recorded means are already known: the credible intervals do not describe uncertainty about those fixed census means. Treating employees as exchangeable may be inappropriate when unmodeled team structure, employee selection or organizational processes materially affect their trajectories.

The analysis conditions on fixed Clef scores, formula measurements and eligible groups. It does not incorporate uncertainty about human ratings, calibration, proxy validity or cross-year measurement equivalence. It does not model shared manager effects, company-year shocks, unrecorded goals or unseen types of trajectory. It does not identify a counterfactual AI effect. More draws cannot remove these limitations.

### Posterior construction and cohorts

Following [Rubin's Bayesian bootstrap (1981)](https://people.eecs.berkeley.edu/~jordan/sail/readings/rubin.pdf), assign masses to observed employee trajectories. The limiting zero-concentration/improper prior has density proportional to the product of inverse masses. A multinomial likelihood with one count for each observed employee yields **Dirichlet(1, …, 1) posterior weights**. These are posterior weights, not a uniform-prior specification. No posterior mass is placed on unseen trajectories. The use of employee trajectories as the support is this pipeline's clustering choice.

In every independent draw, generate one positive Exponential(1) weight per employee. Normalized weights have that Dirichlet posterior distribution. Reuse the **same employee weight across all years, metrics and cohorts**. Within each annual metric-valid set, renormalize and take a weighted mean of the employee-year averages of valid eligible goals. Each contrast is the after-year mean minus the before-year mean within the same draw. This preserves dependence from partially overlapping employee sets, and prevents employees with more recorded goals from gaining extra analysis weight.

* `available`: each annual metric uses every employee with a valid mean in that year; sets can differ. The cluster count is their union and overlap is their intersection.
* `paired`: the same employees must have a valid metric in both contrasted years. This estimates mean change in that selected cohort.
* `common_three_years`: employees must be observed and metric-valid in 2023, 2024 and 2025. This narrower complete-case cohort is used for both contrasts.

Default inference covers clarity, specificity, assessability, coherence, combined words per goal, combined Flesch Reading Ease, combined Flesch–Kincaid grade, timing `present` probability and strategy `present` probability: 27 annual rows and 54 contrast rows (nine metrics × three cohorts × two contrasts). A configured subset or other supported analysis metrics changes those counts. The main report foregrounds 2025 minus 2024 available/paired results; historical, complete-case, annual and all-metric tables expand on demand. Quality intervals share a symmetric score-point scale. Other measures retain their native units in tables. Increases in length, readability or flags are not automatically improvements.

### Intervals, probabilities and numerical error

Defaults are 4,000 independent draws, 0.95 credible mass, the run seed (2026 by default) and batches of 64. `bayesian.seed` can override the run seed. The PCG64 RNG, settings and settings hash are recorded in `manifest.bayesian`. Batching bounds the draw-by-employee weight buffer; posterior summary arrays remain in memory. No PyMC, MCMC sampling, R-hat or new model dependency is required.

The posterior mean averages the draws. A credible interval uses equal tails: quantiles at `(1 − credible_mass)/2` and `(1 + credible_mass)/2`. It quantifies conditional uncertainty in the **mean**, not the observed range or a prediction interval for individual goals. The report labels the actual configured mass.

`p_increase`, `p_decrease` and `p_zero` are the fractions of draws with change greater than, less than or exactly equal to zero. Exact zero uses numerical equality, not a meaningful-difference band. `positive_draws` and `draws` make the Monte Carlo estimate auditable. `probability_mcse = sqrt(p_increase × (1 − p_increase) / draws)` estimates its numerical Monte Carlo standard error. `mean_mcse = posterior_sd / sqrt(draws)` estimates numerical error in the posterior mean. These MCSEs do not measure model validity or the width of the posterior distribution. A finite-draw probability or plug-in MCSE equal to zero does not prove that unobserved tail outcomes are impossible. Posterior probabilities here concern mean changes; Clef probabilities concern rubric options for a fixed text.

Optional `bayesian.practical_thresholds` maps a selected metric to a **positive native-unit** value `t`. It reports posterior draw fractions `P(change > t)`, `P(−t ≤ change ≤ t)` and `P(change < −t)`. Quality uses score points, words use words per goal, readability uses formula/grade units, and flags use probability points on 0–1 (0.01 equals one percentage point). There is no default practical threshold and no implied validated meaningful cutoff.

An annual estimate requires at least two valid employee clusters. An available contrast requires at least two in each annual set; a paired or complete-case contrast requires at least two in its selected cohort. Otherwise `status=insufficient_clusters`, with no posterior interval or probability. Constant annual values or constant changes give `status=degenerate_empirical_support` and a mathematical point interval. This is a consequence of the empirical-support model, not certainty about unobserved trajectories or measurement error. All-missing metrics remain visible through counts and status.

### Regeneration and provenance

The ordinary `run` command computes inference from the current employee-year summaries; no separate reanalysis command or heavy inference backend is needed. Scoring cache identity excludes Bayesian settings. With a complete cache, rerun the same HTTP configuration with the Clef server off to regenerate the report and tables without new model calls. Any miss still uses the configured real backend and fails if it is unavailable; it never falls back to demo probabilities. Changed inputs or scoring identities can require a live local server. `backend_calls`, `cache_hits` and `manifest.bayesian` distinguish scoring provenance from this run's posterior computation.
