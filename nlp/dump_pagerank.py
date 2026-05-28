"""Read pagerank values from local Neo4J and persist them into characters.json.

Run this BEFORE migrating to AuraDB so the values travel with the data.
"""
import json, os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

NEO4J_URI  = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER",     "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASSWORD", "pushingdaisies")

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")


def main():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    with driver.session() as s:
        rows = {r["id"]: r["pagerank"] for r in s.run(
            "MATCH (c:Character) RETURN c.id AS id, coalesce(c.pagerank, 0.0) AS pagerank"
        )}
    driver.close()
    print(f"Fetched pagerank for {len(rows)} characters")

    path = os.path.join(PROCESSED_DIR, "characters.json")
    with open(path) as f:
        chars = json.load(f)

    for c in chars:
        c["pagerank"] = rows.get(c["id"], 0.0)

    with open(path, "w") as f:
        json.dump(chars, f, indent=2)

    print(f"Updated {path}")


if __name__ == "__main__":
    main()
