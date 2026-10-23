from importlib.resources import files
import json
import math
from .config import digest

QUALITY = ("clarity", "specificity", "assessability", "coherence")
OPTIONS = ("0", "1", "2", "3", "not_assessable")


def load_rubric():
    return json.loads(files("goal_eval").joinpath("resources/rubric-v1.json").read_text(encoding="utf-8"))


def request_for(text, model, rubric):
    questions = {}
    for key, criterion in rubric["criteria"].items():
        questions[key] = {"type": "choice", "instructions": criterion["question"],
                          "criteria": {**{str(i): a for i, a in enumerate(criterion["anchors"])}, "not_assessable": rubric["not_assessable"]}}
    for key, question in rubric["flags"].items():
        questions[key] = {"type": "choice", "instructions": question,
                          "criteria": {"present": "Explicitly present in text.", "absent": "Not explicitly present in text.", "not_assessable": "Insufficient text to judge."}}
    return {"model": model, "state": {"context": rubric["context"], "goal_text": text}, "questions": questions}


def validate_probabilities(p, options):
    if not isinstance(p, dict) or set(p) != set(options):
        raise ValueError("Probability response has missing or unknown options")
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 or v > 1 for v in p.values()):
        raise ValueError("Probabilities must be finite numbers in [0,1]")
    # Official SystemOne rounds each option to four decimals (five options).
    if abs(sum(p.values()) - 1) > .001:
        raise ValueError("Probability sum is not one within rounding tolerance 0.001")
    return {k: float(v) for k, v in p.items()}


def summarize(p, threshold=.5):
    p = validate_probabilities(p, OPTIONS)
    mass = sum(p[str(i)] for i in range(4))
    abstain = p["not_assessable"] >= threshold or mass <= 0
    q = [p[str(i)] / mass for i in range(4)] if mass else []
    return {"score": None if abstain else sum(i * v for i, v in enumerate(q)),
            "entropy": None if abstain else -sum(v * math.log(v) for v in q if v) / math.log(4),
            "abstained": abstain}


def validate_response(response, model, rubric):
    if not isinstance(response, dict) or response.get("model") != model:
        raise ValueError("Response model identity does not match the configured model")
    answers = response.get("answers")
    expected = set(QUALITY) | set(rubric["flags"])
    if not isinstance(answers, dict) or set(answers) != expected:
        raise ValueError("Response has missing or unknown questions")
    return {key: validate_probabilities(answers[key].get("probabilities"), OPTIONS if key in QUALITY else ("present", "absent", "not_assessable")) for key in expected}


def rubric_identity(rubric):
    return {"version": rubric["version"], "sha256": digest(rubric)}
