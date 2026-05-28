"""Build character relationships from extracted episode JSON files.

Relationship types:
  DIALOGUE_WITH  — two characters exchange dialogue in the same scene
  CO_APPEARS     — two characters appear in the same scene (action mentions)
  SPEAKS_ABOUT   — character A's dialogue mentions character B by name

Output: data/processed/relationships.json
"""
import itertools
import json
import os
from collections import defaultdict

from ner_pipeline import canonicalise, load_episodes

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")


def _pair_key(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a < b else (b, a)


def build_relationships(episodes: list[dict]) -> list[dict]:
    # { (src, tgt, type) -> {weight, sentiment_sum, sentiment_count, episodes} }
    edges: dict[tuple, dict] = defaultdict(lambda: {
        "weight": 0,
        "sentiment_sum": 0.0,
        "sentiment_count": 0,
        "episodes": set(),
    })

    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        sia = SentimentIntensityAnalyzer()
    except ImportError:
        sia = None
        print("[warn] VADER not available — sentiment will be 0.0")

    for ep in episodes:
        eid = ep["episode_id"]

        for scene in ep["scenes"]:
            speakers_ordered: list[str] = []
            speaker_set: set[str] = set()
            dialogue_lines: dict[str, list[str]] = defaultdict(list)

            for line in scene["lines"]:
                if line["type"] == "dialogue":
                    cid = canonicalise(line["character"])
                    if not cid:
                        continue
                    speakers_ordered.append(cid)
                    speaker_set.add(cid)
                    dialogue_lines[cid].append(line.get("text", ""))

            # DIALOGUE_WITH: consecutive speaker pairs in scene
            seen_pairs: set[tuple] = set()
            for i in range(len(speakers_ordered) - 1):
                a, b = speakers_ordered[i], speakers_ordered[i + 1]
                if a == b:
                    continue
                key = (*_pair_key(a, b), "DIALOGUE_WITH")
                seen_pairs.add(key)

            for key in seen_pairs:
                a, b, _ = key
                edges[key]["weight"] += 1
                edges[key]["episodes"].add(eid)
                # Sentiment: average of both characters' lines in this scene
                if sia:
                    texts = dialogue_lines[a] + dialogue_lines[b]
                    combined = " ".join(texts)
                    if combined.strip():
                        score = sia.polarity_scores(combined)["compound"]
                        edges[key]["sentiment_sum"] += score
                        edges[key]["sentiment_count"] += 1

            # CO_APPEARS: all pairs of speakers in same scene
            for a, b in itertools.combinations(sorted(speaker_set), 2):
                key = (*_pair_key(a, b), "CO_APPEARS")
                edges[key]["weight"] += 1
                edges[key]["episodes"].add(eid)

            # SPEAKS_ABOUT: character A's dialogue mentions character B by name
            # Load canonical names for lookup
            try:
                with open(os.path.join(PROCESSED_DIR, "characters.json")) as f:
                    char_list = json.load(f)
                name_to_id = {}
                for c in char_list:
                    for part in c["name"].split():
                        name_to_id[part.lower()] = c["id"]
            except FileNotFoundError:
                name_to_id = {}

            for speaker_id, lines in dialogue_lines.items():
                full_text = " ".join(lines).lower()
                for mentioned_name, mentioned_id in name_to_id.items():
                    if mentioned_id == speaker_id:
                        continue
                    if mentioned_name in full_text and len(mentioned_name) > 2:
                        key = (*_pair_key(speaker_id, mentioned_id), "SPEAKS_ABOUT")
                        edges[key]["weight"] += 1
                        edges[key]["episodes"].add(eid)

    # Serialise
    result = []
    for (src, tgt, rel_type), data in edges.items():
        sentiment = (
            data["sentiment_sum"] / data["sentiment_count"]
            if data["sentiment_count"] > 0 else 0.0
        )
        result.append({
            "source":    src,
            "target":    tgt,
            "type":      rel_type,
            "weight":    data["weight"],
            "sentiment": round(sentiment, 3),
            "episodes":  sorted(data["episodes"]),
        })

    # Sort by weight descending
    result.sort(key=lambda r: r["weight"], reverse=True)
    return result


def save_relationships(rels: list[dict]):
    out_path = os.path.join(PROCESSED_DIR, "relationships.json")
    with open(out_path, "w") as f:
        json.dump(rels, f, indent=2)
    print(f"[ok] {len(rels)} relationships saved → {out_path}")


if __name__ == "__main__":
    episodes = load_episodes()
    rels = build_relationships(episodes)
    save_relationships(rels)
    print("\nTop 15 strongest relationships:")
    for r in rels[:15]:
        print(f"  {r['source']:<15} ↔ {r['target']:<15}  [{r['type']:<15}]  "
              f"weight={r['weight']:>4}  sentiment={r['sentiment']:+.2f}")
