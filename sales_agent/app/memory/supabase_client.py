"""
memory/supabase_client.py

Provides:
  - supabase_client()  → Supabase Python SDK client (for CRUD on leads table)
  - get_vector_store() → LangChain SupabaseVectorStore over product_catalog table
"""
from functools import lru_cache

from supabase import create_client, Client
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_openai import OpenAIEmbeddings

from app.config import get_settings


@lru_cache()
def supabase_client() -> Client:
    s = get_settings()
    return create_client(s.supabase_url, s.supabase_service_role_key)


@lru_cache()
def get_embeddings() -> OpenAIEmbeddings:
    s = get_settings()
    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=s.openai_api_key,
    )


def get_vector_store() -> SupabaseVectorStore:
    """
    Returns a LangChain vector store backed by the `product_catalog` table
    in Supabase (pgvector). The table and the `match_products` RPC function
    are created by supabase/migrations/002_vector_catalog.sql.
    """
    return SupabaseVectorStore(
        client=supabase_client(),
        embedding=get_embeddings(),
        table_name="product_catalog",
        query_name="match_products",
    )
