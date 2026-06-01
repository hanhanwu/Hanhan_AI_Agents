"""
tests/test_graph.py

Integration tests for the LangGraph sales agent.
These use MemorySaver (no Supabase required) so they can run in CI
without environment credentials.

Run with:
    pytest tests/test_graph.py -v
"""
import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver

from app.agents.graph import build_graph


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def graph():
    """Build a graph with in-memory checkpointing (no Supabase needed)."""
    return build_graph(checkpointer=MemorySaver())


@pytest.fixture
def config():
    return {"configurable": {"thread_id": "test-session-001"}}


def _base_state(message: str) -> dict:
    return {
        "messages": [HumanMessage(content=message)],
        "session_id": "test-session-001",
        "crm_context": {},
        "lead_score": 0.0,
        "intent": "",
        "next": "product",
    }


# ---------------------------------------------------------------------------
# Router tests
# ---------------------------------------------------------------------------

class TestIntentRouter:

    @patch("app.agents.graph._llm")
    def test_product_intent(self, mock_llm_fn, graph, config):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content="product")
        mock_llm_fn.return_value = mock_llm

        state = _base_state("What features does the Growth plan include?")
        result = graph.invoke(state, config=config)
        assert result["intent"] == "product"

    @patch("app.agents.graph._llm")
    def test_qualify_intent(self, mock_llm_fn, graph, config):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content="qualify")
        mock_llm_fn.return_value = mock_llm

        state = _base_state("We have a team of 30 and budget around $200k")
        result = graph.invoke(state, config=config)
        assert result["intent"] == "qualify"

    @patch("app.agents.graph._llm")
    def test_escalate_intent(self, mock_llm_fn, graph, config):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content="escalate")
        mock_llm_fn.return_value = mock_llm

        state = _base_state("I need to speak to a real person NOW")
        result = graph.invoke(state, config=config)
        # Escalation node sets next to "end" and terminates
        assert any(
            "specialist" in getattr(m, "content", "").lower()
            for m in result["messages"]
        )

    @patch("app.agents.graph._llm")
    def test_invalid_intent_defaults_to_product(self, mock_llm_fn, graph, config):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content="gibberish")
        mock_llm_fn.return_value = mock_llm

        state = _base_state("huh?")
        result = graph.invoke(state, config=config)
        assert result["intent"] == "product"


# ---------------------------------------------------------------------------
# Escalation node test
# ---------------------------------------------------------------------------

class TestEscalationNode:

    @patch("app.agents.graph._llm")
    def test_escalation_message_contains_handoff(self, mock_llm_fn, graph, config):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content="escalate")
        mock_llm_fn.return_value = mock_llm

        state = _base_state("Transfer me to a human")
        result = graph.invoke(state, config=config)
        ai_messages = [
            m for m in result["messages"]
            if getattr(m, "type", None) == "ai"
        ]
        assert ai_messages, "No AI messages found after escalation"
        assert "specialist" in ai_messages[-1].content.lower()


# ---------------------------------------------------------------------------
# Session persistence test
# ---------------------------------------------------------------------------

class TestSessionPersistence:

    @patch("app.agents.graph._llm")
    def test_messages_accumulate_across_turns(self, mock_llm_fn, graph):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content="product")
        mock_llm_fn.return_value = mock_llm

        config = {"configurable": {"thread_id": "persist-test-001"}}

        # Turn 1
        graph.invoke(_base_state("Tell me about your pricing"), config=config)

        # Turn 2
        graph.invoke(
            {
                "messages": [HumanMessage(content="What about enterprise?")],
                "session_id": "persist-test-001",
                "crm_context": {},
                "lead_score": 0.0,
                "intent": "",
                "next": "product",
            },
            config=config,
        )

        state = graph.get_state(config)
        assert len(state.values["messages"]) >= 2
