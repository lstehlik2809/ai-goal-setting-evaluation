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


def render(tables, manifest, title="Recorded goal text across three years"):
    annual = tables["annual"]
    synthetic = manifest["synthetic"]
    notices = ("<strong>SYNTHETIC DEMONSTRATION.</strong> These records are fabricated. " + ("Demo probabilities are also fabricated. " if manifest["backend"]["kind"] == "demo" else "") + "Findings illustrate the software and say nothing about employees or AI." if synthetic else "<strong>Exploratory descriptive results.</strong> These are recorded-text comparisons, not causal effects of AI.")
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
    sections = ["<h2>Annual employee means</h2><p>Each employee has equal weight after averaging their eligible goals. Each metric has its own valid denominator. Dots use a fixed 0–3 domain.</p>", responsive_chart(score_chart, annual), table(quality),
                "<h2>Length and readability</h2><p>These measures describe recorded language, not goal quality or comprehension. Formula readability requires at least 20 words, two sentence segments and terminal punctuation. Missing readability remains missing. Each panel uses its own labeled units and range.</p>", responsive_chart(linguistic_chart, annual), table(linguistic), details("All linguistic and flag annual summaries", annual.loc[~annual.metric.isin(QUALITY)]),
                "<h2>Annual contrasts</h2><p>2024 minus 2023 supplies historical context; 2025 minus 2024 is the primary descriptive contrast. No intervals or significance tests are calculated.</p>", table(tables["contrasts"].loc[tables["contrasts"].metric.isin(QUALITY)]), details("All annual contrasts", tables["contrasts"]),
                "<h2>Within-employee contrasts and common trajectories</h2><p>Paired eligibility is metric-specific. Common-three-year trajectories additionally require observation and a valid metric in every year. Goals are not matched individually. Export absence does not establish employee departure.</p>", table(tables["paired"].loc[tables["paired"].metric.isin(QUALITY)]), details("All paired contrasts", tables["paired"]), details("Common-three-year trajectories", tables["common_three_years"]),
                "<h2>Coverage and observation sets</h2><p>Language confidence is a detector score, not a validated probability for these goals. Short, mixed and uncertain text may be classified unreliably.</p>", responsive_chart(count_chart, tables["coverage"]), table(tables["coverage"].loc[tables["coverage"].measure.isin(["input_goals", "observed_employees", "english_goals", "english_employees"])]), details("All coverage and missingness counts", tables["coverage"]), details("Employee overlap counts", tables["employee_overlap"]),
                "<h2>Goal-level distributions and counts</h2><p>Bins describe conditional ordinal expectations; these are not human rating categories. Goal counts include eligible English goals.</p>", details("Quality score distributions", tables["distributions"]), details("Eligible goals per employee", tables["goal_counts"]),
                "<h2>Sensitivity analyses</h2><p>English inclusion thresholds (english_threshold), not-assessable cutoffs 0.25/0.5/0.75 (abstention_threshold), length bands (length_band) and title-only scoring (title_only) describe how the selected records change. High entropy does not imply medium quality or trigger exclusion. Title-only scoring uses title language eligibility.</p>", details("All sensitivity comparisons with denominators", tables["sensitivities"]),
                "<h2>Agent redesign hypotheses</h2><ul>", "".join(hypothesis), "</ul>",
                "<h2>Interpretation and provenance</h2><p>Year, business conditions, workforce composition, goal-setting processes and export practices can change together. Repeat-employee restriction addresses only some composition differences. AI availability does not establish use. No untreated counterfactual is available, and a causal AI effect is not identified. Actual feasibility, appropriate challenge, commitment, strategic alignment and performance cannot be established from goal text.</p>",
                f'<p>Run {escape(manifest["run_id"])} · backend {escape(str(manifest["backend"]["kind"]))} · model {escape(str(manifest["backend"]["model"]))} · revision {escape(str(manifest["backend"]["revision"]))} · rubric {escape(manifest["rubric"]["version"])}</p>',
                ("<p>Local adapter protocol tested; real Clef execution and hardware feasibility remain unverified in the shipped synthetic demo. See manifest.json for versions and input fingerprints.</p>" if manifest["backend"]["kind"] == "demo" else "<p>The configured local backend returned validated probability responses for this run. Protocol validation does not establish rating validity. Server weight/runtime revisions are operator-declared unless separately verified. See manifest.json for versions, input fingerprints and measured run resources.</p>")]
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' + escape(title) + '</title><style>body{font:16px/1.5 system-ui,sans-serif;color:#20333c;background:#f7f9fb;margin:0}main{max-width:1120px;margin:auto;padding:24px}h1{font-size:2rem;line-height:1.2}h2{margin-top:2.5rem}aside{border-left:5px solid #ba7b1e;background:#fff2d8;padding:18px}svg{display:block;width:100%;max-width:720px;background:white}svg text{font:13px system-ui,sans-serif;fill:#20333c}.scroll{overflow:auto;margin:1rem 0}table{border-collapse:collapse;background:white;font-size:14px}th,td{padding:7px 12px;text-align:right;border-bottom:1px solid #e0e5e9}th{background:#eaf0f3}td:first-child,th:first-child{text-align:left}p{max-width:90ch}summary{cursor:pointer;color:#145a72;padding:10px 0}details{border-bottom:1px solid #d8dfe7}.mobile{display:none}@media(max-width:600px){main{padding:14px}h1{font-size:1.5rem}.desktop{display:none}.mobile{display:block}table{font-size:13px}}</style><main><h1>' + escape(title) + '</h1><aside>' + notices + '</aside>' + "".join(sections) + '</main></html>'
