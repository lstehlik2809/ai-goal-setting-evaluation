# Measurement and descriptive comparisons

This pipeline examines recorded text, not the full employee–manager negotiation. It preserves original annual snapshots and excludes employee attributes. It does not match individual goals between years or infer employment status from export absence. The 2025–2024 contrast is primary; 2024–2023 supplies historical context. Neither is a causal estimate. No p-values or confidence intervals are invented.

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
