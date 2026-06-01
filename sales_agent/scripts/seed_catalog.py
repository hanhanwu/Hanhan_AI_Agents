#!/usr/bin/env python
"""
scripts/seed_catalog.py

Embeds sample product catalog entries and loads them into the
`product_catalog` Supabase table via LangChain SupabaseVectorStore.

Usage:
    python scripts/seed_catalog.py

Add your real product descriptions to CATALOG_ITEMS below, or adapt
this script to read from a CSV / JSON file.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from langchain_core.documents import Document
from app.memory.supabase_client import get_vector_store

CATALOG_ITEMS = [
    Document(
        page_content=(
            "Starter Plan — $49/month. Up to 5 users. "
            "Core CRM features: contact management, deal pipeline, email sync. "
            "Best for small teams just getting started with CRM."
        ),
        metadata={"title": "Starter Plan", "tier": "starter", "price": "$49/mo"},
    ),
    Document(
        page_content=(
            "Growth Plan — $149/month. Up to 25 users. "
            "Everything in Starter plus: sales automation, custom workflows, "
            "reporting dashboards, and priority support. "
            "Best for growing teams that need automation."
        ),
        metadata={"title": "Growth Plan", "tier": "growth", "price": "$149/mo"},
    ),
    Document(
        page_content=(
            "Enterprise Plan — custom pricing. Unlimited users. "
            "Everything in Growth plus: SSO, custom SLAs, dedicated CSM, "
            "API access, advanced permissions, and on-boarding services. "
            "Best for large organisations with compliance requirements."
        ),
        metadata={"title": "Enterprise Plan", "tier": "enterprise", "price": "Custom"},
    ),
    Document(
        page_content=(
            "CRM Integration Add-on — connects with Salesforce, HubSpot, and Pipedrive. "
            "Bi-directional sync of contacts, deals, and activities. "
            "Available on Growth and Enterprise plans."
        ),
        metadata={"title": "CRM Integration Add-on", "tier": "addon", "price": "$29/mo"},
    ),
    Document(
        page_content=(
            "AI Sales Assistant — embedded AI that drafts follow-up emails, "
            "summarises call notes, and suggests next best actions. "
            "Uses conversation history to personalise recommendations. "
            "Available as an add-on on all plans."
        ),
        metadata={"title": "AI Sales Assistant", "tier": "addon", "price": "$39/mo"},
    ),
    Document(
        page_content=(
            "Security & Compliance Package — SOC 2 Type II, GDPR data processing "
            "agreement, custom data retention policies, audit logs. "
            "Required add-on for healthcare and financial services customers."
        ),
        metadata={"title": "Security & Compliance Package", "tier": "addon", "price": "$49/mo"},
    ),
]


def main():
    print(f"Seeding {len(CATALOG_ITEMS)} catalog items into Supabase pgvector...")
    vs = get_vector_store()
    ids = vs.add_documents(CATALOG_ITEMS)
    print(f"Done. Inserted {len(ids)} documents.")
    for doc_id, doc in zip(ids, CATALOG_ITEMS):
        print(f"  [{doc_id}] {doc.metadata['title']}")


if __name__ == "__main__":
    main()
