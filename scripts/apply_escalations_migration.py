"""
Applies migration 20260910120000_create_support_escalations.sql to Supabase PostgreSQL.
Verifies table structure and verifies all Level 3 tables and Level 4 knowledge_embeddings are untouched.
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv("backend/.env")
db_url = os.environ.get("DATABASE_URL")

if not db_url:
    raise ValueError("DATABASE_URL not found in backend/.env")

with open("supabase/migrations/20260910120000_create_support_escalations.sql", "r", encoding="utf-8") as f:
    sql = f.read()

conn = psycopg2.connect(db_url)
conn.autocommit = True
cur = conn.cursor()

print("Applying support_escalations migration...")
cur.execute(sql)
print("Migration executed successfully!")

# Verify table structure
cur.execute("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns 
    WHERE table_name = 'support_escalations'
    ORDER BY ordinal_position;
""")
cols = cur.fetchall()
print("\nColumns in support_escalations:")
for c in cols:
    print(f"  {c[0]}: {c[1]} (Nullable: {c[2]})")

# Verify Level 3 and Level 4 counts remain 100% untouched
print("\nVerifying Level 3 & Level 4 tables record counts are 100% preserved:")
expected_counts = {
    "customers": 99441,
    "orders": 99441,
    "order_items": 112650,
    "order_payments": 103886,
    "products": 32951,
    "product_category_name_translation": 73,
    "customer_support_intents": 26872,
    "customer_demo_accounts": 25,
    "knowledge_embeddings": 57,
}

for tbl, exp in expected_counts.items():
    cur.execute(f"SELECT count(*) FROM {tbl};")
    actual = cur.fetchone()[0]
    status = "PRESERVED" if actual == exp else "MISMATCH"
    print(f"  [{status}] {tbl}: {actual:,} (expected {exp:,})")

cur.close()
conn.close()
