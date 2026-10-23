from functools import lru_cache
from langid.langid import LanguageIdentifier, model
from .metrics import WORD


class Detector:
    def __init__(self, cfg):
        self.cfg = cfg
        self.identifier = LanguageIdentifier.from_modelstring(model, norm_probs=True)

    @lru_cache(maxsize=20000)
    def detect(self, text):
        if not text.strip():
            return {"language": "und", "language_confidence": None, "language_evidence": False, "english_eligible": False, "language_reason": "unusable_text"}
        code, confidence = self.identifier.classify(text)
        evidence = len(WORD.findall(text)) >= self.cfg["min_words"] and sum(c.isalpha() for c in text) >= self.cfg["min_letters"]
        return {"language": code, "language_confidence": float(confidence), "language_evidence": evidence,
                "english_eligible": eligible(code, confidence, evidence, self.cfg["threshold"]),
                "language_reason": reason(code, confidence, evidence, self.cfg["threshold"])}


def eligible(code, confidence, evidence, threshold):
    return bool(evidence and code == "en" and confidence is not None and confidence >= threshold)


def reason(code, confidence, evidence, threshold):
    if not evidence:
        return "insufficient_evidence"
    if code != "en":
        return "non_english"
    return "eligible" if confidence >= threshold else "uncertain_english"
