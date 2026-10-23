"""Self-contained HTML: charts and their complete tabular alternatives."""
from html import escape
import math
import pandas as pd
from .rubric import QUALITY


def fmt(value):
    return "Missing" if pd.isna(value) else f"{value:.3f}" if isinstance(value, float) else str(value)


def table(frame):
    if frame.empty:
        return "<p>No eligible observations.</p>"
    return '<div class="scroll">' + frame.to_html(index=False, escape=True, na_rep="Missing", float_format=lambda x: f"{x:.3f}", border=0, classes="data") + '</div>'


def score_chart(annual, narrow=False):
    # Fixed 0–3 horizontal scale for every panel. No score magnitude bars.
    width = 390 if narrow else 660
    left, step = (115, 66) if narrow else (190, 115)
    parts = [f'<svg viewBox="0 0 {width} 510" role="img" aria-label="Annual mean textual scores; fixed zero to three scale">']
    for panel, metric in enumerate(QUALITY):
        y = 30 + panel * 125
        parts.append(f'<text x="10" y="{y}">{escape(metric.title())}</text>')
        for tick in (0, 1, 2, 3):
            x = left + tick * step
            parts.append(f'<line x1="{x}" x2="{x}" y1="{y+8}" y2="{y+83}" stroke="#d8dfe7"/><text x="{x}" y="{y+102}">{tick}</text>')
        for i, year in enumerate((2023, 2024, 2025)):
            row = annual.loc[annual.metric.eq(metric) & annual.year.eq(year)]
            yy = y + 20 + i * 27
            if row.empty:
                continue
            r = row.iloc[0]
            parts.append(f'<text x="10" y="{yy+4}">{year} n={int(r.n_employees)}</text>')
            if pd.notna(r["mean"]):
                x = left + float(r["mean"]) * step
                parts.append(f'<circle cx="{x}" cy="{yy}" r="5" fill="#166378"/><text x="{x+10}" y="{yy+4}">{float(r["mean"]):.2f}</text>')
            else:
                parts.append(f'<text x="{left}" y="{yy+4}">Missing</text>')
    parts.append("</svg>")
    return "".join(parts)


def count_chart(coverage, narrow=False):
    rows = coverage.loc[coverage.measure.isin(["input_goals", "english_goals"])].copy()
    maximum = max(1, rows["count"].max()) if len(rows) else 1
    width, left, span = (390, 180, 155) if narrow else (660, 200, 380)
    parts = [f'<svg viewBox="0 0 {width} 240" role="img" aria-label="Input and English eligible goal counts with zero baseline">', f'<line x1="{left}" x2="{left+span}" y1="210" y2="210" stroke="#444"/>', f'<text x="{left}" y="235">0</text>', f'<text x="{left+span}" y="235">{maximum}</text>']
    for i, r in enumerate(rows.itertuples()):
        y = 8 + 32 * i
        label = "input" if r.measure == "input_goals" else "English eligible"
        parts.append(f'<text x="8" y="{y+16}">{r.year} {label}</text><rect x="{left}" y="{y}" width="{span*r.count/maximum}" height="20" fill="#678c9c"/><text x="{left+8+span*r.count/maximum}" y="{y+16}">{r.count}</text>')
    return "".join(parts) + "</svg>"


def responsive_chart(function, frame):
    return '<div class="desktop">' + function(frame) + '</div><div class="mobile">' + function(frame, narrow=True) + '</div>'


def linguistic_chart(annual, narrow=False):
    metrics = [("combined_words", "Combined words per goal"), ("combined_flesch_ease", "Flesch Reading Ease"), ("combined_fk_grade", "Flesch–Kincaid grade")]
    width, left, span = (390, 115, 195) if narrow else (660, 190, 345)
    parts = [f'<svg viewBox="0 0 {width} 480" role="img" aria-label="Length and formula readability in separate units; employee means">']
    for panel, (metric, label) in enumerate(metrics):
        y = 25 + panel * 155
        selected = annual.loc[annual.metric.eq(metric)]
        values = selected["mean"].dropna()
        low, high = (float(values.min()), float(values.max())) if len(values) else (0., 1.)
        padding = max((high-low)*.15, 1.)
        low, high = low-padding, high+padding
        if metric == "combined_words":
            low = 0.
        parts.append(f'<text x="8" y="{y}">{escape(label)}</text><line x1="{left}" x2="{left+span}" y1="{y+109}" y2="{y+109}" stroke="#888"/><text x="{left}" y="{y+128}">{low:.1f}</text><text x="{left+span}" y="{y+128}">{high:.1f}</text>')
        for i, year in enumerate((2023, 2024, 2025)):
            row = selected.loc[selected.year.eq(year)]
            yy = y + 25 + i*28
            if row.empty:
                continue
            r = row.iloc[0]
            parts.append(f'<text x="8" y="{yy+4}">{year} n={int(r.n_employees)}</text>')
            if pd.notna(r["mean"]):
                x = left + span * (float(r["mean"]) - low) / (high-low)
                parts.append(f'<circle cx="{x}" cy="{yy}" r="5" fill="#166378"/><text x="{x+9}" y="{yy+4}">{r["mean"]:.1f}</text>')
            else:
                parts.append(f'<text x="{left}" y="{yy+4}">Missing</text>')
    return "".join(parts) + '</svg>'


def details(label, frame):
    return f'<details><summary>{escape(label)} ({len(frame)} rows)</summary>' + table(frame) + '</details>'


LINGUISTIC_LABELS = {
    "characters": ("Characters", "characters per goal"), "words": ("Words", "words per goal"),
    "sentences": ("Sentence segments", "segments per goal"), "bullets": ("Bullets", "bullets per goal"),
    "mean_word_length": ("Mean word length", "characters per word"),
    "mean_sentence_length": ("Mean sentence length", "words per segment"),
    "flesch_ease": ("Flesch Reading Ease", "Flesch points"), "fk_grade": ("Flesch–Kincaid grade", "grade units"),
}
METRIC_LABELS = {
    **{f"{prefix}_{metric}": (f"{prefix.title()} · {label}", units)
       for prefix in ("title", "description", "combined") for metric, (label, units) in LINGUISTIC_LABELS.items()},
    **{metric: (metric.title(), "score points") for metric in QUALITY},
    "combined_words": ("Combined words per goal", "words per goal"),
    "combined_flesch_ease": ("Flesch Reading Ease", "Flesch points"),
    "combined_fk_grade": ("Flesch–Kincaid grade", "grade units"),
    "timing_present": ("Timing present probability", "probability points (0–1)"),
    "strategy_present": ("Strategy present probability", "probability points (0–1)"),
}
COHORT_LABELS = {"available": "Available annual employees", "paired": "Paired employees", "common_three_years": "Common three-year employees"}
CONTRAST_COLUMNS = ["metric", "cohort", "before_year", "after_year", "n_before", "n_after", "n_overlap", "n_clusters", "observed_change", "posterior_mean", "posterior_sd", "ci_lower", "ci_upper", "credible_mass", "p_increase", "p_decrease", "p_zero", "positive_draws", "draws", "probability_mcse", "mean_mcse", "practical_threshold", "p_above_threshold", "p_within_threshold", "p_below_threshold", "status"]
ANNUAL_COLUMNS = ["metric", "year", "n_employees", "observed_mean", "posterior_mean", "posterior_sd", "ci_lower", "ci_upper", "credible_mass", "draws", "mean_mcse", "status"]


def metric_label(metric):
    # Known metrics get units; unknown configured metrics remain escaped by the table.
    return METRIC_LABELS.get(metric, (str(metric), "native units"))


def credible_label(mass):
    return f"{float(mass) * 100:g}%"


def bayesian_full_table(frame, annual=False):
    """Only aggregate API fields enter HTML, never arbitrary private columns."""
    columns = ANNUAL_COLUMNS if annual else CONTRAST_COLUMNS
    safe = frame.loc[:, [column for column in columns if column in frame]].copy()
    if safe.empty:
        return "<p>No Bayesian estimates were computed.</p>"
    safe.insert(1, "units", safe["metric"].map(lambda metric: metric_label(metric)[1]))
    safe["metric"] = safe["metric"].map(lambda metric: metric_label(metric)[0])
    if "cohort" in safe:
        safe["cohort"] = safe["cohort"].map(lambda cohort: COHORT_LABELS.get(cohort, str(cohort)))
    if "credible_mass" in safe:
        safe["credible_mass"] = safe["credible_mass"].map(lambda mass: credible_label(mass) if pd.notna(mass) else "Not computed")
    return '<div class="scroll">' + safe.to_html(index=False, escape=True, na_rep="Not computed", float_format=lambda value: f"{value:.12g}", border=0, classes="data") + '</div>'


def bayesian_details(label, frame, annual=False):
    return f'<details><summary>{escape(label)} ({len(frame)} rows)</summary>' + bayesian_full_table(frame, annual) + '</details>'


def bayesian_primary_table(frame):
    rows = []
    for row in frame.itertuples(index=False):
        label, units = metric_label(row.metric)
        computed = row.status != "insufficient_clusters" and pd.notna(row.ci_lower) and pd.notna(row.ci_upper)
        rows.append({"Metric": label, "Change units": units, "Cohort": COHORT_LABELS.get(row.cohort, str(row.cohort)),
                     "N 2024": row.n_before, "N 2025": row.n_after, "Overlap": row.n_overlap, "Clusters": row.n_clusters,
                     "Posterior mean change": f"{row.posterior_mean:.3f}" if computed else "Not computed",
                     "Equal-tailed CrI": f"{credible_label(row.credible_mass)} [{row.ci_lower:.3f}, {row.ci_upper:.3f}]" if computed else "Not computed",
                     "P(change > 0), MC estimate": f"{row.p_increase:.4f}" if computed and pd.notna(row.p_increase) else "Not computed",
                     "Status": row.status})
    return table(pd.DataFrame(rows))


def bayesian_quality_chart(frame, narrow=False):
    """Forest plot: aligned changes, a common symmetric scale and no magnitude bars."""
    width, left, span = (390, 122, 230) if narrow else (720, 204, 450)
    valid = frame.loc[frame.status.ne("insufficient_clusters")]
    bounds = pd.concat([valid["ci_lower"], valid["ci_upper"], valid["posterior_mean"]]).dropna()
    radius = max(.05, float(bounds.abs().max()) * 1.1) if len(bounds) else 1.
    def position(value):
        return left + span * (float(value) + radius) / (2 * radius)
    levels = ", ".join(credible_label(mass) for mass in sorted(frame.credible_mass.dropna().unique()))
    parts = [f'<svg viewBox="0 0 {width} 470" role="img" aria-label="2025 minus 2024 quality changes; posterior means and {escape(levels)} equal-tailed credible intervals, employee-cluster Bayesian bootstrap. Exact values and counts follow in a table.">']
    for tick in (-radius, 0, radius):
        x = position(tick)
        color = "#536674" if tick == 0 else "#d8dfe7"
        parts.append(f'<line x1="{x}" x2="{x}" y1="35" y2="405" stroke="{color}"/><text x="{x}" y="430" text-anchor="middle">{tick:+.2f}</text>')
    for panel, metric in enumerate(QUALITY):
        y = 25 + panel * 95
        parts.append(f'<text x="8" y="{y}">{escape(metric.title())}</text>')
        for index, cohort in enumerate(("available", "paired")):
            yy = y + 26 + index * 27
            parts.append(f'<text x="8" y="{yy + 4}">{"Available" if cohort == "available" else "Paired"}</text>')
            selected = frame.loc[frame.metric.eq(metric) & frame.cohort.eq(cohort)]
            if selected.empty:
                parts.append(f'<text x="{left}" y="{yy + 4}">Not computed</text>')
                continue
            row = selected.iloc[0]
            if row.status == "insufficient_clusters" or pd.isna(row.ci_lower) or pd.isna(row.ci_upper):
                parts.append(f'<text x="{left}" y="{yy + 4}">Insufficient clusters</text>')
                continue
            low, high, mean = position(row.ci_lower), position(row.ci_upper), position(row.posterior_mean)
            color = "#166378" if cohort == "available" else "#6b497a"
            dash = "" if cohort == "available" else ' stroke-dasharray="4 3"'
            description = escape(f'{metric.title()}, {COHORT_LABELS[cohort]}: posterior mean {row.posterior_mean:.3f}; {credible_label(row.credible_mass)} CrI [{row.ci_lower:.3f}, {row.ci_upper:.3f}]; {row.status}')
            parts.append(f'<g><title>{description}</title><line x1="{low}" x2="{high}" y1="{yy}" y2="{yy}" stroke="{color}" stroke-width="2"{dash}/><line x1="{low}" x2="{low}" y1="{yy-5}" y2="{yy+5}" stroke="{color}"/><line x1="{high}" x2="{high}" y1="{yy-5}" y2="{yy+5}" stroke="{color}"/>')
            parts.append(f'<circle cx="{mean}" cy="{yy}" r="5" fill="{color}"/>' if cohort == "available" else f'<path d="M {mean} {yy-6} L {mean+6} {yy} L {mean} {yy+6} L {mean-6} {yy} Z" fill="{color}"/>')
            parts.append('</g>')
    parts.append(f'<text x="{left+span/2}" y="459" text-anchor="middle">Score point change (2025 − 2024)</text></svg>')
    return "".join(parts)


def bayesian_section(tables, manifest):
    heading = '<h2>Bayesian inference for annual changes</h2>'
    metadata = manifest.get("bayesian", {})
    contrasts = tables.get("bayesian_contrasts", pd.DataFrame())
    annual = tables.get("bayesian_annual", pd.DataFrame())
    if not metadata.get("enabled", False):
        reason = "disabled in configuration" if metadata.get("enabled") is False else "not available for this run"
        return heading + f'<p>Bayesian inference was not computed: {reason}. The descriptive summaries remain available below.</p>'
    if contrasts.empty:
        return heading + '<p>Bayesian inference was not computed: no contrast estimates are available for this run.</p>'
    assumptions = ('<aside class="inference-limitations"><strong>Read these assumptions before the estimates.</strong>'
        '<p>This employee-cluster Bayesian bootstrap treats joint employee trajectories, including observation and eligibility patterns, as exchangeable. It describes conditional generalization from the observed employee support to a population with those same selection processes. If these exports are a complete census, their recorded means are already known: the intervals do not express uncertainty about those fixed census means.</p>'
        '<p>Results condition on fixed, unvalidated Clef proxy scores and the eligible groups. They do not propagate human-rating, calibration, cross-year measurement error, manager effects or company-year shocks. No counterfactual AI causal effect is identified.</p></aside>')
    primary = contrasts.loc[contrasts.before_year.eq(2024) & contrasts.after_year.eq(2025) & contrasts.cohort.isin(["available", "paired"])]
    quality = primary.loc[primary.metric.isin(QUALITY)]
    other = primary.loc[~primary.metric.isin(QUALITY)]
    historical = contrasts.loc[~(contrasts.before_year.eq(2024) & contrasts.after_year.eq(2025))]
    common = contrasts.loc[contrasts.cohort.eq("common_three_years") & contrasts.before_year.eq(2024) & contrasts.after_year.eq(2025)]
    levels = ", ".join(credible_label(mass) for mass in sorted(contrasts.credible_mass.dropna().unique()))
    parts = [heading, assumptions,
        f'<p>Primary comparison: <strong>2025 minus 2024</strong>. Dots are posterior mean changes; lines are {escape(levels)} equal-tailed credible intervals (CrIs) for mean change, not the range of individual goals. The vertical reference is zero change. Available employees use every metric-valid employee in each year; paired employees require that metric in both years. Each employee first contributes their average of valid eligible goals.</p>',
        '<p>Circle / solid line = available employees; diamond / dashed line = paired employees. The four qualities share one symmetric score-point scale. A positive value means an increase in the measured proxy. It does not establish practical importance or an AI effect.</p>',
        responsive_chart(bayesian_quality_chart, quality) if not quality.empty else '<p>No quality contrasts were computed.</p>',
        bayesian_primary_table(quality),
        '<h3>Language and descriptive flag changes</h3><p>Each metric retains its native units. Higher length, readability or flag values are increases, not automatically improvements. Probability points use the 0–1 scale: 0.01 is one percentage point.</p>',
        bayesian_primary_table(other),
        '<p>P(change &gt; 0) is the fraction of posterior draws with a positive change, a Monte Carlo (MC) estimate. A displayed 0 or 1 is not proof that alternatives are impossible. Full tables provide positive_draws, draws and probability_mcse; mean_mcse describes numerical Monte Carlo error in the posterior mean. These numerical errors differ from posterior uncertainty and from Clef rubric-option probabilities.</p>',
        bayesian_details("Full primary contrast estimates and Monte Carlo diagnostics", primary),
        bayesian_details("Historical contrasts: 2024 minus 2023", historical),
        bayesian_details("Common three-year complete-case primary contrasts", common),
        bayesian_details("All configured metric and cohort contrasts", contrasts),
        bayesian_details("Annual Bayesian employee means", annual, annual=True),
        '<details><summary>Bayesian bootstrap model, prior and computation</summary><p>One shared random weight per employee is used across their years, metrics and cohorts in each draw. Restricting and renormalizing these shared weights preserves partial employee overlap. Annual means are weighted employee means; contrasts subtract the two weighted annual means. Paired and common-three-year results condition on their metric-valid selected cohorts.</p>'
        '<p>The Bayesian bootstrap uses a limiting zero-concentration (improper) prior on masses at observed joint employee trajectories and a multinomial likelihood, yielding Dirichlet(1, …, 1) posterior weights. Dirichlet(1, …, 1) is the posterior distribution of weights, not a claim that the prior was uniform. The empirical-support model gives no mass to unseen trajectories. Independent posterior draws require no MCMC convergence diagnostics.</p>'
        '<p>insufficient_clusters means fewer than two valid employees in a required annual set or selected cohort: no interval or probability is reported. degenerate_empirical_support identifies a mathematical point interval under constant empirical support; it is not certainty about unobserved trajectories or the measurement process.</p>']
    settings = metadata.get("effective_settings", {})
    recorded = []
    for key, label in (("draws", "Independent draws"), ("credible_mass", "Credible mass"), ("seed", "Seed"), ("draw_batch_size", "Draw batch size")):
        value = settings.get(key, metadata.get(key))
        if value is not None and isinstance(value, (str, int, float)):
            recorded.append(f'{escape(label)}: {escape(str(value))}')
    if recorded:
        parts.append('<p>' + ' · '.join(recorded) + '</p>')
    if "practical_threshold" in contrasts and contrasts.practical_threshold.notna().any():
        parts.append('<p>User-configured practical thresholds use each metric’s native units. For a positive threshold t, p_above_threshold estimates P(change &gt; t), p_within_threshold estimates P(−t ≤ change ≤ t), and p_below_threshold estimates P(change &lt; −t). The threshold is a user judgment, not a validated cutoff for meaningful improvement.</p>')
    else:
        parts.append('<p>No practical thresholds were configured. Directional probabilities alone do not establish a meaningful difference.</p>')
    parts.append('</details>')
    return "".join(parts)


def render(tables, manifest, title="Recorded goal text across three years"):
    annual = tables["annual"]
    synthetic = manifest["synthetic"]
    notices = ("<strong>SYNTHETIC DEMONSTRATION.</strong> These records are fabricated. " + ("Demo probabilities are also fabricated. " if manifest["backend"]["kind"] == "demo" else "") + "Findings illustrate the software and say nothing about employees or AI." if synthetic else "<strong>Exploratory comparative results.</strong> These are recorded-text comparisons, not causal effects of AI.")
    notices += "<p>The rubric and model scores have no human validation here. Domain accuracy, calibration and comparability across years remain unverified. Probabilities describe rubric options, not goal attainment.</p>"
    if manifest.get("scope", {}).get("kind") == "input_prefix":
        notices += f'<p><strong>PARTIAL INPUT PREFIX / PILOT.</strong> This run processed {manifest["processed_rows"]} records with a requested limit of {manifest["scope"]["requested_limit"]}. It may omit entire years and does not describe all configured annual snapshots.</p>'
    hypothesis = []
    suggestions = {"clarity": "ask the author to clarify ambiguous intent and confirm a plain-language restatement", "specificity": "ask for the intended deliverable, scope or learning target", "assessability": "ask what observable quantitative or qualitative evidence would demonstrate progress", "coherence": "ask the author to reconcile conflicting aims and success criteria"}
    for metric, action in suggestions.items():
        valid = annual.loc[annual.metric.eq(metric) & annual["mean"].notna()]
        signal = "No valid signal is available" if valid.empty else "Observed annual employee means range from " + f'{valid["mean"].min():.2f} to {valid["mean"].max():.2f}'
        hypothesis.append(f"<li>{escape(metric.title())}: {signal}. Hypothesis to test: {escape(action)}. Establish usefulness with a separate evaluation before changing the agent.</li>")
    quality = annual.loc[annual.metric.isin(QUALITY)]
    linguistic = annual.loc[annual.metric.isin(["combined_words", "combined_flesch_ease", "combined_fk_grade"])]
    if manifest["backend"]["kind"] == "demo":
        provenance = "Local adapter protocol tested; real Clef execution and hardware feasibility remain unverified in the shipped synthetic demo. See manifest.json for versions and input fingerprints."
    elif manifest.get("backend_calls") == 0 and manifest.get("cache_hits", 0) > 0:
        provenance = "This run reused validated cached probabilities from the configured local backend and made zero new model calls. "
        if manifest.get("bayesian", {}).get("enabled"):
            provenance += "The Bayesian summaries were computed for this run from those fixed scores. "
        provenance += "Protocol validation does not establish rating validity. Server weight/runtime revisions are operator-declared unless separately verified. See manifest.json for scoring cache statistics, versions, input fingerprints and run resources."
    else:
        provenance = "The configured local backend supplied validated probability responses, either newly computed or reused from its cache. Protocol validation does not establish rating validity. Server weight/runtime revisions are operator-declared unless separately verified. See manifest.json for scoring cache statistics, versions, input fingerprints and measured run resources."
    sections = [bayesian_section(tables, manifest), "<h2>Annual employee means</h2><p>Each employee has equal weight after averaging their eligible goals. Each metric has its own valid denominator. Dots use a fixed 0–3 domain.</p>", responsive_chart(score_chart, annual), table(quality),
                "<h2>Length and readability</h2><p>These measures describe recorded language, not goal quality or comprehension. Formula readability requires at least 20 words, two sentence segments and terminal punctuation. Missing readability remains missing. Each panel uses its own labeled units and range.</p>", responsive_chart(linguistic_chart, annual), table(linguistic), details("All linguistic and flag annual summaries", annual.loc[~annual.metric.isin(QUALITY)]),
                "<h2>Descriptive annual contrasts</h2><p>2024 minus 2023 supplies historical context; 2025 minus 2024 is the primary descriptive contrast. These tables retain the observed equal-employee differences; Bayesian uncertainty is presented separately above when computed.</p>", table(tables["contrasts"].loc[tables["contrasts"].metric.isin(QUALITY)]), details("All annual contrasts", tables["contrasts"]),
                "<h2>Within-employee contrasts and common trajectories</h2><p>Paired eligibility is metric-specific. Common-three-year trajectories additionally require observation and a valid metric in every year. Goals are not matched individually. Export absence does not establish employee departure.</p>", table(tables["paired"].loc[tables["paired"].metric.isin(QUALITY)]), details("All paired contrasts", tables["paired"]), details("Common-three-year trajectories", tables["common_three_years"]),
                "<h2>Coverage and observation sets</h2><p>Language confidence is a detector score, not a validated probability for these goals. Short, mixed and uncertain text may be classified unreliably.</p>", responsive_chart(count_chart, tables["coverage"]), table(tables["coverage"].loc[tables["coverage"].measure.isin(["input_goals", "observed_employees", "english_goals", "english_employees"])]), details("All coverage and missingness counts", tables["coverage"]), details("Employee overlap counts", tables["employee_overlap"]),
                "<h2>Goal-level distributions and counts</h2><p>Bins describe conditional ordinal expectations; these are not human rating categories. Goal counts include eligible English goals.</p>", details("Quality score distributions", tables["distributions"]), details("Eligible goals per employee", tables["goal_counts"]),
                "<h2>Sensitivity analyses</h2><p>English inclusion thresholds (english_threshold), not-assessable cutoffs 0.25/0.5/0.75 (abstention_threshold), length bands (length_band) and title-only scoring (title_only) describe how the selected records change. High entropy does not imply medium quality or trigger exclusion. Title-only scoring uses title language eligibility.</p>", details("All sensitivity comparisons with denominators", tables["sensitivities"]),
                "<h2>Agent redesign hypotheses</h2><ul>", "".join(hypothesis), "</ul>",
                "<h2>Interpretation and provenance</h2><p>Year, business conditions, workforce composition, goal-setting processes and export practices can change together. Repeat-employee restriction addresses only some composition differences. AI availability does not establish use. No untreated counterfactual is available, and a causal AI effect is not identified. Actual feasibility, appropriate challenge, commitment, strategic alignment and performance cannot be established from goal text.</p>",
                f'<p>Run {escape(manifest["run_id"])} · backend {escape(str(manifest["backend"]["kind"]))} · model {escape(str(manifest["backend"]["model"]))} · revision {escape(str(manifest["backend"]["revision"]))} · rubric {escape(manifest["rubric"]["version"])}</p>',
                '<p>' + provenance + '</p>']
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' + escape(title) + '</title><style>body{font:16px/1.5 system-ui,sans-serif;color:#20333c;background:#f7f9fb;margin:0}main{max-width:1120px;margin:auto;padding:24px}h1{font-size:2rem;line-height:1.2}h2{margin-top:2.5rem}aside{border-left:5px solid #ba7b1e;background:#fff2d8;padding:18px}svg{display:block;width:100%;max-width:720px;background:white}svg text{font:13px system-ui,sans-serif;fill:#20333c}.scroll{overflow:auto;margin:1rem 0}table{border-collapse:collapse;background:white;font-size:14px}th,td{padding:7px 12px;text-align:right;border-bottom:1px solid #e0e5e9}th{background:#eaf0f3}td:first-child,th:first-child{text-align:left}p{max-width:90ch;overflow-wrap:anywhere}summary{cursor:pointer;color:#145a72;padding:10px 0}details{border-bottom:1px solid #d8dfe7}.mobile{display:none}@media(max-width:600px){main{padding:14px}h1{font-size:1.5rem}.desktop{display:none}.mobile{display:block}table{font-size:13px}}</style><main><h1>' + escape(title) + '</h1><aside>' + notices + '</aside>' + "".join(sections) + '</main></html>'
