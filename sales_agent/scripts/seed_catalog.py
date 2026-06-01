#!/usr/bin/env python
"""
scripts/seed_catalog.py

Loads data/catalog/products.json into the Supabase `product_catalog`
pgvector table via LangChain SupabaseVectorStore.

Usage:
    python scripts/seed_catalog.py
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pathlib import Path
from langchain_core.documents import Document
from app.memory.supabase_client import get_vector_store

DATA_PATH = Path(__file__).parent.parent / "data" / "catalog" / "products.json"


def main():
    raw = json.loads(DATA_PATH.read_text())
    docs = [Document(page_content=item["content"], metadata=item["metadata"]) for item in raw]

    print(f"Seeding {len(docs)} product catalog entries into Supabase pgvector...")
    vs = get_vector_store()
    ids = vs.add_documents(docs)
    print(f"Done. Inserted {len(ids)} documents.")
    for doc_id, doc in zip(ids, docs):
        print(f"  [{doc_id}] {doc.metadata['title']}")


if __name__ == "__main__":
    main()
