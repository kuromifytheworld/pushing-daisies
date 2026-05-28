"""Extract each character's most distinctive dialogue words using TF-IDF.

Adds  top_words: ["pie", "dead", "touch", ...]  to every entry in characters.json.
Run after ner_pipeline.py has produced characters.json.
"""
import json
import math
import os
import re
from collections import Counter

import sys
sys.path.insert(0, os.path.dirname(__file__))
from ner_pipeline import canonicalise

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")

STOPWORDS = set("""
i me my myself we our you your he him his she her it its they them their
what which who is am are was were be been being have has had do does did
will would could should may might must shall can a an the and but or nor
not of in on at to for with by from as into through during before after
above below between up down out off over under again then once here there
when where why how all both each few more most other some such no only same
so than too very just because if though while since about against between
into through during before after also that this these those s t m don
oh well know think gonna going said come yes right okay just now back
still even really need want tell going got let got take way made look
never always every something anything nothing someone anyone everyone
didn isn wasn weren don isn can hasn couldn wouldn shouldn
like just get one back now going good thing mean little well yeah
that's don't can't didn't isn't wasn't make sure look come
""".split())

# Character names to always exclude from any character's bubble
CHAR_NAMES = {
    "ned", "chuck", "charlotte", "emerson", "olive", "lily", "vivian",
    "charles", "digby", "randy", "simone", "dwight", "coroner",
}


def load_dialogue() -> dict[str, list[str]]:
    """Return {char_id: [all dialogue words...]} across all episodes."""
    char_words: dict[str, list[str]] = {}

    for fname in sorted(os.listdir(PROCESSED_DIR)):
        if not (fname.endswith(".json") and fname.startswith("S")):
            continue
        with open(os.path.join(PROCESSED_DIR, fname)) as f:
            ep = json.load(f)

        for scene in ep["scenes"]:
            for line in scene["lines"]:
                if line["type"] != "dialogue":
                    continue
                cid = canonicalise(line.get("character", ""))
                if not cid:
                    continue
                text = line.get("text", "").lower()
                words = re.findall(r"[a-z']{3,}", text)
                words = [
                    w.strip("'")
                    for w in words
                    if w.strip("'") not in STOPWORDS
                    and w.strip("'") not in CHAR_NAMES
                    and len(w.strip("'")) >= 3
                ]
                char_words.setdefault(cid, []).extend(words)

    return char_words


def compute_tfidf(char_words: dict[str, list[str]], top_n: int = 5) -> dict[str, list[str]]:
    """TF-IDF per character: score = (word_freq_for_char / total_words_for_char)
    * log(total_chars / chars_that_use_word).
    Returns {char_id: [top_word1, top_word2, ...]}
    """
    # Count per character
    char_counts: dict[str, Counter] = {
        cid: Counter(words) for cid, words in char_words.items()
    }
    char_totals: dict[str, int] = {
        cid: sum(c.values()) for cid, c in char_counts.items()
    }

    # Document frequency: how many characters use each word
    df: Counter = Counter()
    for counts in char_counts.values():
        df.update(counts.keys())

    n_chars = len(char_counts)

    result: dict[str, list[str]] = {}
    for cid, counts in char_counts.items():
        total = char_totals[cid]
        if total == 0:
            result[cid] = []
            continue

        scores: dict[str, float] = {}
        for word, freq in counts.items():
            if freq < 2:
                continue
            tf  = freq / total
            idf = math.log((n_chars + 1) / (df[word] + 1)) + 1.0
            scores[word] = tf * idf

        top = sorted(scores, key=lambda w: scores[w], reverse=True)[:top_n]
        result[cid] = top

    return result


def update_characters(top_words: dict[str, list[str]]):
    path = os.path.join(PROCESSED_DIR, "characters.json")
    with open(path) as f:
        chars = json.load(f)

    for c in chars:
        c["top_words"] = top_words.get(c["id"], [])

    with open(path, "w") as f:
        json.dump(chars, f, indent=2)

    print(f"[ok] top_words added to {len(chars)} characters → {path}")
    return chars


if __name__ == "__main__":
    print("Loading dialogue…")
    char_words = load_dialogue()
    print(f"  {len(char_words)} characters have dialogue")

    print("Computing TF-IDF…")
    top_words = compute_tfidf(char_words, top_n=5)

    print("\nDistinctive words per main character:")
    for cid in ["ned", "chuck", "emerson", "olive", "lily", "vivian"]:
        words = top_words.get(cid, [])
        print(f"  {cid:<12} → {words}")

    update_characters(top_words)
