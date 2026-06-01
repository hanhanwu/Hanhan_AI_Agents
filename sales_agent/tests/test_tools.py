"""
tests/test_tools.py

Unit tests for individual sales tools.
All Supabase and external calls are mocked.

Run with:
    pytest tests/test_tools.py -v
"""
import pytest
from unittest.mock import patch, MagicMock

from app.tools.sales_tools import score_lead, lookup_lead, upsert_lead, search_product_catalog


# ---------------------------------------------------------------------------
# score_lead
# ---------------------------------------------------------------------------

class TestScoreLead:

    def test_all_high_returns_one(self):
        result = score_lead.invoke({
            "budget": "high", "authority": "high",
            "need": "high", "timeline": "high"
        })
        assert result == 1.0

    def test_all_low_returns_zero(self):
        result = score_lead.invoke({
            "budget": "low", "authority": "low",
            "need": "low", "timeline": "low"
        })
        assert result == 0.0

    def test_mixed_returns_average(self):
        # high(1.0) + medium(0.5) + medium(0.5) + low(0.0) = 2.0 / 4 = 0.5
        result = score_lead.invoke({
            "budget": "high", "authority": "medium",
            "need": "medium", "timeline": "low"
        })
        assert result == 0.5

    def test_case_insensitive(self):
        result = score_lead.invoke({
            "budget": "HIGH", "authority": "Medium",
            "need": "LOW", "timeline": "High"
        })
        assert result == 0.75

    def test_unknown_value_treated_as_zero(self):
        result = score_lead.invoke({
            "budget": "unknown", "authority": "high",
            "need": "high", "timeline": "high"
        })
        assert result == 0.75


# ---------------------------------------------------------------------------
# lookup_lead
# ---------------------------------------------------------------------------

class TestLookupLead:

    @patch("app.tools.sales_tools.supabase_client")
    def test_returns_lead_data(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client_fn.return_value = mock_client
        (mock_client.table.return_value.select.return_value
         .eq.return_value.maybe_single.return_value.execute.return_value
         .data) = {"email": "test@acme.com", "name": "Alice"}

        result = lookup_lead.invoke({"email": "test@acme.com"})
        assert result["email"] == "test@acme.com"

    @patch("app.tools.sales_tools.supabase_client")
    def test_returns_empty_dict_when_not_found(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client_fn.return_value = mock_client
        (mock_client.table.return_value.select.return_value
         .eq.return_value.maybe_single.return_value.execute.return_value
         .data) = None

        result = lookup_lead.invoke({"email": "nobody@nowhere.com"})
        assert result == {}

    @patch("app.tools.sales_tools.supabase_client")
    def test_returns_empty_dict_on_exception(self, mock_client_fn):
        mock_client_fn.side_effect = Exception("DB error")
        result = lookup_lead.invoke({"email": "err@test.com"})
        assert result == {}


# ---------------------------------------------------------------------------
# upsert_lead
# ---------------------------------------------------------------------------

class TestUpsertLead:

    @patch("app.tools.sales_tools.supabase_client")
    def test_upserts_and_returns_record(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client_fn.return_value = mock_client
        (mock_client.table.return_value.upsert.return_value
         .execute.return_value.data) = [{"email": "alice@acme.com", "lead_score": 0.75}]

        result = upsert_lead.invoke({
            "email": "alice@acme.com",
            "lead_score": 0.75,
        })
        assert result["lead_score"] == 0.75

    @patch("app.tools.sales_tools.supabase_client")
    def test_only_non_none_fields_sent(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client_fn.return_value = mock_client
        (mock_client.table.return_value.upsert.return_value
         .execute.return_value.data) = [{"email": "bob@acme.com"}]

        upsert_lead.invoke({"email": "bob@acme.com"})

        call_args = mock_client.table.return_value.upsert.call_args
        payload = call_args[0][0]
        # Only email should be in payload when all others are None
        assert set(payload.keys()) == {"email"}


# ---------------------------------------------------------------------------
# search_product_catalog
# ---------------------------------------------------------------------------

class TestSearchProductCatalog:

    @patch("app.tools.sales_tools.get_vector_store")
    def test_returns_formatted_results(self, mock_vs_fn):
        from langchain_core.documents import Document
        mock_vs = MagicMock()
        mock_vs_fn.return_value = mock_vs
        mock_vs.similarity_search.return_value = [
            Document(
                page_content="Starter plan for small teams",
                metadata={"title": "Starter Plan", "tier": "starter", "price": "$49/mo"}
            )
        ]

        results = search_product_catalog.invoke({"query": "small team pricing"})
        assert len(results) == 1
        assert results[0]["title"] == "Starter Plan"
        assert results[0]["price"] == "$49/mo"

    @patch("app.tools.sales_tools.get_vector_store")
    def test_returns_empty_list_on_error(self, mock_vs_fn):
        mock_vs_fn.side_effect = Exception("Connection error")
        results = search_product_catalog.invoke({"query": "anything"})
        assert results == []
