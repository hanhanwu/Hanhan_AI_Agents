"""
memory/checkpointer.py

Wraps LangGraph's PostgresSaver so the rest of the app never imports
psycopg directly. Call get_checkpointer() once at startup.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import psycopg
from psycopg.rows import dict_row
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
    prepare_threshold=None disables auto-prepared statements, which prevents
    DuplicatePreparedStatement errors when using PgBouncer or --reload.
    """
    s = get_settings()
    async with await psycopg.AsyncConnection.connect(
        s.supabase_db_url,
        autocommit=True,
        prepare_threshold=None,
        row_factory=dict_row,
    ) as conn:
        checkpointer = AsyncPostgresSaver(conn=conn)
        await checkpointer.setup()   # idempotent — creates tables if missing
        yield checkpointer
