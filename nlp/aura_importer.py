"""Import data into Neo4J AuraDB (no GDS required — uses pre-computed pagerank).

Usage:
    NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io \
    NEO4J_USER=neo4j \
    NEO4J_PASSWORD=<aura-password> \
    python aura_importer.py
"""
import json, os, sys
from typing import Union
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

NEO4J_URI  = os.environ["NEO4J_URI"]
NEO4J_USER = os.environ["NEO4J_USER"]
NEO4J_PASS = os.environ["NEO4J_PASSWORD"]

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")


def load_json(name: str) -> Union[list, dict]:
    with open(os.path.join(PROCESSED_DIR, name)) as f:
        return json.load(f)


def load_episode_jsons() -> list:
    result = []
    for fname in sorted(os.listdir(PROCESSED_DIR)):
        if fname.endswith(".json") and fname.startswith("S"):
            with open(os.path.join(PROCESSED_DIR, fname)) as f:
                result.append(json.load(f))
    return result


class Importer:
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

    def close(self):
        self.driver.close()

    def run(self, cypher: str, **params):
        with self.driver.session() as s:
            s.run(cypher, **params)

    def setup(self):
        print("Constraints...")
        for q in [
            "CREATE CONSTRAINT char_id IF NOT EXISTS FOR (c:Character) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT ep_id   IF NOT EXISTS FOR (e:Episode)   REQUIRE e.id IS UNIQUE",
        ]:
            self.run(q)

    def clear(self):
        print("Clearing existing data...")
        with self.driver.session() as s:
            s.run("MATCH (n) DETACH DELETE n")

    def import_characters(self, chars: list):
        print(f"Characters ({len(chars)})...")
        for c in chars:
            self.run("""
                MERGE (c:Character {id: $id})
                SET c.name          = $name,
                    c.type          = $type,
                    c.alive         = $alive,
                    c.scene_count   = $scene_count,
                    c.episode_count = $episode_count,
                    c.pagerank      = $pagerank,
                    c.top_words     = $top_words
            """,
            id=c["id"], name=c["name"], type=c["type"],
            alive=c["alive"], scene_count=c["scene_count"],
            episode_count=len(c.get("episodes", [])),
            pagerank=c.get("pagerank", 0.0),
            top_words=c.get("top_words", []))

    def import_episodes(self, episodes: list):
        print(f"Episodes ({len(episodes)})...")
        for ep in episodes:
            self.run("""
                MERGE (e:Episode {id: $id})
                SET e.season=$season, e.number=$number, e.title=$title
            """,
            id=ep["episode_id"],
            season=int(ep["season"]),
            number=int(ep["episode"]),
            title=ep["title"])

    def import_appears_in(self, chars: list):
        print("APPEARS_IN links...")
        for c in chars:
            for ep_id in c.get("episodes", []):
                self.run("""
                    MATCH (c:Character {id:$cid})
                    MATCH (e:Episode   {id:$eid})
                    MERGE (c)-[:APPEARS_IN]->(e)
                """, cid=c["id"], eid=ep_id)

    def import_relationships(self, rels: list):
        allowed = {"DIALOGUE_WITH", "CO_APPEARS", "SPEAKS_ABOUT"}
        keep = [r for r in rels if r["type"] in allowed]
        print(f"Relationships ({len(keep)})...")
        for r in keep:
            self.run(f"""
                MATCH (a:Character {{id:$src}})
                MATCH (b:Character {{id:$tgt}})
                MERGE (a)-[r:{r['type']} {{episode_scope:'all'}}]-(b)
                ON CREATE SET r.weight=$w, r.sentiment=$s, r.episodes=$eps
                ON MATCH  SET r.weight=r.weight+$w,
                              r.sentiment=(r.sentiment+$s)/2.0
            """,
            src=r["source"], tgt=r["target"],
            w=r["weight"], s=r["sentiment"], eps=r["episodes"])


def main():
    chars    = load_json("characters.json")
    rels     = load_json("relationships.json")
    episodes = load_episode_jsons()

    imp = Importer()
    try:
        imp.setup()
        imp.clear()
        imp.import_characters(chars)
        imp.import_episodes(episodes)
        imp.import_appears_in(chars)
        imp.import_relationships(rels)
        print("\n[done] AuraDB import complete!")
    finally:
        imp.close()


if __name__ == "__main__":
    main()
