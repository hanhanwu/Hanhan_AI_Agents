#!/usr/bin/env python
"""
scripts/seed_leads.py

Loads data/leads/leads.csv into the Supabase `leads` table.
Uses upsert on email so it is safe to run multiple times.

Usage:
    python scripts/seed_leads.py
"""
import sys, os, csv
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pathlib import Path
from app.memory.supabase_client import supabase_client

DATA_PATH = Path(__file__).parent.parent / "data" / "leads" / "leads.csv"

# CSV fields that map directly to table columns
FLOAT_FIELDS = {"lead_score"}
OPTIONAL_FIELDS = {"budget", "authority", "need", "timeline", "lead_score", "notes",
                   "company", "industry", "name"}


def main():
    rows = []
    with DATA_PATH.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            record = {}
            for key, val in row.items():
                val = val.strip()
                if not val:
                    continue
                if key in FLOAT_FIELDS:
                    record[key] = float(val)
                else:
                    record[key] = val
            rows.append(record)

    print(f"Upserting {len(rows)} leads into Supabase `leads` table...")
    client = supabase_client()
    result = client.table("leads").upsert(rows, on_conflict="email").execute()
    inserted = len(result.data) if result.data else 0
    print(f"Done. {inserted} records upserted.")
    for record in result.data or []:
        print(f"  [{record.get('id', '?')}] {record.get('email')} — score: {record.get('lead_score')}")


if __name__ == "__main__":
    main()
