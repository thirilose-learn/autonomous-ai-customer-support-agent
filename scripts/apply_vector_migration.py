import os
import psycopg2
from dotenv import load_dotenv

load_dotenv("backend/.env")
db_url = os.environ.get("DATABASE_URL")

with open("supabase/migrations/20260907214500_create_knowledge_embeddings.sql", "r", encoding="utf-8") as f:
    sql = f.read()

conn = psycopg2.connect(db_url)
conn.autocommit = True
cur = conn.cursor()

print("Applying Level 4 migration...")
cur.execute(sql)
print("Migration executed successfully!")

# Verify table and column
cur.execute("""
    SELECT column_name, data_type, udt_name 
    FROM information_schema.columns 
    WHERE table_name = 'knowledge_embeddings';
""")
cols = cur.fetchall()
print("Columns in knowledge_embeddings:")
for c in cols:
    print(f"  {c[0]}: {c[1]} ({c[2]})")

# Verify index
cur.execute("""
    SELECT indexname, indexdef 
    FROM pg_indexes 
    WHERE tablename = 'knowledge_embeddings';
""")
idxs = cur.fetchall()
print("Indexes on knowledge_embeddings:")
for i in idxs:
    print(f"  {i[0]}: {i[1]}")

# Verify Level 3 tables are completely untouched
print("\nVerifying Level 3 tables record counts are 100% preserved:")
expected_counts = {
    "customers": 99441,
    "orders": 99441,
    "order_items": 112650,
    "order_payments": 103886,
    "products": 32951,
    "product_category_name_translation": 73,
    "customer_support_intents": 26872,
    "customer_demo_accounts": 25,
}

for tbl, exp in expected_counts.items():
    cur.execute(f"SELECT count(*) FROM {tbl};")
    actual = cur.fetchone()[0]
    status = "PRESERVED" if actual == exp else "MISMATCH"
    print(f"  [{status}] {tbl}: {actual:,} (expected {exp:,})")

cur.close()
conn.close()
