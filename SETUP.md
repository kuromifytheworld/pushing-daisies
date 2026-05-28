# Pushing Daisies — Character Network: Setup Guide

## Quick Start

### 1. Install Python dependencies
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 2. Start Neo4J
```bash
docker-compose up -d neo4j
# Wait ~20 seconds for Neo4J to start, then open:
# http://localhost:7474  (Neo4J Browser)
# Login: neo4j / pushingdaisies
```

### 3. Run the NLP pipeline (downloads PDFs + processes + imports)
```bash
cd nlp
python run_pipeline.py
```
This takes ~5–10 minutes the first time.

### 4. Start the API
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
# API docs: http://localhost:8000/docs
```

### 5. Open the frontend
Open `frontend/index.html` in your browser.

---

## Run steps individually (if needed)

```bash
cd nlp

# Download PDFs only
python download.py

# Extract text from PDFs
python extract_text.py

# Build character list
python ner_pipeline.py

# Build relationships + sentiment
python relationship_builder.py

# Import into Neo4J
python neo4j_importer.py
```

---

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/graph` | Full network (`?season=1&episode=3&min_weight=2`) |
| `GET /api/characters` | All characters ranked by PageRank |
| `GET /api/character/{id}` | Single character details + relationships |
| `GET /api/shortest-path?from=ned&to=emerson` | Shortest path between two characters |
| `GET /api/timeline` | Per-episode network snapshots |
| `GET /api/centrality` | PageRank ranking |
| `GET /api/episodes` | Episode list |
| `GET /health` | Neo4J connectivity check |
| `GET /docs` | Interactive Swagger UI |

---

## Verify Neo4J import

In Neo4J Browser (http://localhost:7474):
```cypher
// Count nodes
MATCH (n) RETURN labels(n), count(n)

// Top characters by scene count
MATCH (c:Character) RETURN c.name, c.scene_count ORDER BY c.scene_count DESC LIMIT 10

// Ned ↔ Chuck relationship
MATCH (a:Character {id:'ned'})-[r]-(b:Character {id:'chuck'}) RETURN a.name, type(r), r.weight, r.sentiment, b.name
```
