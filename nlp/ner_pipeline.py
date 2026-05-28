"""Build a canonical character list from extracted script JSON files.

Strategy:
1. Collect every unique speaker name from dialogue lines (high precision).
2. Use spaCy NER on action lines to catch characters mentioned but never speaking.
3. Merge aliases with a hand-crafted normalisation table.
4. Output data/processed/characters.json
"""
import json
import os
import re
from collections import defaultdict
from typing import Optional

try:
    import spacy
    NLP = spacy.load("en_core_web_sm")
except Exception:
    NLP = None
    print("[warn] spaCy model not available — NER on action lines disabled")

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")

# Hand-crafted alias table: raw name → canonical id
ALIAS_MAP = {
    "NED":          "ned",
    "THE PIE MAKER": "ned",
    "PIE MAKER":    "ned",
    "CHUCK":        "chuck",
    "CHARLOTTE":    "chuck",
    "CHARLES":      "chuck",
    "EMERSON":      "emerson",
    "EMERSON COD":  "emerson",
    "OLIVE":        "olive",
    "OLIVE SNOOK":  "olive",
    "VIVIAN":       "vivian",
    "LILY":         "lily",
    "NARRATOR":     "_narrator",
    "YOUNG NED":    "ned",
    "YOUNG CHUCK":  "chuck",
    "YOUNG OLIVE":  "olive",
}

# Characters to exclude from the network
EXCLUDE = {
    "_narrator", "vo", "v.o.", "o.s.", "o.c.",
    # Script formatting artefacts
    "final_draft", "end_of_act_one", "end_of_act_two", "end_of_act_three",
    "end_of_act_four", "end_of_act_five", "end_of_act_six",
    "act_one", "act_two", "act_three", "act_four", "act_five",
    "tag", "teaser", "cold_open", "previously_on",
}

CHARACTER_META = {
    "ned":     {"name": "Ned (The Pie Maker)", "type": "main",       "alive": True},
    "chuck":   {"name": "Chuck",               "type": "main",       "alive": True},
    "emerson": {"name": "Emerson Cod",         "type": "main",       "alive": True},
    "olive":   {"name": "Olive Snook",         "type": "supporting", "alive": True},
    "vivian":  {"name": "Vivian Charles",      "type": "supporting", "alive": True},
    "lily":    {"name": "Lily Charles",        "type": "supporting", "alive": True},
}


def canonicalise(raw: str) -> Optional[str]:
    key = raw.strip().upper()
    if key in ALIAS_MAP:
        cid = ALIAS_MAP[key]
    else:
        cid = re.sub(r"[^a-z0-9_]", "_", raw.strip().lower())
    if cid in EXCLUDE or cid.startswith("_"):
        return None
    return cid


def load_episodes() -> list[dict]:
    episodes = []
    for fname in sorted(os.listdir(PROCESSED_DIR)):
        if fname.endswith(".json") and fname.startswith("S"):
            with open(os.path.join(PROCESSED_DIR, fname)) as f:
                episodes.append(json.load(f))
    return episodes


def build_characters(episodes: list[dict]) -> dict:
    """Return {char_id: {name, type, alive, episodes: set, scene_count}}"""
    chars: dict[str, dict] = {}

    def ensure(cid: str, raw_name: str):
        if cid not in chars:
            meta = CHARACTER_META.get(cid, {})
            chars[cid] = {
                "id":          cid,
                "name":        meta.get("name", raw_name.title()),
                "type":        meta.get("type", "guest"),
                "alive":       meta.get("alive", True),
                "episodes":    set(),
                "scene_count": 0,
            }

    for ep in episodes:
        eid = ep["episode_id"]
        for scene in ep["scenes"]:
            speakers_in_scene: set[str] = set()
            for line in scene["lines"]:
                if line["type"] == "dialogue":
                    cid = canonicalise(line["character"])
                    if cid:
                        ensure(cid, line["character"])
                        chars[cid]["episodes"].add(eid)
                        speakers_in_scene.add(cid)

                elif line["type"] == "action" and NLP:
                    doc = NLP(line["text"])
                    for ent in doc.ents:
                        if ent.label_ == "PERSON":
                            cid = canonicalise(ent.text)
                            if cid:
                                ensure(cid, ent.text)
                                chars[cid]["episodes"].add(eid)

            for cid in speakers_in_scene:
                chars[cid]["scene_count"] += 1

    # Serialise sets to sorted lists
    for c in chars.values():
        c["episodes"] = sorted(c["episodes"])

    return chars


def save_characters(chars: dict):
    out_path = os.path.join(PROCESSED_DIR, "characters.json")
    with open(out_path, "w") as f:
        json.dump(list(chars.values()), f, indent=2)
    print(f"[ok] {len(chars)} characters saved → {out_path}")
    return list(chars.values())


if __name__ == "__main__":
    episodes = load_episodes()
    chars = build_characters(episodes)
    save_characters(chars)
    # Print top 20 by scene count
    top = sorted(chars.values(), key=lambda c: c["scene_count"], reverse=True)[:20]
    print("\nTop characters by scene count:")
    for c in top:
        print(f"  {c['name']:<35} scenes={c['scene_count']:>4}  eps={len(c['episodes'])}")
