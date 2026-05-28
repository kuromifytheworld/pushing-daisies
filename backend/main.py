"""FastAPI backend for the Pushing Daisies character network."""
import os
from contextlib import asynccontextmanager
from typing import List, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from neo4j import GraphDatabase

from graph_queries import (
    get_graph,
    get_character,
    get_shortest_path,
    get_timeline,
    get_centrality,
)

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

NEO4J_URI  = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER",     "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASSWORD", "pushingdaisies")

driver = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global driver
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    yield
    driver.close()


app = FastAPI(
    title="Pushing Daisies — Character Network API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/graph")
def graph(
    season:     Optional[int] = Query(None, ge=1, le=2),
    episode:    Optional[int] = Query(None, ge=1, le=13),
    rel_types:  Optional[List[str]] = Query(None),
    min_weight: int        = Query(1, ge=1),
):
    return get_graph(driver, season=season, episode=episode,
                     rel_types=rel_types, min_weight=min_weight)


@app.get("/api/characters")
def characters():
    with driver.session() as s:
        rows = [dict(r) for r in s.run("""
            MATCH (c:Character)
            RETURN c.id AS id, c.name AS name, c.type AS type,
                   c.alive AS alive, c.scene_count AS scene_count,
                   c.episode_count AS episode_count,
                   coalesce(c.pagerank, 0.0) AS pagerank,
                   coalesce(c.top_words, []) AS top_words
            ORDER BY c.scene_count DESC
        """)]
    return rows


@app.get("/api/character/{char_id}")
def character(char_id: str):
    result = get_character(driver, char_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Character '{char_id}' not found")
    return result


@app.get("/api/shortest-path")
def shortest_path(
    from_id: str = Query(..., alias="from"),
    to_id:   str = Query(..., alias="to"),
):
    result = get_shortest_path(driver, from_id, to_id)
    if not result:
        raise HTTPException(status_code=404, detail="No path found between these characters")
    return result


@app.get("/api/timeline")
def timeline():
    return get_timeline(driver)


@app.get("/api/centrality")
def centrality():
    return get_centrality(driver)


@app.get("/api/love-story")
def love_story():
    import json as _json, os as _os
    # love_story.json lives next to this file for easy Docker bundling
    path = _os.path.join(_os.path.dirname(__file__), "love_story.json")
    with open(path) as f:
        return _json.load(f)


@app.get("/api/episodes")
def episodes():
    with driver.session() as s:
        rows = [dict(r) for r in s.run("""
            MATCH (e:Episode)
            RETURN e.id AS id, e.season AS season, e.number AS number, e.title AS title
            ORDER BY e.season, e.number
        """)]
    return rows


@app.get("/health")
def health():
    try:
        with driver.session() as s:
            s.run("RETURN 1")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
