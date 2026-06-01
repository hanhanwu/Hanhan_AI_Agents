"""
tools/sales_tools.py

All @tool-decorated functions used by the sales agents.
Each tool is kept small and single-purpose so agents can compose them.
"""
import logging
from typing import Optional

import httpx
from langchain_core.tools import tool
from tenacity import retry, stop_after_attempt, wait_exponential

from app.memory.supabase_client import supabase_client, get_vector_store

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CRM tool  (reads/writes the `leads` table in Supabase)
# ---------------------------------------------------------------------------

@tool
def lookup_lead(email: str) -> dict:
    """
    Fetch a lead record from the Supabase `leads` table by email.
    Returns an empty dict if the lead is not found.
    """
    try:
        result = (
            supabase_client()
            .table("leads")
            .select("*")
            .eq("email", email)
            .maybe_single()
            .execute()
        )
        return result.data or {}
    except Exception as e:
        logger.warning("lookup_lead failed for %s: %s", email, e)
        return {}


@tool
def upsert_lead(
    email: str,
    name: Optional[str] = None,
    company: Optional[str] = None,
    industry: Optional[str] = None,
    budget: Optional[str] = None,
    authority: Optional[str] = None,
    need: Optional[str] = None,
    timeline: Optional[str] = None,
    lead_score: Optional[float] = None,
    notes: Optional[str] = None,
) -> dict:
    """
    Create or update a lead record in Supabase.
    Only non-None fields are written so callers can do partial updates.
    Returns the upserted record.
    """
    payload = {"email": email}
    for key, val in {
        "name": name,
        "company": company,
        "industry": industry,
        "budget": budget,
        "authority": authority,
        "need": need,
        "timeline": timeline,
        "lead_score": lead_score,
        "notes": notes,
    }.items():
        if val is not None:
            payload[key] = val

    try:
        result = (
            supabase_client()
            .table("leads")
            .upsert(payload, on_conflict="email")
            .execute()
        )
        return result.data[0] if result.data else {}
    except Exception as e:
        logger.error("upsert_lead failed for %s: %s", email, e)
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Product catalog tool  (semantic search via pgvector)
# ---------------------------------------------------------------------------

@tool
def search_product_catalog(query: str, top_k: int = 3) -> list[dict]:
    """
    Semantic search over the product catalog stored in Supabase pgvector.
    Returns the top_k most relevant product chunks with title and summary.
    """
    try:
        docs = get_vector_store().similarity_search(query, k=top_k)
        return [
            {
                "title": doc.metadata.get("title", "Product"),
                "summary": doc.page_content,
                "tier": doc.metadata.get("tier", ""),
                "price": doc.metadata.get("price", ""),
            }
            for doc in docs
        ]
    except Exception as e:
        logger.error("search_product_catalog failed: %s", e)
        return []


# ---------------------------------------------------------------------------
# Lead scoring tool  (BANT)
# ---------------------------------------------------------------------------

@tool
def score_lead(
    budget: str,
    authority: str,
    need: str,
    timeline: str,
) -> float:
    """
    Compute a BANT lead score between 0.0 and 1.0.
    Each dimension should be 'high', 'medium', or 'low'.
    """
    mapping = {"high": 1.0, "medium": 0.5, "low": 0.0}
    scores = [mapping.get(v.lower().strip(), 0.0) for v in [budget, authority, need, timeline]]
    return round(sum(scores) / len(scores), 2)


# ---------------------------------------------------------------------------
# Scheduling / follow-up tool  (stub — wire to real provider)
# ---------------------------------------------------------------------------

@tool
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4))
def schedule_followup(lead_email: str, date: str, notes: str) -> str:
    """
    Create a calendar placeholder and queue a follow-up email for the lead.
    `date` should be ISO-8601 (e.g. '2026-06-15T14:00:00').
    Returns a confirmation string.

    Replace the stub body with real SendGrid / Google Calendar SDK calls.
    """
    logger.info("Scheduling follow-up for %s on %s", lead_email, date)
    # --- stub: replace with real integrations ---
    # sendgrid_client.send(to=lead_email, subject="Following up", body=notes)
    # gcal_client.create_event(attendee=lead_email, start=date, description=notes)
    return f"Follow-up scheduled for {lead_email} on {date}."


# ---------------------------------------------------------------------------
# Convenience export
# ---------------------------------------------------------------------------

ALL_TOOLS = [
    lookup_lead,
    upsert_lead,
    search_product_catalog,
    score_lead,
    schedule_followup,
]
