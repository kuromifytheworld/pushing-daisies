from pydantic import BaseModel
from typing import Optional


class Character(BaseModel):
    id: str
    name: str
    type: str
    alive: bool
    scene_count: int
    episode_count: int
    pagerank: Optional[float] = None


class Relationship(BaseModel):
    source: str
    target: str
    type: str
    weight: int
    sentiment: float
    episodes: list[str]


class GraphResponse(BaseModel):
    characters: list[Character]
    relationships: list[Relationship]


class PathNode(BaseModel):
    id: str
    name: str


class PathEdge(BaseModel):
    source: str
    target: str
    type: str
    weight: int


class ShortestPathResponse(BaseModel):
    nodes: list[PathNode]
    edges: list[PathEdge]
    length: int


class CentralityEntry(BaseModel):
    id: str
    name: str
    pagerank: float
    betweenness: Optional[float] = None
    degree: int
