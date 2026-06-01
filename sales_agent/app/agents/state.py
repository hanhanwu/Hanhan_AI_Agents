from typing import TypedDict, Annotated, Literal
from langgraph.graph import add_messages


class SalesState(TypedDict):
    # Full conversation — add_messages merges lists automatically
    messages: Annotated[list, add_messages]

    # Set by the intent router each turn
    intent: str

    # BANT score 0.0–1.0; updated by qualify_agent
    lead_score: float

    # Stable for the lifetime of the session
    session_id: str

    # Loaded once at session start from CRM / Supabase leads table
    crm_context: dict

    # Controls which node runs next
    next: Literal["qualify", "product", "objection", "escalate", "end"]
