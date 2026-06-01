#!/usr/bin/env python
"""
scripts/seed_all.py

Runs all three seeders in the correct order:
  1. seed_catalog   — product catalog → pgvector
  2. seed_leads     — CRM leads       → leads table
  3. seed_objections — objection playbook → pgvector

Usage:
    python scripts/seed_all.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def run(label, module_path):
    print(f"\n{'='*50}")
    print(f"  {label}")
    print(f"{'='*50}")
    import importlib.util
    spec = importlib.util.spec_from_file_location("mod", module_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.main()

scripts_dir = os.path.dirname(__file__)

run("1/3  Product catalog   → pgvector",    f"{scripts_dir}/seed_catalog.py")
run("2/3  Leads             → leads table", f"{scripts_dir}/seed_leads.py")
run("3/3  Objection playbook → pgvector",   f"{scripts_dir}/seed_objections.py")

print("\n✓ All seed data loaded. The agent is ready to run.")
