#!/usr/bin/env python3
import subprocess
import json
import sys

# Read access token
with open("/home/business_os/.supabase/access-token") as f:
    token = f.read().strip()

def run_sql(query):
    cmd = [
        "curl", "-s", "-X", "POST",
        "https://api.supabase.com/v1/projects/htnufvbzsfdfadnnfnje/database/query",
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
