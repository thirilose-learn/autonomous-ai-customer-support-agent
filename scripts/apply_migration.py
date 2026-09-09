"""
Applies SQL schema migrations to Supabase PostgreSQL and inspects catalog objects.
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIGRATION_FILE = os.path.join(BASE_DIR, "supabase", "migrations", "20260907203000_initial_schema.sql")


def apply_migration():
    load_dotenv(os.path.join(BASE_DIR, "backend", ".env"))
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set in backend/.env")
        sys.exit(1)

    print(f"Reading migration file: {MIGRATION_FILE}")
    with open(MIGRATION_FILE, "r", encoding="utf-8") as f:
        sql = f.read()

    print("Connecting to PostgreSQL to execute schema migration...")
    conn = psycopg2.connect(db_url, connect_timeout=15)
    conn.autocommit = True
    cur = conn.cursor()

    try:
        # Execute the migration script
        cur.execute(sql)
        print("Schema migration executed successfully!")

        # Notify PostgREST to reload schema cache
        cur.execute("NOTIFY pgrst, 'reload schema';")
        print("Notified PostgREST schema cache reload.")

        # Inspect database catalog directly for validation
        print("\n--- Direct PostgreSQL Catalog Inspection ---")

        # 1. Inspect Extensions
        cur.execute("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';")
        ext = cur.fetchone()
        print(f"Extension 'vector': {'INSTALLED (v' + ext[1] + ')' if ext else 'NOT FOUND'}")

        # 2. Inspect Tables
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = [r[0] for r in cur.fetchall()]
        print(f"Tables in public schema ({len(tables)}): {tables}")

        # 3. Inspect Indexes
        cur.execute("""
            SELECT indexname, tablename 
            FROM pg_indexes 
            WHERE schemaname = 'public' AND indexname LIKE 'idx_%'
            ORDER BY indexname;
        """)
        indexes = cur.fetchall()
        print(f"Targeted Indexes ({len(indexes)}):")
        for idx, tbl in indexes:
            print(f"  - {idx} on {tbl}")

        # 4. Inspect Foreign Key Constraints
        cur.execute("""
            SELECT conname, conrelid::regclass AS table_name, confrelid::regclass AS foreign_table
            FROM pg_constraint
            WHERE contype = 'f' AND connamespace = 'public'::regnamespace
            ORDER BY conname;
        """)
        fks = cur.fetchall()
        print(f"Foreign Key Constraints ({len(fks)}):")
        for con, tbl, ftbl in fks:
            print(f"  - {con}: {tbl} -> {ftbl}")

        # 5. Inspect Initial Table Row Counts (Must all be 0 in Level 3C)
        print("\n--- Initial Table Row Counts (Level 3C Schema-Only) ---")
        expected_tables = [
            "product_category_name_translation",
            "customers",
            "products",
            "orders",
            "order_items",
            "order_payments",
            "customer_support_intents",
            "customer_demo_accounts",
        ]
        all_empty = True
        for t in expected_tables:
            cur.execute(f"SELECT COUNT(*) FROM {t};")
            cnt = cur.fetchone()[0]
            status = "EMPTY (0 rows)" if cnt == 0 else f"NON-EMPTY ({cnt} rows)"
            print(f"  - {t}: {cnt} rows [{status}]")
            if cnt != 0:
                all_empty = False

        if not all_empty:
            print("\nWARNING: Some tables are not empty!")
        else:
            print("\nSUCCESS: All tables are verified schema-only with 0 rows!")

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    apply_migration()
