"""Import processed character/relationship data into Neo4J.

Run after: extract_text.py → ner_pipeline.py → relationship_builder.py
"""
import json
from typing import Union
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

NEO4J_URI  = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER",     "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASSWORD", "pushingdaisies")

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")


def load_json(name: str) -> Union[list, dict]:
    with open(os.path.join(PROCESSED_DIR, name)) as f:
        return json.load(f)


SETUP_CYPHER = [
    "CREATE CONSTRAINT char_id IF NOT EXISTS FOR (c:Character) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT ep_id   IF NOT EXISTS FOR (e:Episode)   REQUIRE e.id IS UNIQUE",
    "CREATE CONSTRAINT scene_id IF NOT EXISTS FOR (s:Scene)    REQUIRE s.id IS UNIQUE",
]

CREATE_CHARACTER = """
MERGE (c:Character {id: $id})
SET c.name        = $name,
    c.type        = $type,
    c.alive       = $alive,
    c.scene_count = $scene_count,
    c.episode_count = $episode_count
"""

CREATE_EPISODE = """
MERGE (e:Episode {id: $id})
SET e.season = $season, e.number = $number, e.title = $title
"""

CREATE_APPEARS_IN = """
MATCH (c:Character {id: $char_id})
MATCH (e:Episode   {id: $ep_id})
MERGE (c)-[:APPEARS_IN]->(e)
"""

CREATE_RELATIONSHIP = """
MATCH (a:Character {id: $source})
MATCH (b:Character {id: $target})
MERGE (a)-[r:%s {episode_scope: 'all'}]-(b)
ON CREATE SET r.weight    = $weight,
              r.sentiment = $sentiment,
              r.episodes  = $episodes
ON MATCH  SET r.weight    = r.weight + $weight,
              r.sentiment = (r.sentiment + $sentiment) / 2.0
"""

CREATE_SCENE = """
MATCH (e:Episode {id: $ep_id})
MERGE (s:Scene {id: $scene_id})
SET s.heading = $heading, s.episode_id = $ep_id
MERGE (s)-[:PART_OF]->(e)
"""

CREATE_CHAR_IN_SCENE = """
MATCH (c:Character {id: $char_id})
MATCH (s:Scene     {id: $scene_id})
MERGE (c)-[:IN_SCENE]->(s)
"""


class Importer:
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

    def close(self):
        self.driver.close()

    def run(self, cypher: str, **params):
        with self.driver.session() as session:
            session.run(cypher, **params)

    def setup_constraints(self):
        print("Setting up constraints...")
        for q in SETUP_CYPHER:
            self.run(q)

    def clear_all(self):
        print("Clearing existing data...")
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

    def import_characters(self, chars: list):
        print(f"Importing {len(chars)} characters...")
        for c in chars:
            self.run(CREATE_CHARACTER,
                     id=c["id"], name=c["name"], type=c["type"],
                     alive=c["alive"], scene_count=c["scene_count"],
                     episode_count=len(c["episodes"]))

    def import_episodes(self, episodes: list):
        print(f"Importing {len(episodes)} episodes...")
        for ep in episodes:
            self.run(CREATE_EPISODE,
                     id=ep["episode_id"],
                     season=int(ep["season"]),
                     number=int(ep["episode"]),
                     title=ep["title"])

    def import_appears_in(self, chars: list):
        print("Linking characters → episodes...")
        for c in chars:
            for ep_id in c["episodes"]:
                self.run(CREATE_APPEARS_IN, char_id=c["id"], ep_id=ep_id)

    def import_relationships(self, rels: list):
        print(f"Importing {len(rels)} relationships...")
        allowed_types = {"DIALOGUE_WITH", "CO_APPEARS", "SPEAKS_ABOUT"}
        for r in rels:
            rel_type = r["type"]
            if rel_type not in allowed_types:
                continue
            cypher = CREATE_RELATIONSHIP % rel_type
            self.run(cypher,
                     source=r["source"], target=r["target"],
                     weight=r["weight"], sentiment=r["sentiment"],
                     episodes=r["episodes"])

    def import_scenes(self, episodes: list):
        print("Importing scenes...")
        for ep in episodes:
            eid = ep["episode_id"]
            for i, scene in enumerate(ep["scenes"]):
                scene_id = f"{eid}_S{i:03d}"
                self.run(CREATE_SCENE,
                         ep_id=eid, scene_id=scene_id,
                         heading=scene["heading"][:100])
                speakers = {l["character"] for l in scene["lines"] if l["type"] == "dialogue"}
                from ner_pipeline import canonicalise
                for raw in speakers:
                    cid = canonicalise(raw)
                    if cid:
                        self.run(CREATE_CHAR_IN_SCENE, char_id=cid, scene_id=scene_id)

    def compute_pagerank(self):
        print("Computing PageRank via GDS...")
        with self.driver.session() as session:
            try:
                session.run("CALL gds.graph.drop('charGraph', false)")
            except Exception:
                pass
            session.run("""
                CALL gds.graph.project(
                  'charGraph',
                  'Character',
                  {DIALOGUE_WITH: {orientation: 'UNDIRECTED'},
                   CO_APPEARS:    {orientation: 'UNDIRECTED'}}
                )
            """)
            session.run("""
                CALL gds.pageRank.write('charGraph', {
                  writeProperty: 'pagerank',
                  maxIterations: 20
                })
            """)
            print("  PageRank written to Character.pagerank")


def load_episode_jsons() -> list[dict]:
    result = []
    for fname in sorted(os.listdir(PROCESSED_DIR)):
        if fname.endswith(".json") and fname.startswith("S"):
            with open(os.path.join(PROCESSED_DIR, fname)) as f:
                result.append(json.load(f))
    return result


def run_import():
    chars    = load_json("characters.json")
    rels     = load_json("relationships.json")
    episodes = load_episode_jsons()

    imp = Importer()
    try:
        imp.setup_constraints()
        imp.clear_all()
        imp.import_characters(chars)
        imp.import_episodes(episodes)
        imp.import_appears_in(chars)
        imp.import_relationships(rels)
        imp.import_scenes(episodes)
        try:
            imp.compute_pagerank()
        except Exception as e:
            print(f"  [warn] GDS PageRank skipped: {e}")
        print("\n[done] Neo4J import complete!")
    finally:
        imp.close()


if __name__ == "__main__":
    run_import()
