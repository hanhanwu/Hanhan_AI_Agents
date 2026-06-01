"""
agents/graph.py

Defines every LangGraph node and wires them into the compiled sales graph.

Nodes
-----
  router_node     – LLM intent classification → sets state["next"]
  qualify_node    – BANT qualification agent with CRM + scoring tools
  product_node    – Product information agent with catalog search
  objection_node  – Objection handling agent
  escalate_node   – Graceful human handoff (no LLM, deterministic)

Entry point: build_graph(checkpointer) → CompiledGraph
"""
import logging
from typing import Literal

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent

from app.agents.state import SalesState
from app.tools.sales_tools import (
    lookup_lead,
    upsert_lead,
    search_product_catalog,
    score_lead,
    schedule_followup,
)
from app.config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared LLM instance
# ---------------------------------------------------------------------------

def _llm() -> ChatGroq:
    s = get_settings()
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        groq_api_key=s.groq_api_key,
        temperature=0.3,
    )


# ---------------------------------------------------------------------------
# Intent router node
# ---------------------------------------------------------------------------

INTENT_SYSTEM = """You are a sales intent classifier. Given the latest customer
message, return EXACTLY one word — no punctuation, no explanation:

  qualify    – customer is sharing context about their situation/needs (budget, team size, timeline)
  product    – questions about features, pricing, comparisons, demos
  objection  – pushback, hesitation, "too expensive", competitor mention
  escalate   – requests a human agent, expresses strong frustration
  end        – wants to close or says goodbye

Return only the single word."""


def router_node(state: SalesState) -> dict:
    last_msg = state["messages"][-1]
    content = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

    response = _llm().invoke([
        SystemMessage(content=INTENT_SYSTEM),
        HumanMessage(content=content),
    ])

    intent = response.content.strip().lower().split()[0]
    valid = {"qualify", "product", "objection", "escalate", "end"}
    if intent not in valid:
        intent = "product"   # safe default

    logger.info("Intent classified: %s", intent)
    return {"intent": intent, "next": intent}


def dispatch(state: SalesState) -> Literal["qualify", "product", "objection", "escalate", "__end__"]:
    next_node = state.get("next", "product")
    return "__end__" if next_node == "end" else next_node


# ---------------------------------------------------------------------------
# Qualify agent node
# ---------------------------------------------------------------------------

qualify_agent = create_react_agent(
    _llm(),
    tools=[lookup_lead, upsert_lead, score_lead],
    state_modifier="""You are a sales qualification specialist.

Your goal: uncover Budget, Authority, Need, and Timeline through natural,
helpful conversation — never an interrogation.

Guidelines:
- Call lookup_lead early in the session to check existing CRM data.
- Ask one BANT question at a time, woven naturally into helpful dialogue.
- Once you have all four dimensions, call score_lead and then upsert_lead
  to persist the score.
- Always respond with warmth and genuine curiosity about their business.
""",
)


def qualify_node(state: SalesState) -> dict:
    result = qualify_agent.invoke(state)
    # Extract updated lead_score if the agent produced one
    lead_score = state.get("lead_score", 0.0)
    for msg in reversed(result.get("messages", [])):
        content = getattr(msg, "content", "")
        if isinstance(content, str) and "score_lead" in content:
            break
        if hasattr(msg, "tool_call_id"):
            try:
                score_val = float(content)
                if 0.0 <= score_val <= 1.0:
                    lead_score = score_val
                    break
            except (ValueError, TypeError):
                pass

    return {**result, "lead_score": lead_score}


# ---------------------------------------------------------------------------
# Product agent node
# ---------------------------------------------------------------------------

product_agent = create_react_agent(
    _llm(),
    tools=[search_product_catalog, schedule_followup],
    state_modifier="""You are a product expert for our sales team.

Guidelines:
- Always call search_product_catalog before answering product questions.
- Tie every feature back to the customer's stated need.
- Present pricing tiers only when the customer asks or when budget context
  has been established.
- Offer to schedule a demo or follow-up call when there is strong interest.
  Use schedule_followup if the customer agrees to a date.
""",
)


def product_node(state: SalesState) -> dict:
    return product_agent.invoke(state)


# ---------------------------------------------------------------------------
# Objection handling agent node
# ---------------------------------------------------------------------------

objection_agent = create_react_agent(
    _llm(),
    tools=[search_product_catalog],
    state_modifier="""You are an expert at handling sales objections empathetically.

Framework: Acknowledge → Clarify → Reframe

Common objections and approaches:
- Price: anchor to ROI, offer a smaller starting tier
- Timing: explore what would need to change, keep the door open
- Competitor: acknowledge strengths, differentiate on specific value props
- Need: ask deeper questions to surface the underlying pain
- Authority: offer to include decision-makers in a follow-up call

Always validate the customer's concern before reframing.
Use search_product_catalog to find specific differentiators when relevant.
""",
)


def objection_node(state: SalesState) -> dict:
    return objection_agent.invoke(state)


# ---------------------------------------------------------------------------
# Escalation node  (deterministic — no LLM call)
# ---------------------------------------------------------------------------

def escalate_node(state: SalesState) -> dict:
    from langchain_core.messages import AIMessage

    handoff = (
        "I completely understand, and I want to make sure you get the best "
        "possible support. I'm connecting you with one of our specialists right now "
        "— they'll have the full context of our conversation so you won't need to "
        "repeat yourself. You should hear from them within a few minutes."
    )

    # In production: emit to your ticketing / live-chat system here
    # e.g. zendesk_client.create_ticket(session_id=state["session_id"], ...)
    logger.info("Escalating session %s to human agent", state.get("session_id"))

    return {
        "messages": [AIMessage(content=handoff)],
        "next": "end",
    }


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_graph(checkpointer=None):
    """
    Compile and return the LangGraph sales agent graph.

    Pass a LangGraph checkpointer (e.g. AsyncPostgresSaver) to enable
    persistent sessions. If None, the graph runs statelessly (useful for tests).
    """
    builder = StateGraph(SalesState)

    builder.add_node("router",    router_node)
    builder.add_node("qualify",   qualify_node)
    builder.add_node("product",   product_node)
    builder.add_node("objection", objection_node)
    builder.add_node("escalate",  escalate_node)

    builder.set_entry_point("router")

    builder.add_conditional_edges("router", dispatch, {
        "qualify":   "qualify",
        "product":   "product",
        "objection": "objection",
        "escalate":  "escalate",
        "__end__":   END,
    })

    # All conversation agents loop back to the router for the next turn
    for node in ["qualify", "product", "objection"]:
        builder.add_edge(node, "router")

    # Escalation terminates the graph
    builder.add_edge("escalate", END)

    return builder.compile(checkpointer=checkpointer)
