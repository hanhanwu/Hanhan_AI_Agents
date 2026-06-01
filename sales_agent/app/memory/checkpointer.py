"""
memory/checkpointer.py

Wraps LangGraph's PostgresSaver so the rest of the app never imports
psycopg directly. Call get_checkpointer() once at startup.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.config import get_settings


@asynccontextmanager
async def get_checkpointer() -> AsyncGenerator[AsyncPostgresSaver, None]:
    """
    Async context manager that yields a LangGraph AsyncPostgresSaver.
    Use as:

        async with get_checkpointer() as cp:
            graph = build_graph(cp)
            ...

    The checkpointer uses the SUPABASE_DB_URL direct Postgres connection.
    LangGraph will auto-create the `checkpoints` and `checkpoint_writes`
    tables on first use (or run AsyncPostgresSaver.setup() explicitly).
    """
    s = get_settings()
    async with AsyncPostgresSaver.from_conn_string(s.supabase_db_url) as checkpointer:
        await checkpointer.setup()   # idempotent — creates tables if missing
        yield checkpointer
