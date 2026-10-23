"""Declared, deterministic segmentation and standard Flesch formulas."""
import re
from functools import lru_cache
import cmudict

WORD = re.compile(r"[^\W\d_]+(?:['’-][^\W\d_]+)*", re.UNICODE)


@lru_cache(maxsize=1)
def dictionary():
    return cmudict.dict()


@lru_cache(maxsize=100000)
def syllables(word):
    word = word.lower().replace("’", "'")
    known = dictionary().get(word)
    if known:
        return sum(char.isdigit() for phoneme in known[0] for char in phoneme), False
    # OOV: vowel groups; subtract a terminal silent e, except le; minimum one.
    letters = re.sub("[^a-z]", "", word)
    n = len(re.findall("[aeiouy]+", letters))
    if letters.endswith("e") and not letters.endswith("le") and n > 1:
        n -= 1
    return max(1, n), True


def measure(text):
    if text is None or not text.strip():
        return {k: None for k in ("characters", "words", "sentences", "bullets", "syllables", "oov_words", "mean_word_length", "mean_sentence_length", "flesch_ease", "fk_grade", "readability_eligible", "fragment")}
    words = WORD.findall(text)
    # Newlines delimit list fragments; final punctuation closes a segment.
    sentences = len([s for s in re.split(r"[.!?]+(?:\s|$)|\n+", text) if WORD.search(s)])
    count = len(words)
    syl = [syllables(w) for w in words]
    total = sum(s[0] for s in syl)
    eligible = count >= 20 and sentences >= 2 and bool(re.search(r"[.!?](?:\s|$)", text))
    return {"characters": len(text), "words": count, "sentences": sentences,
            "bullets": len(re.findall(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+", text)),
            "syllables": total, "oov_words": sum(s[1] for s in syl),
            "mean_word_length": sum(len(w) for w in words) / count if count else None,
            "mean_sentence_length": count / sentences if sentences else None,
            "flesch_ease": 206.835 - 1.015 * count / sentences - 84.6 * total / count if eligible else None,
            "fk_grade": .39 * count / sentences + 11.8 * total / count - 15.59 if eligible else None,
            "readability_eligible": eligible, "fragment": count < 20 or not bool(re.search(r"[.!?](?:\s|$)", text))}
