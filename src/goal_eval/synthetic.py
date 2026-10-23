"""Fabricated goals with changing observation sets; never imitate company data."""
import csv
from pathlib import Path
import random

TEMPLATES = [
    ("Improve customer onboarding", "By September {date}, map the onboarding process and test two revisions. Review completion rates and five customer interviews with the team each month."),
    ("Learn a research method", "Complete a course in interview design and practice with three volunteers. Produce a reviewed interview guide and explain what was learned at the team workshop."),
    ("Improve reporting", "Prepare a monthly dashboard for the support team. Agree the definitions with stakeholders and review one sample report together before releasing it."),
    ("Deliver the migration", "Move all agreed services by December {date}. Record test results, unresolved risks and a rollback plan; obtain review from the service owners."),
    ("Improve collaboration", ""),
    ("Develop technical skills", "\\N"),
    ("Maintain documentation", "Review the guide each quarter, update outdated steps and ask two colleagues to try it. Record unresolved questions for the next review."),
    ("Increase conversion and reduce conversion", "Increase the conversion rate while keeping the same rate below its current value; use the identical definition and time window."),
    ("Zlepšit týmovou spolupráci", "Připravit plán spolupráce a společně vyhodnotit zkušenosti po třech měsících."),
    ("Mejorar el proceso de atención", "Preparar un informe mensual y revisar los resultados con el equipo de atención al cliente."),
    ("OKR", ""),
    ("", "\\N"),
    ("Review customer feedback", "Review feedback from five customers and document two recurring issues. Propose a small test with the team and discuss the results at the next workshop."),
    ("Improve the workflow", "Review el proceso con el equipo and document the learning. Test the revised workflow with colleagues and reflect on the results."),
]


def generate(directory, employees=120, seed=2026):
    if employees < 10:
        raise ValueError("Use at least ten synthetic employees")
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    for year in (2023, 2024, 2025):
        with open(directory / f"goals-{year}.csv", "w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(["employee_id", "goal_name", "goal_description"])
            for person in range(1, employees + 1):
                # Some observed only before/after; absence is not employment status.
                if year == 2023 and person % 9 == 0 or year == 2025 and person % 11 == 0:
                    continue
                for goal in range(1 + rng.randrange(4)):
                    title, description = TEMPLATES[rng.randrange(len(TEMPLATES))]
                    writer.writerow([f"{person:05d}", title, description.format(date=year)])
    return directory
