#!/usr/bin/env python
"""
scripts/seed_objections.py

Loads data/objections/playbook.json into a `objection_playbook` table
in Supabase pgvector. The objection_agent uses this for grounded rebuttals.

Requires migration 004_objection_playbook.sql to be applied first.

Usage:
    python scripts/seed_objections.py
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pathlib import Path
from langchain_core.documents import Document
from langchain_community.vectorstores import SupabaseVectorStore
from app.memory.supabase_client import supabase_client, get_embeddings

DATA_PATH = Path(__file__).parent.parent / "data" / "objections" / "playbook.json"


def get_objection_store() -> SupabaseVectorStore:
    return SupabaseVectorStore(
        client=supabase_client(),
        embedding=get_embeddings(),
        table_name="objection_playbook",
        query_name="match_objections",
    )


def main():
    raw = json.loads(DATA_PATH.read_text())
    docs = [Document(page_content=item["content"], metadata=item["metadata"]) for item in raw]

    print(f"Seeding {len(docs)} objection playbook entries into Supabase pgvector...")
    vs = get_objection_store()
    ids = vs.add_documents(docs)
    print(f"Done. Inserted {len(ids)} documents.")
    for doc_id, doc in zip(ids, docs):
        print(f"  [{doc_id}] [{doc.metadata['category']}] {doc.page_content[:60]}...")


if __name__ == "__main__":
    main()
