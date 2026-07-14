#!/usr/bin/env python3
import os
import subprocess
import json
import sys

PROJECT_REF = os.environ.get("SUPABASE_PROJECT_REF", "htnufvbzsfdfadnnfnje")

token = os.environ.get("SUPABASE_ACCESS_TOKEN", "")
if not token:
    token_path = os.path.expanduser("~/.supabase/access-token")
    if os.path.isfile(token_path):
        with open(token_path) as f:
            token = f.read().strip()

def run_sql(query):
    cmd = [
        "curl", "-s", "-X", "POST",
        f"https://api.supabase.com/v1/projects/{PROJECT_REF}/database/query",
        "-H", f"Authorization: Bearer {token}",
        "-H", "Content-Type: application/json",
        "-d", json.dumps({"query": query})
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    return result.stdout

if len(sys.argv) < 2:
    print("Usage: check_db.py <SQL query>")
    sys.exit(1)

query = sys.argv[1]
print(run_sql(query))
