# Sales Agent Harness

LangGraph-based sales chatbot with intent routing, specialized agents, Supabase memory, and FastAPI serving.

## Architecture

```
app/
  agents/         LangGraph graph, nodes, state schema
  tools/          CRM, product catalog, email/calendar tools
  memory/         Supabase checkpointer + vector store wrappers
  api/            FastAPI routes and middleware
supabase/
  migrations/     SQL for checkpoints, vector catalog, leads tables
scripts/
  seed_catalog.py Embed and load product catalog into pgvector
tests/
  test_graph.py   Graph integration tests
  test_tools.py   Tool unit tests
```

## Quickstart

### 1. Install dependencies
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Fill in ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY
```

### 3. Run Supabase migrations
```bash
supabase db push
# or apply manually via Supabase dashboard SQL editor
```

### 4. Seed the product catalog
```bash
python scripts/seed_catalog.py
```

### 5. Run the API
```bash
uvicorn app.api.main:app --reload
```

### 6. Test a conversation
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "lead-001", "message": "I need a CRM solution for my 50-person team"}'
```

## Environment variables

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API key |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Supabase service role key (bypasses RLS) |
| `SUPABASE_DB_URL` | Direct Postgres connection string for LangGraph checkpointer |
| `LANGCHAIN_API_KEY` | LangSmith tracing key (optional) |
| `LANGCHAIN_TRACING_V2` | Set to `true` to enable LangSmith tracing |
