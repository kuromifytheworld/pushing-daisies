"""Cypher query functions for the Pushing Daisies graph."""
from typing import List, Optional
from neo4j import Driver


def get_graph(
    driver: Driver,
    season: Optional[int] = None,
    episode: Optional[int] = None,
    rel_types: Optional[List[str]] = None,
    min_weight: int = 1,
) -> dict:
    rel_filter = "|".join(rel_types) if rel_types else "DIALOGUE_WITH|CO_APPEARS|SPEAKS_ABOUT"

    if season and episode:
        ep_id = f"S{season:02d}E{episode:02d}"
        char_q = """
            MATCH (c:Character)-[:APPEARS_IN]->(e:Episode {id: $ep_id})
            RETURN c.id AS id, c.name AS name, c.type AS type,
                   c.alive AS alive, c.scene_count AS scene_count,
                   c.episode_count AS episode_count,
                   coalesce(c.pagerank, 0.0) AS pagerank,
                   coalesce(c.top_words, []) AS top_words
        """
        rel_q = f"""
            MATCH (a:Character)-[r:{rel_filter}]-(b:Character)
            WHERE $ep_id IN r.episodes AND r.weight >= $min_weight
            RETURN a.id AS source, b.id AS target,
                   type(r) AS type, r.weight AS weight,
                   r.sentiment AS sentiment, r.episodes AS episodes
        """
        with driver.session() as s:
            chars = [dict(rec) for rec in s.run(char_q, ep_id=ep_id)]
            rels  = [dict(rec) for rec in s.run(rel_q, ep_id=ep_id, min_weight=min_weight)]

    elif season:
        char_q = """
            MATCH (c:Character)-[:APPEARS_IN]->(e:Episode {season: $season})
            WITH DISTINCT c
            RETURN c.id AS id, c.name AS name, c.type AS type,
                   c.alive AS alive, c.scene_count AS scene_count,
                   c.episode_count AS episode_count,
                   coalesce(c.pagerank, 0.0) AS pagerank,
                   coalesce(c.top_words, []) AS top_words
        """
        rel_q = f"""
            MATCH (e:Episode {{season: $season}})
            MATCH (a:Character)-[r:{rel_filter}]-(b:Character)
            WHERE any(ep IN r.episodes WHERE ep STARTS WITH 'S' + right('0'+toString($season),2))
              AND r.weight >= $min_weight
            RETURN a.id AS source, b.id AS target,
                   type(r) AS type, r.weight AS weight,
                   r.sentiment AS sentiment, r.episodes AS episodes
        """
        with driver.session() as s:
            chars = [dict(rec) for rec in s.run(char_q, season=season)]
            rels  = [dict(rec) for rec in s.run(rel_q, season=season, min_weight=min_weight)]

    else:
        char_q = """
            MATCH (c:Character)
            RETURN c.id AS id, c.name AS name, c.type AS type,
                   c.alive AS alive, c.scene_count AS scene_count,
                   c.episode_count AS episode_count,
                   coalesce(c.pagerank, 0.0) AS pagerank,
                   coalesce(c.top_words, []) AS top_words
        """
        rel_q = f"""
            MATCH (a:Character)-[r:{rel_filter}]-(b:Character)
            WHERE r.weight >= $min_weight
            RETURN a.id AS source, b.id AS target,
                   type(r) AS type, r.weight AS weight,
                   r.sentiment AS sentiment, r.episodes AS episodes
        """
        with driver.session() as s:
            chars = [dict(rec) for rec in s.run(char_q)]
            rels  = [dict(rec) for rec in s.run(rel_q, min_weight=min_weight)]

    # Deduplicate undirected edges
    seen = set()
    deduped = []
    for r in rels:
        key = (min(r["source"], r["target"]), max(r["source"], r["target"]), r["type"])
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    return {"characters": chars, "relationships": deduped}


def get_character(driver: Driver, char_id: str) -> Optional[dict]:
    with driver.session() as s:
        char_rec = s.run("""
            MATCH (c:Character {id: $id})
            RETURN c.id AS id, c.name AS name, c.type AS type,
                   c.alive AS alive, c.scene_count AS scene_count,
                   c.episode_count AS episode_count,
                   coalesce(c.pagerank, 0.0) AS pagerank
        """, id=char_id).single()
        if not char_rec:
            return None
        char = dict(char_rec)

        rels = [dict(r) for r in s.run("""
            MATCH (c:Character {id: $id})-[r]-(other:Character)
            RETURN other.id AS partner_id, other.name AS partner_name,
                   type(r) AS type, r.weight AS weight, r.sentiment AS sentiment
            ORDER BY r.weight DESC LIMIT 20
        """, id=char_id)]

        episodes = [dict(r) for r in s.run("""
            MATCH (c:Character {id: $id})-[:APPEARS_IN]->(e:Episode)
            RETURN e.id AS id, e.season AS season, e.number AS number, e.title AS title
            ORDER BY e.season, e.number
        """, id=char_id)]

        char["relationships"] = rels
        char["episodes"]      = episodes
        return char


def get_shortest_path(driver: Driver, from_id: str, to_id: str) -> Optional[dict]:
    with driver.session() as s:
        result = s.run("""
            MATCH path = shortestPath(
              (a:Character {id: $from_id})-[*..6]-(b:Character {id: $to_id})
            )
            RETURN path
        """, from_id=from_id, to_id=to_id).single()

        if not result:
            return None

        path = result["path"]
        nodes = [{"id": n["id"], "name": n["name"]} for n in path.nodes]
        edges = []
        for rel in path.relationships:
            edges.append({
                "source": rel.start_node["id"],
                "target": rel.end_node["id"],
                "type":   rel.type,
                "weight": rel.get("weight", 1),
            })
        return {"nodes": nodes, "edges": edges, "length": len(edges)}


def get_timeline(driver: Driver) -> list[dict]:
    with driver.session() as s:
        eps = [dict(r) for r in s.run("""
            MATCH (e:Episode)
            RETURN e.id AS id, e.season AS season, e.number AS number, e.title AS title
            ORDER BY e.season, e.number
        """)]
        result = []
        for ep in eps:
            chars = [dict(r) for r in s.run("""
                MATCH (c:Character)-[:APPEARS_IN]->(e:Episode {id: $ep_id})
                RETURN c.id AS id, count(*) AS count
            """, ep_id=ep["id"])]
            rels = [dict(r) for r in s.run("""
                MATCH (a:Character)-[r:DIALOGUE_WITH]-(b:Character)
                WHERE $ep_id IN r.episodes
                RETURN a.id AS source, b.id AS target, r.weight AS weight
            """, ep_id=ep["id"])]
            result.append({
                "episode": ep,
                "character_ids": [c["id"] for c in chars],
                "relationships": rels,
            })
        return result


def get_centrality(driver: Driver) -> list[dict]:
    with driver.session() as s:
        rows = [dict(r) for r in s.run("""
            MATCH (c:Character)
            OPTIONAL MATCH (c)-[r]-()
            WITH c, count(r) AS degree
            RETURN c.id AS id, c.name AS name,
                   coalesce(c.pagerank, 0.0) AS pagerank,
                   degree
            ORDER BY pagerank DESC
            LIMIT 30
        """)]
    return rows
