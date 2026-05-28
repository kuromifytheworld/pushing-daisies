"""Master script: run the full NLP pipeline end-to-end."""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

print("=" * 50)
print("Step 1/5: Downloading PDFs")
print("=" * 50)
from download import download_all
download_all()

print("\n" + "=" * 50)
print("Step 2/5: Extracting text from PDFs")
print("=" * 50)
from extract_text import extract_all
extract_all()

print("\n" + "=" * 50)
print("Step 3/5: Building character list (NER)")
print("=" * 50)
from ner_pipeline import load_episodes, build_characters, save_characters
episodes = load_episodes()
chars = build_characters(episodes)
save_characters(chars)

print("\n" + "=" * 50)
print("Step 4/5: Building relationships")
print("=" * 50)
from relationship_builder import build_relationships, save_relationships
rels = build_relationships(episodes)
save_relationships(rels)

print("\n" + "=" * 50)
print("Step 5/5: Importing into Neo4J")
print("=" * 50)
from neo4j_importer import run_import
run_import()

print("\n✓ Pipeline complete!")
